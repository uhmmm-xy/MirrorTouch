"""Selectable — 可被选中能力接口

Mixin 类，为组件提供选中/取消选中行为。
与 BaseWidget.is_hold 共享状态。
"""


class Selectable:
    """可被选中的组件能力。

    使用方式:
        class ButtonWidget(BaseWidget, Selectable):
            pass

    SelectHandler 自动调用 select()/deselect()。
    """

    is_hold: bool = False

    def select(self):
        """标记为选中状态（高亮绘制）"""
        self.is_hold = True

    def deselect(self):
        """取消选中状态"""
        self.is_hold = False
