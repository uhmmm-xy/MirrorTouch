"""Directional — 方向控制能力接口

Mixin 类，为组件（摇杆）提供方向控制行为。
TestInputHandler 自动调用 set_direction()/reset()。
"""


class Directional:
    """可方向控制的组件能力。

    使用方式:
        class JoystickComponent(BaseWidget, Directional):
            def set_direction(self, dx, dy): ...
            def reset(self): ...

    TestInputHandler 在测试模式下自动调用。
    """

    def set_direction(self, dx: float, dy: float):
        """设置方向向量 (-1~1 归一化)，(0,0) 回中"""
        raise NotImplementedError("子类必须实现 set_direction")

    def reset(self):
        """回中"""
        raise NotImplementedError("子类必须实现 reset")
