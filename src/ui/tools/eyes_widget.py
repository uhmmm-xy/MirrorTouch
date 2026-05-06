"""EyesWidget — 视角控件（田字格 + 测试模式轨迹）

每个 Screen 最多一个 Eyes 组件。
不绑定键盘按键，坐标绑定在 mouseMoveMap。
测试模式：鼠标在 Eyes 内自由移动，绘制 2s 轨迹线（0.5s 淡出），触碰边界跳对角象限。
"""

import math, random, time
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from src.ui.tools.base_widget import BaseWidget
from src.ui.abilities import Selectable, Draggable
from src.utils.helpers import clamp
from src.utils.enums import IconType
from src.ui.tools.registry import register_component
from src.utils.widgets_data import WidgetsData


@register_component(IconType.EYES)
class EyesWidget(BaseWidget, Selectable, Draggable):
    """视角控件：田字格四象限 + 测试模式轨迹"""

    TRAIL_MAX_MS = 2000    # 轨迹点最长保留时间
    TRAIL_FADE_MS = 500    # 轨迹淡出时长

    def __init__(self, data: WidgetsData, parent=None, handler=None):
        super().__init__(data, parent, handler)
        # 测试模式轨迹历史：(global_x, global_y, timestamp_ms)
        self._trail: list[tuple[float, float, float]] = []
        self._test_center_x: float = 0
        self._test_center_y: float = 0

    # ── 绘制：田字格 ──

    def draw(self, painter: QPainter):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        cx, cy, s = self.x, self.y, self.size
        half = s / 2

        # ── 底色 ──
        if self.is_hold:
            bg = QColor(255, 160, 60, 30)
        else:
            bg = QColor(100, 180, 255, 20)
        painter.setPen(QPen(QColor(100, 180, 255, 80), 1))
        painter.setBrush(QBrush(bg))
        painter.drawRect(int(cx - half), int(cy - half), int(s), int(s))

        # ── 四象限分割线 ──
        painter.setPen(QPen(QColor(100, 180, 255, 100), 1))
        painter.drawLine(int(cx - half), int(cy), int(cx + half), int(cy))  # 横线
        painter.drawLine(int(cx), int(cy - half), int(cx), int(cy + half))  # 竖线

        # ── 四象限微色 ──
        qw, qh = half, half
        colors = [
            QColor(100, 180, 255, 15),  # Q1 右上
            QColor(180, 130, 255, 15),  # Q2 左上
            QColor(255, 160, 100, 15),  # Q3 左下
            QColor(130, 200, 130, 15),  # Q4 右下
        ]
        quadrants = [
            (cx, cy - qh, qw, qh),           # Q1
            (cx - qw, cy - qh, qw, qh),      # Q2
            (cx - qw, cy, qw, qh),           # Q3
            (cx, cy, qw, qh),                # Q4
        ]
        for i, (qx, qy, qw_i, qh_i) in enumerate(quadrants):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(colors[i]))
            painter.drawRect(int(qx), int(qy), int(qw_i), int(qh_i))

        # ── 中心十字 ──
        cross = max(4, int(s * 0.06))
        painter.setPen(QPen(QColor(200, 200, 200, 180), 2))
        painter.drawLine(int(cx - cross), int(cy), int(cx + cross), int(cy))
        painter.drawLine(int(cx), int(cy - cross), int(cx), int(cy + cross))

        # ── 外框高亮 ──
        if self.is_hold:
            painter.setPen(QPen(QColor(255, 160, 60), 2))
        else:
            painter.setPen(QPen(QColor(100, 180, 255), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(int(cx - half), int(cy - half), int(s), int(s))

        # ── 标签 ──
        if self.data and self.data.comment:
            painter.setPen(QColor(200, 200, 200, 180))
            font = QFont("Microsoft YaHei", max(6, int(s * 0.18)))
            painter.setFont(font)
            painter.drawText(
                QRectF(cx - half, cy + half + 2, s, half * 0.5),
                Qt.AlignCenter, self.data.comment
            )

        # ── 测试模式轨迹 ──
        self._draw_trail(painter)

        painter.restore()

    def _draw_trail(self, painter: QPainter):
        """绘制轨迹路径线（2s 保留，0.5s 淡出）"""
        now = time.time() * 1000
        # 清理过期轨迹点
        self._trail = [p for p in self._trail if now - p[2] < self.TRAIL_MAX_MS]
        if len(self._trail) < 2:
            return

        for i in range(1, len(self._trail)):
            x1, y1, t1 = self._trail[i - 1]
            x2, y2, t2 = self._trail[i]
            age = now - t2
            if age > self.TRAIL_FADE_MS:
                alpha = max(0, int(200 * (1 - (age - self.TRAIL_FADE_MS) / (self.TRAIL_MAX_MS - self.TRAIL_FADE_MS))))
            else:
                alpha = 200
            if alpha <= 0:
                continue
            painter.setPen(QPen(QColor(255, 255, 100, alpha), 2))
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # 当前位置圆点
        last_x, last_y, _ = self._trail[-1]
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 100, 200)))
        painter.drawEllipse(int(last_x - 3), int(last_y - 3), 6, 6)

    # ── 测试模式：边缘跳转 ──

    def move_to(self, new_x: int, new_y: int):
        """移动时同步 screen.mouse_move_start"""
        super().move_to(new_x, new_y)
        if self.data and self.parent:
            self.parent.mouse_move_start = (self.data.pos_x, self.data.pos_y)

    def test_update_trail(self, local_x: float, local_y: float) -> bool:
        """更新轨迹。鼠标在 Eyes 内自由移动，触碰边界跳转。

        local_x, local_y: Canvas 内鼠标局部坐标（像素）
        Returns: True 已触发跳转
        """
        now = time.time() * 1000
        cx = self._test_center_x
        cy = self._test_center_y
        half = self.size / 2

        # 记录轨迹点（Canvas 局部坐标）
        self._trail.append((local_x, local_y, now))

        # 检测是否触碰 Eyes 边界
        dx = local_x - cx
        dy = local_y - cy
        if abs(dx) >= half or abs(dy) >= half:
            self._jump_to_opposite(cx, cy, dx, dy)
            self._trail.clear()
            return True
        return False

    def _jump_to_opposite(self, cx: float, cy: float, dx: int, dy: int):
        """跳转到对角象限随机点，通过 QCursor 移动"""
        half = self.size / 2
        if dx >= 0 and dy < 0:      # Q1 → Q3
            qx_min, qx_max = -half, 0
            qy_min, qy_max = 0, half
        elif dx < 0 and dy < 0:     # Q2 → Q4
            qx_min, qx_max = 0, half
            qy_min, qy_max = 0, half
        elif dx < 0 and dy >= 0:    # Q3 → Q1
            qx_min, qx_max = 0, half
            qy_min, qy_max = -half, 0
        else:                       # Q4 → Q2
            qx_min, qx_max = -half, 0
            qy_min, qy_max = -half, 0

        angle = random.uniform(0, math.pi / 2)
        target_dist = half * random.uniform(0.2, 0.8)
        new_dx = int(qx_min + abs(math.cos(angle)) * (qx_max - qx_min))
        new_dy = int(qy_min + abs(math.sin(angle)) * (qy_max - qy_min))
        new_dx = clamp(new_dx, int(qx_min), int(qx_max))
        new_dy = clamp(new_dy, int(qy_min), int(qy_max))

        # 转为全局坐标移动鼠标
        from PyQt5.QtGui import QCursor
        cur = QCursor.pos()
        offset_x = new_dx - dx  # Canvas 内偏移量
        offset_y = new_dy - dy
        QCursor.setPos(cur.x() + offset_x, cur.y() + offset_y)

    def set_test_center(self, canvas_cx: float, canvas_cy: float):
        """设置测试模式下的 Eyes 中心（Canvas 坐标）"""
        self._test_center_x = canvas_cx
        self._test_center_y = canvas_cy

    def reset_test_trail(self):
        """清除轨迹"""
        self._trail.clear()
