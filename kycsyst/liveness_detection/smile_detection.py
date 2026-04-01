"""
Smile Detection using OpenCV + dlib 68-point landmarks.

Uses the Mouth Aspect Ratio (MAR) approach with dlib facial landmarks,
analogous to the Eye Aspect Ratio used by BlinkDetector. Falls back to
mouth-region brightness analysis if dlib is unavailable.
"""

import cv2 as cv
import numpy as np
from scipy.spatial import distance as dist

# Try to import dlib (optional but recommended)
try:
    import dlib
    DLIB_AVAILABLE = True
except ImportError:
    DLIB_AVAILABLE = False

# ---------------------------------------------------------------------------
# dlib 68-point mouth landmark indices
# ---------------------------------------------------------------------------
# Outer mouth: 48–59  (12 points, upper & lower outer lip)
# Inner mouth: 60–67  (8 points, inner lip)
OUTER_LIP_TOP_IDX    = 51   # Top of outer upper lip (centre)
OUTER_LIP_BOTTOM_IDX = 57   # Bottom of outer lower lip (centre)
OUTER_LIP_LEFT_IDX   = 48   # Left corner
OUTER_LIP_RIGHT_IDX  = 54   # Right corner

INNER_LIP_TOP_IDX    = 62   # Top inner lip
INNER_LIP_BOTTOM_IDX = 66   # Bottom inner lip

# Cheek reference points (used to normalise mouth width to face size)
# Jawline extremes: 0 (left) and 16 (right)
JAWLINE_LEFT_IDX  = 0
JAWLINE_RIGHT_IDX = 16


class SmileDetector:
    """
    Detects smile / open-mouth (surprise) from full camera frames using
    dlib 68-point landmarks and Mouth Aspect Ratio (MAR).

    If dlib or the shape-predictor file are unavailable, falls back to an
    MTCNN-landmarks-based heuristic using the 5-point face landmarks that
    MTCNN already provides (left_mouth, right_mouth relative to eye width).

    Returns one of: "smile", "surprise", "neutral"
    """

    SHAPE_PREDICTOR_PATH = "shape_predictor_68_face_landmarks.dat"

    # Tunable thresholds
    # MAR = vertical mouth opening / horizontal mouth width
    SURPRISE_MAR = 0.45   # Very open mouth → surprise
    SMILE_MAR    = 0.10   # Slightly open / stretched → smile
    # Smile spread: mouth-width / face-width (jaw)
    SMILE_SPREAD = 0.48   # Mouth stretching wide = smile

    def __init__(self, surprise_mar=None, smile_mar=None, smile_spread=None,
                 smile_spread_threshold=None, surprise_mar_threshold=None,
                 smile_mar_threshold=None):
        """
        Parameters (all optional, have sensible defaults):
            surprise_mar (float): MAR threshold for surprise/open-mouth.
            smile_mar (float): Minimum MAR for smile (must be lower than surprise_mar).
            smile_spread (float): Mouth-width / face-width ratio for smile.
        
        Legacy keyword aliases accepted for backwards compatibility.
        """
        self.surprise_mar = surprise_mar or surprise_mar_threshold or self.SURPRISE_MAR
        self.smile_mar    = smile_mar    or smile_mar_threshold    or self.SMILE_MAR
        self.smile_spread = smile_spread or smile_spread_threshold or self.SMILE_SPREAD

        self.use_dlib = False
        self._detector = None
        self._predictor = None

        if DLIB_AVAILABLE:
            try:
                self._detector  = dlib.get_frontal_face_detector()
                self._predictor = dlib.shape_predictor(self.SHAPE_PREDICTOR_PATH)
                self.use_dlib   = True
            except Exception as e:
                # Shape-predictor file not found — use fallback
                pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, frame_rgb):
        """
        Detect expression from an RGB frame (full camera frame).

        Parameters:
            frame_rgb (np.ndarray): RGB image (H × W × 3).

        Returns:
            str: 'smile', 'surprise', or 'neutral'.
        """
        if frame_rgb is None or frame_rgb.size == 0:
            return "neutral"

        if self.use_dlib:
            return self._detect_dlib(frame_rgb)
        else:
            return self._detect_fallback_opencv(frame_rgb)

    def detect_from_face_crop(self, face_rgb):
        """
        Detect expression from a cropped face image.

        Parameters:
            face_rgb (np.ndarray): Cropped RGB face image.

        Returns:
            str: 'smile', 'surprise', or 'neutral'.
        """
        if face_rgb is None or face_rgb.size == 0:
            return "neutral"
        return self.detect(face_rgb)

    def release(self):
        """No persistent resources to release in this implementation."""
        pass

    # ------------------------------------------------------------------
    # dlib-based detection (accurate)
    # ------------------------------------------------------------------

    def _detect_dlib(self, frame_rgb):
        """Use dlib 68-point landmarks to compute MAR and spread ratio."""
        gray = cv.cvtColor(frame_rgb, cv.COLOR_RGB2GRAY)
        faces = self._detector(gray, 0)

        if not faces:
            return "neutral"

        shape = self._predictor(gray, faces[0])
        pts   = np.array([[shape.part(i).x, shape.part(i).y] for i in range(68)])

        return self._classify_from_68pts(pts)

    def _classify_from_68pts(self, pts):
        """Compute MAR + spread and return emotion string."""
        top    = pts[OUTER_LIP_TOP_IDX]
        bottom = pts[OUTER_LIP_BOTTOM_IDX]
        left   = pts[OUTER_LIP_LEFT_IDX]
        right  = pts[OUTER_LIP_RIGHT_IDX]

        # Also average inner lip vertical distance for smoother MAR
        inner_top    = pts[INNER_LIP_TOP_IDX]
        inner_bottom = pts[INNER_LIP_BOTTOM_IDX]

        vertical_outer = dist.euclidean(top, bottom)
        vertical_inner = dist.euclidean(inner_top, inner_bottom)
        horizontal     = dist.euclidean(left, right)

        if horizontal < 1e-6:
            return "neutral"

        # Combined MAR (average of outer and inner)
        mar = (vertical_outer + vertical_inner) / (2.0 * horizontal)

        # Face width for spread normalisation
        jaw_left  = pts[JAWLINE_LEFT_IDX]
        jaw_right = pts[JAWLINE_RIGHT_IDX]
        face_width = dist.euclidean(jaw_left, jaw_right)
        spread = horizontal / face_width if face_width > 1e-6 else 0.0

        if mar > self.surprise_mar:
            return "surprise"
        elif spread > self.smile_spread and mar > self.smile_mar:
            return "smile"
        else:
            return "neutral"

    # ------------------------------------------------------------------
    # OpenCV fallback (no dlib) — uses Haar cascade on mouth crop
    # ------------------------------------------------------------------

    def _detect_fallback_opencv(self, frame_rgb):
        """
        Fallback: Use OpenCV Haar cascade (smile detector) on a face crop.
        Less accurate than dlib but zero extra dependencies.
        """
        gray = cv.cvtColor(frame_rgb, cv.COLOR_RGB2GRAY)
        h, w = gray.shape

        # Load Haar smile cascade (ships with OpenCV)
        try:
            smile_cascade = cv.CascadeClassifier(
                cv.data.haarcascades + "haarcascade_smile.xml"
            )
            face_cascade = cv.CascadeClassifier(
                cv.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
        except Exception:
            return "neutral"

        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
        if not len(faces):
            return "neutral"

        # Use largest face
        x, y, fw, fh = max(faces, key=lambda r: r[2] * r[3])

        # Search for smile in the lower half of the face
        roi_gray = gray[y + fh // 2:y + fh, x:x + fw]

        smiles = smile_cascade.detectMultiScale(
            roi_gray,
            scaleFactor=1.7,
            minNeighbors=22,   # High value reduces false positives
            minSize=(25, 15),
        )

        if len(smiles):
            return "smile"
        return "neutral"
