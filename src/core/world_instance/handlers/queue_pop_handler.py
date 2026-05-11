"""QueuePopHandler — 全量取出帧窗口

[MIRROR-TOUCH-T4] 返回 deque 内全部现有帧（1~9 均可），不等待凑数。
返回后清空 deque。
"""
from collections import deque


def pop_all(dq: deque) -> list:
    """取出 deque 内全部帧，返回后清空"""
    if not dq:
        return []
    batch = list(dq)
    dq.clear()
    return batch
