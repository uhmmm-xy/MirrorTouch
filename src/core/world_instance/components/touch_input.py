"""TouchInput — 单次触控输入（挂 SessionEntity）

[MIRROR-TOUCH-T5] 字段说明：
  base_x, base_y: 基点坐标（来自映射配置，绝对参照，永久不变）
  x, y:          实际点击坐标（初始 = base，SerialSystem 拟人时偏移）
  event_type:    "down" | "up" | "move"（仅三种，无 click）
  size:          触控半径（像素, 来自映射配置 scale_size 转换），透传至 SerialSystem 做边界校验
  key_id:        会话标识（hotkey），TQS 用其关联 session
"""
from dataclasses import dataclass, field
import time


@dataclass
class TouchInput:
    base_x: int = 0
    base_y: int = 0
    x: int = 0
    y: int = 0
    event_type: str = "move"
    timestamp: float = field(default_factory=time.time)
    key_id: str = ""
    size: int = 0
