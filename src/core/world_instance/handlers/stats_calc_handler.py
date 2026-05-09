"""StatsCalcHandler — 帧率与丢帧统计"""
import esper
import time
from src.core.world_instance.components.frame_stats import FrameStats


_last_time: float = 0.0
_frame_count: int = 0


def register():
    esper.set_handler("stats.calc", _on_calc)


def _on_calc(device_entity: int):
    """每次调用刷新 FPS（基于上次调用以来的帧率）"""
    global _last_time, _frame_count
    now = time.time()
    if not esper.entity_exists(device_entity):
        return
    stats = esper.component_for_entity(device_entity, FrameStats)
    current_total = stats.total
    if _last_time > 0 and _frame_count > 0:
        elapsed = now - _last_time
        if elapsed > 0:
            stats.fps = (current_total - _frame_count) / elapsed
    _last_time = now
    _frame_count = current_total
