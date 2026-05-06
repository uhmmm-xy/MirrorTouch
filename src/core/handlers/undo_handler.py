"""UndoHandler — 撤销系统 Handler

优先级 5：绘制撤销按钮 + 处理点击撤销。
最多缓存 30 步 WidgetsData 快照。
"""

from PyQt5.QtCore import QPoint, Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from src.core.handlers.base_handler import BaseHandler
from src.utils.widgets_data import WidgetsData


class UndoHandler(BaseHandler):
    """撤销系统：快照栈 + Canvas 内撤销按钮

    使用方式:
        handler.record(screen)   — 记录快照
        handler.clear()          — 清空栈（导出 JSON 后）
        handler.can_undo         — 是否可撤销
    """

    priority: int = 5

    # Canvas 头部区域布局常量
    HEADER_H = 48
    BTN_X = 124
    BTN_Y = 8
    BTN_W = 76
    BTN_H = 32

    def __init__(self):
        super().__init__()
        self._stack: list[list[dict]] = []
        self._max_steps = 30
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    # ── API ──

    def record(self, screen: "ScreenComponent"):
        """记录当前所有控件的 WidgetsData 快照"""
        snapshot = [w.data.to_dict() for w in screen.children]
        self._stack.append(snapshot)
        if len(self._stack) > self._max_steps:
            self._stack.pop(0)
        screen._request_update()

    def clear(self):
        """清空撤销栈（导出 JSON 后调用）"""
        self._stack.clear()

    @property
    def can_undo(self) -> bool:
        return len(self._stack) > 0

    # ── 鼠标事件 ──

    def on_press(self, pos: QPoint, button: Qt.MouseButton,
                 screen: "ScreenComponent", canvas: "QWidget") -> bool:
        if button != Qt.LeftButton:
            return self.PASS
        if not self._hit_button(pos):
            return self.PASS
        if not self.can_undo:
            return self.PASS

        # 当前 snap 是 mousePressEvent 为本次点击记录的（= 当前状态）
        # 先弹出它，再取真正的上一个快照恢复
        self._stack.pop()
        if not self._stack:
            screen._request_update()
            return self.HANDLED

        # 执行撤销
        snapshot = self._stack.pop()
        screen.clear_widgets()
        for item in snapshot:
            data = WidgetsData.from_dict(item)
            screen.add_widget(screen._create_widget(data))
        screen.relayout_widgets()
        screen.selected_widget = None
        screen._request_update()
        return self.HANDLED

    # ── 按钮区域 ──

    def _button_rect(self) -> QRectF:
        return QRectF(self.BTN_X, self.BTN_Y, self.BTN_W, self.BTN_H)

    def _hit_button(self, pos: QPoint) -> bool:
        return self._button_rect().contains(pos)

    # ── 绘制 ──

    def draw_overlay(self, painter: QPainter,
                     screen: "ScreenComponent"):
        """在 Canvas 头部区域绘制撤销按钮"""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        r = self._button_rect()
        rx, ry, rw, rh = int(r.x()), int(r.y()), int(r.width()), int(r.height())

        # 按钮背景
        if self.can_undo:
            painter.setPen(QPen(QColor(100, 180, 255), 1))
            painter.setBrush(QBrush(QColor(100, 180, 255, 40)))
        else:
            painter.setPen(QPen(QColor(80, 80, 80), 1))
            painter.setBrush(QBrush(QColor(60, 60, 60, 60)))

        painter.drawRoundedRect(rx, ry, rw, rh, 6, 6)

        # 按钮文字
        text_color = QColor(200, 200, 200) if self.can_undo else QColor(100, 100, 100)
        painter.setPen(text_color)
        font = QFont("Microsoft YaHei", 10)
        painter.setFont(font)
        painter.drawText(QRectF(rx, ry, rw, rh), Qt.AlignCenter, "撤销")

        painter.restore()
