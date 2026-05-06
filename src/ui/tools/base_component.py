from PyQt5.QtCore import Qt, QPoint, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from src.utils.enums import TipStatus, ComponentEvent
from PyQt5.QtWidgets import QWidget

class BaseComponent:
    """组件父类 —— 纯 View 层

    职责：几何 + 层级 + 绘制 + 事件回调分发。
    交互逻辑（选中/拖拽/缩放）交由 Handler 通过 Ability 接口处理。
    """

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

    # ── 内部工具 ──

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

    # ── 属性 ──

    @property
    def is_hovered(self):
        return self._hovered

    @property
    def children(self):
        return self._children
