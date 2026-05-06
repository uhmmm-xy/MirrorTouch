import math
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from src.ui.tools.base_widget import BaseWidget
from src.utils.widgets_data import WidgetsData
from src.utils.enums import IconType
from src.ui.tools.registry import register_component


@register_component(IconType.RADIAL)
class RadialWidget(BaseWidget):
    """径向转盘：按住绑定键激活，鼠标角度选择 8 方向扇形"""

    def __init__(self, data: WidgetsData = None, parent=None, handler=None):
        super().__init__(data, parent, handler)
        self._active = False
        self._highlight_index = -1  # 0~7 高亮扇形，-1 无高亮
        self._accum_x = 0
        self._accum_y = 0

    # ── 激活状态 ──

    @property
    def active(self):
        return self._active

    def activate(self):
        self._active = True
        self._request_update()

    def deactivate(self):
        self._active = False
        self._highlight_index = -1
        self._request_update()

    # ── 鼠标角度更新 ──

    def update_angle(self, dx: int, dy: int):
        if not self._active:
            return

        self._accum_x += dx
        self._accum_y += dy

        self._accum_x = max(-25, min(25, self._accum_x))
        self._accum_y = max(-25, min(25, self._accum_y))

        if self._accum_x == 0 and self._accum_y == 0:
            self._highlight_index = -1
        else:
            angle = math.degrees(math.atan2(-self._accum_y, self._accum_x))
            if angle < 0:
                angle += 360
            self._highlight_index = int((angle + 22.5) % 360 // 45)

        self._request_update()

    # ── 绘制 ──

    def draw(self, painter: QPainter):
        self._draw_button(painter)
        if self._active:
            self._draw_radial(painter)
            

    def _draw_button(self, painter: QPainter):
        """未激活时绘制为普通圆形按钮"""
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
            from src.utils.key_descriptions import describe
            short = describe(self.data.key)
            painter.setPen(QColor(255, 255, 255, 220))
            font = QFont("Microsoft YaHei", max(8, int(s * 0.35)))
            painter.setFont(font)
            painter.drawText(QRectF(cx - half, cy - half, s, s), Qt.AlignCenter, short)

        painter.restore()

    def _draw_radial(self, painter: QPainter):
        if not self.parent:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.parent.screen_rect
        cx = rect.x() + rect.width() / 2
        cy = rect.y() + rect.height() / 2
        outer_r = rect.height() * 0.25
        inner_r = outer_r * 0.5

        # 底色圆环
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(30, 30, 30, 180)))
        painter.drawEllipse(int(cx - outer_r), int(cy - outer_r),
                            int(outer_r * 2), int(outer_r * 2))

        # 高亮扇形
        if 0 <= self._highlight_index < 8:
            start_deg = (self._highlight_index * 45 - 90 - 22.5)
            span_deg = 45

            path = QPainterPath()
            outer_rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
            inner_rect = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)

            # 外圆弧正向
            path.arcMoveTo(outer_rect, start_deg)
            path.arcTo(outer_rect, start_deg, span_deg)
            # 内圆弧反向
            path.arcTo(inner_rect, start_deg + span_deg, -span_deg)
            path.closeSubpath()

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 180, 80, 160)))
            painter.drawPath(path)

        # 分割线
        painter.setPen(QPen(QColor(255, 255, 255, 80), 1))
        for i in range(8):
            angle = math.radians(i * 45 - 90 - 22.5)
            x1 = cx + inner_r * math.cos(angle)
            y1 = cy + inner_r * math.sin(angle)
            x2 = cx + outer_r * math.cos(angle)
            y2 = cy + outer_r * math.sin(angle)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # 内外圆边框
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(int(cx - outer_r), int(cy - outer_r),
                            int(outer_r * 2), int(outer_r * 2))
        painter.drawEllipse(int(cx - inner_r), int(cy - inner_r),
                            int(inner_r * 2), int(inner_r * 2))

        painter.restore()