"""MiddlewareEntity — 中间件全局单例，应用启动时创建，永久存在"""
import esper
from src.core.world_instance.components.middleware_binding import MiddlewareBinding
from src.core.world_instance.components.connection_component import ConnectionComponent


def create_middleware_entity() -> int:
    e = esper.create_entity()
    esper.add_component(e, MiddlewareBinding())
    esper.add_component(e, ConnectionComponent())
    return e
