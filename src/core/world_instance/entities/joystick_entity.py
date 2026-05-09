"""JoystickEntity — 摇杆（方向键持续 move）"""
import esper
from src.core.world_instance.components.touch_input import TouchInput


def create_joystick_entity(hotkey: str, screen_x: int, screen_y: int,
                           size: int = 80, directions: list | None = None) -> int:
    e = esper.create_entity()
    esper.add_component(e, TouchInput(key_id=hotkey))
    return e
