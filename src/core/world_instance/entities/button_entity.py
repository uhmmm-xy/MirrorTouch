"""ButtonEntity — 普通按键（按下触发 down 后 up）"""
import esper
from src.core.world_instance.components.touch_input import TouchInput


def create_button_entity(hotkey: str, screen_x: int, screen_y: int,
                         size: int = 40) -> int:
    e = esper.create_entity()
    esper.add_component(e, TouchInput(key_id=hotkey))
    return e
