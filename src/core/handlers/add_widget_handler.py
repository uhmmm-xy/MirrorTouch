"""AddWidgetHandler — 添加控件 Handler（Canvas 内按钮）

优先级 5：在选中/拖拽之前处理。
Canvas 头部绘制 [+] 添加按钮，支持点击创建 + 拖入创建。
"""

from PyQt5.QtCore import QPoint, Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from src.core.handlers.base_handler import BaseHandler
from src.utils.widgets_data import WidgetsData, WidgetType


class AddWidgetHandler(BaseHandler):
    """Canvas 内添加控件按钮

    交互:
        - 点击按钮 → Screen 中心创建 CLICK 组件
        - 从按钮拖入 Screen → 落点创建组件
    """

    priority: int = 5

    # Canvas 头部区域布局常量
    HEADER_H = 48
    BTN_X = 12
    BTN_Y = 8
    BTN_W = 104
    BTN_H = 32

    def __init__(self, undo_handler: "UndoHandler" = None):
        super().__init__()
        self._enabled = True
        self._tracking = False
        self._drag_pos: QPoint | None = None
        self._undo = undo_handler

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    # ── 鼠标事件 ──

    def on_press(self, pos: QPoint, button: Qt.MouseButton,
                 screen: "ScreenComponent", canvas: "QWidget") -> bool:
        if not self._enabled or button != Qt.LeftButton:
            return self.PASS
        if not self._button_rect().contains(pos):
            return self.PASS

        self._tracking = True
        self._drag_pos = QPoint(pos)
        return self.HANDLED  # 阻止 SelectHandler 等

    def on_move(self, pos: QPoint,
                screen: "ScreenComponent", canvas: "QWidget") -> bool:
        if not self._tracking:
            return self.PASS
        self._drag_pos = QPoint(pos)
        screen._request_update()
        return self.HANDLED  # 拖拽中，阻止其他 handler

    def on_release(self, pos: QPoint, button: Qt.MouseButton,
                   screen: "ScreenComponent", canvas: "QWidget") -> bool:
        if not self._tracking or button != Qt.LeftButton:
            return self.PASS

        self._tracking = False
        self._drag_pos = None

        # 添加前记录快照
        if self._undo:
            self._undo.record(screen)

        # 判断落点：Screen 内 → 落点创建；按钮上 → 中心创建
        if screen.screen_rect.contains(pos):
            rx, ry = screen.local_to_screen(pos.x(), pos.y())
            self._create_at(screen, rx, ry)
        else:
            self._create_at(screen, 0.5, 0.5)

        return self.HANDLED

    # ── 内部 ──

    def _create_at(self, screen: "ScreenComponent", rx: float, ry: float):
        """在指定相对坐标创建 CLICK 组件并自动选中"""
        from src.utils.enums import WidgetType
        data = WidgetsData(
            key="",
            comment="新控件",
            widget_type=WidgetType.CLICK,
            pos_x=rx,
            pos_y=ry,
            scale_size=0.05,
        )
        widget = screen._create_widget(data)
        screen.add_widget(widget)
        screen.relayout_widgets()
        screen.select_widget(widget)
        screen._request_update()

    def create_eyes(self, screen: "ScreenComponent", rx: float, ry: float):
        """创建 Eyes 控件（单例：移除旧的再创建新的）"""
        from src.utils.enums import WidgetType
        from src.ui.tools.eyes_widget import EyesWidget

        # 移除旧 Eyes
        for child in list(screen.children):
            if isinstance(child, EyesWidget):
                screen.remove_widget(child)

        data = WidgetsData(
            key="",
            comment="视角",
            widget_type=WidgetType.EYES,
            pos_x=rx,
            pos_y=ry,
            scale_size=0.08,
        )
        widget = screen._create_widget(data)
        screen.add_widget(widget)
        screen.relayout_widgets()

        # 同步 mouseMoveMap
        screen.mouse_move_start = (rx, ry)

        screen.select_widget(widget)
        screen._request_update()

    # ── 按钮区域 ──

    def _button_rect(self) -> QRectF:
        return QRectF(self.BTN_X, self.BTN_Y, self.BTN_W, self.BTN_H)

    # ── 绘制 ──

    def draw_overlay(self, painter: QPainter,
                     screen: "ScreenComponent"):
        """在 Canvas 头部绘制添加按钮 + 拖拽时的幽灵圆圈"""
        if not self._enabled:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # ── 添加按钮 ──
        r = self._button_rect()
        rx, ry, rw, rh = int(r.x()), int(r.y()), int(r.width()), int(r.height())
        painter.setPen(QPen(QColor(100, 200, 100), 1))
        painter.setBrush(QBrush(QColor(100, 200, 100, 40)))
        painter.drawRoundedRect(rx, ry, rw, rh, 6, 6)
        painter.setPen(QColor(200, 255, 200))
        font = QFont("Microsoft YaHei", 10)
        painter.setFont(font)
        painter.drawText(QRectF(rx, ry, rw, rh), Qt.AlignCenter, "+ 添加控件")

        # ── 拖拽幽灵圆圈 ──
        if self._tracking and self._drag_pos and screen.screen_rect.contains(self._drag_pos):
            ghost_r = int(screen.size * 0.05)
            cx, cy = self._drag_pos.x(), self._drag_pos.y()
            painter.setPen(QPen(QColor(100, 200, 100, 180), 2))
            painter.setBrush(QBrush(QColor(100, 200, 100, 60)))
            painter.drawEllipse(cx - ghost_r, cy - ghost_r, ghost_r * 2, ghost_r * 2)

        painter.restore()

        return self.PASS
