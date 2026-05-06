import math
from PyQt5.QtCore import Qt, QRectF, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont
from src.ui.tools.base_widget import BaseWidget
from src.utils.widgets_data import WidgetsData, WidgetType
from src.utils.enums import IconType
from src.ui.tools.registry import register_component


@register_component(IconType.JOYSTICK)
class JoystickComponent(BaseWidget):
    """摇杆控件：三圈同心圆 + 摇杆头 + 月牙高光"""

    def __init__(self, data: WidgetsData = None, parent=None, handler=None):
        super().__init__(data, parent, handler)
        self.knob_x = None
        self.knob_y = None
        self._target_x = None
        self._target_y = None
        self._is_turbo = False
        self._is_creep = False

        self._anim_timer = QTimer()
        self._anim_timer.timeout.connect(self._animate_step)
        self._anim_timer.setInterval(16)  # ~60fps

    # ── 运行时状态 ──

    @property
    def is_turbo(self):
        return self._is_turbo

    @is_turbo.setter
    def is_turbo(self, value: bool):
        if self._is_turbo != value:
            self._is_turbo = value
            self._recalc_target()
            self._request_update()

    @property
    def is_creep(self):
        return self._is_creep

    @is_creep.setter
    def is_creep(self, value: bool):
        if self._is_creep != value:
            self._is_creep = value
            self._recalc_target()
            self._request_update()

    # ── 半径属性 ──

    @property
    def r_mid(self):
        return self.size // 2

    @property
    def r_outer(self):
        return int(self.r_mid * 1.5)

    @property
    def r_inner(self):
        return int(self.r_mid * 0.65)

    @property
    def knob_radius(self):
        return int(self.size * 0.19)

    # ── 当前最大偏移 ──

    def _draw_radii(self):
        """返回 (r_outer_draw, r_inner_draw)，与 _draw_base 保持一致"""
        turbo_offset = self.data.turbo_offset if self.data else 0.2
        creep_offset = self.data.creep_offset if self.data else 0.1
        r_outer_draw = self.r_mid + int(self.r_mid * turbo_offset)
        r_inner_draw = max(int(self.r_mid * creep_offset), int(self.r_mid * 0.1))
        return r_outer_draw, r_inner_draw

    @property
    def max_knob_offset(self):
        """摇杆头圆心到当前激活圈边缘的最大距离"""
        r_outer_draw, r_inner_draw = self._draw_radii()
        if self._is_turbo:
            return r_outer_draw
        if self._is_creep:
            return r_inner_draw
        return self.r_mid

    # ── 动画 ──

    def _animate_step(self):
        if self.knob_x is None or self._target_x is None:
            self._anim_timer.stop()
            return

        lerp_factor = 0.3
        new_x = self.knob_x + (self._target_x - self.knob_x) * lerp_factor
        new_y = self.knob_y + (self._target_y - self.knob_y) * lerp_factor

        if abs(new_x - self._target_x) < 0.5 and abs(new_y - self._target_y) < 0.5:
            self.knob_x = self._target_x
            self.knob_y = self._target_y
            self._anim_timer.stop()
        else:
            self.knob_x = new_x
            self.knob_y = new_y

        self._request_update()

    def _set_target(self, tx, ty):
        self._target_x = tx
        self._target_y = ty
        if self.knob_x is None:
            self.knob_x = self.x
            self.knob_y = self.y
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def _recalc_target(self):
        """范围切换时重新计算目标位置（保持方向不变）"""
        if self._target_x is None:
            return
        dx = self._target_x - self.x
        dy = self._target_y - self.y
        if dx == 0 and dy == 0:
            return
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1:
            return
        max_offset = self.max_knob_offset
        self._target_x = self.x + int(dx / length * max_offset)
        self._target_y = self.y + int(dy / length * max_offset)
        if self.knob_x is None:
            self.knob_x = self.x
            self.knob_y = self.y
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    # ── 按键驱动 ──

    def set_direction(self, dx: float, dy: float):
        """设置摇杆头方向 (-1~1 归一化)，(0,0) 回中"""
        if dx == 0 and dy == 0:
            self._target_x = self.x
            self._target_y = self.y
        else:
            length = math.sqrt(dx * dx + dy * dy)
            if length > 1.0:
                dx /= length
                dy /= length
            max_offset = self.max_knob_offset
            self._target_x = self.x + int(dx * max_offset)
            self._target_y = self.y + int(dy * max_offset)
        self._set_target(self._target_x, self._target_y)

    def reset_knob(self):
        """摇杆头回中"""
        self._target_x = self.x
        self._target_y = self.y
        self._set_target(self._target_x, self._target_y)

    # ── move_to ──

    def move_to(self, new_x: int, new_y: int):
        delta_x = new_x - self.x
        delta_y = new_y - self.y
        if self.knob_x is not None:
            self.knob_x += delta_x
        if self.knob_y is not None:
            self.knob_y += delta_y
        if self._target_x is not None:
            self._target_x += delta_x
        if self._target_y is not None:
            self._target_y += delta_y
        super().move_to(new_x, new_y)

    # ── 绘制 ──

    def draw(self, painter: QPainter):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        self._draw_base(painter)
        self._draw_knob(painter)
        painter.restore()

    def _draw_base(self, painter: QPainter):
        cx, cy = self.x, self.y

        r_outer_draw, r_inner_draw = self._draw_radii()

        # 外圈
        if self._is_turbo:
            painter.setPen(QPen(QColor(255, 180, 80, 180), 2))
            painter.setBrush(QBrush(QColor(255, 180, 80, 30)))
        else:
            painter.setPen(QPen(QColor(255, 180, 80, 50), 1))
            painter.setBrush(QBrush(QColor(255, 180, 80, 8)))
        painter.drawEllipse(cx - r_outer_draw, cy - r_outer_draw,
                            r_outer_draw * 2, r_outer_draw * 2)

        # 中圈
        if not self._is_turbo and not self._is_creep:
            painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
            painter.setBrush(QBrush(QColor(255, 255, 255, 30)))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 50), 2))
            painter.setBrush(QBrush(QColor(255, 255, 255, 12)))
        painter.drawEllipse(cx - self.r_mid, cy - self.r_mid,
                            self.r_mid * 2, self.r_mid * 2)

        # 内圈
        if self._is_creep:
            painter.setPen(QPen(QColor(100, 200, 255, 180), 2))
            painter.setBrush(QBrush(QColor(100, 200, 255, 30)))
        else:
            painter.setPen(QPen(QColor(100, 200, 255, 50), 1))
            painter.setBrush(QBrush(QColor(100, 200, 255, 8)))
        painter.drawEllipse(cx - r_inner_draw, cy - r_inner_draw,
                            r_inner_draw * 2, r_inner_draw * 2)

        # 十字线
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
        painter.drawLine(cx - self.r_mid, cy, cx + self.r_mid, cy)
        painter.drawLine(cx, cy - self.r_mid, cx, cy + self.r_mid)

    def _draw_knob(self, painter: QPainter):
        kx = int(self.knob_x) if self.knob_x is not None else self.x
        ky = int(self.knob_y) if self.knob_y is not None else self.y
        kr = self.knob_radius
        knob_color = QColor(100, 180, 255, 180)

        painter.setPen(QPen(QColor(100, 180, 255), 2))
        painter.setBrush(QBrush(knob_color))
        painter.drawEllipse(kx - kr, ky - kr, kr * 2, kr * 2)

        self._draw_highlight(painter, kx, ky, kr)

        if self.data.comment:
            painter.setPen(QColor(255, 255, 255, 180))
            font = QFont("Microsoft YaHei", max(8, int(self.size * 0.12)))
            painter.setFont(font)
            painter.drawText(QRectF(self.x - self.r_outer, self.y + self.r_outer + 4,
                                    self.r_outer * 2, 16),
                             Qt.AlignCenter, self.data.comment)

    def _draw_highlight(self, painter: QPainter, kx: int, ky: int, kr: int):
        angle = math.radians(30)
        offset = int(kr * 0.65)
        hx = kx + offset * math.cos(angle)
        hy = ky - offset * math.sin(angle)
        hr = int(kr * 0.30)

        highlight_path = QPainterPath()
        highlight_path.addEllipse(hx - hr, hy - hr, hr * 2, hr * 2)

        cut_r = int(hr * 1.3)
        cut_x = hx - int(hr * 0.5)
        cut_y = hy + int(hr * 0.5)
        cut_path = QPainterPath()
        cut_path.addEllipse(cut_x - cut_r, cut_y - cut_r, cut_r * 2, cut_r * 2)

        moon_path = highlight_path.subtracted(cut_path)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 120)))
        painter.drawPath(moon_path)