"""RadialEntity — 转盘实体（RADIAL 类型：按键激活后方向选择持续 move）"""
import esper
from src.core.world_instance.components.widget_config import WidgetConfig


def create_radial_entity(cfg: WidgetConfig) -> int:
    e = esper.create_entity()
    esper.add_component(e, cfg)
    return e
