from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PyQt5.QtWidgets import QPushButton
from qfluentwidgets import PushButton as FluentPushButton
from src.ui.tools.base_component import BaseComponent
from src.utils.enums import ComponentEvent


class CaptureInput(QPushButton):
    """隐藏的捕获控件，只负责 grab 键盘/鼠标事件"""

    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setFixedSize(0, 0)
        self.capturing = False
        self.on_captured = None
        self.setFocusPolicy(Qt.StrongFocus)

    def event(self, event: QEvent):
        if self.capturing and event.type() == QEvent.KeyPress:
            ke = QKeyEvent(event)
            self.keyPressEvent(ke)
            return True
        return super().event(event)

    def keyPressEvent(self, event: QKeyEvent):
        if self.capturing:
            key = event.key()
            tab = {
                Qt.Key_Tab: "Tab",
                Qt.Key_Escape: "Escape", Qt.Key_Return: "Enter",
                Qt.Key_Enter: "Enter", Qt.Key_Shift: "Shift",
                Qt.Key_Control: "Control", Qt.Key_Alt: "Alt",
                Qt.Key_CapsLock: "CapsLock", Qt.Key_Space: "Space",
                Qt.Key_Up: "Up", Qt.Key_Down: "Down",
                Qt.Key_Left: "Left", Qt.Key_Right: "Right",
                Qt.Key_Home: "Home", Qt.Key_End: "End",
                Qt.Key_PageUp: "PageUp", Qt.Key_PageDown: "PageDown",
                Qt.Key_Insert: "Insert", Qt.Key_Delete: "Delete",
                Qt.Key_Backspace: "Backspace",
                Qt.Key_Print: "Print", Qt.Key_Pause: "Pause",
                Qt.Key_Meta: "Meta", Qt.Key_NumLock: "NumLock",
            }
            for i in range(1, 13):
                tab[getattr(Qt, f"Key_F{i}")] = f"F{i}"

            if key in tab and self.on_captured:
                self.on_captured(tab[key])
                return
            text = event.text()
            if text and text.isprintable() and self.on_captured:
                self.on_captured(text.upper())
                return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if self.capturing:
            btn = event.button()
            map_ = {
                Qt.LeftButton: "LeftButton",
                Qt.RightButton: "RightButton",
                Qt.MiddleButton: "MiddleButton",
                Qt.XButton1: "LM1",
                Qt.XButton2: "LM2",
            }
            if btn in map_ and self.on_captured:
                self.on_captured(map_[btn])
                return
        super().mousePressEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if self.capturing:
            if event.angleDelta().y() > 0 and self.on_captured:
                self.on_captured("WheelUp")
            elif self.on_captured:
                self.on_captured("WheelDown")
            return
        super().wheelEvent(event)

    def start(self):
        self.capturing = True
        self.grabKeyboard()
        self.grabMouse()

    def stop(self):
        self.capturing = False
        self.releaseKeyboard()
        self.releaseMouse()


class KeyCaptureButton(BaseComponent):
    """键位捕获组件：展示用 FluentPushButton + 隐藏 CaptureInput 捕获事件"""

    def __init__(self, parent=None, handler=None):
        super().__init__(0, 0, 200, "键位捕获", parent=parent, handler=handler)
        self._raw_key = ""

        self._input = CaptureInput()
        self._input.on_captured = self.apply_captured

        self._btn = FluentPushButton("")
        self._btn.clicked.connect(self._start_capture)

    @property
    def raw_key(self) -> str:
        return self._raw_key

    def set_raw_key(self, key: str):
        self._raw_key = key
        self._btn.setText(key)

    def widget(self):
        return self._btn

    def _start_capture(self):
        self._btn.setText("...")
        self._input.start()
        self._btn.wheelEvent = self._input.wheelEvent

    def apply_captured(self, key: str):
        self._raw_key = key
        self._btn.setText(key)
        self._input.stop()
        self._btn.wheelEvent = lambda e: None
        self._dispatch(ComponentEvent.CHANGE)