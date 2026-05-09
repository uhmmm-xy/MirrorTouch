"""FrameQueue — 单手指帧队列滑动窗口（挂 ThreadEntity）"""
from dataclasses import dataclass, field
from collections import deque
from threading import Lock


@dataclass
class FrameQueue:
    frames: deque = field(default_factory=lambda: deque(maxlen=9))
    max_size: int = 9
    batch_size: int = 3
    finger_id: int = -1
    has_update: bool = False
    lock: "threading.Lock" = field(default_factory=lambda: __import__('threading').Lock())
    _lock: Lock = field(default_factory=Lock)
