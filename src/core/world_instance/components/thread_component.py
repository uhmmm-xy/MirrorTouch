"""ThreadComponent — 线程信息"""
from dataclasses import dataclass

@dataclass
class ThreadComponent:
    name: str = ""
    running: bool = False
