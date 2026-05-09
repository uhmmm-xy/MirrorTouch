"""HoldBehaviorHandler — 按下 down，松开 up"""
from src.core.world_instance.components.touch_input import TouchInput


def on_press(x: int, y: int) -> list[TouchInput]:
    return [TouchInput(x=x, y=y, event_type="down")]


def on_release() -> list[TouchInput]:
    return [TouchInput(x=0, y=0, event_type="up")]
