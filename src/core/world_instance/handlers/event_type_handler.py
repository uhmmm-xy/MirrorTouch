"""EventTypeHandler — 按键类型 → 事件序列"""
from src.core.world_instance.components.touch_input import TouchInput


def generate_events(key_id: str, key_type: str, x: int, y: int,
                    event: str = "press") -> list[TouchInput]:
    """根据按键类型和触发事件生成 TouchInput 序列"""
    if key_type == "CLICK":
        if event == "press":
            return [
                TouchInput(x=x, y=y, event_type="down", key_id=key_id),
                TouchInput(x=x, y=y, event_type="up", key_id=key_id),
            ]
    elif key_type == "HOLD":
        if event == "press":
            return [TouchInput(x=x, y=y, event_type="down", key_id=key_id)]
        elif event == "release":
            return [TouchInput(x=0, y=0, event_type="up", key_id=key_id)]
    elif key_type in ("JOYSTICK", "RADIAL"):
        if event == "move":
            return [TouchInput(x=x, y=y, event_type="move", key_id=key_id)]
    elif key_type == "EYES":
        if event == "press":
            return [TouchInput(x=x, y=y, event_type="down", key_id=key_id)]
        elif event == "move":
            return [TouchInput(x=x, y=y, event_type="move", key_id=key_id)]
        elif event == "release":
            return [TouchInput(x=0, y=0, event_type="up", key_id=key_id)]
    return []
