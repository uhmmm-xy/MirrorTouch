from PyQt5.QtCore import Qt, QPoint, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from src.utils.enums import TipStatus, ComponentEvent
from PyQt5.QtWidgets import QWidget

class BaseComponent:
    """组件父类，通过 EventHandler 回调分发事件"""

    def __init__(self, x: int, y: int, size: int = 80,
                 name: str = "", icon_type=None, parent=None,
                 handler=None):
        self.x = x
        self.y = y
        self.size = size
        self.name = name
        self.tip_status = TipStatus.UNSELECTED
        self.icon_type = icon_type
        self.parent = parent
        self.handler = handler
        self._children: list["BaseComponent"] = []

        self._dragging = False
        self._drag_offset = QPoint()
        self._hovered = False

    # ── 事件注册 ──

    def on(self, event: ComponentEvent, callback):
        if self.handler:
            self.handler.register(self, event, callback)
        return self

    def off(self, event: ComponentEvent = None):
        if self.handler:
            self.handler.unregister(self, event)
        return self

    # ── 几何 ──

    def rect(self) -> QRectF:
        half = self.size / 2
        return QRectF(self.x - half, self.y - half, self.size, self.size)

    def contains(self, px: int, py: int) -> bool:
        return self.rect().contains(px, py)

    # ── 移动（子类可覆盖，处理子组件跟随） ──

    def move_to(self, new_x: int, new_y: int):
        """移动组件到新坐标（子类覆盖以联动子组件）"""
        self.x = new_x
        self.y = new_y
        self._request_update()

    def move_by(self, dx: int, dy: int):
        """相对位移"""
        self.move_to(self.x + dx, self.y + dy)

    def add_child(self, child: "BaseComponent"):
        child.parent = self
        self._children.append(child)


    # ── 鼠标事件入口 ──

    def handle_mouse_press(self, px: int, py: int, button):
        if button == Qt.LeftButton and self.contains(px, py):
            self._dragging = True
            self._drag_offset = QPoint(self.x - px, self.y - py)
            self.tip_status = TipStatus.DRAG
            self._dispatch(ComponentEvent.DRAG_START, px, py)
            return True

        if button == Qt.RightButton and self.contains(px, py):
            self.tip_status = TipStatus.RIGHT_CLICK
            self._dispatch(ComponentEvent.RIGHT_CLICK, px, py)
            return True

        self.tip_status = TipStatus.UNSELECTED
        return False

    def handle_mouse_move(self, px: int, py: int):
        if self._dragging:
            new_x = px + self._drag_offset.x()
            new_y = py + self._drag_offset.y()
            self.move_to(new_x, new_y)
            self._dispatch(ComponentEvent.DRAG_MOVE, px, py)

        elif self.tip_status == TipStatus.RIGHT_CLICK:
            dx = px - self.x
            dy = py - self.y
            self.size = max(20, int((abs(dx) + abs(dy)) / 2))
            self._dispatch(ComponentEvent.RIGHT_DRAG, px, py)
            self._request_update()

        else:
            was_hovered = self._hovered
            self._hovered = self.contains(px, py)
            if self._hovered and not was_hovered:
                self._dispatch(ComponentEvent.HOVER_ENTER, px, py)
            elif not self._hovered and was_hovered:
                self._dispatch(ComponentEvent.HOVER_LEAVE, px, py)

    def handle_mouse_release(self, px: int, py: int, button):
        if button == Qt.LeftButton and self._dragging:
            self._dragging = False
            self.tip_status = TipStatus.UNSELECTED
            self._dispatch(ComponentEvent.DRAG_END, px, py)
            self._request_update()
            return True

        if button == Qt.RightButton and self.tip_status == TipStatus.RIGHT_CLICK:
            self.tip_status = TipStatus.UNSELECTED
            self._dispatch(ComponentEvent.RIGHT_RELEASE, px, py)
            self._request_update()
            return True

        return False

    def handle_click(self):
        self.tip_status = TipStatus.CLICK
        self._dispatch(ComponentEvent.CLICK)

    # ── 绘制 ──

    def draw(self, painter: QPainter):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        cx, cy, s = self.x, self.y, self.size
        half = s / 2

        painter.setPen(QPen(QColor(255, 255, 255, 100), 2))
        painter.setBrush(QBrush(QColor(255, 255, 255, 15)))
        painter.drawEllipse(int(cx - half), int(cy - half), int(s), int(s))

        mid = s * 0.55
        mid_half = mid / 2
        painter.setPen(QPen(QColor(255, 255, 255, 70), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(int(cx - mid_half), int(cy - mid_half), int(mid), int(mid))

        inner = s * 0.15
        inner_half = inner / 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 180)))
        painter.drawEllipse(int(cx - inner_half), int(cy - inner_half), int(inner), int(inner))

        if self.name:
            painter.setPen(QColor(255, 255, 255, 200))
            font = QFont("Microsoft YaHei", 10)
            painter.setFont(font)
            text_y = int(cy + half + 16)
            painter.drawText(QRectF(cx - 40, text_y, 80, 20), Qt.AlignCenter, self.name)

        painter.restore()

    def _dispatch(self, event: ComponentEvent, *args):
        if self.handler:
            self.handler.dispatch(self, event, *args)

    def _request_update(self):
        node = self.parent
        while node:
            if isinstance(node, QWidget):
                node.update()
                return
            node = getattr(node, 'parent', None)

    @property
    def is_dragging(self):
        return self._dragging

    @property
    def is_hovered(self):
        return self._hovered
    
    @property
    def children(self):
        return self._children