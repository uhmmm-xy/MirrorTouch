"""StreamConfig — 视频流配置"""
from dataclasses import dataclass, field

@dataclass
class StreamConfig:
    max_size: int = 720
    max_fps: int = 60
    bit_rate: str = "8000"
    codec: str = "h264"
    crop: str | None = None
    turn_screen_off: bool = False
    stay_awake: bool = True
    no_control: bool = True
