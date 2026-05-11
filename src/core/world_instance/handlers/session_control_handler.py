"""SessionControlHandler — 启停串口系统和帧队列

[MIRROR-TOUCH-T2] 接收 KMS 创建的 output_queue，启动 TQS 和 SerialSystem。
KMS 为纯生产者，本 Handler 仅做生命周期管理。
"""
import queue
from src.utils.logger import log


def handle_start(config, output_queue: queue.Queue):
    """启动触控链路：TQS → SerialSystem

    Args:
        config: TouchConfig (port, baudrate, consume_frequency)
        output_queue: KMS 的统一出口队列
    """
    control_q = queue.Queue()   # TQS 内部控制帧队列 → SerialSystem
    update_q = queue.Queue()    # SerialSystem 消费通知 → TQS (fid)
    port = config.port or "COM3"
    baudrate = config.baudrate or 115200
    freq = config.consume_frequency or 800

    import esper
    esper.dispatch_event("serial.start", control_q, update_q, port, baudrate, freq)
    esper.dispatch_event("queue.start", output_queue, control_q, update_q)

    # ADB 真实分辨率 → 写入 TouchConfig 和 SerialSystem
    try:
        from src.core.config_manager import load_config
        from src.core.world_instance.handlers.adb_handler import get_screen_size
        cfg2 = load_config()
        w, h = get_screen_size(cfg2.adb_path)
        from src.core.world_instance.handlers.coordinate_calc_handler import set_screen_size
        set_screen_size(w, h)
        from src.core.world_instance.serial_system import set_screen_size as serial_set_size
        serial_set_size(w, h)
        log.info(f"[SessionControl] ADB 分辨率: {w}x{h}")
    except Exception as e:
        log.warning(f"[SessionControl] ADB 分辨率获取失败, 使用默认: {e}")

    log.info(f"[SessionControl] 触控启动 {port}@{baudrate} {freq}Hz")


def handle_stop():
    """停止：关闭 TouchQueue → 关闭 Serial"""
    import esper
    esper.dispatch_event("queue.stop")
    esper.dispatch_event("serial.stop")
    log.info("[SessionControl] 触控停止")
