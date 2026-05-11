"""World Bootstrap — Esper World 初始化与销毁"""
import esper


# ── 存储关键实体 ID ──
_middleware_entity: int = 0
_log_entity: int = 0
_device_meta_entity: int = 0
_current_session: int = 0
_current_device: int = 0


def init_world() -> dict:
    """初始化 World：创建永久实体 + 注册事件 + 注册 System"""
    global _middleware_entity, _log_entity, _device_meta_entity, _current_session, _current_device
    esper.clear_database()

    from src.core.world_instance.entities.middleware_entity import create_middleware_entity
    from src.core.world_instance.entities.log_entity import create_log_entity
    from src.core.world_instance.components.device_component import DeviceComponent

    _middleware_entity = create_middleware_entity()
    _log_entity = create_log_entity()

    # [MIRROR-TOUCH-T1] 创建设备元数据实体，挂载 DeviceComponent（全默认初始值）
    _device_meta_entity = esper.create_entity()
    esper.add_component(_device_meta_entity, DeviceComponent())

    _current_session = 0
    _current_device = 0

    # 注册事件 Handler
    from src.core.world_instance import middleware_system
    from src.core.world_instance import scrcpy_system
    from src.core.world_instance.handlers import adb_handler
    from src.core.world_instance.handlers import scrcpy_server_handler
    from src.core.world_instance.handlers import frame_drain_handler
    from src.core.world_instance.handlers import stats_calc_handler
    middleware_system.register()
    scrcpy_system.register()
    adb_handler.register()
    scrcpy_server_handler.register()
    frame_drain_handler.register()
    stats_calc_handler.register()
    esper.set_handler("world.shutdown", _on_shutdown)

    # 触控模块
    from src.core.world_instance import key_mapping_system
    from src.core.world_instance import touch_queue_system
    from src.core.world_instance import serial_system
    key_mapping_system.register()
    touch_queue_system.register()
    serial_system.register()

    return {
        "middleware_entity": _middleware_entity,
        "log_entity": _log_entity,
        "device_meta_entity": _device_meta_entity,
    }


def shutdown_world():
    """销毁 World"""
    global _middleware_entity, _log_entity, _device_meta_entity, _current_session, _current_device
    esper.dispatch_event("world.shutdown")
    esper.clear_database()
    _middleware_entity = 0
    _log_entity = 0
    _device_meta_entity = 0
    _current_session = 0
    _current_device = 0


# ── 实体 ID 查询 ──

def get_middleware_entity() -> int:
    return _middleware_entity

def get_log_entity() -> int:
    return _log_entity

def get_device_meta_entity() -> int:
    """[MIRROR-TOUCH-T1] 获取设备元数据实体 ID，供 UI 层与其他系统通过固定路径获取"""
    return _device_meta_entity

def get_current_session() -> int:
    return _current_session

def get_current_device() -> int:
    return _current_device


def set_current_session(eid: int):
    global _current_session
    _current_session = eid

def set_current_device(eid: int):
    global _current_device
    _current_device = eid


def _on_shutdown():
    """World 关闭兜底：恢复 stdout"""
    from src.core.world_instance.handlers.scrcpy_server_handler import _restore_stdout
    try:
        _restore_stdout()
    except Exception:
        pass
