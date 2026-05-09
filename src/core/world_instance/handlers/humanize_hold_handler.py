"""HumanizeHoldHandler — 长按超时微小抖动"""
import random


def hold_jitter(x: int, y: int) -> tuple[int, int]:
    """±1px 抖动，比 click 偏移小一个量级"""
    return x + random.randint(-1, 1), y + random.randint(-1, 1)
