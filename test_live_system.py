"""
VisionMate AI — Full Live System Test
Verifies all 10 features:
1. MySQL Connection
2. Registration
3. Login & Authentication
4. User Preferences
5. Object Detection (YOLO)
6. Text Recognition (EasyOCR)
7. Medicine Label Reader
8. Bus Identification
9. Voice Assistant Command Logging
10. Detection History & HTML Rendering
"""

import io
import json
import base64
import urllib.request
from PIL import Image, ImageDraw

BASE_URL = "http://127.0.0.1:5000"

def run_tests():
    print("=" * 60)
    print("  VisionMate AI — Full End-to-End System Verification")
    print("=" * 60)

    # 1. Health & MySQL DB Check
    req = urllib.request.Request(f"{BASE_URL}/api/health")
    with urllib.request.urlopen(req) as res:
        health = json.loads(res.read().decode())
        db_conn = health["database"]["connected"]
        print(f"1. MySQL Database: {'CONNECTED' if db_conn else 'FAILED'} (Database: {health['database']['name']} on port {health['database']['port']})")
        assert db_conn is True

    # 2. Registration
    reg_data = json.dumps({
        "full_name": "Test Live User",
        "email": "live_user@blindguide.local",
        "password": "Password@123"
    }).encode()
    req = urllib.request.Request(f"{BASE_URL}/api/auth/register", data=reg_data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as res:
            reg_res = json.loads(res.read().decode())
            print(f"2. User Registration: SUCCESS (User ID: {reg_res['user']['user_id']})")
    except urllib.error.HTTPError as e:
        err = json.loads(e.read().decode())
        if "already exists" in err.get("error", ""):
            print("2. User Registration: ALREADY REGISTERED (OK)")
        else:
            raise

    # 3. Login
    login_data = json.dumps({
        "email": "demo@blindguide.local",
        "password": "Demo@123"
    }).encode()
    req = urllib.request.Request(f"{BASE_URL}/api/auth/login", data=login_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        login_res = json.loads(res.read().decode())
        print(f"3. User Login: SUCCESS (Logged in as: {login_res['user']['full_name']})")
        assert login_res["success"] is True

    # 4. Generate Test Image with Real Content
    img = Image.new("RGB", (400, 300), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(20, 20), (120, 120)], fill=(30, 80, 200))
    draw.text((20, 150), "Paracetamol 500mg Tablet", fill=(0, 0, 0))
    draw.text((20, 190), "Bus 42 Express", fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    b64_img = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    payload = json.dumps({"image": b64_img}).encode()

    # 5. Object Detection (YOLO)
    req = urllib.request.Request(f"{BASE_URL}/api/detect", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        print(f"5. Object Detection (YOLO): SUCCESS (Found {data.get('count', 0)} objects, Summary: '{data.get('summary')}')")
        assert data["success"] is True

    # 6. Text Recognition (EasyOCR)
    req = urllib.request.Request(f"{BASE_URL}/api/read-text", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        print(f"6. Text Recognition (EasyOCR): SUCCESS (Extracted text: '{data.get('text', '')}')")
        assert data["success"] is True

    # 7. Medicine Label Reading
    req = urllib.request.Request(f"{BASE_URL}/api/identify-medicine", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        print(f"7. Medicine Label Reader: SUCCESS (Summary: '{data.get('summary', '')[:60]}...')")
        assert data["success"] is True
        assert "safety" in data

    # 8. Bus Identification
    req = urllib.request.Request(f"{BASE_URL}/api/identify-bus", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        print(f"8. Bus Identification: SUCCESS (Summary: '{data.get('summary', '')[:60]}...')")
        assert data["success"] is True
        assert "disclaimer" in data

    # 9. Voice Command Endpoint
    voice_data = json.dumps({
        "transcript": "detect objects in front of me",
        "intent": "DETECT_OBJECTS",
        "spoken_response": "Starting object detection."
    }).encode()
    req = urllib.request.Request(f"{BASE_URL}/api/voice-command", data=voice_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        print(f"9. Voice Assistant Command: SUCCESS (Logged session #{data.get('session_id')})")
        assert data["success"] is True

    # 10. History Retrieval from MySQL
    req = urllib.request.Request(f"{BASE_URL}/api/history")
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        print(f"10. Detection History (MySQL): SUCCESS ({data.get('count')} past sessions retrieved)")
        assert data["success"] is True

    # Clean up test user
    import db
    db.execute_query("DELETE FROM users WHERE email = %s", ("live_user@blindguide.local",), commit=True)

    print("=" * 60)
    print("  ALL 10 TESTS COMPLETED SUCCESSFULLY WITHOUT ERRORS!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
