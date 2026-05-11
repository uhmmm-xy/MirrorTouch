"""InputCaptureHandler — 接收 UI 按键事件，匹配映射，计算坐标，生成 TouchInput 序列

[MIRROR-TOUCH-T2] UI 信息交换层：
  1. kms.find_entity_id(hotkey) → Esper Entity ID
  2. esper.component_for_entity(eid, WidgetConfig) → cfg
  3. calc_pixel → base/offset 像素
  4. event_type_handler.generate_events(entity_id, cfg, ...) → TouchInput 序列（所有字段自完备）
  5. 全部推入 KMS._output_queue
"""
from src.utils.logger import log


def handle_input(hotkey: str, event: str, offset_x: float = 0.0, offset_y: float = 0.0):
    """UI 按键事件入口

    Args:
        hotkey:    按键标识
        event:     'press' | 'release' | 'move'
        offset_x/y: 鼠标增量比例 (move), press/release 传 0
    """
    import src.core.world_instance.key_mapping_system as kms
    import esper
    from src.core.world_instance.components.widget_config import WidgetConfig

    eid = kms.find_entity_id(hotkey)
    if eid == 0 or not esper.entity_exists(eid):
        log.warning(f"[InputCapture] 未找到实体: {hotkey}")
        return

    cfg = esper.component_for_entity(eid, WidgetConfig)

    from src.core.world_instance.handlers.coordinate_calc_handler import calc_pixel
    base_px, base_py = calc_pixel(cfg.pos_x, cfg.pos_y)
    size_px = int(cfg.scale_size * max(base_px + base_py, 100))

    offset_px, offset_py = 0, 0
    if event == "move":
        offset_px, offset_py = calc_pixel(offset_x, offset_y)

    from src.core.world_instance.handlers.event_type_handler import generate_events
    events = generate_events(eid, cfg, event, offset_px, offset_py, base_px, base_py, size_px)

    if not events:
        return

    output_q = kms._output_queue
    if output_q is None:
        log.error("[InputCapture] output_queue 未初始化")
        return
    for ti in events:
        output_q.put(ti)
