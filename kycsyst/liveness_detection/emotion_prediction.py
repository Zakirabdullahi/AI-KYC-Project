"""
Emotion prediction for liveness challenge-response verification.
Uses MediaPipe Face Mesh via SmileDetector for real detection.
"""

import cv2 as cv
import numpy as np
from PIL import Image

from liveness_detection.smile_detection import SmileDetector


class EmotionPredictor:
    """
    Emotion prediction for liveness challenge-response verification.
    Detects emotions: smile, surprise, neutral.

    Uses MediaPipe Face Mesh (via SmileDetector) for accurate,
    landmark-based detection — no random placeholders.
    """

    def __init__(self, device="cpu"):
        """
        Initialize emotion predictor.

        Parameters:
            device (str): Kept for API compatibility (unused — MediaPipe runs on CPU).
        """
        self.emotions = ["neutral", "smile", "surprise"]
        self.smile_detector = SmileDetector(
            smile_spread_threshold=0.45,
            surprise_mar_threshold=0.35,
            smile_mar_threshold=0.10,
        )

    def predict(self, face_image):
        """
        Predict emotion from face image.

        Parameters:
            face_image (np.ndarray or PIL.Image): Face image (RGB).

        Returns:
            str: Predicted emotion — 'smile', 'surprise', or 'neutral'.
        """
        # Normalise to RGB numpy array
        if isinstance(face_image, Image.Image):
            face_image = np.array(face_image)

        if face_image is None or face_image.size == 0:
            return "neutral"

        # Ensure uint8 RGB
        if face_image.dtype != np.uint8:
            face_image = (face_image * 255).clip(0, 255).astype(np.uint8)

        # BGR → RGB if needed (OpenCV frames are BGR)
        if len(face_image.shape) == 3 and face_image.shape[2] == 3:
            # Check if the image looks like it was read by OpenCV (BGR)
            # We trust callers to pass RGB; detect() handles any input
            emotion = self.smile_detector.detect_from_face_crop(face_image)
        else:
            emotion = "neutral"

        return emotion

    def predict_from_frame(self, full_frame_rgb):
        """
        Predict emotion from a full RGB frame (more accurate: uses entire face context).

        Parameters:
            full_frame_rgb (np.ndarray): Full RGB frame from camera.

        Returns:
            str: Predicted emotion — 'smile', 'surprise', or 'neutral'.
        """
        return self.smile_detector.detect(full_frame_rgb)
