# VisionMate AI

**An AI-powered visual assistance web application for visually impaired users.**

VisionMate AI helps blind and visually impaired people by providing:

- **Object Detection** — Identifies everyday objects using YOLOv8n
- **Text Reader** — Extracts printed text using EasyOCR
- **Medicine Label Reader** — Reads medicine packaging text (with safety notice)
- **Bus Identification** — Detects buses and attempts to read route boards
- **Voice Assistant** — Voice commands and text-to-speech output
- **Camera integration** — Live camera preview + image capture

---

## Project Structure

```
VisionMateAI/
├── app.py                  ← Flask backend (all AI endpoints)
├── requirements.txt        ← Python dependencies
├── README.md
├── templates/
│   └── index.html          ← Main dashboard (Jinja2 template)
├── static/
│   ├── css/
│   │   └── style.css       ← Complete styling
│   ├── js/
│   │   └── app.js          ← All frontend logic
│   └── images/
│       └── logo.svg        ← Application logo
└── tests/
    └── test_api.py         ← Pytest test suite
```

---

## Windows Setup & Execution

### Prerequisites

- **Python 3.9 – 3.11** (recommended: 3.10)
  Download from: https://www.python.org/downloads/
- **pip** (bundled with Python)

### Step 1 — Open Command Prompt in the project folder

```cmd
cd "c:\xampp\project\htdocs\blind guide"
```

### Step 2 — Create and activate a virtual environment (recommended)

```cmd
python -m venv venv
venv\Scripts\activate
```

### Step 3 — Install dependencies

```cmd
pip install -r requirements.txt
```

> **Note:** The first installation downloads PyTorch (≈ 1 GB) and EasyOCR model files.
> Ensure you have a stable internet connection.

### Step 4 — Run the Flask server

```cmd
python app.py
```

Expected output:
```
INFO - Starting VisionMate AI server …
 * Running on http://0.0.0.0:5000
```

### Step 5 — Open the application

Open your browser and navigate to:

```
http://127.0.0.1:5000
```

---

## Using the Application

### Camera Input
1. Click **Start Camera** — browser will request camera permission.
2. Allow camera access.
3. Click **Capture** to freeze a frame for AI analysis.

### Image Upload
1. Click **Upload Image** and select a JPG, PNG, or WebP file (max 10 MB).

### AI Features
After loading an image, click any of the four feature cards:

| Button | Shortcut | Description |
|--------|----------|-------------|
| Detect Objects | `D` | YOLOv8n object detection |
| Read Text | `T` | EasyOCR text extraction |
| Read Label | `M` | Medicine packaging OCR |
| Identify Bus | `B` | Bus detection + route OCR |

### Voice Commands
Click the **microphone button** (or press `Space`) and say:
- *"Detect objects"*
- *"Read text"*
- *"Identify medicine"*
- *"Identify bus"*
- *"Repeat result"*
- *"Stop speaking"*

> Voice recognition requires **Chrome** or **Edge**.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `D` | Object Detection |
| `T` | Read Text |
| `M` | Medicine Label |
| `B` | Bus Identification |
| `Space` | Toggle Microphone |
| `S` | Speak Results |
| `X` | Stop Speaking |
| `C` | Capture from Camera |
| `Esc` | Close Help Dialog |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serve the dashboard |
| GET | `/api/health` | Server health status |
| POST | `/api/detect` | Object detection (YOLOv8n) |
| POST | `/api/read-text` | Text extraction (EasyOCR) |
| POST | `/api/identify-medicine` | Medicine label OCR |
| POST | `/api/identify-bus` | Bus detection + route OCR |

All POST endpoints accept `multipart/form-data` with an `image` field,
or `application/json` with a base64-encoded `image` field.

### Example JSON response (detect)
```json
{
  "success": true,
  "feature": "Object Detection",
  "count": 2,
  "detections": [
    { "label": "person", "confidence": 91.3, "position": "center", "bbox": [120, 45, 340, 480] },
    { "label": "chair",  "confidence": 76.8, "position": "right",  "bbox": [360, 200, 520, 450] }
  ],
  "summary": "Detected: person (91.3%) on the center, chair (76.8%) on the right."
}
```

---

## Running Tests

```cmd
pip install pytest
python -m pytest tests/ -v
```

---

## Known Limitations & Notes

### First Run
- YOLOv8n model weights (`yolov8n.pt`, ≈ 6 MB) are auto-downloaded by Ultralytics.
- EasyOCR downloads its language models on first use (≈ 200 MB). Internet required.

### Medicine Label Reader
- **Text extraction only.** This tool reads printed text from images.
- It cannot identify loose pills, verify dosage, or confirm safety.
- **Always verify with a licensed pharmacist before use.**

### Bus Identification
- Bus detection uses YOLOv8n (COCO dataset). COCO includes a `bus` class.
- Route board OCR crops the upper portion of the detected bus region.
- OCR accuracy depends heavily on image clarity, angle, and lighting.
- **Always verify the route with the driver before boarding.**

### Voice Recognition
- Requires Chrome 33+ or Edge 79+. Not supported in Firefox.
- Microphone permission must be granted.

### GPU Acceleration
- By default, all models run on CPU.
- For faster inference, install `torch` with CUDA and change `gpu=False` to `gpu=True` in `app.py`.

### Camera on Mobile
- The app requests the rear/environment-facing camera automatically.
- Camera access requires HTTPS on most mobile browsers. Use a local HTTPS proxy (e.g., `ngrok`) for mobile testing.

---

## Safety Disclaimer

> AI predictions may be **incomplete or incorrect**. This application is a demonstration
> prototype intended for educational use. Do not rely solely on it for safety-critical
> decisions. Medical and transport information must always be verified with a qualified
> professional or official source.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Python 3, Flask |
| Object Detection | Ultralytics YOLOv8n |
| Image Processing | OpenCV |
| OCR | EasyOCR |
| Voice Output | Web Speech API (SpeechSynthesis) |
| Voice Input | Web Speech API (SpeechRecognition) |

---

*VisionMate AI — College Mini Project*
