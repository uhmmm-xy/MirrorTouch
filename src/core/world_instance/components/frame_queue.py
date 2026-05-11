"""FrameQueue — 单手指帧队列滑动窗口

[MIRROR-TOUCH-T4] 简化版：
  - 仅保留 frames(deque maxlen=9) + max_size + finger_id
  - 移除 batch_size, has_update, lock（deque 本身线程安全）
"""
from dataclasses import dataclass, field
from collections import deque


@dataclass
class FrameQueue:
    frames: deque = field(default_factory=lambda: deque(maxlen=9))
    max_size: int = 9
    finger_id: int = -1
