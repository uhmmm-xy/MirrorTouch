"""ResizeHandler — 右键拖拽调整大小 Handler

优先级 25：在 SelectHandler + DragHandler 之后。
右键按下已选中控件 → 拖拽调整 size → 同步 data.scale_size。
"""

from PyQt5.QtCore import QPoint, Qt
from src.core.handlers.base_handler import BaseHandler


class ResizeHandler(BaseHandler):
    """右键拖拽调整控件大小

    流程:
        1. on_press: 右键命中 selected_widget → 记录初始尺寸
        2. on_move:  拖拽计算新尺寸 → resize_to()
        3. on_release: 结束 → 同步 data.scale_size
    """

    priority: int = 25

    def __init__(self, undo_handler: "UndoHandler" = None):
        super().__init__()
        self._target = None
        self._initial_size: int = 0
        self._start_x: int = 0
        self._start_y: int = 0
        self._undo = undo_handler

    # ── 鼠标事件 ──

    def on_press(self, pos: QPoint, button: Qt.MouseButton,
                 screen: "ScreenComponent", canvas: "QWidget") -> bool:
        if button != Qt.RightButton:
            return self.PASS

        target = screen.selected_widget
        if target is None:
            return self.PASS
        if not target.contains(pos.x(), pos.y()):
            return self.PASS

        self._target = target
        self._initial_size = target.size
        self._start_x = pos.x()
        self._start_y = pos.y()

        # 缩放开始前记录快照
        if self._undo:
            self._undo.record(screen)

        target.on_resize_start()
        return self.HANDLED

    def on_move(self, pos: QPoint,
                screen: "ScreenComponent", canvas: "QWidget") -> bool:
        if self._target is None:
            return self.PASS

        dx = abs(pos.x() - self._start_x)
        dy = abs(pos.y() - self._start_y)
        new_size = self._initial_size + (dx + dy) // 2
        self._target.resize_to(new_size)

        # 同步 data.scale_size
        if self._target.data and screen.size > 0:
            self._target.data.scale_size = new_size / screen.size

        screen._request_update()
        return self.HANDLED

    def on_release(self, pos: QPoint, button: Qt.MouseButton,
                   screen: "ScreenComponent", canvas: "QWidget") -> bool:
        if button != Qt.RightButton or self._target is None:
            return self.PASS

        self._target.on_resize_end()
        self._target = None
        self._start_x = 0
        self._start_y = 0
        return self.HANDLED
