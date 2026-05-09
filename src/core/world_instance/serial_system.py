"""SerialSystem — 串口服务，独立线程"""
import esper
import queue
import threading
from src.utils.logger import log

_running: bool = False
_thread: threading.Thread | None = None
_output_queue: queue.Queue | None = None
_update_queue: queue.Queue | None = None
_ser = None


def register():
    esper.set_handler("serial.start", _on_start)
    esper.set_handler("serial.stop", _on_stop)


def _on_start(out_q: queue.Queue, update_q: queue.Queue, port: str, baudrate: int, frequency: int):
    global _running, _thread, _output_queue, _update_queue, _ser
    from src.core.world_instance.handlers.serial_connect_handler import handle_connect
    _ser = handle_connect(port, baudrate)
    _output_queue = out_q
    _update_queue = update_q
    _running = True
    _thread = threading.Thread(
        target=_run, args=(frequency,), daemon=True, name="SerialSystem"
    )
    _thread.start()
    log.info(f"[Serial] 线程启动 {port}@{baudrate} {frequency}Hz")


def _on_stop():
    global _running, _ser
    _running = False
    from src.core.world_instance.handlers.serial_connect_handler import handle_disconnect
    handle_disconnect(_ser)
    _ser = None
    log.info("[Serial] 线程停止")


def _run(frequency: int):
    interval = 1.0 / frequency
    import time
    while _running:
        time.sleep(interval)
        try:
            _process(_output_queue.get(timeout=0.001))
        except queue.Empty:
            pass
        try:
            _consume_finger(_update_queue.get(timeout=0.001))
        except queue.Empty:
            pass


def _process(item):
    from src.core.world_instance.handlers.safety_verify_handler import is_ok
    from src.core.world_instance.handlers.protocol_pack_handler import pack_d, pack_u
    import src.core.world_instance.key_mapping_system as kms
    import src.core.world_instance.touch_queue_system as tqs
    if not is_ok(_ser):
        return
    route = kms._route_map.get(item.key_id, {})
    fid = route.get("finger_id", 0)

    if item.event_type == "down":
        fq = tqs._pool.get(fid)
        if fq:
            with fq.lock:
                fq.frames.clear(); fq.has_update = False
                _ser.write(pack_u(fid))
                x, y = _hum_offset(item.x, item.y)
                _ser.write(pack_d(fid, x, y))
        else:
            _ser.write(pack_u(fid))
            x, y = _hum_offset(item.x, item.y)
            _ser.write(pack_d(fid, x, y))
    elif item.event_type == "up":
        fq = tqs._pool.get(fid)
        if fq:
            with fq.lock:
                fq.frames.clear(); fq.has_update = False
                _ser.write(pack_u(fid))
        else:
            _ser.write(pack_u(fid))


def _hum_offset(x: int, y: int) -> tuple:
    from src.core.world_instance.handlers.humanize_click_handler import offset_click
    return offset_click(x, y)


def _consume_finger(fid: int):
    from src.core.world_instance.handlers.safety_verify_handler import is_ok
    from src.core.world_instance.handlers.queue_pop_handler import pop_batch
    from src.core.world_instance.handlers.humanize_move_handler import smooth_3f
    from src.core.world_instance.handlers.protocol_pack_handler import pack_s
    import src.core.world_instance.touch_queue_system as tqs
    if not is_ok(_ser):
        return
    fq = tqs._pool.get(fid)
    if not fq:
        return
    batch = pop_batch(fq)
    if not batch:
        return
    px, py = 0, 0
    for ti in batch:
        mx, my = smooth_3f(px, py, ti.x, ti.y)
        _ser.write(pack_s(fid, mx, my))
        px, py = mx, my
