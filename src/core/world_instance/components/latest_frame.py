"""LatestFrame — 最新视频帧（容量=1，覆盖写入）"""
from dataclasses import dataclass
from PyQt5.QtGui import QImage

@dataclass
class LatestFrame:
    qimage: QImage | None = None
    timestamp: float = 0.0
    width: int = 0
    height: int = 0
