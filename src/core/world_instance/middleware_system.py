"""MiddlewareSystem — 中间件生命周期管理"""
import esper
from src.core.world_instance.components.connection_component import ConnectionComponent


def register():
    esper.set_handler("middleware.start", _on_start)
    esper.set_handler("middleware.stop", _on_stop)
    esper.set_handler("middleware.connect", _on_connect)
    esper.set_handler("middleware.disconnect", _on_disconnect)


# ── Handler ──

def _on_start(serial: str = ""):
    """启动中间件服务（由 middleware.connect 触发）"""
    from src.utils.logger import log
    mw = _mw_entity()
    conn = esper.component_for_entity(mw, ConnectionComponent)
    log.info(f"[MiddlewareSystem] 启动中间件, serial={serial}")
    # TODO: 调用 framebridge 底层启停由 ScrcpySystem 统一管理


def _on_stop():
    from src.utils.logger import log
    log.info("[MiddlewareSystem] 停止中间件")


def _on_connect(device_entity: int):
    """设备连接 → active_connections += 1"""
    from src.core.world_instance.handlers.middleware_lifecycle_handler import handle_connect
    handle_connect(device_entity)


def _on_disconnect(device_entity: int):
    """设备断开 → active_connections -= 1"""
    from src.core.world_instance.handlers.middleware_lifecycle_handler import handle_disconnect
    handle_disconnect(device_entity)


def _mw_entity() -> int:
    """查找 MiddlewareEntity"""
    for e, (c,) in esper.get_components(ConnectionComponent):
        return e
    return 0
