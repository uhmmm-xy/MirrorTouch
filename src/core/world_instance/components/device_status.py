"""DeviceStatus — 设备连接状态"""
from dataclasses import dataclass

@dataclass
class DeviceStatus:
    connected: bool = False
    streaming: bool = False
