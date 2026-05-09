"""HumanizeMoveHandler — 3 帧平滑 + 方向漂移"""
import random


def smooth_3f(px: int, py: int, x: int, y: int) -> tuple[int, int]:
    """两帧之间平滑过渡（线性 1/3 步进）"""
    dx = random.randint(-2, 2)
    dy = random.randint(-2, 2)
    mx = (px + x * 2) // 3 + dx
    my = (py + y * 2) // 3 + dy
    return mx, my
