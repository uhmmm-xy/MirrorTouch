"""EyesEntity — 视角实体（EYES 类型：mouseMoveMap 持续 move）"""
import esper
from src.core.world_instance.components.widget_config import WidgetConfig


def create_eyes_entity(cfg: WidgetConfig) -> int:
    e = esper.create_entity()
    esper.add_component(e, cfg)
    return e
