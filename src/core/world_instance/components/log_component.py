"""LogComponent — 日志条目"""
from dataclasses import dataclass, field

@dataclass
class LogComponent:
    entries: list = field(default_factory=list)
