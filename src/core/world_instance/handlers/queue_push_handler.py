"""QueuePushHandler — 移动帧入队"""
import esper
from src.core.world_instance.components.touch_input import TouchInput
from src.core.world_instance.components.frame_queue import FrameQueue
from src.utils.logger import log


def handle_push(ti: TouchInput, pool: dict, in_q, update_q):
    if ti.event_type in ("down", "up"):
        return
    fid = _get_finger(ti.key_id, pool)
    if fid < 0:
        return
    if fid not in pool:
        pool[fid] = FrameQueue(finger_id=fid)
    fq = pool[fid]
    fq.frames.append(ti)
    if not fq.has_update:
        fq.has_update = True
        update_q.put(fid)


def _get_finger(key_id: str, pool: dict) -> int:
    import src.core.world_instance.key_mapping_system as kms
    route = kms._route_map.get(key_id, {})
    return route.get("finger_id", -1)
