"""
BlindGuide AI-Based — Flask Backend
AI-Powered Visual Assistance for Visually Impaired Users
Integrated with XAMPP MySQL Database (ai_blind_guide)
"""

import os
import io
import time
import logging
import base64
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename

# Database integration
import db

# Graceful imports — AI packages may not be installed yet
try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False
    cv2 = None
    np = None

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("BlindGuideAI")

# ── App config ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "blindguide-ai-based-secret-key-2026-secure")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024   # 10 MB upload limit
app.config["ALLOWED_EXTENSIONS"] = {"jpg", "jpeg", "png", "webp"}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── CORS & Global Response Headers ───────────────────────────────────────────
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

# ── Lazy-loaded AI models ─────────────────────────────────────────────────────
_yolo_model = None
_ocr_reader = None
_models_loaded = False
_model_error   = None


def get_yolo():
    global _yolo_model
    if _yolo_model is None:
        from ultralytics import YOLO
        log.info("Loading YOLOv8n …")
        yolo_path = os.path.join(BASE_DIR, "yolov8n.pt")
        _yolo_model = YOLO(yolo_path)
        log.info("YOLOv8n ready.")
    return _yolo_model


def get_ocr():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        log.info("Loading EasyOCR …")
        _ocr_reader = easyocr.Reader(["en"], gpu=False)
        log.info("EasyOCR ready.")
    return _ocr_reader


# ── Helpers ───────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )


def decode_image(file_storage):
    """Decode an uploaded FileStorage object to an OpenCV BGR array."""
    data = file_storage.read()
    arr  = np.frombuffer(data, np.uint8)
    img  = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image.")
    return img


def decode_base64_image(b64_string: str):
    """Decode a base64-encoded image (from canvas capture) to OpenCV array."""
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    raw = base64.b64decode(b64_string)
    arr = np.frombuffer(raw, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode base64 image.")
    return img


def position_label(x_center: float, img_width: int) -> str:
    """Return a human-readable horizontal position (left / center / right)."""
    ratio = x_center / img_width
    if ratio < 0.33:
        return "left"
    elif ratio > 0.67:
        return "right"
    else:
        return "center"


def get_image_and_source():
    """
    Try to get an image from the request in two ways:
    1. File upload  (multipart/form-data field 'image') -> source 'UPLOAD'
    2. Base-64 JSON (application/json field 'image')    -> source 'CAMERA'
    Returns (img_array, input_source_str)
    """
    if "image" in request.files:
        f = request.files["image"]
        if f.filename == "":
            raise ValueError("No file selected.")
        if not allowed_file(f.filename):
            raise ValueError("Unsupported file type. Use JPG, PNG, or WebP.")
        # If filename indicates canvas snapshot, tag as CAMERA, else UPLOAD
        source = "CAMERA" if "capture" in f.filename.lower() else "UPLOAD"
        return decode_image(f), source

    data = request.get_json(silent=True) or {}
    if "image" in data:
        return decode_base64_image(data["image"]), "CAMERA"

    raise ValueError("No image provided in request.")


def get_image_from_request():
    """Backward compatibility helper."""
    img, _ = get_image_and_source()
    return img


# ── Page Routes ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    db_ok, db_msg = db.test_connection()
    return jsonify({
        "status": "ok",
        "server": "BlindGuide AI-Based",
        "version": "2.0.0",
        "timestamp": time.time(),
        "ai_ready": _CV2_AVAILABLE,
        "database": {
            "connected": db_ok,
            "message": db_msg,
            "name": db.DB_NAME,
            "host": db.DB_HOST,
            "port": db.DB_PORT,
        }
    })


# ── Database & User Authentication Routes ──────────────────────────────────────

@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(silent=True) or request.form
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    success, result = db.register_user(full_name, email, password)
    if not success:
        return jsonify({"success": False, "error": result}), 400

    # Auto log-in on successful registration
    session["user_id"] = result["user_id"]
    session["user_name"] = result["full_name"]
    session["user_email"] = result["email"]

    return jsonify({
        "success": True,
        "message": f"Welcome, {result['full_name']}! Registration successful.",
        "user": result
    })


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or request.form
    email = data.get("email", "").strip()
    password = data.get("password", "")

    success, result = db.authenticate_user(email, password)
    if not success:
        return jsonify({"success": False, "error": result}), 401

    session["user_id"] = result["user_id"]
    session["user_name"] = result["full_name"]
    session["user_email"] = result["email"]

    return jsonify({
        "success": True,
        "message": f"Welcome back, {result['full_name']}!",
        "user": result
    })


@app.route("/api/auth/logout", methods=["POST", "GET"])
def auth_logout():
    user_id = session.get("user_id")
    if user_id:
        db.log_activity(user_id=user_id, action="USER_LOGOUT", details="User logged out")
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": True, "authenticated": False, "user": None})

    user = db.get_user_profile(user_id)
    if not user:
        session.clear()
        return jsonify({"success": True, "authenticated": False, "user": None})

    return jsonify({
        "success": True,
        "authenticated": True,
        "user": user
    })


@app.route("/api/user/preferences", methods=["GET", "POST"])
def user_preferences():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "Authentication required"}), 401

    if request.method == "GET":
        profile = db.get_user_profile(user_id)
        if not profile:
            return jsonify({"success": False, "error": "User not found"}), 404
        return jsonify({"success": True, "preferences": profile.get("preferences", {})})

    # POST - update preferences
    data = request.get_json(silent=True) or request.form
    lang = data.get("language_code")
    speech_on = data.get("speech_enabled")
    speech_rate = data.get("speech_rate")
    high_contrast = data.get("high_contrast_mode")

    success, msg = db.update_user_preferences(
        user_id=user_id,
        language_code=lang,
        speech_enabled=speech_on,
        speech_rate=speech_rate,
        high_contrast_mode=high_contrast
    )
    if not success:
        return jsonify({"success": False, "error": msg}), 500

    profile = db.get_user_profile(user_id)
    return jsonify({
        "success": True,
        "message": msg,
        "preferences": profile.get("preferences", {}) if profile else {}
    })


@app.route("/api/history", methods=["GET"])
def get_history():
    user_id = session.get("user_id")
    limit = request.args.get("limit", default=20, type=int)
    history = db.get_detection_history(user_id=user_id, limit=min(limit, 50))
    return jsonify({
        "success": True,
        "count": len(history),
        "history": history
    })


@app.route("/api/voice-command", methods=["POST"])
def log_voice_command():
    data = request.get_json(silent=True) or {}
    transcript = data.get("transcript", "").strip()
    intent = data.get("intent", "UNKNOWN")
    spoken = data.get("spoken_response", "")

    user_id = session.get("user_id")
    sid = db.start_detection_session(user_id=user_id, feature_type="VOICE_COMMAND", input_source="VOICE")
    if sid:
        db.finish_detection_session(
            session_id=sid,
            status="COMPLETED",
            processing_time_ms=50,
            results=[{
                "result_type": "VOICE_INTENT",
                "result_text": transcript or intent,
                "confidence": 1.0,
                "spoken_response": spoken or transcript
            }],
            user_id=user_id
        )
    return jsonify({"success": True, "session_id": sid})


# ── Object Detection ──────────────────────────────────────────────────────────

@app.route("/api/detect", methods=["POST"])
def detect_objects():
    if not _CV2_AVAILABLE:
        return jsonify({"success": False, "error": "AI packages not installed. Run: python -m pip install -r requirements.txt"}), 503

    t0 = time.time()
    user_id = session.get("user_id")
    sid = None

    try:
        img, source = get_image_and_source()
        sid = db.start_detection_session(user_id=user_id, feature_type="OBJECT_DETECTION", input_source=source)

        model = get_yolo()
        h, w = img.shape[:2]

        results = model(img, conf=0.40, verbose=False)[0]

        detections = []
        db_results = []

        for box in results.boxes:
            cls_id     = int(box.cls[0])
            label      = model.names[cls_id]
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = map(float, box.xyxy[0])
            x_center   = (x1 + x2) / 2
            position   = position_label(x_center, w)

            detections.append({
                "label":      label,
                "confidence": round(confidence * 100, 1),
                "position":   position,
                "bbox":       [round(x1), round(y1), round(x2), round(y2)],
            })

            db_results.append({
                "result_type": "OBJECT",
                "result_text": f"{label} detected on {position}",
                "confidence": confidence,
                "spoken_response": f"{label} on the {position}"
            })

        # Sort by confidence descending
        detections.sort(key=lambda d: d["confidence"], reverse=True)

        if not detections:
            summary = "No objects were detected in the image."
            db_results.append({
                "result_type": "OBJECT",
                "result_text": "No objects detected",
                "confidence": 1.0,
                "spoken_response": summary
            })
        else:
            parts = []
            for d in detections[:5]:
                parts.append(
                    f"{d['label']} ({d['confidence']}%) on the {d['position']}"
                )
            summary = "Detected: " + ", ".join(parts) + "."

        duration_ms = int((time.time() - t0) * 1000)
        db.finish_detection_session(
            session_id=sid,
            status="COMPLETED",
            processing_time_ms=duration_ms,
            results=db_results,
            user_id=user_id
        )

        return jsonify({
            "success": True,
            "feature": "Object Detection",
            "detections": detections,
            "summary": summary,
            "count": len(detections),
            "session_id": sid,
        })

    except Exception as e:
        log.exception("Object detection error")
        duration_ms = int((time.time() - t0) * 1000)
        if sid:
            db.finish_detection_session(
                session_id=sid,
                status="FAILED",
                processing_time_ms=duration_ms,
                error_message=str(e),
                user_id=user_id
            )
        return jsonify({"success": False, "error": str(e)}), 500


# ── Text Reader ───────────────────────────────────────────────────────────────

@app.route("/api/read-text", methods=["POST"])
def read_text():
    t0 = time.time()
    user_id = session.get("user_id")
    sid = None

    try:
        img, source = get_image_and_source()
        sid = db.start_detection_session(user_id=user_id, feature_type="TEXT_RECOGNITION", input_source=source)

        reader = get_ocr()

        # EasyOCR expects RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        raw     = reader.readtext(img_rgb, detail=1, paragraph=False)

        lines = []
        db_results = []

        for (_, text, conf) in raw:
            text = text.strip()
            if text and conf >= 0.30:
                c_val = float(conf)
                lines.append({"text": text, "confidence": round(c_val * 100, 1)})
                db_results.append({
                    "result_type": "OCR_TEXT",
                    "result_text": text,
                    "confidence": c_val,
                    "spoken_response": text
                })

        full_text = " ".join(item["text"] for item in lines)

        if not full_text.strip():
            summary = "No readable text was found in the image."
            db_results.append({
                "result_type": "OCR_TEXT",
                "result_text": "No text detected",
                "confidence": 1.0,
                "spoken_response": summary
            })
        else:
            summary = full_text

        duration_ms = int((time.time() - t0) * 1000)
        db.finish_detection_session(
            session_id=sid,
            status="COMPLETED",
            processing_time_ms=duration_ms,
            results=db_results,
            user_id=user_id
        )

        return jsonify({
            "success": True,
            "feature": "Text Reader",
            "lines":   lines,
            "text":    full_text,
            "summary": summary,
            "session_id": sid,
        })

    except Exception as e:
        log.exception("Text reader error")
        duration_ms = int((time.time() - t0) * 1000)
        if sid:
            db.finish_detection_session(
                session_id=sid,
                status="FAILED",
                processing_time_ms=duration_ms,
                error_message=str(e),
                user_id=user_id
            )
        return jsonify({"success": False, "error": str(e)}), 500


# ── Medicine Label Reader ─────────────────────────────────────────────────────

@app.route("/api/identify-medicine", methods=["POST"])
def identify_medicine():
    t0 = time.time()
    user_id = session.get("user_id")
    sid = None

    try:
        img, source = get_image_and_source()
        sid = db.start_detection_session(user_id=user_id, feature_type="MEDICINE_LABEL_READING", input_source=source)

        reader = get_ocr()

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        raw     = reader.readtext(img_rgb, detail=1, paragraph=False)

        lines = []
        for (_, text, conf) in raw:
            text = text.strip()
            if text:
                c_val = float(conf)
                lines.append({
                    "text":       text,
                    "confidence": round(c_val * 100, 1),
                    "uncertain":  bool(c_val < 0.50),
                })

        full_text = " ".join(item["text"] for item in lines)

        if not full_text.strip():
            summary = (
                "No text could be extracted from this image. "
                "Please ensure the label is in focus and well-lit, "
                "then try again."
            )
        else:
            summary = (
                f"Label text extracted: {full_text}. "
                "Please verify this information with a pharmacist before use."
            )

        safety = (
            "⚠️ IMPORTANT: This tool extracts printed text only. "
            "It cannot identify medicines from appearance, verify dosage, "
            "or confirm whether a medicine is safe for you. "
            "Always verify the label with a licensed pharmacist."
        )

        avg_conf = None
        if lines:
            avg_conf = sum(l["confidence"] for l in lines) / (len(lines) * 100.0)

        db_results = [{
            "result_type": "MEDICINE_TEXT",
            "result_text": full_text if full_text else "No label text extracted",
            "confidence": avg_conf,
            "spoken_response": summary
        }]

        duration_ms = int((time.time() - t0) * 1000)
        db.finish_detection_session(
            session_id=sid,
            status="COMPLETED",
            processing_time_ms=duration_ms,
            results=db_results,
            user_id=user_id
        )

        return jsonify({
            "success":   True,
            "feature":   "Medicine Label Reader",
            "lines":     lines,
            "text":      full_text,
            "summary":   summary,
            "safety":    safety,
            "session_id": sid,
        })

    except Exception as e:
        log.exception("Medicine identification error")
        duration_ms = int((time.time() - t0) * 1000)
        if sid:
            db.finish_detection_session(
                session_id=sid,
                status="FAILED",
                processing_time_ms=duration_ms,
                error_message=str(e),
                user_id=user_id
            )
        return jsonify({"success": False, "error": str(e)}), 500


# ── Bus Identification ────────────────────────────────────────────────────────

@app.route("/api/identify-bus", methods=["POST"])
def identify_bus():
    t0 = time.time()
    user_id = session.get("user_id")
    sid = None

    try:
        img, source = get_image_and_source()
        sid = db.start_detection_session(user_id=user_id, feature_type="BUS_IDENTIFICATION", input_source=source)

        model = get_yolo()
        h, w  = img.shape[:2]

        results = model(img, conf=0.35, verbose=False)[0]

        bus_detections = []
        bus_classes    = {"bus"}          # COCO class name

        for box in results.boxes:
            cls_id = int(box.cls[0])
            label  = model.names[cls_id].lower()
            if label in bus_classes:
                conf_val = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                bus_detections.append({
                    "confidence": round(conf_val * 100, 1),
                    "bbox":       [x1, y1, x2, y2],
                })

        ocr_texts   = []
        route_guess = None

        if bus_detections:
            reader = get_ocr()
            best = max(bus_detections, key=lambda d: d["confidence"])
            x1, y1, x2, y2 = best["bbox"]

            band_h  = max(1, int((y2 - y1) * 0.35))
            crop    = img[y1 : y1 + band_h, x1 : x2]

            if crop.size > 0:
                crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                raw      = reader.readtext(crop_rgb, detail=1, paragraph=False)
                for (_, text, conf) in raw:
                    text = text.strip()
                    if text and conf >= 0.25:
                        ocr_texts.append({
                            "text":       text,
                            "confidence": round(float(conf) * 100, 1),
                        })

            if ocr_texts:
                route_guess = " ".join(t["text"] for t in ocr_texts)

        # Build summary
        if not bus_detections:
            summary = "No bus was detected in the image."
            board   = "No bus detected."
            best_conf = None
        else:
            n       = len(bus_detections)
            conf    = bus_detections[0]["confidence"]
            best_conf = float(conf) / 100.0
            summary = f"{n} bus{'es' if n > 1 else ''} detected (confidence {conf}%). "
            if route_guess:
                summary += (
                    f"Possible route board text: \"{route_guess}\". "
                    "Please verify the route with the driver before boarding."
                )
                board = route_guess
            else:
                summary += (
                    "Route board text could not be read. "
                    "Please verify the route with the driver or official display."
                )
                board = "Route not recognized."

        disclaimer = (
            "⚠️ Always confirm the bus route and destination with the driver "
            "or an official display before boarding."
        )

        db_results = [{
            "result_type": "BUS",
            "result_text": f"Bus: {board}",
            "confidence": best_conf,
            "spoken_response": summary
        }]

        duration_ms = int((time.time() - t0) * 1000)
        db.finish_detection_session(
            session_id=sid,
            status="COMPLETED",
            processing_time_ms=duration_ms,
            results=db_results,
            user_id=user_id
        )

        return jsonify({
            "success":    True,
            "feature":    "Bus Identification",
            "buses":      bus_detections,
            "bus_count":  len(bus_detections),
            "ocr_texts":  ocr_texts,
            "route_text": route_guess,
            "board":      board,
            "summary":    summary,
            "disclaimer": disclaimer,
            "session_id": sid,
        })

    except Exception as e:
        log.exception("Bus identification error")
        duration_ms = int((time.time() - t0) * 1000)
        if sid:
            db.finish_detection_session(
                session_id=sid,
                status="FAILED",
                processing_time_ms=duration_ms,
                error_message=str(e),
                user_id=user_id
            )
        return jsonify({"success": False, "error": str(e)}), 500


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Starting VisionMate AI server …")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
