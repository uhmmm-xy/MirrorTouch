"""Resizable — 可调整大小能力接口

Mixin 类，为组件提供右键拖拽调整大小行为。
ResizeHandler 自动调用 resize_to()。
"""


class Resizable:
    """可调整大小的组件能力。

    使用方式:
        class ButtonWidget(BaseWidget, Resizable):
            pass

    ResizeHandler 自动调用 resize_to()。
    """

    size: int = 36

    def resize_to(self, new_size: int):
        """调整组件大小（由 ResizeHandler 调用）"""
        self.size = max(10, new_size)

    def on_resize_start(self):
        """调整开始时的钩子（可选覆盖）"""
        pass

    def on_resize_end(self):
        """调整结束时的钩子（可选覆盖）"""
        pass
