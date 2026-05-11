"""RadialBehaviorHandler — RADIAL 按键完整处理

[MIRROR-TOUCH-ENTITY] generate() 是 Entity 驱动入口，event_type_handler 纯分发至此。
"""
from src.core.world_instance.components.touch_input import TouchInput


def generate(entity_id: int, cfg, event: str, ox: int, oy: int, bx: int, by: int, sz: int) -> list[TouchInput]:
    """RADIAL: move → [move(锚点+偏移)]（比例值）"""
    if event == "move":
        px, py = bx + ox, by + oy
        return [TouchInput(base_x=bx, base_y=by, x=px, y=py, event_type="move", key_id=cfg.key_id, size=sz)]
    return []
