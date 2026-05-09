"""SessionControlHandler — 启停串口系统和帧队列"""
import queue
from src.utils.logger import log


def handle_start(config):
    in_q = queue.Queue(maxsize=200)
    direct_q = queue.Queue()
    update_q = queue.Queue()
    port = config.port or "COM3"
    baudrate = config.baudrate or 115200
    freq = config.consume_frequency or 800

    import esper
    esper.dispatch_event("serial.start", direct_q, update_q, port, baudrate, freq)
    esper.dispatch_event("queue.start", in_q, update_q)

    # ADB 真实分辨率
    try:
        from src.core.config_manager import load_config
        from src.core.world_instance.handlers.adb_handler import get_screen_size
        cfg2 = load_config()
        w, h = get_screen_size(cfg2.adb_path)
        from src.core.world_instance.handlers.coordinate_calc_handler import set_screen_size
        set_screen_size(w, h)
    except Exception:
        pass

    import src.core.world_instance.key_mapping_system as kms
    kms._input_queue = in_q
    kms._direct_queue = direct_q
    kms._running = True
    log.info(f"[SessionControl] 触控启动 {port}@{baudrate} {freq}Hz")


def handle_stop():
    """停止：关闭 TouchQueue → 关闭 Serial → 清空路由"""
    import esper
    esper.dispatch_event("queue.stop")
    esper.dispatch_event("serial.stop")

    import src.core.world_instance.key_mapping_system as kms
    kms._running = False
    kms._route_map.clear()
    kms._input_queue = None
    kms._direct_queue = None
    log.info("[SessionControl] 触控停止")
