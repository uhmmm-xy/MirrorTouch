"""EyesBehaviorHandler — mouseMoveMap 持续输出 move"""
from src.core.world_instance.components.touch_input import TouchInput


def on_move(x: int, y: int) -> list[TouchInput]:
    return [TouchInput(x=x, y=y, event_type="move")]
