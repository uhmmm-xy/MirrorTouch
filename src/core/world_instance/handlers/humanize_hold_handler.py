"""HumanizeHoldHandler — 长按超时微小抖动

[MIRROR-TOUCH-T6] ±1px 低量级微抖动，比 click 偏移小一个量级。
"""
import random


def hold_jitter(x: int, y: int) -> tuple[int, int]:
    """±1px 抖动"""
    return x + random.randint(-1, 1), y + random.randint(-1, 1)
