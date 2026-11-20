/* ═══════════════════════════════════════════════════════════════════════════
   VisionMate AI — app.js
   Complete frontend logic: camera, uploads, AI API calls, TTS, voice commands,
   MySQL Database Authentication, User Preferences & Detection History.
   ═══════════════════════════════════════════════════════════════════════════ */

"use strict";

// ─── Constants ────────────────────────────────────────────────────────────────
const API = {
  health:      "/api/health",
  detect:      "/api/detect",
  readText:    "/api/read-text",
  medicine:    "/api/identify-medicine",
  bus:         "/api/identify-bus",
  register:    "/api/auth/register",
  login:       "/api/auth/login",
  logout:      "/api/auth/logout",
  me:          "/api/auth/me",
  preferences: "/api/user/preferences",
  history:     "/api/history",
  voiceCmd:    "/api/voice-command",
};

const STATUS = { ready: "Ready", camera: "Camera Active", processing: "Processing…", error: "Error" };

// ─── State ────────────────────────────────────────────────────────────────────
let cameraStream      = null;
let capturedImageBlob = null;   // Blob from canvas capture
let uploadedFile      = null;   // File from file-input
let voiceEnabled      = true;
let lastResultText    = "";
let isRecognizing     = false;
let isStartingMic     = false;
let recognition       = null;
let lastApiEndpoint   = null;
let lastApiLabel      = null;

let currentUser       = null;
let userPreferences   = {
  language_code: "en",
  speech_enabled: true,
  speech_rate: 1.0,
  high_contrast_mode: false
};

// ─── DOM refs ─────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const els = {
  // header
  historyBtn:     $("historyBtn"),
  authBtn:        $("authBtn"),
  authBtnLabel:   $("authBtnLabel"),
  voiceToggleBtn: $("voiceToggleBtn"),
  helpBtn:        $("helpBtn"),

  // status
  statusBadge: $("statusBadge"),
  statusDot:   $("statusDot"),
  statusText:  $("statusText"),

  // camera / upload
  startCameraBtn: $("startCameraBtn"),
  stopCameraBtn:  $("stopCameraBtn"),
  captureBtn:     $("captureBtn"),
  imageUpload:    $("imageUpload"),
  cameraVideo:    $("cameraVideo"),
  previewImage:   $("previewImage"),
  captureCanvas:  $("captureCanvas"),
  previewPlaceholder: $("previewPlaceholder"),
  cameraError:    $("cameraError"),
  cameraRetryBtn: $("cameraRetryBtn"),

  // features
  detectBtn:   $("detectBtn"),
  textBtn:     $("textBtn"),
  medicineBtn: $("medicineBtn"),
  busBtn:      $("busBtn"),

  // voice
  micBtn:           $("micBtn"),
  micLabel:         $("micLabel"),
  voiceStatus:      $("voiceStatus"),
  voiceStatusText:  $("voiceStatusText"),
  voiceRetryBtn:    $("voiceRetryBtn"),
  recognizedCmd:    $("recognizedCmd"),
  cmdText:          $("cmdText"),
  speechUnsupported: $("speechUnsupported"),

  // results
  loadingIndicator: $("loadingIndicator"),
  loadingText:      $("loadingText"),
  resultsPlaceholder: $("resultsPlaceholder"),
  resultsError:     $("resultsError"),
  resultsErrorText: $("resultsErrorText"),
  resultRetryBtn:   $("resultRetryBtn"),
  resultsBody:      $("resultsBody"),
  resultFeatureBadge: $("resultFeatureBadge"),
  resultTimestamp:  $("resultTimestamp"),
  resultSummary:    $("resultSummary"),
  resultDetails:    $("resultDetails"),
  resultSafety:     $("resultSafety"),
  speakControls:    $("speakControls"),
  speakBtn:         $("speakBtn"),
  repeatBtn:        $("repeatBtn"),
  stopSpeakBtn:     $("stopSpeakBtn"),

  // help modal
  helpModal:        $("helpModal"),
  closeHelpModal:   $("closeHelpModal"),
  modalBackdrop:    $("modalBackdrop"),

  // auth modal
  authModal:          $("authModal"),
  authModalBackdrop:  $("authModalBackdrop"),
  closeAuthModal:     $("closeAuthModal"),
  tabLogin:           $("tabLogin"),
  tabRegister:        $("tabRegister"),
  tabProfile:         $("tabProfile"),
  loginPanel:         $("loginPanel"),
  registerPanel:      $("registerPanel"),
  profilePanel:       $("profilePanel"),
  authAlert:          $("authAlert"),
  loginForm:          $("loginForm"),
  loginEmail:         $("loginEmail"),
  loginPassword:      $("loginPassword"),
  loginSubmitBtn:     $("loginSubmitBtn"),
  demoLoginBtn:       $("demoLoginBtn"),
  registerForm:       $("registerForm"),
  regName:            $("regName"),
  regEmail:           $("regEmail"),
  regPassword:        $("regPassword"),
  registerSubmitBtn:  $("registerSubmitBtn"),
  profileUserName:    $("profileUserName"),
  profileUserEmail:   $("profileUserEmail"),
  preferencesForm:    $("preferencesForm"),
  prefLanguage:       $("prefLanguage"),
  prefSpeechEnabled:  $("prefSpeechEnabled"),
  prefSpeechRate:     $("prefSpeechRate"),
  speechRateVal:      $("speechRateVal"),
  prefHighContrast:   $("prefHighContrast"),
  savePrefBtn:        $("savePrefBtn"),
  logoutBtn:          $("logoutBtn"),

  // history modal
  historyModal:         $("historyModal"),
  historyModalBackdrop: $("historyModalBackdrop"),
  closeHistoryModal:    $("closeHistoryModal"),
  refreshHistoryBtn:    $("refreshHistoryBtn"),
  historyList:          $("historyList"),
};

// ═══════════════════════════════════════════════════════════════════════════════
// STATUS HELPERS
// ═══════════════════════════════════════════════════════════════════════════════
function setStatus(state, text) {
  els.statusBadge.dataset.state = state;
  els.statusText.textContent     = text || STATUS[state] || state;
}

// ═══════════════════════════════════════════════════════════════════════════════
// SPEECH SYNTHESIS (TTS)
// ═══════════════════════════════════════════════════════════════════════════════
function speak(text, interrupt = true) {
  if (!voiceEnabled || !userPreferences.speech_enabled) return;
  if (!("speechSynthesis" in window)) return;
  if (interrupt) window.speechSynthesis.cancel();
  const utt  = new SpeechSynthesisUtterance(text);
  utt.lang   = userPreferences.language_code === "en" ? "en-US" : (userPreferences.language_code || "en-US");
  utt.rate   = userPreferences.speech_rate || 1.0;
  utt.pitch  = 1.0;
  utt.volume = 1.0;
  window.speechSynthesis.speak(utt);
}

function stopSpeaking() {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}

// ═══════════════════════════════════════════════════════════════════════════════
// VOICE TOGGLE
// ═══════════════════════════════════════════════════════════════════════════════
els.voiceToggleBtn.addEventListener("click", () => {
  voiceEnabled = !voiceEnabled;
  userPreferences.speech_enabled = voiceEnabled;
  if (els.prefSpeechEnabled) els.prefSpeechEnabled.checked = voiceEnabled;
  els.voiceToggleBtn.setAttribute("aria-pressed", voiceEnabled.toString());
  els.voiceToggleBtn.querySelector(".btn-label").textContent = voiceEnabled ? "Voice On" : "Voice Off";
  if (!voiceEnabled) stopSpeaking();
  speak(voiceEnabled ? "Voice output enabled." : "Voice output disabled.");
});

// ═══════════════════════════════════════════════════════════════════════════════
// CAMERA
// ═══════════════════════════════════════════════════════════════════════════════
els.startCameraBtn.addEventListener("click", startCamera);
els.stopCameraBtn.addEventListener("click",  stopCamera);
els.captureBtn.addEventListener("click",    captureImage);
els.cameraRetryBtn?.addEventListener("click", startCamera);

async function startCamera() {
  hideError();
  if (els.cameraRetryBtn) els.cameraRetryBtn.style.display = "none";
  setStatus("camera");
  try {
    const constraints = {
      video: {
        facingMode: { ideal: "environment" },
        width:  { ideal: 1280 },
        height: { ideal: 720 },
      },
    };
    cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
    els.cameraVideo.srcObject = cameraStream;
    showElement(els.cameraVideo);
    hideElement(els.previewImage);
    hideElement(els.previewPlaceholder);

    els.startCameraBtn.disabled  = true;
    els.stopCameraBtn.disabled   = false;
    els.captureBtn.disabled      = false;

    speak("Camera started.");
  } catch (err) {
    setStatus("error");
    const msg = cameraErrMsg(err);
    showError(msg);
    if (els.cameraRetryBtn) els.cameraRetryBtn.style.display = "inline-block";
    speak("Camera error. " + msg);
  }
}

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach(t => t.stop());
    cameraStream = null;
  }
  els.cameraVideo.srcObject = null;
  hideElement(els.cameraVideo);
  showElement(els.previewPlaceholder);

  els.startCameraBtn.disabled = false;
  els.stopCameraBtn.disabled  = true;
  els.captureBtn.disabled     = true;

  setStatus("ready");
  speak("Camera stopped.");
}

function captureImage() {
  const video = els.cameraVideo;
  if (!video.srcObject) return;
  const canvas = els.captureCanvas;
  canvas.width  = video.videoWidth  || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0);

  canvas.toBlob(blob => {
    capturedImageBlob = blob;
    uploadedFile      = null;

    const url = URL.createObjectURL(blob);
    els.previewImage.src = url;
    showElement(els.previewImage);
    speak("Image captured.");
  }, "image/jpeg", 0.92);
}

function cameraErrMsg(err) {
  if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
    return "Camera permission denied. Please allow camera access in your browser address bar.";
  }
  if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
    return "No camera device found on this system.";
  }
  if (err.name === "NotReadableError" || err.name === "TrackStartError") {
    return "Camera is already in use by another application.";
  }
  return "Could not start camera: " + (err.message || err.toString());
}

// ═══════════════════════════════════════════════════════════════════════════════
// IMAGE UPLOAD
// ═══════════════════════════════════════════════════════════════════════════════
els.imageUpload.addEventListener("change", handleUpload);

function handleUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const allowed = ["image/jpeg", "image/jpg", "image/png", "image/webp"];
  if (!allowed.includes(file.type)) {
    showError("Unsupported file type. Please upload JPG, JPEG, PNG, or WebP.");
    speak("Unsupported file type.");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showError("File is too large. Maximum size is 10 MB.");
    speak("File too large.");
    return;
  }

  uploadedFile      = file;
  capturedImageBlob = null;
  hideError();

  const url = URL.createObjectURL(file);
  els.previewImage.src = url;
  showElement(els.previewImage);
  hideElement(els.previewPlaceholder);
  hideElement(els.cameraVideo);

  speak("Image loaded: " + file.name);
}

function buildFormData() {
  const fd = new FormData();
  if (uploadedFile) {
    fd.append("image", uploadedFile, uploadedFile.name);
    return fd;
  }
  if (capturedImageBlob) {
    fd.append("image", capturedImageBlob, "capture.jpg");
    return fd;
  }
  return null;
}

function hasImage() {
  return !!(uploadedFile || capturedImageBlob);
}

// ═══════════════════════════════════════════════════════════════════════════════
// AI API CALLS
// ═══════════════════════════════════════════════════════════════════════════════
function setProcessing(on) {
  if (on) {
    showElement(els.loadingIndicator);
    hideElement(els.resultsPlaceholder);
    hideElement(els.resultsBody);
    if (els.resultsError) els.resultsError.style.display = "none";
    els.speakControls.style.display = "none";
    setStatus("processing");
  } else {
    hideElement(els.loadingIndicator);
  }
  [els.detectBtn, els.textBtn, els.medicineBtn, els.busBtn].forEach(b => b.disabled = on);
}

async function callAPI(endpoint, label) {
  lastApiEndpoint = endpoint;
  lastApiLabel    = label;

  if (!hasImage()) {
    speak("Please load an image first, then try again.");
    showError("No image available. Start the camera and capture, or upload an image.");
    return;
  }

  setProcessing(true);
  els.loadingText.textContent = `Running ${label}…`;
  hideError();
  if (els.resultsError) els.resultsError.style.display = "none";

  try {
    const fd  = buildFormData();
    const res = await fetch(endpoint, { method: "POST", body: fd });
    const data = await res.json();
    setProcessing(false);

    if (data.success) {
      setStatus("ready");
      displayResult(data);
    } else {
      setStatus("error");
      const msg = data.error || "An error occurred.";
      showApiError(msg);
      speak("Error: " + msg);
    }
  } catch (err) {
    setProcessing(false);
    setStatus("error");
    const msg = "Could not connect to the server. Please ensure the Flask server is running on port 5000.";
    showApiError(msg);
    speak(msg);
    console.error(err);
  }
}

function showApiError(msg) {
  if (els.resultsError && els.resultsErrorText) {
    els.resultsErrorText.textContent = "AI Error: " + msg;
    els.resultsError.style.display = "block";
    hideElement(els.resultsPlaceholder);
    hideElement(els.resultsBody);
  }
}

els.resultRetryBtn?.addEventListener("click", () => {
  if (lastApiEndpoint && lastApiLabel) {
    callAPI(lastApiEndpoint, lastApiLabel);
  }
});

// Feature button listeners
els.detectBtn.addEventListener("click",   () => callAPI(API.detect,   "Object Detection"));
els.textBtn.addEventListener("click",     () => callAPI(API.readText,  "Text Reader"));
els.medicineBtn.addEventListener("click", () => callAPI(API.medicine,  "Medicine Label Reader"));
els.busBtn.addEventListener("click",      () => callAPI(API.bus,       "Bus Identification"));

// ═══════════════════════════════════════════════════════════════════════════════
// RESULT DISPLAY
// ═══════════════════════════════════════════════════════════════════════════════
function displayResult(data) {
  els.resultFeatureBadge.textContent = data.feature || "AI Result";
  els.resultTimestamp.textContent    = new Date().toLocaleTimeString();

  els.resultSummary.textContent = data.summary || "No summary available.";
  lastResultText = data.summary || "";

  els.resultDetails.innerHTML = buildDetailsHTML(data);

  const safety = data.safety || data.disclaimer || null;
  if (safety) {
    els.resultSafety.textContent = safety;
    els.resultSafety.style.display = "block";
  } else {
    els.resultSafety.style.display = "none";
  }

  showElement(els.resultsBody);
  hideElement(els.resultsPlaceholder);
  if (els.resultsError) els.resultsError.style.display = "none";
  els.speakControls.style.display = "flex";

  speak(data.summary || "Results ready.");
  if (safety) speak(safety, false);
}

function buildDetailsHTML(data) {
  const feature = (data.feature || "").toLowerCase();

  /* Object Detection */
  if (feature.includes("object") && data.detections) {
    if (!data.detections.length) return "<p class='text-muted'>No objects detected.</p>";
    let rows = data.detections.map(d => `
      <tr>
        <td>${esc(capitalize(d.label))}</td>
        <td>${esc(capitalize(d.position))}</td>
        <td>
          <div class="confidence-bar-wrap">
            <div class="confidence-bar"><div class="confidence-fill" style="width:${d.confidence}%"></div></div>
            <span class="conf-label">${d.confidence}%</span>
          </div>
        </td>
      </tr>`).join("");
    return `<table>
      <thead><tr><th>Object</th><th>Position</th><th>Confidence</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  }

  /* Text Reader */
  if (feature.includes("text reader") && data.lines) {
    if (!data.lines.length) return "<p>No text lines extracted.</p>";
    let html = "<table><thead><tr><th>Text</th><th>Confidence</th></tr></thead><tbody>";
    data.lines.forEach(l => {
      html += `<tr>
        <td>${esc(l.text)}</td>
        <td><div class="confidence-bar-wrap">
          <div class="confidence-bar"><div class="confidence-fill" style="width:${l.confidence}%"></div></div>
          <span class="conf-label">${l.confidence}%</span>
        </div></td>
      </tr>`;
    });
    html += "</tbody></table>";
    return html;
  }

  /* Medicine Label */
  if (feature.includes("medicine") && data.lines) {
    if (!data.lines.length) return "<p>No label text extracted.</p>";
    let html = "<table><thead><tr><th>Extracted Text</th><th>Status</th><th>Confidence</th></tr></thead><tbody>";
    data.lines.forEach(l => {
      const tag = l.uncertain
        ? `<span class="tag-uncertain">⚠ Uncertain</span>`
        : `<span style="color:var(--success);font-size:var(--fs-xs);font-weight:600;">✓ OK</span>`;
      html += `<tr>
        <td>${esc(l.text)}</td>
        <td>${tag}</td>
        <td><div class="confidence-bar-wrap">
          <div class="confidence-bar"><div class="confidence-fill" style="width:${l.confidence}%"></div></div>
          <span class="conf-label">${l.confidence}%</span>
        </div></td>
      </tr>`;
    });
    html += "</tbody></table>";
    return html;
  }

  /* Bus Identification */
  if (feature.includes("bus")) {
    let html = "";
    if (data.bus_count > 0) {
      html += `<p style="margin-bottom:10px;color:var(--text-secondary)">
        <strong style="color:var(--text-primary)">${data.bus_count}</strong> bus${data.bus_count > 1 ? "es" : ""} detected.
      </p>`;
      if (data.route_text) {
        html += `<p style="margin-bottom:12px;">
          <strong>Route board text:</strong>
          <span style="color:var(--cyan-400);font-size:var(--fs-md);font-weight:700;"> ${esc(data.route_text)}</span>
        </p>`;
      } else {
        html += `<p style="color:var(--warning);margin-bottom:12px;">Route board text could not be read from the image.</p>`;
      }
    }
    if (data.ocr_texts && data.ocr_texts.length) {
      html += "<table><thead><tr><th>OCR Text</th><th>Confidence</th></tr></thead><tbody>";
      data.ocr_texts.forEach(t => {
        html += `<tr>
          <td>${esc(t.text)}</td>
          <td><div class="confidence-bar-wrap">
            <div class="confidence-bar"><div class="confidence-fill" style="width:${t.confidence}%"></div></div>
            <span class="conf-label">${t.confidence}%</span>
          </div></td>
        </tr>`;
      });
      html += "</tbody></table>";
    }
    return html || "<p>No additional details.</p>";
  }

  return "";
}

// ═══════════════════════════════════════════════════════════════════════════════
// SPEAK CONTROLS
// ═══════════════════════════════════════════════════════════════════════════════
els.speakBtn.addEventListener("click",     () => speak(lastResultText));
els.repeatBtn.addEventListener("click",    () => speak(lastResultText));
els.stopSpeakBtn.addEventListener("click", () => stopSpeaking());

// ═══════════════════════════════════════════════════════════════════════════════
// VOICE ASSISTANT (SPEECH-TO-TEXT & VOICE COMMANDS)
// ═══════════════════════════════════════════════════════════════════════════════
(function initSpeechRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    els.speechUnsupported.style.display = "block";
    els.micBtn.disabled = true;
    return;
  }

  recognition = new SR();
  recognition.lang = userPreferences.language_code === "en" ? "en-US" : (userPreferences.language_code || "en-US");
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 3;

  recognition.onstart = () => {
    isRecognizing = true;
    isStartingMic = false;
    els.micBtn.classList.add("listening");
    els.micBtn.setAttribute("aria-pressed", "true");
    els.micLabel.textContent = "Listening…";
    els.voiceStatusText.textContent = "Listening… speak your command now.";
    if (els.voiceRetryBtn) els.voiceRetryBtn.style.display = "none";
  };

  recognition.onresult = e => {
    if (!e.results || !e.results[0] || !e.results[0][0]) return;
    const transcript = e.results[0][0].transcript.trim().toLowerCase();
    handleVoiceCommand(transcript);
  };

  recognition.onerror = e => {
    stopListening();
    let msg = "Voice recognition error.";
    if (e.error === "not-allowed" || e.error === "permission-denied") {
      msg = "Microphone access was denied. Please allow microphone access in your browser address bar.";
    } else if (e.error === "audio-capture") {
      msg = "No microphone was found or the microphone is busy.";
    } else if (e.error === "network") {
      msg = "Speech recognition network error. Please check your internet connection.";
    } else if (e.error === "no-speech") {
      msg = "No speech detected. Please tap the microphone and try again.";
    } else if (e.error === "aborted") {
      return; // Silently ignore user abort
    }
    els.voiceStatusText.textContent = msg;
    if (els.voiceRetryBtn) els.voiceRetryBtn.style.display = "inline-block";
    speak(msg);
  };

  recognition.onend = () => stopListening();

  els.micBtn.addEventListener("click", toggleMic);
  els.voiceRetryBtn?.addEventListener("click", toggleMic);
})();

async function toggleMic() {
  if (!recognition) return;
  if (isRecognizing) {
    stopListening();
    try { recognition.stop(); } catch (_) {}
    return;
  }

  if (isStartingMic) return; // Prevent double trigger
  isStartingMic = true;

  // Stop any active TTS speaking before listening
  stopSpeaking();

  if (els.voiceRetryBtn) els.voiceRetryBtn.style.display = "none";
  els.voiceStatusText.textContent = "Requesting microphone permission…";

  // Pre-flight microphone permission check
  try {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Release test audio stream immediately
      stream.getTracks().forEach(t => t.stop());
    }
  } catch (err) {
    isStartingMic = false;
    let msg = "Microphone permission denied. Please allow microphone access in your browser address bar.";
    els.voiceStatusText.textContent = msg;
    if (els.voiceRetryBtn) els.voiceRetryBtn.style.display = "inline-block";
    speak(msg);
    return;
  }

  try {
    recognition.start();
  } catch (err) {
    isStartingMic = false;
    if (err.name === "InvalidStateError") {
      // Recognition was already active, restart cleanly
      try { recognition.stop(); } catch (_) {}
      setTimeout(() => {
        try { recognition.start(); } catch (_) {}
      }, 200);
    }
  }
}

function stopListening() {
  isRecognizing = false;
  isStartingMic = false;
  els.micBtn.classList.remove("listening");
  els.micBtn.setAttribute("aria-pressed", "false");
  els.micLabel.textContent = "Tap to Speak";
  els.voiceStatusText.textContent = "Say a command after pressing the microphone button.";
}

function handleVoiceCommand(transcript) {
  els.cmdText.textContent = transcript;
  showElement(els.recognizedCmd);

  const cmd = transcript.toLowerCase();
  let intent = "UNKNOWN";

  if (cmd.includes("detect") || cmd.includes("object") || cmd.includes("what do you see") || cmd.includes("look")) {
    intent = "DETECT_OBJECTS";
    speak("Starting object detection.");
    callAPI(API.detect, "Object Detection");
  } else if (cmd.includes("read text") || cmd.includes("text") || cmd.includes("read words") || cmd.includes("read book")) {
    intent = "READ_TEXT";
    speak("Reading text from image.");
    callAPI(API.readText, "Text Reader");
  } else if (cmd.includes("medicine") || cmd.includes("pill") || cmd.includes("tablet") || cmd.includes("prescription") || cmd.includes("label")) {
    intent = "IDENTIFY_MEDICINE";
    speak("Reading medicine packaging label.");
    callAPI(API.medicine, "Medicine Label Reader");
  } else if (cmd.includes("bus") || cmd.includes("route") || cmd.includes("transit") || cmd.includes("transport")) {
    intent = "IDENTIFY_BUS";
    speak("Identifying bus and reading route board.");
    callAPI(API.bus, "Bus Identification");
  } else if (cmd.includes("start camera") || cmd.includes("open camera") || cmd.includes("turn on camera")) {
    intent = "START_CAMERA";
    speak("Starting camera.");
    startCamera();
  } else if (cmd.includes("stop camera") || cmd.includes("close camera") || cmd.includes("turn off camera")) {
    intent = "STOP_CAMERA";
    speak("Stopping camera.");
    stopCamera();
  } else if (cmd.includes("capture") || cmd.includes("take photo") || cmd.includes("take picture") || cmd.includes("snap")) {
    intent = "CAPTURE_IMAGE";
    speak("Capturing frame.");
    captureImage();
  } else if (cmd.includes("repeat") || cmd.includes("say again")) {
    intent = "REPEAT_RESULT";
    speak(lastResultText || "No previous result to repeat.");
  } else if (cmd.includes("stop speaking") || cmd.includes("stop") || cmd.includes("quiet") || cmd.includes("silence") || cmd.includes("mute")) {
    intent = "STOP_SPEAKING";
    stopSpeaking();
  } else if (cmd.includes("history")) {
    intent = "VIEW_HISTORY";
    speak("Opening detection history.");
    openHistoryModal();
    loadHistory();
  } else if (cmd.includes("account") || cmd.includes("login") || cmd.includes("sign in") || cmd.includes("profile")) {
    intent = "ACCOUNT";
    speak("Opening account settings.");
    els.authBtn?.click();
  } else if (cmd.includes("voice on") || cmd.includes("enable voice")) {
    intent = "VOICE_ON";
    voiceEnabled = true;
    userPreferences.speech_enabled = true;
    speak("Voice output enabled.");
  } else if (cmd.includes("voice off") || cmd.includes("disable voice")) {
    intent = "VOICE_OFF";
    voiceEnabled = false;
    userPreferences.speech_enabled = false;
    stopSpeaking();
  } else if (cmd.includes("help") || cmd.includes("shortcuts")) {
    intent = "HELP";
    speak("Opening keyboard shortcuts help.");
    openModal();
  } else {
    const msg = "Command not recognized. Try saying: detect objects, read text, identify medicine, identify bus, start camera, or capture image.";
    els.voiceStatusText.textContent = msg;
    speak(msg);
  }

  // Log voice command in MySQL session database
  try {
    fetch(API.voiceCmd, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcript: transcript, intent: intent, spoken_response: "Command: " + transcript })
    }).catch(() => {});
  } catch (_) {}
}

// ═══════════════════════════════════════════════════════════════════════════════
// USER AUTHENTICATION & PREFERENCES
// ═══════════════════════════════════════════════════════════════════════════════

function setAuthAlert(msg, type = "error") {
  if (!els.authAlert) return;
  if (!msg) {
    els.authAlert.style.display = "none";
    return;
  }
  els.authAlert.textContent = msg;
  els.authAlert.className = `auth-alert ${type}`;
  els.authAlert.style.display = "block";
}

function switchAuthTab(tab) {
  setAuthAlert("");
  [els.tabLogin, els.tabRegister, els.tabProfile].forEach(t => {
    if (t) {
      t.classList.remove("active");
      t.setAttribute("aria-selected", "false");
    }
  });
  [els.loginPanel, els.registerPanel, els.profilePanel].forEach(p => {
    if (p) p.style.display = "none";
  });

  if (tab === "login") {
    els.tabLogin.classList.add("active");
    els.tabLogin.setAttribute("aria-selected", "true");
    els.loginPanel.style.display = "block";
    els.loginEmail.focus();
  } else if (tab === "register") {
    els.tabRegister.classList.add("active");
    els.tabRegister.setAttribute("aria-selected", "true");
    els.registerPanel.style.display = "block";
    els.regName.focus();
  } else if (tab === "profile") {
    els.tabProfile.classList.add("active");
    els.tabProfile.setAttribute("aria-selected", "true");
    els.profilePanel.style.display = "block";
  }
}

els.tabLogin?.addEventListener("click", () => switchAuthTab("login"));
els.tabRegister?.addEventListener("click", () => switchAuthTab("register"));
els.tabProfile?.addEventListener("click", () => switchAuthTab("profile"));

els.authBtn?.addEventListener("click", () => {
  if (currentUser) {
    switchAuthTab("profile");
  } else {
    switchAuthTab("login");
  }
  openAuthModal();
});

els.closeAuthModal?.addEventListener("click", closeAuthModal);
els.authModalBackdrop?.addEventListener("click", closeAuthModal);

function openAuthModal() {
  els.authModal.style.display = "flex";
  document.body.style.overflow = "hidden";
}

function closeAuthModal() {
  els.authModal.style.display = "none";
  document.body.style.overflow = "";
}

// Demo account fill helper
els.demoLoginBtn?.addEventListener("click", () => {
  els.loginEmail.value = "demo@blindguide.local";
  els.loginPassword.value = "Demo@123";
  handleLogin();
});

// Handle Login
els.loginForm?.addEventListener("submit", handleLogin);
async function handleLogin() {
  const email = els.loginEmail.value.trim();
  const password = els.loginPassword.value;

  if (!email || !password) {
    setAuthAlert("Please enter both email and password.");
    return;
  }

  els.loginSubmitBtn.disabled = true;
  els.loginSubmitBtn.textContent = "Signing In…";

  try {
    const res = await fetch(API.login, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    els.loginSubmitBtn.disabled = false;
    els.loginSubmitBtn.textContent = "Sign In";

    if (data.success) {
      currentUser = data.user;
      applyUserPreferences(data.user.preferences);
      updateAuthUI();
      setAuthAlert("Signed in successfully!", "success");
      speak(`Welcome, ${data.user.full_name}!`);
      setTimeout(() => {
        closeAuthModal();
      }, 900);
    } else {
      setAuthAlert(data.error || "Login failed. Please check credentials.");
      speak("Login failed: " + (data.error || "Invalid credentials"));
    }
  } catch (err) {
    els.loginSubmitBtn.disabled = false;
    els.loginSubmitBtn.textContent = "Sign In";
    setAuthAlert("Server connection error during login.");
  }
}

// Handle Register
els.registerForm?.addEventListener("submit", handleRegister);
async function handleRegister() {
  const full_name = els.regName.value.trim();
  const email = els.regEmail.value.trim();
  const password = els.regPassword.value;

  if (!full_name || !email || !password) {
    setAuthAlert("Please fill in all registration fields.");
    return;
  }

  els.registerSubmitBtn.disabled = true;
  els.registerSubmitBtn.textContent = "Creating Account…";

  try {
    const res = await fetch(API.register, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name, email, password })
    });
    const data = await res.json();
    els.registerSubmitBtn.disabled = false;
    els.registerSubmitBtn.textContent = "Create Account";

    if (data.success) {
      currentUser = data.user;
      applyUserPreferences(data.user.preferences);
      updateAuthUI();
      setAuthAlert("Account created successfully!", "success");
      speak(`Account created! Welcome, ${data.user.full_name}!`);
      setTimeout(() => {
        closeAuthModal();
      }, 900);
    } else {
      setAuthAlert(data.error || "Registration failed.");
      speak("Registration failed: " + (data.error || "Please check details."));
    }
  } catch (err) {
    els.registerSubmitBtn.disabled = false;
    els.registerSubmitBtn.textContent = "Create Account";
    setAuthAlert("Server connection error during registration.");
  }
}

// Handle Preferences Update
els.prefSpeechRate?.addEventListener("input", e => {
  els.speechRateVal.textContent = parseFloat(e.target.value).toFixed(1) + "x";
});

els.prefHighContrast?.addEventListener("change", e => {
  document.body.classList.toggle("high-contrast", e.target.checked);
});

els.preferencesForm?.addEventListener("submit", handleSavePreferences);
async function handleSavePreferences() {
  if (!currentUser) return;

  const language_code = els.prefLanguage.value;
  const speech_enabled = els.prefSpeechEnabled.checked;
  const speech_rate = parseFloat(els.prefSpeechRate.value);
  const high_contrast_mode = els.prefHighContrast.checked;

  els.savePrefBtn.disabled = true;
  els.savePrefBtn.textContent = "Saving…";

  try {
    const res = await fetch(API.preferences, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        language_code,
        speech_enabled,
        speech_rate,
        high_contrast_mode
      })
    });
    const data = await res.json();
    els.savePrefBtn.disabled = false;
    els.savePrefBtn.textContent = "Save Preferences";

    if (data.success) {
      applyUserPreferences(data.preferences);
      setAuthAlert("Preferences saved to MySQL database!", "success");
      speak("Preferences saved.");
    } else {
      setAuthAlert(data.error || "Could not save preferences.");
    }
  } catch (err) {
    els.savePrefBtn.disabled = false;
    els.savePrefBtn.textContent = "Save Preferences";
    setAuthAlert("Failed to reach server.");
  }
}

// Handle Logout
els.logoutBtn?.addEventListener("click", handleLogout);
async function handleLogout() {
  try {
    await fetch(API.logout, { method: "POST" });
  } catch (_) {}
  currentUser = null;
  updateAuthUI();
  switchAuthTab("login");
  setAuthAlert("Signed out successfully.", "success");
  speak("Signed out.");
}

function updateAuthUI() {
  if (currentUser) {
    els.authBtnLabel.textContent = currentUser.full_name.split(" ")[0];
    els.authBtn.title = `Signed in as ${currentUser.full_name}`;
    els.tabProfile.style.display = "inline-block";
    els.profileUserName.textContent = currentUser.full_name;
    els.profileUserEmail.textContent = currentUser.email;
  } else {
    els.authBtnLabel.textContent = "Sign In";
    els.authBtn.title = "Account / Sign In";
    els.tabProfile.style.display = "none";
  }
}

function applyUserPreferences(prefs) {
  if (!prefs) return;
  userPreferences = {
    language_code: prefs.language_code || "en",
    speech_enabled: prefs.speech_enabled !== undefined ? Boolean(prefs.speech_enabled) : true,
    speech_rate: parseFloat(prefs.speech_rate || 1.0),
    high_contrast_mode: Boolean(prefs.high_contrast_mode)
  };

  voiceEnabled = userPreferences.speech_enabled;
  els.voiceToggleBtn.setAttribute("aria-pressed", voiceEnabled.toString());
  els.voiceToggleBtn.querySelector(".btn-label").textContent = voiceEnabled ? "Voice On" : "Voice Off";

  if (els.prefLanguage) els.prefLanguage.value = userPreferences.language_code;
  if (els.prefSpeechEnabled) els.prefSpeechEnabled.checked = userPreferences.speech_enabled;
  if (els.prefSpeechRate) {
    els.prefSpeechRate.value = userPreferences.speech_rate;
    els.speechRateVal.textContent = userPreferences.speech_rate.toFixed(1) + "x";
  }
  if (els.prefHighContrast) {
    els.prefHighContrast.checked = userPreferences.high_contrast_mode;
  }
  document.body.classList.toggle("high-contrast", userPreferences.high_contrast_mode);
}

// ═══════════════════════════════════════════════════════════════════════════════
// DETECTION HISTORY MODAL
// ═══════════════════════════════════════════════════════════════════════════════
els.historyBtn?.addEventListener("click", () => {
  openHistoryModal();
  loadHistory();
});
els.refreshHistoryBtn?.addEventListener("click", loadHistory);
els.closeHistoryModal?.addEventListener("click", closeHistoryModal);
els.historyModalBackdrop?.addEventListener("click", closeHistoryModal);

function openHistoryModal() {
  els.historyModal.style.display = "flex";
  document.body.style.overflow = "hidden";
}

function closeHistoryModal() {
  els.historyModal.style.display = "none";
  document.body.style.overflow = "";
}

async function loadHistory() {
  els.historyList.innerHTML = `<p class="text-secondary" style="text-align:center;padding:24px;">Loading detection records from database…</p>`;
  try {
    const res = await fetch(API.history);
    const data = await res.json();
    if (!data.success || !data.history || !data.history.length) {
      els.historyList.innerHTML = `<p class="text-secondary" style="text-align:center;padding:24px;">No detection records found in database.</p>`;
      return;
    }

    let html = "";
    data.history.forEach(session => {
      const feat = (session.feature_type || "").replace(/_/g, " ");
      const timeStr = session.created_at || "Recent";
      let resultsHtml = "";

      if (session.results && session.results.length) {
        resultsHtml = session.results.map(r => {
          const conf = r.confidence !== null && r.confidence !== undefined ? ` (${Math.round(r.confidence * 100)}%)` : "";
          return `<div class="history-detail-item"><strong>${esc(r.result_type)}:</strong> ${esc(r.result_text)}${conf}</div>`;
        }).join("");
      } else {
        resultsHtml = `<div class="history-detail-item text-secondary">No item breakdown saved.</div>`;
      }

      html += `
        <div class="history-card">
          <div class="history-card-top">
            <span class="history-badge">${esc(feat)}</span>
            <span class="history-time">${esc(timeStr)}</span>
          </div>
          <div class="history-results">
            ${resultsHtml}
          </div>
        </div>
      `;
    });

    els.historyList.innerHTML = html;
  } catch (err) {
    els.historyList.innerHTML = `<p class="text-secondary" style="text-align:center;padding:24px;color:var(--error);">Failed to load history from MySQL database.</p>`;
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// KEYBOARD SHORTCUTS
// ═══════════════════════════════════════════════════════════════════════════════
document.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;

  const key = e.key.toLowerCase();
  switch (key) {
    case "d": callAPI(API.detect,  "Object Detection"); break;
    case "t": callAPI(API.readText,"Text Reader"); break;
    case "m": callAPI(API.medicine,"Medicine Label Reader"); break;
    case "b": callAPI(API.bus,     "Bus Identification"); break;
    case "h": openHistoryModal(); loadHistory(); break;
    case "a": els.authBtn?.click(); break;
    case " ": e.preventDefault(); toggleMic(); break;
    case "s": speak(lastResultText); break;
    case "x": stopSpeaking(); break;
    case "c": if (!els.captureBtn.disabled) captureImage(); break;
    case "escape":
      closeModal();
      closeAuthModal();
      closeHistoryModal();
      break;
  }
});

// ═══════════════════════════════════════════════════════════════════════════════
// HELP MODAL
// ═══════════════════════════════════════════════════════════════════════════════
els.helpBtn.addEventListener("click", openModal);
els.closeHelpModal.addEventListener("click", closeModal);
els.modalBackdrop.addEventListener("click", closeModal);

function openModal() {
  els.helpModal.style.display = "flex";
  els.closeHelpModal.focus();
  document.body.style.overflow = "hidden";
}
function closeModal() {
  els.helpModal.style.display = "none";
  document.body.style.overflow = "";
  els.helpBtn.focus();
}

// ═══════════════════════════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════════════════════════
function showElement(el) { if (el) el.style.display = ""; }
function hideElement(el) { if (el) el.style.display = "none"; }

function showError(msg) {
  if (!els.cameraError) return;
  els.cameraError.textContent = msg;
  els.cameraError.style.display = "block";
}
function hideError() { if (els.cameraError) els.cameraError.style.display = "none"; }

function esc(str) {
  return String(str)
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;");
}
function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }

// ═══════════════════════════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════════════════════════
(async function init() {
  // Check backend & DB health
  try {
    const res  = await fetch(API.health);
    const data = await res.json();
    if (data.status === "ok") {
      const dbConnected = data.database && data.database.connected;
      const statusMsg = dbConnected ? "Ready · MySQL Connected" : "Ready · DB Offline";
      setStatus("ready", statusMsg);
      if (!dbConnected) {
        console.warn("MySQL Database is not connected:", data.database?.message);
      }
    }
  } catch (_) {
    setStatus("error", "Server Offline");
    showError("Cannot reach the VisionMate AI server. Please start the Flask server (python app.py) and refresh.");
  }

  // Check current session auth state
  try {
    const authRes = await fetch(API.me);
    const authData = await authRes.json();
    if (authData.success && authData.authenticated && authData.user) {
      currentUser = authData.user;
      applyUserPreferences(authData.user.preferences);
      updateAuthUI();
    }
  } catch (_) {}

  // Check speech synthesis support
  if (!("speechSynthesis" in window)) {
    console.warn("SpeechSynthesis not supported.");
    voiceEnabled = false;
    els.voiceToggleBtn.querySelector(".btn-label").textContent = "Voice Off";
  }
})();
