"""ButtonBehaviorHandler — 按下触发 down 后 up"""
from src.core.world_instance.components.touch_input import TouchInput


def on_press(x: int, y: int) -> list[TouchInput]:
    return [
        TouchInput(x=x, y=y, event_type="down"),
        TouchInput(x=x, y=y, event_type="up"),
    ]
