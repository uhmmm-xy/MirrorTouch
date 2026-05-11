"""ButtonEntity — 普通按键实体（CLICK 类型：按下触发 down 后 up）"""
import esper
from src.core.world_instance.components.widget_config import WidgetConfig


def create_button_entity(cfg: WidgetConfig) -> int:
    e = esper.create_entity()
    esper.add_component(e, cfg)
    return e
