# serial_page.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt


class SerialPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("serialPage")
        layout = QVBoxLayout(self)
        label = QLabel("串口设置")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)