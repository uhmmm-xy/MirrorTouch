"""Activable — 可激活能力接口

Mixin 类，为组件提供测试模式下的激活/停用行为。
TestInputHandler 自动调用 activate()/deactivate()。
"""


class Activable:
    """可激活的组件能力（测试模式）。

    使用方式:
        class ButtonWidget(BaseWidget, Activable):
            pass

    TestInputHandler 在测试模式下匹配按键后自动调用。
    """

    is_hold: bool = False

    def activate(self):
        """进入激活状态（高亮）"""
        self.is_hold = True

    def deactivate(self):
        """退出激活状态"""
        self.is_hold = False
