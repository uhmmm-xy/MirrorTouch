"""JoystickEntity — 摇杆实体（JOYSTICK 类型：方向键持续 move）"""
import esper
from src.core.world_instance.components.widget_config import WidgetConfig


def create_joystick_entity(cfg: WidgetConfig) -> int:
    e = esper.create_entity()
    esper.add_component(e, cfg)
    return e
