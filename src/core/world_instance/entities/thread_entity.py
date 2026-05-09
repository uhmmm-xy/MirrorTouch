"""ThreadEntity — 一个工作线程，System 按需创建"""
import esper
from src.core.world_instance.components.thread_component import ThreadComponent


def create_thread_entity(name: str) -> int:
    e = esper.create_entity()
    esper.add_component(e, ThreadComponent(name=name, running=True))
    return e
