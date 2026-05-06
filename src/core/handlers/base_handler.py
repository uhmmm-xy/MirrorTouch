"""Handler 基类 —— 统一事件处理接口

所有 Handler 继承此类，按 priority 排序后链式调用。
返回值 HANDLED 阻止后续 handler，PASS 继续传递。
"""

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QPainter


class BaseHandler:
    """Handler 抽象基类

    Attributes:
        priority: 处理优先级，越小越先处理。建议范围:
            0~9   系统级（AddWidget、Delete）
            10~19 选中/拖拽
            20~29 缩放
            30~39 测试模式输入
            90~99 兜底/调试
    """

    priority: int = 50

    # ── 返回值常量 ──
    HANDLED: bool = True   # 事件已处理，停止传递
    PASS: bool = False     # 事件未处理，继续传递

    # ── 鼠标事件 ──

    def on_press(self, pos: QPoint, button: Qt.MouseButton,
                 screen: "ScreenComponent", canvas: "QWidget") -> bool:
        """鼠标按下。返回 HANDLED 或 PASS。"""
        return self.PASS

    def on_move(self, pos: QPoint,
                screen: "ScreenComponent", canvas: "QWidget") -> bool:
        """鼠标移动。返回 HANDLED 或 PASS。"""
        return self.PASS

    def on_release(self, pos: QPoint, button: Qt.MouseButton,
                   screen: "ScreenComponent", canvas: "QWidget") -> bool:
        """鼠标释放。返回 HANDLED 或 PASS。"""
        return self.PASS

    # ── 键盘事件 ──

    def on_key_press(self, key_str: str,
                     screen: "ScreenComponent") -> bool:
        """按键按下。返回 HANDLED 或 PASS。"""
        return self.PASS

    def on_key_release(self, key_str: str,
                       screen: "ScreenComponent") -> bool:
        """按键释放。返回 HANDLED 或 PASS。"""
        return self.PASS

    # ── 覆盖层绘制（可选） ──

    def draw_overlay(self, painter: QPainter,
                     screen: "ScreenComponent"):
        """在 screen.draw() 之后绘制额外覆盖层。"""
        pass
