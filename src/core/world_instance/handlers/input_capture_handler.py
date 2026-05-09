"""InputCaptureHandler — 接收 UI 按键事件，匹配映射，计算坐标"""
import esper
from src.core.world_instance.components.touch_input import TouchInput
from src.utils.logger import log
from src.utils.logger import log


def handle_input(hotkey: str, event: str, x: int = 0, y: int = 0):
    """UI 按键事件入口
    event: 'press' | 'release' | 'move'
    x, y: 屏幕像素坐标（由 UI 层预计算或在此转换）
    """
    import src.core.world_instance.key_mapping_system as kms
    if not kms._running or kms._direct_queue is None:
        return

    # 查找映射
    route = kms._route_map.get(hotkey)

    if event == 'press':
        if route is None:
            from src.core.world_instance.handlers.finger_assign_handler import assign
            fid = assign()
            kms._route_map[hotkey] = {"finger_id": fid}
            log.info(f"[KMS] down fid={fid} key={hotkey} ({x},{y})")
        ti = TouchInput(x=x, y=y, event_type="down", key_id=hotkey)
        kms._direct_queue.put(ti)

    elif event == 'release':
        if route is not None:
            ti = TouchInput(x=0, y=0, event_type="up", key_id=hotkey)
            kms._direct_queue.put(ti)
            from src.core.world_instance.handlers.finger_release_handler import release
            release(route["finger_id"])
            del kms._route_map[hotkey]

    elif event == 'move':
        if route is not None:
            ti = TouchInput(x=x, y=y, event_type="move", key_id=hotkey)
            kms._input_queue.put(ti)
