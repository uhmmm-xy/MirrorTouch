"""HoldEntity — 长按按键实体（HOLD 类型：按下 down，松开 up）"""
import esper
from src.core.world_instance.components.widget_config import WidgetConfig


def create_hold_entity(cfg: WidgetConfig) -> int:
    e = esper.create_entity()
    esper.add_component(e, cfg)
    return e
