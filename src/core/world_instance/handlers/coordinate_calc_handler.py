"""CoordinateCalcHandler — 相对坐标 → 屏幕像素坐标

[MIRROR-TOUCH-T5] 读取 TouchConfig 中的真实屏幕宽高，clamp 输出。
"""
from src.core.world_instance.components.latest_frame import LatestFrame
from src.core.world_instance.world_bootstrap import get_current_device
import esper

_screen_w: int = 1080
_screen_h: int = 1920


def set_screen_size(w: int, h: int):
    global _screen_w, _screen_h
    _screen_w, _screen_h = w, h


def calc_pixel(rx: float, ry: float) -> tuple[int, int]:
    """比例(0-1) → 屏幕像素，结果 clamp 到 [0, w-1] / [0, h-1]"""
    w, h = _screen_w, _screen_h

    # 优先从 TouchConfig 读取真实分辨率
    try:
        from src.core.world_instance.components.touch_config import TouchConfig
        from src.core.world_instance import touch_queue_system as tqs
        # 通过 Esper 查找 TouchConfig 组件
        for ent, (tc,) in esper.get_components(TouchConfig):
            if tc.screen_width > 0 and tc.screen_height > 0:
                w, h = tc.screen_width, tc.screen_height
                break
    except Exception:
        pass

    if w <= 0 or h <= 0:
        # fallback: LatestFrame
        device = get_current_device()
        if device and esper.entity_exists(device) and esper.has_component(device, LatestFrame):
            lf = esper.component_for_entity(device, LatestFrame)
            if lf.width > 0:
                w, h = lf.width, lf.height
            else:
                w, h = 1080, 1920

    px = int(rx * w)
    py = int(ry * h)
    return max(0, min(w - 1, px)), max(0, min(h - 1, py))
