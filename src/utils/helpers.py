"""通用计算工具函数

消除项目中重复的数学/几何计算。
"""

import math


def clamp(value: float, lo: float, hi: float) -> float:
    """将值钳制在 [lo, hi] 区间"""
    return max(lo, min(hi, value))


def vec_len(dx: float, dy: float) -> float:
    """二维向量长度"""
    return math.sqrt(dx * dx + dy * dy)


def dist(x1: float, y1: float, x2: float, y2: float) -> float:
    """两点距离"""
    return vec_len(x2 - x1, y2 - y1)


def lerp(a: float, b: float, t: float) -> float:
    """线性插值 a→b，t ∈ [0,1]"""
    return a + (b - a) * t


def safe_div(num: float, den: float, default: float = 0.0) -> float:
    """安全除法，分母为 0 返回 default"""
    return num / den if den != 0 else default


def safe_ratio(w: float, h: float, default: float = 1.0) -> float:
    """安全宽高比"""
    return safe_div(w, h, default)


def map_range(value: float, in_lo: float, in_hi: float,
              out_lo: float, out_hi: float) -> float:
    """将 value 从 [in_lo, in_hi] 映射到 [out_lo, out_hi]"""
    if in_hi == in_lo:
        return out_lo
    t = (value - in_lo) / (in_hi - in_lo)
    return lerp(out_lo, out_hi, t)
