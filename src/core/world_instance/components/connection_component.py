"""ConnectionComponent — 连接计数"""
from dataclasses import dataclass

@dataclass
class ConnectionComponent:
    middleware_entity_id: int = 0
    active_connections: int = 0
