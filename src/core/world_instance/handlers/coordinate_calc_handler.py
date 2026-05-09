"""CoordinateCalcHandler — 组件相对坐标 → 屏幕像素坐标"""
from src.core.world_instance.components.latest_frame import LatestFrame
from src.core.world_instance.world_bootstrap import get_current_device
import esper

_screen_w: int = 1080
_screen_h: int = 1920


def set_screen_size(w: int, h: int):
    global _screen_w, _screen_h
    _screen_w, _screen_h = w, h


def calc_pixel(rx: float, ry: float) -> tuple[int, int]:
    if _screen_w > 0 and _screen_h > 0:
        return int(rx * _screen_w), int(ry * _screen_h)
    device = get_current_device()
    if device and esper.entity_exists(device) and esper.has_component(device, LatestFrame):
        lf = esper.component_for_entity(device, LatestFrame)
        if lf.width > 0:
            return int(rx * lf.width), int(ry * lf.height)
    return int(rx * 1080), int(ry * 1920)
