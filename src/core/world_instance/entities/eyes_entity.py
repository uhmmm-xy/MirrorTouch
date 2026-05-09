"""EyesEntity — 视角（mouseMoveMap 持续 move）"""
import esper
from src.core.world_instance.components.touch_input import TouchInput


def create_eyes_entity(hotkey: str, screen_x: int, screen_y: int,
                       size: int = 60) -> int:
    e = esper.create_entity()
    esper.add_component(e, TouchInput(key_id=hotkey, event_type="move"))
    return e
