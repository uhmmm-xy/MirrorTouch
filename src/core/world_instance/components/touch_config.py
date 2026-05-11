"""TouchConfig — 串口配置 + 屏幕分辨率 + 消费频率（挂 SessionEntity）

[MIRROR-TOUCH-T5] 新增 screen_width/screen_height，启动时由 ADB 写入。
"""
from dataclasses import dataclass


@dataclass
class TouchConfig:
    port: str = ""
    baudrate: int = 115200
    consume_frequency: int = 800
    screen_width: int = 1080
    screen_height: int = 1920
