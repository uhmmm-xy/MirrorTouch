"""StreamSession — 投屏会话状态"""
from dataclasses import dataclass

@dataclass
class StreamSession:
    state: str = "idle"  # idle | connecting | streaming | error | stopped
