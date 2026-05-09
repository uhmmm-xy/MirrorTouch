"""FrameDrainHandler — QTimer 循环 frame_server_read → LatestFrame"""
import ctypes
from ctypes import POINTER, cast, sizeof, c_void_p, c_uint8, addressof
import esper
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage
from src.utils.logger import log
from src.core.world_instance.components.latest_frame import LatestFrame
from src.core.world_instance.components.frame_stats import FrameStats
from src.core.world_instance.handlers.scrcpy_server_handler import _get_dll, FrameData


_timer: QTimer | None = None
_device_entity: int = 0
_frame_count: int = 0
_last_width: int = 0
_last_height: int = 0


def register():
    esper.set_handler("frame.drain.start", _on_start)
    esper.set_handler("frame.drain.stop", _on_stop)


def _on_start(device_entity: int):
    global _device_entity, _timer, _frame_count
    _device_entity = device_entity
    _frame_count = 0
    log.info("[FrameDrain] 等待解码器初始化 (1s 延迟)")
    QTimer.singleShot(1000, _start_timer)


def _start_timer():
    global _timer
    from src.core.config_manager import load_config
    cfg = load_config()
    interval = max(4, int(1000 / cfg.scrcpy_max_fps))
    _timer = QTimer()
    _timer.timeout.connect(_safe_drain)
    _timer.start(interval)
    log.info(f"[FrameDrain] 帧消费 {cfg.scrcpy_max_fps}fps ({interval}ms)")


def _on_stop(device_entity: int):
    global _timer, _device_entity, _frame_count
    if _timer:
        _timer.stop()
        _timer = None
    _device_entity = 0
    log.info(f"[FrameDrain] 帧消费停止 (共 {_frame_count} 帧)")


def _safe_drain():
    try:
        _drain_frame()
    except Exception as e:
        log.warning(f"[FrameDrain] QTimer 异常: {e}")


def _drain_frame():
    global _device_entity, _frame_count, _last_width, _last_height
    if _device_entity == 0 or not esper.entity_exists(_device_entity):
        return

    dll = _get_dll()
    if dll is None:
        return

    # 与 test_video.py 完全对齐的帧读取方式
    ptr = None
    try:
        ptr = dll.frame_server_read(16)
    except Exception:
        return
    if not ptr:
        return

    try:
        frame = ptr.contents
    except Exception:
        return
    if frame.size <= 0 or frame.width <= 0 or frame.height <= 0:
        return

    # 分辨率变更日志
    if _last_width != frame.width or _last_height != frame.height:
        log.info(f"[FrameDrain] 分辨率变更: {_last_width}x{_last_height} → {frame.width}x{frame.height}")
        _last_width = frame.width
        _last_height = frame.height

    expected = frame.width * frame.height * 3
    actual_data_size = frame.size
    if actual_data_size < expected:
        log.warning(f"[FrameDrain] 帧尺寸不匹配: 期望{expected} 实际{actual_data_size}, 跳过")
        return

    try:
        data_offset = sizeof(FrameData)
        data_ptr = cast(
            c_void_p(addressof(frame) + data_offset),
            POINTER(c_uint8 * frame.size)
        )
        rgb_bytes = bytes(data_ptr.contents)
    except Exception as e:
        log.warning(f"[FrameDrain] 读取帧数据失败: {e}")
        return

    try:
        qimg = QImage(rgb_bytes, frame.width, frame.height, frame.width * 3, QImage.Format_RGB888)
        if qimg.isNull():
            return
        qimg = qimg.copy()
    except Exception as e:
        log.warning(f"[FrameDrain] 解码帧失败: {e}")
        return

    try:
        lf = esper.component_for_entity(_device_entity, LatestFrame)
        lf.qimage = qimg
        lf.timestamp = frame.timestamp_ms
        lf.width = frame.width
        lf.height = frame.height

        stats = esper.component_for_entity(_device_entity, FrameStats)
        stats.total += 1
        _frame_count += 1

        # 每 60 帧触发一次 FPS 计算
        if _frame_count % 60 == 0:
            esper.dispatch_event("stats.calc", _device_entity)

        if _frame_count % 120 == 1:
            log.info(f"[FrameDrain] 帧 #{_frame_count} {frame.width}x{frame.height}")
    except Exception as e:
        log.warning(f"[FrameDrain] 写入 World 失败: {e}")
