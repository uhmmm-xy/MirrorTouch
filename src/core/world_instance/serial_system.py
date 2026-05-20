"""SerialSystem — 串口消费，独立线程

[MIRROR-TOUCH-T2/T6/T7] 职责：
  1. 消费控制帧(down/up)：拟人偏移 → 协议打包 → 串口写入 → 回调 TQS.mark_consumed
  2. 消费窗口帧(move)：全量取出 → 拟人加权平滑 → 边界校验 → 打包 → 串口
  3. 边界校验：欧氏距离 > size 半径? 投影; 超出屏幕? 钳制
  4. 调试回传：拟人后构造字典 → _debug_queue → UI 轮询
  5. 异常捕获：try...except 包裹主循环 → _emergency_stop
"""
import math
import time
import queue
import threading
import esper
from src.utils.logger import log

_running: bool = False
_thread: threading.Thread | None = None
_ser = None

# ── 调试回传 ──
_debug_listeners: list = []
_debug_queue: queue.Queue = queue.Queue(maxsize=100)


def register():
    esper.set_handler("serial.start", _on_start)
    esper.set_handler("serial.stop", _on_stop)


def register_debug_listener(listener: callable):
    """注册调试监听器（UI 组件 on_humanize 回调）"""
    if listener not in _debug_listeners:
        _debug_listeners.append(listener)


def unregister_debug_listener(listener: callable):
    """注销调试监听器"""
    if listener in _debug_listeners:
        _debug_listeners.remove(listener)


def _on_start(port: str, baudrate: int, frequency: int):
    global _running, _thread, _ser
    from src.core.world_instance.handlers.serial_connect_handler import handle_connect
    _ser = handle_connect(port, baudrate)
    _running = True

    _thread = threading.Thread(
        target=_run, args=(frequency,), daemon=True, name="SerialSystem"
    )
    _thread.start()
    log.info(f"[Serial] 线程启动 {port}@{baudrate} {frequency}Hz")


def _serial_write(data: bytes):
    """写串口（调试完成，不输出日志）"""
    if _ser and _ser.is_open:
        _ser.write(data)


def _on_stop():
    """停止：置标志位，等待线程自排空后退出"""
    global _running, _ser
    _running = False
    if _thread and _thread.is_alive():
        _thread.join(timeout=3)
    # 停机后清空残留
    _drain_remaining()
    from src.core.world_instance.handlers.serial_connect_handler import handle_disconnect
    handle_disconnect(_ser)
    _ser = None
    log.info("[Serial] 线程停止")


def _run(frequency: int):
    interval = 1.0 / frequency
    while _running:
        time.sleep(interval)
        try:
            _consume_all_pools()
        except Exception as e:
            log.error(f"[Serial] 消费异常: {e}")
            _emergency_stop(str(e))
            return
    # ── 停机：排空残帧 ──
    _drain_remaining()


def _consume_all_pools():
    """每周期构建全量6指包 → 串口写入"""
    _build_full_frame()


def _build_full_frame():
    """遍历 6 个 _frame_pool，每指取 1 帧 → 拼全量包 → 写串口"""
    from src.core.world_instance.handlers.protocol_pack_handler import pack_full_frame, STATUS_PRESS, STATUS_RELEASE
    import src.core.world_instance.touch_queue_system as tqs

    fingers = []
    for fid in range(6):
        dq = tqs._frame_pool[fid]
        if dq:
            ti = dq.popleft()
            status = STATUS_RELEASE if ti.event_type == "up" else STATUS_PRESS
            fx, fy = _rotate_ratio(ti.x, ti.y)
            nx = int(min(max(fx, 0.0), 1.0) * 32767)
            ny = int(min(max(fy, 0.0), 1.0) * 32767)
            fingers.append({"fid": fid, "status": status, "x": nx, "y": ny})
            # # 消费后记录到 _last_frame（供 TQS 补帧）
            tqs._last_frame[fid] = ti
            if ti.event_type == "up":
                _mark_tqs_fid(fid)
            _debug_emit(fid, ti.event_type, fx, fy)
        else:
            fingers.append({"fid": fid, "status": STATUS_RELEASE, "x": 0, "y": 0})

    data = pack_full_frame(fingers)
    _serial_write(data)
    # TQS 维持 press 状态：SS 取帧后若 deque 空 → 复制 press 帧回 deque
    import src.core.world_instance.touch_queue_system as _tqs
    for fid in range(6):
        _tqs.maintain_press_state(fid)


def _drain_remaining():
    """排空所有 _frame_pool 残帧，全量包发送"""
    _build_full_frame()


# ── 辅助 ──

def _get_fid(key_id: str) -> int:
    import src.core.world_instance.touch_queue_system as tqs
    session = tqs._session_table.get(key_id, {})
    return session.get("fid", -1)


def _mark_tqs_fid(fid: int):
    import src.core.world_instance.touch_queue_system as tqs
    tqs.mark_consumed_fid(fid)


# ── 调试回传 ──

def _debug_emit(fid: int, event_type: str, final_x: float, final_y: float):
    """构造调试字典 → _debug_queue"""
    if not _debug_listeners:
        return
    data = {
        "fid": fid,
        "event_type": event_type,
        "ratio_x": final_x,
        "ratio_y": final_y,
        "timestamp": time.time(),
    }
    try:
        log.warning(f"[Serial] Debug Emit: {data}")
        _debug_queue.put_nowait(data)
    except queue.Full:
        pass  # 满则丢弃最新


# ── 异常停机 ──

def _emergency_stop(reason: str = ""):
    global _running
    _running = False
    from src.core.world_instance.handlers.serial_connect_handler import handle_disconnect
    if _ser and _ser.is_open:
        handle_disconnect(_ser)
    log.info(f"[Serial] 紧急停机: {reason}")
    esper.dispatch_event("touch.error", f"SerialSystem: {reason}")


# ── [MIRROR-TOUCH-T2] 比例旋转（在打包前统一应用）──

def _rotate_ratio(rx: float, ry: float) -> tuple[float, float]:
    """按 DeviceComponent.current_rotation 旋转比例坐标"""
    try:
        from src.core.world_instance.world_bootstrap import get_device_meta_entity
        from src.core.world_instance.components.device_component import DeviceComponent
        from src.core.world_instance.handlers.ratio_validate_handler import apply_rotation

        ent = get_device_meta_entity()
        if ent == 0 or not esper.entity_exists(ent):
            return rx, ry
        dc = esper.component_for_entity(ent, DeviceComponent)
        return apply_rotation(rx, ry, dc.current_rotation)
    except Exception:
        return rx, ry
