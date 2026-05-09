"""LogEntity — 日志空间，应用启动时创建，永久存在"""
import esper
from src.core.world_instance.components.log_component import LogComponent


def create_log_entity() -> int:
    e = esper.create_entity()
    esper.add_component(e, LogComponent())
    return e
