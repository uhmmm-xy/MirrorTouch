"""TouchInput — 单次触控输入（挂 SessionEntity）"""
from dataclasses import dataclass, field
import time


@dataclass
class TouchInput:
    x: int = 0
    y: int = 0
    event_type: str = "move"
    priority: int = 10
    timestamp: float = field(default_factory=time.time)
    key_id: str = ""
