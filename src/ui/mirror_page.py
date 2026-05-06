import math
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QMouseEvent, QCursor, QPainter
from src.ui.tools.event_handler import EventHandler
from src.utils.enums import ComponentEvent, IconType
from src.utils.helpers import dist, lerp, vec_len
from src.utils.logger import log
from src.ui.tools.registry import create_component


class MirrorPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("mirrorPage")
        self.setMouseTracking(True)
        self._locked = False
        self._lock_center = None
        self._last_global_pos = None

        self._key_w = False
        self._key_s = False
        self._key_a = False
        self._key_d = False

        self._handler = EventHandler()

        self._report_timer = QTimer(self)
        self._report_timer.timeout.connect(self._tick)
        self._report_timer.setInterval(16)

        self.setup_ui()
        self.setFocusPolicy(Qt.StrongFocus)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = JoystickLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

    def set_locked(self, locked: bool):
        self._locked = locked
        if locked:
            self._lock_center = self.mapToGlobal(self.rect().center())
            self._last_global_pos = QCursor.pos()
            self._report_timer.start()
            log.info(f"[MirrorTouch] 锁定, 窗口中心: {self.rect().center()}")
        else:
            self._report_timer.stop()
            self._lock_center = None
            self._last_global_pos = None
            self._key_w = self._key_s = self._key_a = self._key_d = False
            self._joystick.knob_x = self._joystick.x
            self._joystick.knob_y = self._joystick.y
            self.label.update()
            log.info("[MirrorTouch] 解锁, 摇杆回中")

    def _tick(self):
        if not self._locked:
            return
        dx, dy = 0, 0
        if self._key_w:
            dy -= 1
        if self._key_s:
            dy += 1
        if self._key_a:
            dx -= 1
        if self._key_d:
            dx += 1
        target_x, target_y = self._joystick.x, self._joystick.y
        if dx != 0 or dy != 0:
            dist_val = vec_len(dx, dy)
            target_x = self._joystick.x + int(dx / dist_val * self._joystick.max_knob_offset)
            target_y = self._joystick.y + int(dy / dist_val * self._joystick.max_knob_offset)
        self._joystick.knob_x += int(lerp(self._joystick.knob_x, target_x, 0.35))
        self._joystick.knob_y += int(lerp(self._joystick.knob_y, target_y, 0.35))
        self.label.update()

    def keyPressEvent(self, event):
        if not self._locked:
            super().keyPressEvent(event)
            return
        key = event.key()
        if key == Qt.Key_W:
            self._key_w = True
        elif key == Qt.Key_S:
            self._key_s = True
        elif key == Qt.Key_A:
            self._key_a = True
        elif key == Qt.Key_D:
            self._key_d = True
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if not self._locked:
            super().keyReleaseEvent(event)
            return
        key = event.key()
        if key == Qt.Key_W:
            self._key_w = False
        elif key == Qt.Key_S:
            self._key_s = False
        elif key == Qt.Key_A:
            self._key_a = False
        elif key == Qt.Key_D:
            self._key_d = False
        else:
            super().keyReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if self._locked:
            self._joystick.handle_mouse_press(event.x(), event.y(), event.button())

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._locked:
            self._joystick.handle_mouse_move(event.x(), event.y())

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._locked:
            self._joystick.handle_mouse_release(event.x(), event.y(), event.button())

    def _on_joystick_drag_move(self, component, px, py):
        offset_x = px - component.x
        offset_y = py - component.y
        dist_val = vec_len(offset_x, offset_y)
        if dist_val > component.max_knob_offset:
            ratio = component.max_knob_offset / dist_val if dist_val > 0 else 1.0
            offset_x *= ratio
            offset_y *= ratio
        component.knob_x = component.x + int(offset_x)
        component.knob_y = component.y + int(offset_y)

    def _on_joystick_drag_end(self, component, px, py):
        component.knob_x = component.x
        component.knob_y = component.y


class JoystickLabel(QLabel):
    def __init__(self, mirror_page):
        super().__init__()
        self._page = mirror_page
        self.setText("投屏画面区域\n(Scrcpy 画面将显示在此处)")
        self.setMouseTracking(True)
        self.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #888888;
                font-size: 18px;
                border: 2px dashed #444444;
                border-radius: 8px;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.end()