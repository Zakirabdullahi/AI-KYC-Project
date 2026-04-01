import cv2 as cv
import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSizePolicy, QMessageBox
)


class VerificationWindow(QWidget):
    """
    Second page: Face verification against ID photo.
    """
    
    def __init__(self, camera, main_window):
        super().__init__()
        self.camera = camera
        self.main_window = main_window
        self.verification_image = None
        self.timer = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        # Title
        title = QLabel("Face Verification")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Instruction
        instruction = QLabel("Step 2: Position your face in the camera")
        instruction.setStyleSheet("font-size: 16px; margin: 10px;")
        instruction.setAlignment(Qt.AlignCenter)
        layout.addWidget(instruction)
        
        # Camera feed
        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setFixedSize(640, 480)
        self.camera_label.setStyleSheet("border: 2px solid #4CAF50;")
        layout.addWidget(self.camera_label)
        
        # Status label
        self.status_label = QLabel("Camera ready")
        self.status_label.setStyleSheet("font-size: 14px; margin: 10px; color: #666;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        capture_btn = QPushButton("Capture Photo")
        capture_btn.setStyleSheet("padding: 10px 20px; font-size: 14px; background-color: #2196F3; color: white;")
        capture_btn.clicked.connect(self.capture_photo)
        button_layout.addWidget(capture_btn)
        
        verify_btn = QPushButton("Verify Identity")
        verify_btn.setStyleSheet("padding: 10px 20px; font-size: 14px; background-color: #4CAF50; color: white;")
        verify_btn.clicked.connect(self.verify_identity)
        button_layout.addWidget(verify_btn)
        
        back_btn = QPushButton("Back")
        back_btn.setStyleSheet("padding: 10px 20px; font-size: 14px;")
        back_btn.clicked.connect(lambda: self.main_window.switch_page(0))
        button_layout.addWidget(back_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def open_camera(self):
        """Start camera feed."""
        if self.timer is None:
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # 30ms refresh rate
        self.status_label.setText("Camera active - Position your face")
    
    def close_camera(self):
        """Stop camera feed."""
        if self.timer is not None:
            self.timer.stop()
    
    def update_frame(self):
        """Update camera frame."""
        ret, frame = self.camera.read()
        if ret:
            frame = cv.flip(frame, 1)  # Mirror effect
            rgb_frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                640, 480,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.camera_label.setPixmap(scaled_pixmap)
    
    def capture_photo(self):
        """Capture current frame as verification photo."""
        ret, frame = self.camera.read()
        if ret:
            frame = cv.flip(frame, 1)
            self.verification_image = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            self.status_label.setText("Photo captured! Click 'Verify Identity' to continue")
            self.status_label.setStyleSheet("font-size: 14px; margin: 10px; color: #4CAF50;")
    
    def verify_identity(self):
        """Verify captured photo against ID."""
        if self.verification_image is None:
            QMessageBox.warning(self, "Warning", "Please capture a photo first!")
            return
        
        # Perform verification using main window's verify method
        result = self.main_window.verify()
        
        if result:
            QMessageBox.information(
                self,
                "Success",
                "Face verified! Proceeding to liveness detection..."
            )
            self.main_window.switch_page(2)
        else:
            QMessageBox.warning(
                self,
                "Verification Failed",
                "Face does not match ID photo. Please try again."
            )
            self.status_label.setText("Verification failed - Try again")
            self.status_label.setStyleSheet("font-size: 14px; margin: 10px; color: #f44336;")
    
    def clear_window(self):
        """Clear window state."""
        self.verification_image = None
        self.camera_label.clear()
        self.status_label.setText("Camera ready")
        self.status_label.setStyleSheet("font-size: 14px; margin: 10px; color: #666;")
