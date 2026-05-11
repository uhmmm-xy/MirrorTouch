"""HumanizeClickHandler — 点击拟人化 ±3~5px

[MIRROR-TOUCH-T6] 对基点坐标应用随机偏移，排除 0。
"""
import random


def offset_click(x: int, y: int) -> tuple[int, int]:
    """基点 ±3~5 像素随机偏移"""
    dx = random.choice([-5, -4, -3, 3, 4, 5])
    dy = random.choice([-5, -4, -3, 3, 4, 5])
    return x + dx, y + dy
