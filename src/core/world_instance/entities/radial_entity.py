"""RadialEntity — 转盘（按键激活后方向选择持续 move）"""
import esper
from src.core.world_instance.components.touch_input import TouchInput


def create_radial_entity(hotkey: str, screen_x: int, screen_y: int,
                         size: int = 60, sectors: int = 8) -> int:
    e = esper.create_entity()
    esper.add_component(e, TouchInput(key_id=hotkey))
    return e
