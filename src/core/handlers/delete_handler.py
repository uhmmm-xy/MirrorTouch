"""DeleteHandler — 拖出删除 Handler

优先级 5：在 DragHandler(15) 之前处理 release 事件。
拖拽控件到下方删除区域 → 悬停变红 → 松手删除。
"""

from PyQt5.QtCore import QPoint, Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from src.core.handlers.base_handler import BaseHandler


class DeleteHandler(BaseHandler):
    """拖出 Screen 删除控件

    视觉状态:
        - 默认:      灰色虚线边框 + "拖至此处删除"
        - 拖入悬停:  红色背景 + "松手删除"
    """

    priority: int = 5

    ZONE_HEIGHT = 56      # 删除区域高度
    BOTTOM_MARGIN = 72    # 距 Canvas 底部距离（Footer 区）

    def __init__(self, drag_handler: "DragHandler" = None):
        super().__init__()
        self._drag_handler = drag_handler
        self._enabled = True
        self._zone_rect: QRectF = QRectF()    # 当前删除区域
        self._is_hovering = False              # 鼠标是否在删除区域内

    # ── 启用控制 ──

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    # ── 区域计算（由 TouchCanvas resize/repaint 时调用） ──

    def update_zone(self, canvas_width: int, canvas_height: int):
        """更新删除区域矩形"""
        zone_y = canvas_height - self.BOTTOM_MARGIN
        zone_x = 20
        zone_w = canvas_width - 40
        self._zone_rect = QRectF(zone_x, zone_y, zone_w, self.ZONE_HEIGHT)

    # ── 鼠标事件 ──

    def on_move(self, pos: QPoint,
                screen: "ScreenComponent", canvas: "QWidget") -> bool:
        if not self._enabled or self._zone_rect.isEmpty():
            return self.PASS

        was_hovering = self._is_hovering
        self._is_hovering = self._zone_rect.contains(pos)
        if self._is_hovering != was_hovering:
            screen._request_update()
        return self.PASS  # 不阻断，让 DragHandler 继续

    def on_release(self, pos: QPoint, button: Qt.MouseButton,
                   screen: "ScreenComponent", canvas: "QWidget") -> bool:
        if button != Qt.LeftButton or not self._enabled:
            return self.PASS

        # 检查：正在拖拽 + 松手在删除区域 + 有选中控件
        is_dragging = self._drag_handler and self._drag_handler.is_dragging
        in_zone = self._zone_rect.contains(pos) if not self._zone_rect.isEmpty() else False
        widget = screen.selected_widget

        if is_dragging and in_zone and widget is not None:
            screen.remove_widget(widget)
            screen.selected_widget = None
            self._is_hovering = False
            screen._request_update()
            return self.HANDLED

        self._is_hovering = False
        return self.PASS

    # ── 覆盖层绘制 ──

    def draw_overlay(self, painter: QPainter,
                     screen: "ScreenComponent"):
        if not self._enabled or self._zone_rect.isEmpty():
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        is_dragging = self._drag_handler and self._drag_handler.is_dragging
        active = is_dragging and self._is_hovering

        rect = self._zone_rect
        rx, ry, rw, rh = int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height())

        # 背景
        if active:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(220, 50, 50, 60)))
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 8)))
        painter.drawRoundedRect(rx, ry, rw, rh, 8, 8)

        # 虚线边框
        pen = QPen()
        pen.setStyle(Qt.DashLine)
        if active:
            pen.setColor(QColor(255, 80, 80, 180))
        else:
            pen.setColor(QColor(150, 150, 150, 100))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rx, ry, rw, rh, 8, 8)

        # 文字
        if active:
            text = "松手删除"
            text_color = QColor(255, 100, 100)
        else:
            text = "拖至此处删除"
            text_color = QColor(150, 150, 150)

        painter.setPen(text_color)
        font = QFont("Microsoft YaHei", 12)
        painter.setFont(font)
        painter.drawText(QRectF(rx, ry, rw, rh), Qt.AlignCenter, text)

        painter.restore()
