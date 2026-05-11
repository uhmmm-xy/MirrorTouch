"""EventTypeHandler — Entity 类型分发

[MIRROR-TOUCH-ENTITY] 纯分发层，不含任何帧生成逻辑。
  各个 widget_type → 对应的 behavior handler.generate(entity_id, cfg, ...)
"""
from src.core.world_instance.components.widget_config import WidgetConfig


def generate_events(entity_id: int, cfg: WidgetConfig,
                    event: str, offset_px: int = 0, offset_py: int = 0,
                    base_px: int = 0, base_py: int = 0, size_px: int = 0,
                    ):
    """Entity → Handler 分发

    所有 event 判断、帧生成逻辑下沉至各 behavior handler。
    """
    handler = _HANDLERS.get(cfg.widget_type)
    if handler:
        return handler(entity_id, cfg, event, offset_px, offset_py, base_px, base_py, size_px)
    return []


# ── 延迟导入，避免循环依赖 ──

def _handle_click(eid, cfg, event, ox, oy, bx, by, sz):
    from src.core.world_instance.handlers.button_behavior_handler import generate
    return generate(eid, cfg, event, ox, oy, bx, by, sz)


def _handle_hold(eid, cfg, event, ox, oy, bx, by, sz):
    from src.core.world_instance.handlers.hold_behavior_handler import generate
    return generate(eid, cfg, event, ox, oy, bx, by, sz)


def _handle_joystick(eid, cfg, event, ox, oy, bx, by, sz):
    from src.core.world_instance.handlers.joystick_behavior_handler import generate
    return generate(eid, cfg, event, ox, oy, bx, by, sz)


def _handle_radial(eid, cfg, event, ox, oy, bx, by, sz):
    from src.core.world_instance.handlers.radial_behavior_handler import generate
    return generate(eid, cfg, event, ox, oy, bx, by, sz)


def _handle_eyes(eid, cfg, event, ox, oy, bx, by, sz):
    from src.core.world_instance.handlers.eyes_widget_handler import generate
    return generate(eid, cfg, event, ox, oy, bx, by, sz)


_HANDLERS = {
    "click":    _handle_click,
    "hold":     _handle_hold,
    "joystick": _handle_joystick,
    "radial":   _handle_radial,
    "eyes":     _handle_eyes,
}
