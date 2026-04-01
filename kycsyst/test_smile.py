"""
Smoke test for SmileDetector and EmotionPredictor.
Run from d:\\teti project\\kycsyst with the project venv active.

Usage:
    python test_smile.py
"""
import sys
import os
import numpy as np

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing SmileDetector...")
from liveness_detection.smile_detection import SmileDetector

detector = SmileDetector()
print(f"  SmileDetector instantiated (use_dlib={detector.use_dlib}) ✔")

# Blank white 200x200 RGB image (no real face — expect 'neutral')
dummy_face = np.ones((200, 200, 3), dtype=np.uint8) * 200

result = detector.detect(dummy_face)
assert result in ("smile", "surprise", "neutral"), f"Unexpected result: {result}"
print(f"  detect(dummy 200x200) → '{result}' ✔")

result2 = detector.detect_from_face_crop(dummy_face)
assert result2 in ("smile", "surprise", "neutral"), f"Unexpected result: {result2}"
print(f"  detect_from_face_crop(dummy) → '{result2}' ✔")

# None / empty handling
result_none = detector.detect(None)
assert result_none == "neutral", f"Expected 'neutral' for None input, got {result_none}"
print(f"  detect(None) → '{result_none}' ✔")

result_empty = detector.detect_from_face_crop(np.array([]))
assert result_empty == "neutral"
print(f"  detect_from_face_crop(empty) → '{result_empty}' ✔")

print("\nTesting EmotionPredictor...")
from liveness_detection.emotion_prediction import EmotionPredictor
from PIL import Image

predictor = EmotionPredictor()
print("  EmotionPredictor instantiated ✔")

# numpy array
result3 = predictor.predict(dummy_face)
assert result3 in ("smile", "surprise", "neutral"), f"Unexpected: {result3}"
print(f"  predict(numpy) → '{result3}' ✔")

# PIL Image
pil_img = Image.fromarray(dummy_face)
result4 = predictor.predict(pil_img)
assert result4 in ("smile", "surprise", "neutral"), f"Unexpected: {result4}"
print(f"  predict(PIL.Image) → '{result4}' ✔")

# Full frame via predict_from_frame
full_frame = np.ones((480, 640, 3), dtype=np.uint8) * 180
result5 = predictor.predict_from_frame(full_frame)
assert result5 in ("smile", "surprise", "neutral"), f"Unexpected: {result5}"
print(f"  predict_from_frame(640x480) → '{result5}' ✔")

# Release
detector.release()
print("  detector.release() ✔")

print("\n✅ All smoke tests passed!")
