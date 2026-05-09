"""KeyMappingSystem — 键鼠映射核心"""
import esper
from src.utils.logger import log

# 路由会话通道: key_id → {finger_id, queue_ref}
_route_map: dict = {}
# 线程安全队列 → TouchQueueSystem
_input_queue = None  # queue.Queue, 由 SessionControlHandler 创建
# 最优通道队列 → SerialSystem (click/down/up)
_direct_queue = None  # queue.Queue
# 活跃标志
_running: bool = False


def register():
    esper.set_handler("touch.start", _on_start)
    esper.set_handler("touch.stop", _on_stop)
    esper.set_handler("touch.input", _on_input)


def _on_start(config):
    from src.core.world_instance.handlers.session_control_handler import handle_start
    handle_start(config)


def _on_stop():
    from src.core.world_instance.handlers.session_control_handler import handle_stop
    handle_stop()


def _on_input(hotkey: str, event: str, x: int = 0, y: int = 0):
    """UI 按键事件入口"""
    from src.core.world_instance.handlers.input_capture_handler import handle_input
    handle_input(hotkey, event, x, y)
