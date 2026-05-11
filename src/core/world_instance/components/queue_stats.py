"""QueueStats — 队列统计快照

[MIRROR-TOUCH-T4] 轻量化：
  - active_mask: 6 位二进制位图，bit[i]=1 表示 finger i 活跃
  - window_sizes: 6 元素列表，各窗口当前驻留帧数
  - 移除 total_pushed, total_dropped, current_size 累计字段
"""
from dataclasses import dataclass, field


@dataclass
class QueueStats:
    active_mask: int = 0
    window_sizes: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0, 0])
