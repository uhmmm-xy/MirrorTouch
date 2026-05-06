"""SelectHandler — 点击选中 Handler

优先级 10：在拖拽/缩放之前处理。
点击 Screen 区域 → 命中检测 → 选中/取消选中控件。
通过回调通知外部（属性面板同步）。
"""

from typing import Callable, Optional
from PyQt5.QtCore import QPoint, Qt
from src.core.handlers.base_handler import BaseHandler


class SelectHandler(BaseHandler):
    """点击选中控件

    流程:
        1. 反向遍历 screen.children 查找命中
        2. 旧选中调用 deselect()
        3. 新命中调用 select()，更新 screen.selected_widget
        4. 触发 on_selected 回调（属性面板同步）
    """

    priority: int = 10

    def __init__(self, on_selected: Optional[Callable] = None):
        """
        Args:
            on_selected: 选中变更回调，签名为 (widget_or_None) -> None
        """
        self._on_selected = on_selected

    def set_callback(self, callback: Callable):
        """设置选中变更回调"""
        self._on_selected = callback

    # ── 鼠标事件 ──

    def on_press(self, pos: QPoint, button: Qt.MouseButton,
                 screen: "ScreenComponent", canvas: "QWidget") -> bool:
        if button != Qt.LeftButton:
            return self.PASS

        hit = self._hit_test(pos, screen)

        # 取消旧选中
        old = screen.selected_widget
        if old is not None and old is not hit:
            old.deselect()

        # 应用新选中
        if hit is not None:
            hit.select()
            screen._selected_widget = hit
        else:
            screen._selected_widget = None

        screen._request_update()

        # 通知外部
        if self._on_selected:
            self._on_selected(hit)

        return self.PASS  # 不阻断，让 DragHandler 等继续处理

    # ── 辅助 ──

    @staticmethod
    def _hit_test(pos: QPoint, screen: "ScreenComponent"):
        """反向遍历 children 查找命中控件"""
        for child in reversed(screen.children):
            if child.contains(pos.x(), pos.y()):
                return child
        return None
