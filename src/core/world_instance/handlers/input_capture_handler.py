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

    # [MIRROR-TOUCH-T3] 比例空间：锚点直接用映射的 ratio 值，不再截断为像素
    base_rx, base_ry = cfg.pos_x, cfg.pos_y
    size_r = cfg.scale_size

    offset_rx, offset_ry = 0.0, 0.0
    if event == "move":
        # move 传增量——eyes handler 内部累积
        offset_rx, offset_ry = offset_x, offset_y

    from src.core.world_instance.handlers.event_type_handler import generate_events
    events = generate_events(eid, cfg, event, offset_rx, offset_ry, base_rx, base_ry, size_r)

    if not events:
        return

    output_q = kms._output_queue
    if output_q is None:
        log.error("[InputCapture] output_queue 未初始化")
        return
    for ti in events:
        output_q.put(ti)
