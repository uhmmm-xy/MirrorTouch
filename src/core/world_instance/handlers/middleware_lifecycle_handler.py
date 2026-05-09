"""MiddlewareLifecycleHandler — 连接计数管理，0↔1 自动启停"""
import esper
from src.core.world_instance.components.connection_component import ConnectionComponent
from src.utils.logger import log


def handle_connect(device_entity: int):
    """设备连接 → active_connections += 1"""
    mw = _find_middleware()
    if mw == 0:
        log.error("[MiddlewareLifecycle] MiddlewareEntity 不存在")
        return
    conn = esper.component_for_entity(mw, ConnectionComponent)
    was_zero = conn.active_connections == 0
    conn.active_connections += 1
    if was_zero:
        log.info("[MiddlewareLifecycle] 首次连接，启动中间件服务")


def handle_disconnect(device_entity: int):
    """设备断开 → active_connections -= 1"""
    mw = _find_middleware()
    if mw == 0:
        return
    conn = esper.component_for_entity(mw, ConnectionComponent)
    conn.active_connections = max(0, conn.active_connections - 1)
    if conn.active_connections == 0:
        from src.core.config_manager import load_config
        if load_config().keep_service_alive:
            log.info("[MiddlewareLifecycle] 常驻模式，保持服务运行")
        else:
            log.info("[MiddlewareLifecycle] 所有连接断开，停止中间件服务")


def _find_middleware() -> int:
    for e, (c,) in esper.get_components(ConnectionComponent):
        return e
    return 0
