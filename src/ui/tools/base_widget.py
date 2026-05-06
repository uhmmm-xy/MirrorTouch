from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from src.ui.tools.base_component import BaseComponent
from src.utils.widgets_data import WidgetsData, WidgetType
from src.utils.key_descriptions import describe


class BaseWidget(BaseComponent):
    """ScreenComponent 专用控件基类"""

    def __init__(self, data: WidgetsData, parent=None, handler=None):
        from src.ui.tools.screen_component import ScreenComponent
        if parent is not None and not isinstance(parent, ScreenComponent):
            raise TypeError(f"BaseWidget 的 parent 必须是 ScreenComponent, 实际为 {type(parent).__name__}")
        super().__init__(
            x=0, y=0, size=36,
            name=data.comment or data.key,
            icon_type=None,
            parent=parent,
            handler=handler
        )
        self.data = data
        self.is_hold = False       # 运行时高亮状态（选中或测试模式激活）

    def draw(self, painter: QPainter):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        cx, cy, s = self.x, self.y, self.size
        half = s / 2

        if self.is_hold:
            base_color = QColor(255, 160, 60, 200)
            border_color = QColor(255, 160, 60)
        else:
            base_color = QColor(100, 180, 255, 160)
            border_color = QColor(100, 180, 255)

        painter.setPen(QPen(border_color, 2))
        painter.setBrush(QBrush(base_color))
        painter.drawEllipse(int(cx - half), int(cy - half), int(s), int(s))

        if self.data:
            short = describe(self.data.key)
            painter.setPen(QColor(255, 255, 255, 220))
            font = QFont("Microsoft YaHei", max(8, int(s * 0.35)))
            painter.setFont(font)
            painter.drawText(QRectF(cx - half, cy - half, s, s), Qt.AlignCenter, short)

            if self.data.comment and self.data.comment != self.data.key:
                painter.setPen(QColor(200, 200, 200, 180))
                font_small = QFont("Microsoft YaHei", max(6, int(s * 0.22)))
                painter.setFont(font_small)
                painter.drawText(
                    QRectF(cx - half, cy + half + 2, s, half * 0.6),
                    Qt.AlignCenter, self.data.comment
                )

        painter.restore()

    def move_to(self, new_x: int, new_y: int):
        super().move_to(new_x, new_y)
        if self.data and self.parent:
            rx, ry = self.parent.local_to_screen(self.x, self.y)
            self.data.pos_x = rx
            self.data.pos_y = ry