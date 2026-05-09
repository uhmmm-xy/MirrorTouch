"""QueueStats — 队列统计（挂 SessionEntity）"""
from dataclasses import dataclass


@dataclass
class QueueStats:
    total_pushed: int = 0
    total_dropped: int = 0
    current_size: int = 0
