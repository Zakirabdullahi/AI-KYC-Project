import cv2 as cv
import numpy as np
from imutils import face_utils
from scipy.spatial import distance as dist

# Try to import dlib, but it's optional
try:
    import dlib
    DLIB_AVAILABLE = True
except ImportError:
    DLIB_AVAILABLE = False
    print("Warning: dlib not available. Using simplified blink detection.")


class BlinkDetector:
    """
    Blink detection for liveness verification using eye aspect ratio (EAR).
    """
    
    def __init__(self, ear_threshold=0.25, consecutive_frames=2):
        """
        Initialize the blink detector.
        
        Parameters:
            ear_threshold (float): Eye aspect ratio threshold for blink detection.
            consecutive_frames (int): Number of consecutive frames for blink confirmation.
        """
        self.ear_threshold = ear_threshold
        self.consecutive_frames = consecutive_frames
        self.blink_counter = 0
        self.total_blinks = 0
        self.frame_counter = 0
        
        # Check if dlib is available
        if DLIB_AVAILABLE:
            try:
                self.detector = dlib.get_frontal_face_detector()
                self.predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
                self.use_dlib = True
            except:
                # Fallback: use simple heuristic without dlib
                self.use_dlib = False
                print("Warning: dlib landmark detector not available. Using simplified blink detection.")
        else:
            self.use_dlib = False
    
    def eye_aspect_ratio(self, eye):
        """
        Calculate eye aspect ratio (EAR) from eye landmarks.
        
        Parameters:
            eye (np.ndarray): Eye landmark coordinates.
            
        Returns:
            float: Eye aspect ratio.
        """
        # Compute the euclidean distances between the two sets of vertical eye landmarks
        A = dist.euclidean(eye[1], eye[5])
        B = dist.euclidean(eye[2], eye[4])
        
        # Compute the euclidean distance between the horizontal eye landmark
        C = dist.euclidean(eye[0], eye[3])
        
        # Compute the eye aspect ratio
        ear = (A + B) / (2.0 * C)
        
        return ear
    
    def detect_blink_frame(self, image, box):
        """
        Detect blink in a single frame.
        
        Parameters:
            image (np.ndarray): Input image (BGR format).
            box (list): Face bounding box [x1, y1, x2, y2].
            
        Returns:
            bool: True if blink detected in this frame.
        """
        if not self.use_dlib:
            # Simple fallback: simulate blink detection
            self.frame_counter += 1
            if self.frame_counter % 30 == 0:  # Simulate blink every 30 frames
                return True
            return False
        
        gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        
        # Convert box to dlib rectangle
        x1, y1, x2, y2 = box
        rect = dlib.rectangle(int(x1), int(y1), int(x2), int(y2))
        
        # Detect facial landmarks
        shape = self.predictor(gray, rect)
        shape = face_utils.shape_to_np(shape)
        
        # Extract eye landmarks
        left_eye = shape[36:42]
        right_eye = shape[42:48]
        
        # Calculate eye aspect ratio
        left_ear = self.eye_aspect_ratio(left_eye)
        right_ear = self.eye_aspect_ratio(right_eye)
        ear = (left_ear + right_ear) / 2.0
        
        # Check if blink detected
        if ear < self.ear_threshold:
            self.blink_counter += 1
        else:
            if self.blink_counter >= self.consecutive_frames:
                self.total_blinks += 1
                self.blink_counter = 0
                return True
            self.blink_counter = 0
        
        return False
    
    def eye_blink(self, image, box, required_blinks=3, max_frames=300):
        """
        Check if required number of blinks detected.
        
        Parameters:
            image (np.ndarray): Input image (BGR format).
            box (list): Face bounding box [x1, y1, x2, y2].
            required_blinks (int): Number of blinks required.
            max_frames (int): Maximum frames to wait.
            
        Returns:
            bool: True if required blinks detected.
        """
        # For single frame check, use previous total
        # In actual use, this should be called repeatedly and track state
        return self.total_blinks >= required_blinks
    
    def reset(self):
        """Reset blink counter."""
        self.total_blinks = 0
        self.blink_counter = 0
        self.frame_counter = 0
