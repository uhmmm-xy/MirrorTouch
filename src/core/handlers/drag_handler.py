"""DragHandler — 左键拖拽移动 Handler

优先级 15：在 SelectHandler 之后。
左键按下已选中控件 → 记录偏移 → 拖拽移动 → 同步 data 坐标。
通过 Draggable 接口操作。
"""

from PyQt5.QtCore import QPoint, Qt
from src.core.handlers.base_handler import BaseHandler


class DragHandler(BaseHandler):
    """左键拖拽移动已选中控件

    流程:
        1. on_press: 命中 selected_widget → 记录偏移，调用 on_drag_start()
        2. on_move:  拖拽中 → 调用 move_to()
        3. on_release: 结束 → 调用 on_drag_end()，同步 data 坐标
    """

    priority: int = 15

    def __init__(self):
        self._target = None          # 正在拖拽的 widget
        self._offset_x: int = 0
        self._offset_y: int = 0

    @property
    def is_dragging(self) -> bool:
        """是否正在拖拽（DeleteHandler 查询用）"""
        return self._target is not None

    # ── 鼠标事件 ──

    def on_press(self, pos: QPoint, button: Qt.MouseButton,
                 screen: "ScreenComponent", canvas: "QWidget") -> bool:
        if button != Qt.LeftButton:
            return self.PASS

        target = screen.selected_widget
        if target is None:
            return self.PASS
        if not target.contains(pos.x(), pos.y()):
            return self.PASS

        self._target = target
        self._offset_x = target.x - pos.x()
        self._offset_y = target.y - pos.y()

        target.on_drag_start()
        return self.HANDLED

    def on_move(self, pos: QPoint,
                screen: "ScreenComponent", canvas: "QWidget") -> bool:
        if self._target is None:
            return self.PASS

        new_x = pos.x() + self._offset_x
        new_y = pos.y() + self._offset_y
        self._target.move_to(new_x, new_y)
        screen._request_update()
        return self.HANDLED

    def on_release(self, pos: QPoint, button: Qt.MouseButton,
                   screen: "ScreenComponent", canvas: "QWidget") -> bool:
        if button != Qt.LeftButton or self._target is None:
            return self.PASS

        self._target.on_drag_end()

        # 同步 data 相对坐标（move_to 已通过 BaseWidget 同步，此处兜底）
        w = self._target
        if w.data:
            rx, ry = screen.local_to_screen(w.x, w.y)
            w.data.pos_x = rx
            w.data.pos_y = ry

        self._target = None
        return self.HANDLED
