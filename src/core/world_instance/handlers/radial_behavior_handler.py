"""RadialBehaviorHandler — 按键激活后方向选择持续 move"""
from src.core.world_instance.components.touch_input import TouchInput


def on_move(x: int, y: int) -> list[TouchInput]:
    return [TouchInput(x=x, y=y, event_type="move")]
