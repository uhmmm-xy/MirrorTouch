"""IntentDispatchHandler — 解析 Start/Stop Intent，管理 Session + Device 生命周期"""
import esper
from src.core.world_instance.components.stream_session import StreamSession
from src.core.world_instance.components.stream_config import StreamConfig
from src.core.world_instance.components.start_stop_intents import StartStreamIntent, StopStreamIntent
from src.utils.logger import log

# 全局引用（避免循环导入）
_session_entity: int = 0
_device_entity: int = 0


def handle_start(config: StreamConfig | None = None):
    """解析 StartStreamIntent → 创建或复用 Session + Device"""
    global _session_entity, _device_entity
    from src.core.world_instance.entities.session_entity import create_session_entity
    from src.core.world_instance.world_bootstrap import set_current_session, set_current_device

    cfg = config or StreamConfig()
    _session_entity = create_session_entity(cfg)
    set_current_session(_session_entity)

    from src.core.config_manager import load_config
    keep = load_config().keep_service_alive

    # 常驻模式：复用已有 DeviceEntity
    if keep and _device_entity and esper.entity_exists(_device_entity):
        session = esper.component_for_entity(_session_entity, StreamSession)
        session.state = "streaming"
        esper.dispatch_event("frame.drain.start", _device_entity)
        log.info("[IntentDispatch] 常驻模式，复用已有连接")
        return

    from src.core.world_instance.entities.device_entity import create_device_entity
    from src.core.world_instance.components.connection_component import ConnectionComponent

    mw_id = 0
    for e, (c,) in esper.get_components(ConnectionComponent):
        mw_id = e
        break

    _device_entity = create_device_entity(mw_id)
    set_current_device(_device_entity)

    session = esper.component_for_entity(_session_entity, StreamSession)
    session.state = "connecting"
    log.info(f"[IntentDispatch] Session 创建, config: {cfg}")

    esper.dispatch_event("middleware.connect", _device_entity)
    esper.dispatch_event("adb.start", _device_entity)
    esper.dispatch_event("scrcpy.start", _session_entity, _device_entity)


def handle_stop(force: bool = False):
    """解析 StopStreamIntent → 安全逐级关闭
    Args:
        force: True 忽略常驻模式，强制完整关闭
    """
    global _session_entity, _device_entity
    from src.core.config_manager import load_config
    keep = load_config().keep_service_alive and not force

    if keep:
        esper.dispatch_event("frame.drain.stop", _device_entity)
        if _session_entity:
            esper.delete_entity(_session_entity)
            _session_entity = 0
        log.info("[IntentDispatch] 常驻模式，保留设备连接")
    else:
        _safe_stop_chain()


def _safe_stop_chain():
    """安全关闭链：帧消费 → Scrcpy → ADB → 中间件 → 销毁实体"""
    global _session_entity, _device_entity
    log.info("[IntentDispatch] 开始安全关闭...")

    if _device_entity and esper.entity_exists(_device_entity):
        esper.dispatch_event("frame.drain.stop", _device_entity)
        esper.dispatch_event("scrcpy.stop", _session_entity, _device_entity)
        esper.dispatch_event("adb.stop", _device_entity)
        esper.dispatch_event("middleware.disconnect", _device_entity)
        esper.delete_entity(_device_entity)
        _device_entity = 0

    if _session_entity and esper.entity_exists(_session_entity):
        esper.delete_entity(_session_entity)
        _session_entity = 0

    log.info("[IntentDispatch] 安全关闭完成")
