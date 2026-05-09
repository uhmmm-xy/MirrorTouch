"""TouchQueueSystem — 实时帧队列，独立线程"""
import esper
import queue
import threading
from src.utils.logger import log

_running: bool = False
_thread: threading.Thread | None = None
# 帧队列池: finger_id → FrameQueue
_pool: dict = {}
# 从 KeyMappingSystem 接收输入
_input_queue: queue.Queue | None = None
# 到 SerialSystem
_output_queue: queue.Queue | None = None
_update_queue: queue.Queue | None = None


def register():
    esper.set_handler("queue.start", _on_start)
    esper.set_handler("queue.stop", _on_stop)
    esper.set_handler("queue.push", _on_push)


def _on_start(in_q: queue.Queue, update_q: queue.Queue):
    global _running, _thread, _input_queue, _update_queue
    _input_queue = in_q
    _update_queue = update_q
    _running = True
    _pool.clear()
    _thread = threading.Thread(target=_run, daemon=True, name="TouchQueueSystem")
    _thread.start()
    log.info("[TouchQueue] 线程启动")


def _on_stop():
    global _running, _thread
    _running = False
    _pool.clear()
    log.info("[TouchQueue] 线程停止")


def _on_push(touch_input):
    from src.core.world_instance.handlers.queue_push_handler import handle_push
    handle_push(touch_input, _pool, _input_queue, _update_queue)


def _run():
    while _running:
        try:
            _on_push(_input_queue.get(timeout=0.005))
        except queue.Empty:
            pass
