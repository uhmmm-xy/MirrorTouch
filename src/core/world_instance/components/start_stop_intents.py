"""StartStreamIntent / StopStreamIntent — 意图组件"""
from dataclasses import dataclass

@dataclass
class StartStreamIntent:
    config: "StreamConfig | None" = None

@dataclass
class StopStreamIntent:
    pass
