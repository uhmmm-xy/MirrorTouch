"""DeviceConfig — 设备连接配置"""
from dataclasses import dataclass

@dataclass
class DeviceConfig:
    serial: str = ""
    local_port: int = 1234
