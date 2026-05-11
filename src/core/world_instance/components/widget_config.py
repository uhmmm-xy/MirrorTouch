"""WidgetConfig — 按键实体通用配置 Component

纯数据容器，挂载于每个按键 Entity。不含方法逻辑。
"""
from dataclasses import dataclass


@dataclass
class WidgetConfig:
    widget_type: str = ""      # "CLICK" | "HOLD" | "JOYSTICK" | "EYES" | "RADIAL"
    key_id: str = ""           # 按键标识 (如 "F", "LeftButton", "W|S|A|D")
    pos_x: float = 0.0         # 锚点比例 X (0-1)
    pos_y: float = 0.0         # 锚点比例 Y (0-1)
    scale_size: float = 0.03   # 比例大小
