import cv2 as cv
import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox, QProgressBar, QFrame
)
from challenge_response import get_challenge_and_question, result_challenge_response
from liveness_detection.emotion_prediction import EmotionPredictor


# Emoji icons for each challenge type (displayed in overlay)
CHALLENGE_ICONS = {
    "smile": "😊",
    "surprise": "😮",
    "blink eyes": "👁",
    "left": "⬅",
    "right": "➡",
    "front": "⬆",
}

CHALLENGES_REQUIRED = 3  # Number of challenges the user must pass


class ChallengeWindow(QWidget):
    """
    Third page: Liveness detection through multi-challenge-response.
    Requires completing CHALLENGES_REQUIRED consecutive challenges.
    Uses real MediaPipe-based smile/expression detection.
    """

    def __init__(self, camera, main_window, mtcnn, list_models):
        super().__init__()
        self.camera = camera
        self.main_window = main_window
        self.mtcnn = mtcnn
        self.blink_detector = list_models[0]
        self.face_orientation_detector = list_models[1]
        self.emotion_predictor = list_models[2]
        self.list_models = list_models

        self.challenge = None
        self.question = None
        self.timer = None
        self.challenge_completed = False  # current single challenge done?

        # Multi-challenge tracking
        self.challenges_passed = 0
        self.all_done = False

        # Brief green-flash countdown after each success
        self._success_flash_frames = 0

        self.init_ui()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(8)

        # ----- Title -----
        title = QLabel("Liveness Detection")
        title.setStyleSheet(
            "font-size: 26px; font-weight: bold; color: #FF9800; margin: 10px;"
        )
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        instruction = QLabel("Step 3: Complete all liveness challenges")
        instruction.setStyleSheet("font-size: 14px; color: #888; margin-bottom: 4px;")
        instruction.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(instruction)

        # ----- Progress section -----
        progress_frame = QFrame()
        progress_frame.setStyleSheet(
            "background-color: #1E1E2E; border-radius: 8px; padding: 8px;"
        )
        progress_layout = QVBoxLayout(progress_frame)

        self.progress_label = QLabel(
            f"Progress: 0 / {CHALLENGES_REQUIRED} challenges completed"
        )
        self.progress_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #E0E0E0;"
        )
        self.progress_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(CHALLENGES_REQUIRED)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #444;
                border-radius: 6px;
                background-color: #2E2E3E;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF9800, stop:1 #4CAF50
                );
                border-radius: 6px;
            }
            """
        )
        progress_layout.addWidget(self.progress_bar)
        main_layout.addWidget(progress_frame)

        # ----- Challenge question label -----
        self.question_label = QLabel("Click 'Start Challenge' to begin")
        self.question_label.setStyleSheet(
            "font-size: 18px; margin: 8px; padding: 12px; "
            "background-color: #FFF9C4; border-radius: 6px; font-weight: bold;"
        )
        self.question_label.setAlignment(Qt.AlignCenter)
        self.question_label.setWordWrap(True)
        main_layout.addWidget(self.question_label)

        # ----- Camera feed -----
        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setFixedSize(640, 420)
        self.camera_label.setStyleSheet("border: 2px solid #FF9800; border-radius: 4px;")
        main_layout.addWidget(self.camera_label)

        # ----- Status label (below camera) -----
        self.status_label = QLabel("Ready to start")
        self.status_label.setStyleSheet("font-size: 13px; margin: 6px; color: #888;")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        # ----- Buttons -----
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.start_btn = QPushButton("▶  Start Challenge")
        self.start_btn.setStyleSheet(
            "padding: 10px 22px; font-size: 14px; font-weight: bold; "
            "background-color: #FF9800; color: white; border-radius: 6px;"
        )
        self.start_btn.clicked.connect(self.start_challenge)
        button_layout.addWidget(self.start_btn)

        self.complete_btn = QPushButton("✓  Complete Verification")
        self.complete_btn.setStyleSheet(
            "padding: 10px 22px; font-size: 14px; font-weight: bold; "
            "background-color: #4CAF50; color: white; border-radius: 6px;"
        )
        self.complete_btn.clicked.connect(self.complete_verification)
        self.complete_btn.setEnabled(False)
        button_layout.addWidget(self.complete_btn)

        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet(
            "padding: 10px 18px; font-size: 14px; border-radius: 6px; "
            "background-color: #555; color: white;"
        )
        back_btn.clicked.connect(lambda: self.main_window.switch_page(1))
        button_layout.addWidget(back_btn)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    # ------------------------------------------------------------------
    # Camera management
    # ------------------------------------------------------------------

    def open_camera(self):
        """Start camera feed."""
        if self.timer is None:
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # ~33 fps

    def close_camera(self):
        """Stop camera feed."""
        if self.timer is not None:
            self.timer.stop()

    # ------------------------------------------------------------------
    # Frame update + challenge checking
    # ------------------------------------------------------------------

    def update_frame(self):
        """Read camera frame, check challenge response, draw overlay, display."""
        ret, frame = self.camera.read()
        if not ret:
            return

        frame = cv.flip(frame, 1)  # Mirror
        rgb_frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

        # --- Check challenge ---
        if self.challenge is not None and not self.challenge_completed and not self.all_done:
            # Use full frame for emotion (more accurate than face crop)
            if self.challenge in ["smile", "surprise"]:
                emotion = self.emotion_predictor.predict_from_frame(rgb_frame)
                is_correct = (emotion == self.challenge)
            else:
                is_correct = result_challenge_response(
                    rgb_frame,
                    self.challenge,
                    self.question,
                    self.list_models,
                    self.mtcnn,
                )

            if is_correct:
                self._on_challenge_success()

        # --- Draw overlay on frame ---
        display_frame = self._draw_overlay(frame.copy())

        # Convert and display
        display_rgb = cv.cvtColor(display_frame, cv.COLOR_BGR2RGB)
        h, w, ch = display_rgb.shape
        qt_image = QImage(display_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
            640, 420, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.camera_label.setPixmap(scaled_pixmap)

        # Tick down the success flash
        if self._success_flash_frames > 0:
            self._success_flash_frames -= 1

    def _on_challenge_success(self):
        """Handle a single challenge being completed."""
        self.challenge_completed = True
        self.challenges_passed += 1
        self._success_flash_frames = 45  # ~1.5 seconds green flash

        # Update progress UI
        self.progress_bar.setValue(self.challenges_passed)
        self.progress_label.setText(
            f"Progress: {self.challenges_passed} / {CHALLENGES_REQUIRED} challenges completed"
        )

        if self.challenges_passed >= CHALLENGES_REQUIRED:
            # All done!
            self.all_done = True
            self.status_label.setText("✅ All challenges completed! You may proceed.")
            self.status_label.setStyleSheet(
                "font-size: 14px; margin: 6px; color: #4CAF50; font-weight: bold;"
            )
            self.question_label.setText("🎉 Liveness Verified!")
            self.question_label.setStyleSheet(
                "font-size: 20px; margin: 8px; padding: 12px; "
                "background-color: #C8E6C9; border-radius: 6px; font-weight: bold;"
            )
            self.complete_btn.setEnabled(True)
            self.start_btn.setEnabled(False)
        else:
            # Schedule next challenge
            self.status_label.setText(
                f"✔ Challenge {self.challenges_passed} passed! Get ready for the next one..."
            )
            self.status_label.setStyleSheet(
                "font-size: 14px; margin: 6px; color: #4CAF50; font-weight: bold;"
            )
            QTimer.singleShot(1500, self._auto_next_challenge)

    def _auto_next_challenge(self):
        """Automatically start the next challenge after a brief pause."""
        if not self.all_done:
            self._issue_new_challenge()

    def _issue_new_challenge(self):
        """Pick and display a new challenge."""
        from challenge_response import get_challenge_and_question
        self.challenge, self.question = get_challenge_and_question()
        self.challenge_completed = False

        question_text = self.question[0] if isinstance(self.question, list) else self.question
        icon = CHALLENGE_ICONS.get(self.challenge, "")
        self.question_label.setText(f"{icon}  Challenge: {question_text}")
        self.question_label.setStyleSheet(
            "font-size: 18px; margin: 8px; padding: 12px; "
            "background-color: #FFF9C4; border-radius: 6px; font-weight: bold;"
        )
        self.status_label.setText("Perform the action shown above...")
        self.status_label.setStyleSheet("font-size: 13px; margin: 6px; color: #FF9800;")

    # ------------------------------------------------------------------
    # Overlay drawing
    # ------------------------------------------------------------------

    def _draw_overlay(self, bgr_frame):
        """Draw HUD overlay on the BGR camera frame."""
        h, w = bgr_frame.shape[:2]

        if self.challenge is None:
            return bgr_frame

        # Determine overlay color
        if self._success_flash_frames > 0:
            color = (0, 200, 80)      # Green flash on success
            label = "CHALLENGE PASSED!"
        elif self.all_done:
            color = (0, 180, 60)
            label = "ALL DONE!"
        else:
            color = (30, 130, 220)    # Blue = active challenge
            icon = CHALLENGE_ICONS.get(self.challenge, "")
            label = self.challenge.upper()

        # Top banner
        overlay = bgr_frame.copy()
        cv.rectangle(overlay, (0, 0), (w, 44), color, -1)
        # Blend for semi-transparency
        cv.addWeighted(overlay, 0.65, bgr_frame, 0.35, 0, bgr_frame)

        # Text on banner
        cv.putText(
            bgr_frame, label,
            (12, 30),
            cv.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2, cv.LINE_AA
        )

        # Bottom: progress indicator dots
        dot_radius = 10
        dot_spacing = 30
        start_x = w // 2 - (CHALLENGES_REQUIRED * dot_spacing) // 2 + dot_spacing // 2
        dot_y = h - 18
        for i in range(CHALLENGES_REQUIRED):
            if i < self.challenges_passed:
                dot_color = (0, 200, 80)   # Completed → green
            elif self.challenge is not None and not self.challenge_completed and i == self.challenges_passed:
                dot_color = (30, 130, 220)  # Current → blue
            else:
                dot_color = (120, 120, 120)  # Pending → grey
            cx = start_x + i * dot_spacing
            cv.circle(bgr_frame, (cx, dot_y), dot_radius, dot_color, -1)
            cv.circle(bgr_frame, (cx, dot_y), dot_radius, (255, 255, 255), 1)

        return bgr_frame

    # ------------------------------------------------------------------
    # Button actions
    # ------------------------------------------------------------------

    def start_challenge(self):
        """Start the first (or a new) liveness challenge."""
        self._issue_new_challenge()
        self.start_btn.setText("↺  New Challenge")

    def complete_verification(self):
        """Complete the KYC verification process."""
        if self.all_done:
            QMessageBox.information(
                self,
                "Verification Successful",
                "🎉 KYC liveness verification completed!\n\nAll challenges passed successfully.",
            )
            self.main_window.switch_page(0)
        else:
            QMessageBox.warning(
                self,
                "Not Yet Complete",
                f"Please complete all {CHALLENGES_REQUIRED} liveness challenges first.",
            )

    # ------------------------------------------------------------------
    # State reset
    # ------------------------------------------------------------------

    def clear_window(self):
        """Reset all state when navigating away."""
        self.challenge = None
        self.question = None
        self.challenge_completed = False
        self.challenges_passed = 0
        self.all_done = False
        self._success_flash_frames = 0

        self.camera_label.clear()
        self.question_label.setText("Click 'Start Challenge' to begin")
        self.question_label.setStyleSheet(
            "font-size: 18px; margin: 8px; padding: 12px; "
            "background-color: #FFF9C4; border-radius: 6px; font-weight: bold;"
        )
        self.status_label.setText("Ready to start")
        self.status_label.setStyleSheet("font-size: 13px; margin: 6px; color: #888;")
        self.start_btn.setText("▶  Start Challenge")
        self.start_btn.setEnabled(True)
        self.complete_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText(
            f"Progress: 0 / {CHALLENGES_REQUIRED} challenges completed"
        )
