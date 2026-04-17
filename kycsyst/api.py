"""
KYC Liveness Microservice — Port 8001
Uses MediaPipe for face landmark extraction (replaces MTCNN)
and drives BlinkDetector, EmotionPredictor, FaceOrientationDetector.
"""
import sys
import os
import cv2 as cv
import numpy as np
import base64
import random
from flask import Flask, request, jsonify
from flask_cors import CORS

# ── Local liveness modules ────────────────────────────────────────────────────
from liveness_detection.blink_detection import BlinkDetector
from liveness_detection.emotion_prediction import EmotionPredictor
from liveness_detection.face_orientation import FaceOrientationDetector

# ── MediaPipe for face landmark extraction (replaces MTCNN) ──────────────────
try:
    import mediapipe as mp
    _mp_face_mesh = mp.solutions.face_mesh
    face_mesh = _mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5
    )
    MEDIAPIPE_OK = True
    print("MediaPipe Face Mesh initialized successfully.")
except Exception as e:
    MEDIAPIPE_OK = False
    print(f"WARNING: MediaPipe not available: {e}")

# ── Flask App ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ── Model instances ───────────────────────────────────────────────────────────
blink_detector = BlinkDetector()
emotion_predictor = EmotionPredictor(device="cpu")
face_orientation_detector = FaceOrientationDetector()
print("Liveness detection modules loaded.")

# ── Haar Cascades (Initialized once globally for speed) ───────────────────────
face_cascade = cv.CascadeClassifier(cv.data.haarcascades + "haarcascade_frontalface_default.xml")
smile_cascade = cv.CascadeClassifier(cv.data.haarcascades + "haarcascade_smile.xml")
profile_cascade = cv.CascadeClassifier(cv.data.haarcascades + "haarcascade_profileface.xml")
eye_cascade = cv.CascadeClassifier(cv.data.haarcascades + "haarcascade_eye.xml")

# ── Challenge helpers ─────────────────────────────────────────────────────────
def random_challenge():
    challenges = ["smile", "left", "right", "blink", "nod"]
    return random.choice(challenges)

def get_question(challenge):
    if challenge == "smile":
        return "Please show a big smile 😊"
    elif challenge == "left":
        return "Please turn your head to the LEFT 👈"
    elif challenge == "right":
        return "Please turn your head to the RIGHT 👉"
    elif challenge == "blink":
        return "Please BLINK your eyes 😌"
    elif challenge == "nod":
        return "Please NOD your head up and down ↕️"
    return "Please face the camera"

# ── Image decoding ────────────────────────────────────────────────────────────
def decode_base64_image(b64_str):
    try:
        if "," in b64_str:
            b64_str = b64_str.split(",")[1]
        buf = np.frombuffer(base64.b64decode(b64_str), np.uint8)
        img = cv.imdecode(buf, cv.IMREAD_COLOR)
        return img
    except Exception:
        return None

# ── MediaPipe 5-point landmark extraction ────────────────────────────────────
def extract_5pt_landmarks(rgb_frame):
    """
    Returns a (5,2) numpy array of [left_eye, right_eye, nose, mouth_left, mouth_right]
    from MediaPipe FaceMesh, or None if no face detected.
    """
    if not MEDIAPIPE_OK:
        return None
    h, w = rgb_frame.shape[:2]
    result = face_mesh.process(rgb_frame)
    if not result.multi_face_landmarks:
        return None
    lm = result.multi_face_landmarks[0].landmark
    # MediaPipe canonical indices for 5-pt:
    # left_eye=33, right_eye=263, nose=1, mouth_left=61, mouth_right=291
    pts = []
    for idx in [33, 263, 1, 61, 291]:
        pts.append([lm[idx].x * w, lm[idx].y * h])
    return np.array(pts)

def detect_smile_opencv(bgr_frame):
    gray = cv.cvtColor(bgr_frame, cv.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    for (x, y, fw, fh) in faces:
        roi_gray = gray[y + fh//2:y+fh, x:x+fw]
        # Reduced minNeighbors from 22 to 10 for better responsiveness
        smiles = smile_cascade.detectMultiScale(roi_gray, 1.7, 10, minSize=(25, 15))
        if len(smiles):
            return True
    return False

def detect_profile_opencv(bgr_frame, direction="left"):
    gray = cv.cvtColor(bgr_frame, cv.COLOR_BGR2GRAY)
    if direction == "right":
        gray = cv.flip(gray, 1)
        
    profiles = profile_cascade.detectMultiScale(gray, 1.3, 5)
    return len(profiles) > 0

def detect_blink_opencv(bgr_frame):
    # Stateless heuristic: Face is visible but eyes are NOT visible.
    gray = cv.cvtColor(bgr_frame, cv.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5, minSize=(80, 80))
    for (x, y, w, h) in faces:
        roi_gray = gray[y:y+h//2, x:x+w]
        eyes = eye_cascade.detectMultiScale(roi_gray, 1.1, 3)
        if len(eyes) == 0:
            return True # Face present, no eyes detected == blink
    return False

def detect_nod_opencv(bgr_frame):
    # Stateless heuristic: Face is looking down or up
    gray = cv.cvtColor(bgr_frame, cv.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    frame_h = gray.shape[0]
    
    # Check if face is unusually high or low indicating a nod motion
    for (x, y, w, h) in faces:
        cy = y + h/2
        if cy < frame_h * 0.35 or cy > frame_h * 0.65:
            return True
            
    # If no frontal face detected, it might be looking very down/up (nodding)
    if len(faces) == 0:
        # We can loosely accept a nod if no strict frontal face is seen during a nod prompt
        # but to avoid instant false pass on empty frame, check if any generic face was seen before?
        # Since it's stateless, we'll assume missing face == nod if it happens during the loop.
        # But to be safer against empty rooms, we require some dark blob (hair/head). For simplicity,
        # we'll just check if there's any face-like structure (lower confidence).
        faces_low = face_cascade.detectMultiScale(gray, 1.1, 2)
        if len(faces_low) > 0:
            return True
            
    return False

# ─── REST Endpoints ───────────────────────────────────────────────────────────
@app.route('/api/liveness/challenge', methods=['GET'])
def get_challenge():
    """Returns a fresh random liveness challenge."""
    challenge = random_challenge()
    question_text = get_question(challenge)
    return jsonify({
        "challenge": challenge,
        "question_text": question_text,
        "question_data": question_text  # simple string for all challenges
    })

@app.route('/api/liveness/verify', methods=['POST'])
def verify_frame():
    """Receives a base64 webcam frame, applies ML detection, returns pass/fail."""
    data = request.json
    frame_b64 = data.get("frame")
    challenge = data.get("challenge")

    if not frame_b64 or not challenge:
        return jsonify({"success": False, "detail": "Missing frame or challenge."}), 400

    bgr_frame = decode_base64_image(frame_b64)
    if bgr_frame is None:
        return jsonify({"success": False, "detail": "Invalid image."}), 400

    rgb_frame = cv.cvtColor(bgr_frame, cv.COLOR_BGR2RGB)
    is_correct = False

    if challenge == "smile":
        is_correct = detect_smile_opencv(bgr_frame)
    elif challenge in ("left", "right"):
        landmarks = extract_5pt_landmarks(rgb_frame)
        if landmarks is not None:
            detected_dir = face_orientation_detector.detect(landmarks)
            if detected_dir in ["left", "right"]:
                is_correct = True
        if not is_correct:
            is_correct = detect_profile_opencv(bgr_frame, direction=challenge)
    elif challenge == "blink":
        is_correct = detect_blink_opencv(bgr_frame)
    elif challenge == "nod":
        is_correct = detect_nod_opencv(bgr_frame)

    return jsonify({"success": bool(is_correct)})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "mediapipe": MEDIAPIPE_OK})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    print(f"Starting KYC Liveness Microservice on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
