# settings_page.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("settingsPage")
        layout = QVBoxLayout(self)
        label = QLabel("设置")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)