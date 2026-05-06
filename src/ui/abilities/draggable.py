"""Draggable — 可拖拽移动能力接口

Mixin 类，为组件提供拖拽移动行为。
DragHandler 自动调用 move_to()。
"""


class Draggable:
    """可拖拽移动的组件能力。

    使用方式:
        class ButtonWidget(BaseWidget, Draggable):
            pass

    DragHandler 自动调用 move_to()。
    子类可覆盖 on_drag_start/on_drag_end 添加钩子逻辑。
    """

    def move_to(self, new_x: int, new_y: int):
        """移动组件到新坐标（由 DragHandler 调用）"""
        raise NotImplementedError("子类必须实现 move_to")

    def on_drag_start(self):
        """拖拽开始时的钩子（可选覆盖）"""
        pass

    def on_drag_end(self):
        """拖拽结束时的钩子（可选覆盖）"""
        pass
