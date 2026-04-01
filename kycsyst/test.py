from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtCore import QTimer
class MyWidget(QWidget):
    def __init__(self):
        super().__init__()

        
        self.frame_count = 0

        
        self.label = QLabel(self)
        self.label.move(200,200)
        self.label.adjustSize()
        
        self.timer = QTimer()

        
        self.timer.setInterval(30)  # 30 fps

        
        self.timer.timeout.connect(self.update_frame)

        self.update_label_size()  
    
       
        self.timer.start()

    def update_label_size(self):
        self.label.adjustSize()

    def update_frame(self):
        
        self.frame_count += 1

        
        if self.frame_count == 100:
            
            self.label.setText("New text")
            self.update_label_size()  
            
import sys
from PyQt5.QtWidgets import QApplication

app = QApplication(sys.argv)
a = MyWidget()
a.show()
sys.exit(app.exec_())