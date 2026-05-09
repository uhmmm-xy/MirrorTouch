"""HumanizeClickHandler — 点击拟人化 ±3~5px"""
import random


def offset_click(x: int, y: int) -> tuple[int, int]:
    dx = random.randint(-5, 5)
    # 避免 dx==0 太明显
    while dx == 0:
        dx = random.randint(-5, 5)
    dy = random.randint(-5, 5)
    while dy == 0:
        dy = random.randint(-5, 5)
    return x + dx, y + dy
