"""TouchConfig — 串口配置 + 消费频率（挂 SessionEntity）"""
from dataclasses import dataclass


@dataclass
class TouchConfig:
    port: str = ""
    baudrate: int = 115200
    consume_frequency: int = 800  # 800-1000 Hz
