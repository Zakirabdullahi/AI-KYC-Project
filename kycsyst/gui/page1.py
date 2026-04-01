import cv2 as cv
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFileDialog, QSizePolicy
)


class IDCardPhoto(QWidget):
    """
    First page: ID card photo upload for KYC verification.
    """
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.img_path = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        # Title
        title = QLabel("eKYC Identity Verification")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Instruction
        instruction = QLabel("Step 1: Upload your ID card or passport photo")
        instruction.setStyleSheet("font-size: 16px; margin: 10px;")
        instruction.setAlignment(Qt.AlignCenter)
        layout.addWidget(instruction)
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(400, 300)
        self.image_label.setStyleSheet("border: 2px dashed #ccc; background-color: #f9f9f9;")
        self.image_label.setText("No image selected")
        layout.addWidget(self.image_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        upload_btn = QPushButton("Upload ID Photo")
        upload_btn.setStyleSheet("padding: 10px 20px; font-size: 14px;")
        upload_btn.clicked.connect(self.upload_image)
        button_layout.addWidget(upload_btn)
        
        next_btn = QPushButton("Next: Face Verification")
        next_btn.setStyleSheet("padding: 10px 20px; font-size: 14px; background-color: #4CAF50; color: white;")
        next_btn.clicked.connect(self.go_to_next_page)
        button_layout.addWidget(next_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def upload_image(self):
        """Upload ID card image."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select ID Card Photo",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file_name:
            self.img_path = file_name
            pixmap = QPixmap(file_name)
            scaled_pixmap = pixmap.scaled(
                400, 300,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
    
    def go_to_next_page(self):
        """Go to face verification page."""
        if self.img_path is None:
            # Show warning
            self.image_label.setText("Please upload an ID photo first!")
            return
        
        self.main_window.switch_page(1)
    
    def clear_window(self):
        """Clear the window state."""
        self.img_path = None
        self.image_label.clear()
        self.image_label.setText("No image selected")
