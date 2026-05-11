"""HumanizeMoveHandler — 加权平滑 + finger 级历史缓存

[MIRROR-TOUCH-T6] 每 finger_id 维护最多 3 帧历史。
≥2 帧时执行加权平滑，<2 帧直接透传。
"""
import random

# finger_id → [(x, y), ...] 最大 3 帧
_history: dict[int, list[tuple[int, int]]] = {}


def smooth_weighted(fid: int, x: int, y: int) -> tuple[int, int]:
    """finger 级加权平滑

    可用帧 < 2 → 透传
    可用帧 ≥ 2 → 当前帧权重 0.6, 历史帧加权平均 0.4 + 随机微抖动
    """
    if fid not in _history:
        _history[fid] = []

    hist = _history[fid]
    hist.append((x, y))
    if len(hist) > 3:
        hist.pop(0)

    if len(hist) < 2:
        return x, y

    # 加权平滑
    avg_x = sum(p[0] for p in hist[:-1]) / (len(hist) - 1)
    avg_y = sum(p[1] for p in hist[:-1]) / (len(hist) - 1)
    mx = int(avg_x * 0.4 + x * 0.6) + random.randint(-1, 1)
    my = int(avg_y * 0.4 + y * 0.6) + random.randint(-1, 1)
    return mx, my
