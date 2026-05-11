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
_control_queue: queue.Queue | None = None   # 从 TQS 接收控制帧
_update_queue: queue.Queue | None = None    # 从 TQS 接收 fid 消费通知(已废弃)
_ser = None

# ── 调试回传 ──
_debug_listeners: list = []
_debug_queue: queue.Queue = queue.Queue(maxsize=100)

# ── 屏幕分辨率（供边界校验，由 ADB 写入）──
_screen_w: int = 1080
_screen_h: int = 1920


def register():
    esper.set_handler("serial.start", _on_start)
    esper.set_handler("serial.stop", _on_stop)


def set_screen_size(w: int, h: int):
    global _screen_w, _screen_h
    _screen_w, _screen_h = w, h


def register_debug_listener(listener: callable):
    """注册调试监听器（UI 组件 on_humanize 回调）"""
    if listener not in _debug_listeners:
        _debug_listeners.append(listener)


def unregister_debug_listener(listener: callable):
    """注销调试监听器"""
    if listener in _debug_listeners:
        _debug_listeners.remove(listener)


def _on_start(control_q: queue.Queue, update_q: queue.Queue, port: str, baudrate: int, frequency: int):
    global _running, _thread, _control_queue, _update_queue, _ser
    from src.core.world_instance.handlers.serial_connect_handler import handle_connect
    _ser = handle_connect(port, baudrate)
    _control_queue = control_q
    _update_queue = update_q
    _running = True
    _thread = threading.Thread(
        target=_run, args=(frequency,), daemon=True, name="SerialSystem"
    )
    _thread.start()
    log.info(f"[Serial] 线程启动 {port}@{baudrate} {frequency}Hz")


def _on_stop():
    """停止：置标志位，等待线程自排空后退出"""
    global _running, _ser
    _running = False
    if _thread and _thread.is_alive():
        _thread.join(timeout=3)
    from src.core.world_instance.handlers.serial_connect_handler import handle_disconnect
    handle_disconnect(_ser)
    _ser = None
    log.info("[Serial] 线程停止")


def _run(frequency: int):
    interval = 1.0 / frequency
    while _running:
        time.sleep(interval)
        try:
            _process_control(_control_queue.get(timeout=0.001))
        except queue.Empty:
            pass
        try:
            fid = _update_queue.get(timeout=0.001)
            _process_frames(fid)
        except queue.Empty:
            pass
        except Exception as e:
            log.error(f"[Serial] 消费异常: {e}")
            _emergency_stop(str(e))
            return

    # ── 停机：排空残帧 ──
    _drain_remaining()


def _drain_remaining():
    """排空控制帧 + 窗口帧残帧"""
    # 排空 control_queue
    if _control_queue:
        while not _control_queue.empty():
            try:
                item = _control_queue.get_nowait()
                if hasattr(item, 'event_type'):
                    _process_control(item)
            except queue.Empty:
                break
    # 排空 update_queue → 消费残留 move 帧
    if _update_queue:
        while not _update_queue.empty():
            try:
                fid = _update_queue.get_nowait()
                _process_frames(fid)
            except queue.Empty:
                break


def _process_control(item):
    """处理控制帧 down/up"""
    from src.core.world_instance.handlers.safety_verify_handler import is_ok
    from src.core.world_instance.handlers.protocol_pack_handler import pack_d, pack_u

    if not is_ok(_ser):
        return

    if item.event_type == "down":
        # 拟人偏移
        fx, fy = _hum_offset(item.base_x, item.base_y)
        # 边界校验
        fx, fy = _boundary_check(item.base_x, item.base_y, fx, fy, item.size)
        # 打包发送
        _ser.write(pack_u(_get_fid(item.key_id)))
        _ser.write(pack_d(_get_fid(item.key_id), fx, fy))
        # 回调 TQS
        _mark_tqs(item.key_id, "down")
        # 调试回传
        _debug_emit(_get_fid(item.key_id), "down", fx, fy)
        log.info(f"[Serial] down: key={item.key_id} fid={_get_fid(item.key_id)} ({fx},{fy})")

    elif item.event_type == "up":
        _ser.write(pack_u(_get_fid(item.key_id)))
        _mark_tqs(item.key_id, "up")
        _debug_emit(_get_fid(item.key_id), "up", 0, 0)
        log.info(f"[Serial] up: key={item.key_id} fid={_get_fid(item.key_id)}")


def _process_frames(fid: int):
    """处理窗口帧 move 批次"""
    from src.core.world_instance.handlers.safety_verify_handler import is_ok
    from src.core.world_instance.handlers.protocol_pack_handler import pack_s

    if not is_ok(_ser) or fid < 0 or fid > 5:
        return

    import src.core.world_instance.touch_queue_system as tqs
    dq = tqs._frame_pool[fid]
    if not dq:
        return

    # 全量取出所有帧
    frames = list(dq)
    dq.clear()
    if not frames:
        return

    # 逐帧拟人平滑 + 边界校验 + 打包
    for i, ti in enumerate(frames):
        base_x, base_y = ti.base_x, ti.base_y
        fx, fy = _hum_smooth(fid, base_x, base_y)
        fx, fy = _boundary_check(base_x, base_y, fx, fy, ti.size)
        log.info(f"[Serial] move: fid={fid} frame={i} hum=({fx},{fy})")
        _ser.write(pack_s(fid, fx, fy))
        _debug_emit(fid, "move", fx, fy)


# ── 拟人化 ──

def _hum_offset(x: int, y: int) -> tuple:
    from src.core.world_instance.handlers.humanize_click_handler import offset_click
    return offset_click(x, y)


def _hum_smooth(fid: int, x: int, y: int) -> tuple:
    from src.core.world_instance.handlers.humanize_move_handler import smooth_weighted
    return smooth_weighted(fid, x, y)


# ── 边界校验 ──

def _boundary_check(base_x: int, base_y: int, x: int, y: int, size: int) -> tuple[int, int]:
    """双重校验:
    1) 欧氏距离 > size 半径 → 投影至圆边缘
    2) 钳制至屏幕范围
    """
    if size <= 0:
        size = 40
    dx = x - base_x
    dy = y - base_y
    dist = math.sqrt(dx * dx + dy * dy)
    if dist > size and dist > 0:
        ratio = size / dist
        x = int(base_x + dx * ratio)
        y = int(base_y + dy * ratio)
    # 钳制屏幕
    x = max(0, min(_screen_w, x))
    y = max(0, min(_screen_h, y))
    return x, y


# ── 辅助 ──

def _get_fid(key_id: str) -> int:
    import src.core.world_instance.touch_queue_system as tqs
    session = tqs._session_table.get(key_id, {})
    return session.get("fid", -1)


def _mark_tqs(key_id: str, event_type: str):
    import src.core.world_instance.touch_queue_system as tqs
    tqs.mark_consumed(key_id, event_type)


# ── 调试回传 ──

def _debug_emit(fid: int, event_type: str, final_x: int, final_y: int):
    """构造调试字典 → _debug_queue"""
    if not _debug_listeners:
        return
    data = {
        "fid": fid,
        "event_type": event_type,
        "final_x": final_x,
        "final_y": final_y,
        "ratio_x": final_x / max(1, _screen_w),
        "ratio_y": final_y / max(1, _screen_h),
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
