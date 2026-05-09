"""FrameStats — 帧率统计"""
from dataclasses import dataclass

@dataclass
class FrameStats:
    fps: float = 0.0
    total: int = 0
    dropped: int = 0
