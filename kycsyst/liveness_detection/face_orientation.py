import cv2 as cv
import numpy as np
from scipy.spatial import distance as dist


class FaceOrientationDetector:
    """
    Face orientation detector for liveness verification.
    Detects if face is oriented left, right, or front.
    """
    
    def __init__(self):
        """
        Initialize face orientation detector.
        """
        self.orientations = ["front", "left", "right", "up", "down"]
    
    def detect(self, landmarks):
        """
        Detect face orientation from facial landmarks.
        
        Parameters:
            landmarks (np.ndarray): Facial landmarks from MTCNN.
                Expected shape: (5, 2) containing [left_eye, right_eye, nose, left_mouth, right_mouth]
            
        Returns:
            str: Detected orientation ('front', 'left', 'right').
        """
        if landmarks is None or len(landmarks) < 5:
            return "front"
        
        # MTCNN landmarks: [left_eye, right_eye, nose, mouth_left, mouth_right]
        left_eye = landmarks[0]
        right_eye = landmarks[1]
        nose = landmarks[2]
        mouth_left = landmarks[3]
        mouth_right = landmarks[4]
        
        # Calculate face width and eye distances
        eye_distance = dist.euclidean(left_eye, right_eye)
        
        # Calculate nose position relative to eyes
        nose_x = nose[0]
        left_eye_x = left_eye[0]
        right_eye_x = right_eye[0]
        
        # Face center between eyes
        face_center_x = (left_eye_x + right_eye_x) / 2
        
        # Calculate deviation ratio
        deviation = (nose_x - face_center_x) / eye_distance if eye_distance > 0 else 0
        
        # Determine orientation based on nose position
        threshold = 0.15  # Threshold for orientation detection
        
        if deviation > threshold:
            return "right"  # Nose is to the right, face turned left
        elif deviation < -threshold:
            return "left"   # Nose is to the left, face turned right
        else:
            return "front"
    
    def calculate_head_pose(self, landmarks):
        """
        Calculate detailed head pose angles (yaw, pitch, roll).
        
        Parameters:
            landmarks (np.ndarray): Facial landmarks.
            
        Returns:
            dict: Head pose angles {yaw, pitch, roll}.
        """
        # Simplified head pose estimation
        # For production, use more sophisticated 3D head pose estimation
        
        if landmarks is None or len(landmarks) < 5:
            return {"yaw": 0, "pitch": 0, "roll": 0}
        
        left_eye = landmarks[0]
        right_eye = landmarks[1]
        
        # Calculate roll (head tilt)
        dy = right_eye[1] - left_eye[1]
        dx = right_eye[0] - left_eye[0]
        roll = np.arctan2(dy, dx) * 180 / np.pi
        
        return {
            "yaw": 0,    # Would need more landmarks for accurate yaw
            "pitch": 0,  # Would need more landmarks for accurate pitch
            "roll": roll
        }
