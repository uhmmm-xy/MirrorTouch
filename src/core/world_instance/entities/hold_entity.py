"""HoldEntity — 长按按键（按下触发 down，松开触发 up）"""
import esper
from src.core.world_instance.components.touch_input import TouchInput


def create_hold_entity(hotkey: str, screen_x: int, screen_y: int,
                       size: int = 40, hold_interval: int = 50) -> int:
    e = esper.create_entity()
    esper.add_component(e, TouchInput(key_id=hotkey))
    return e
