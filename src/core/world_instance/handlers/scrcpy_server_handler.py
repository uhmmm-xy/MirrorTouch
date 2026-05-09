"""ScrcpyServerHandler — 构建参数 + 调用 framebridge.dll 启停"""
import os
import sys
import ctypes
from ctypes import POINTER
import esper
from datetime import datetime
from src.utils.logger import log


class FrameData(ctypes.Structure):
    _fields_ = [
        ("frame_id",     ctypes.c_uint64),
        ("timestamp_ms", ctypes.c_uint64),
        ("width",        ctypes.c_int32),
        ("height",       ctypes.c_int32),
        ("size",         ctypes.c_int32),
        ("_padding",     ctypes.c_int32),
    ]


_dll: ctypes.CDLL | None = None
_scrcpy_server_path: str = ""
_stdout_fd: int = -1
_log_file = None


def register():
    esper.set_handler("scrcpy.start", _on_start)
    esper.set_handler("scrcpy.stop", _on_stop)


def _get_dll() -> ctypes.CDLL | None:
    global _dll, _scrcpy_server_path
    if _dll is not None:
        return _dll

    sdk_dir = os.path.join("resources", "libs", "FrameBridge_SDK")
    dll_path = os.path.join(sdk_dir, "framebridge.dll")
    server_path = os.path.join(sdk_dir, "scrcpy-server")
    _scrcpy_server_path = server_path

    if not os.path.exists(dll_path):
        log.error(f"[ScrcpyServer] framebridge.dll 未找到: {dll_path}")
        return None

    try:
        _dll = ctypes.CDLL(dll_path)
        _dll.frame_server_start.argtypes = [
            ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_int32, ctypes.c_int32, ctypes.c_int32,
        ]
        _dll.frame_server_start.restype = ctypes.c_int32
        # 与测试脚本对齐：restype = POINTER(FrameData) 而非 c_void_p
        _dll.frame_server_read.argtypes = [ctypes.c_int32]
        _dll.frame_server_read.restype = POINTER(FrameData)
        _dll.frame_server_stop.argtypes = []
        _dll.frame_server_stop.restype = None
        _dll.frame_server_get_error.argtypes = []
        _dll.frame_server_get_error.restype = ctypes.c_char_p
        log.info(f"[ScrcpyServer] DLL 加载成功: {dll_path}")
        return _dll
    except Exception as e:
        log.error(f"[ScrcpyServer] DLL 加载失败: {e}")
        return None


def _on_start(session_entity: int, device_entity: int):
    from src.core.world_instance.components.stream_config import StreamConfig
    from src.core.world_instance.components.device_config import DeviceConfig
    from src.core.world_instance.components.stream_session import StreamSession
    from src.core.config_manager import load_config

    sc = esper.component_for_entity(session_entity, StreamConfig)
    dc = esper.component_for_entity(device_entity, DeviceConfig)
    session = esper.component_for_entity(session_entity, StreamSession)
    app_cfg = load_config()

    session.state = "connecting"

    dll = _get_dll()
    if dll is None:
        session.state = "error"
        return

    # 计算比特率 kbps（"16000" → 16000）
    try:
        bit_rate_kbps = int(sc.bit_rate)
    except ValueError:
        bit_rate_kbps = 8000

    adb_path = app_cfg.adb_path.encode("utf-8")
    server_path = _scrcpy_server_path.encode("utf-8")
    serial = dc.serial.encode("utf-8") if dc.serial else "".encode("utf-8")

    log.info(f"[ScrcpyServer] 启动 {sc.max_size}p {sc.max_fps}fps {bit_rate_kbps}kbps")
    _redirect_stdout(app_cfg.log_middleware_stdout, dc.serial or "device")
    ret = dll.frame_server_start(adb_path, server_path, serial, sc.max_size, sc.max_fps, bit_rate_kbps)

    if ret != 0:
        err = dll.frame_server_get_error()
        log.error(f"[ScrcpyServer] 启动失败: {err.decode() if err else 'unknown'}")
        session.state = "error"
    else:
        session.state = "streaming"
        esper.dispatch_event("frame.drain.start", device_entity)
        log.info("[ScrcpyServer] 推流已启动")


def _on_stop(session_entity: int, device_entity: int):
    esper.dispatch_event("frame.drain.stop", device_entity)

    from src.core.world_instance.components.stream_session import StreamSession
    if esper.entity_exists(session_entity) and esper.has_component(session_entity, StreamSession):
        session = esper.component_for_entity(session_entity, StreamSession)
        session.state = "stopped"

    dll = _get_dll()
    if dll:
        dll.frame_server_stop()
    _restore_stdout()
    log.info("[ScrcpyServer] 已停止")


def _redirect_stdout(enabled: bool, device_id: str):
    """重定向 C 层 stdout 不影响 Python sys.stdout"""
    global _stdout_fd, _log_file
    if enabled:
        os.makedirs("resources/logs", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join("resources", "logs", f"middleware_{device_id}_{ts}.log")
        _log_file = open(path, "w", encoding="utf-8")
        _stdout_fd = os.dup(1)
        os.dup2(_log_file.fileno(), 1)
        log.info(f"[ScrcpyServer] 中间件日志: {path}")
    else:
        _stdout_fd = os.dup(1)
        _devnull = open(os.devnull, "w")
        os.dup2(_devnull.fileno(), 1)


def _restore_stdout():
    """恢复 stdout"""
    global _stdout_fd, _log_file
    if _stdout_fd >= 0:
        sys.stdout.flush()
        os.dup2(_stdout_fd, 1)
        os.close(_stdout_fd)
        _stdout_fd = -1
    if _log_file:
        _log_file.flush()
        _log_file.close()
        _log_file = None