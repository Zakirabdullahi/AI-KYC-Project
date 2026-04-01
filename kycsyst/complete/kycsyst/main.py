import sys 
import cv2 as cv
import numpy as np
import torch  # Required for loading models

from face_verification import *
from facenet.models.mtcnn import MTCNN
from gui.page1 import *
from gui.page2 import *
from gui.page3 import *
from gui.utils import *
from liveness_detection.blink_detection import BlinkDetector
from liveness_detection.emotion_prediction import EmotionPredictor
from liveness_detection.face_orientation import FaceOrientationDetector
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QSizePolicy
from utils.functions import *
from verification_models import VGGFace2

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("eKYC GUI")
        self.resize(1600, 800)  # Allow dynamic resizing
        self.setMinimumSize(800, 600)  # Prevent window from being too small

        # Model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.mtcnn = MTCNN(device=self.device)
        self.verification_model = VGGFace2.load_model(device=self.device)

        self.blink_detector = BlinkDetector()
        self.face_orientation_detector = FaceOrientationDetector()
        self.emotion_predictor = EmotionPredictor(device=self.device)

        # Camera
        self.camera = cv.VideoCapture(0)

        # Stacked widget (Resizable)
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCentralWidget(self.stacked_widget)

        # Pages
        self.first_page = IDCardPhoto(main_window=self)
        self.second_page = VerificationWindow(camera=self.camera, main_window=self)
        self.third_page = ChallengeWindow(
            camera=self.camera,
            main_window=self,
            mtcnn=self.mtcnn,
            list_models=[
                self.blink_detector,
                self.face_orientation_detector,
                self.emotion_predictor,
            ],
        )

        self.stacked_widget.addWidget(self.first_page)
        self.stacked_widget.addWidget(self.second_page)
        self.stacked_widget.addWidget(self.third_page)

    def verify(self):
        id_image = get_image(self.first_page.img_path)
        verification_image = self.second_page.verification_image

        return verify(
            id_image,
            verification_image,
            self.mtcnn,
            self.verification_model,
            model_name="VGG-Face2",
        )

    def switch_page(self, index):
        """Switches between pages while managing the camera properly."""
        if index == 0:
            self.first_page.clear_window()
            self.second_page.close_camera()
            self.third_page.close_camera()

        elif index == 1:
            self.second_page.clear_window()
            self.second_page.open_camera()
            self.third_page.close_camera()

        elif index == 2:
            self.third_page.clear_window()
            self.third_page.open_camera()
            self.second_page.close_camera()

        self.stacked_widget.setCurrentIndex(index)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
