"""MiddlewareBinding — 中间件绑定"""
from dataclasses import dataclass
from typing import Any

@dataclass
class MiddlewareBinding:
    queue: Any = None          # 中间件帧队列引用
    device_serial: str = ""    # 设备序列号
