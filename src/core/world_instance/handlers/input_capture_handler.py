"""InputCaptureHandler — 接收 UI 按键事件，匹配映射，计算坐标，生成 TouchInput 序列

[MIRROR-TOUCH-T2] UI 信息交换层：
  1. kms.find_entity_id(hotkey) → Esper Entity ID
  2. esper.component_for_entity(eid, WidgetConfig) → cfg
  3. press/release → 使用映射锚点
  4. move → 传递偏移量给 widget handler（由 handler 内部累积计算）
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
        log.warning(f"[InputCapture] 未找到实体: hotkey={hotkey} event={event}")
        return
    # log.info(f"[InputCapture] matched: hotkey={hotkey} eid={eid}")

    cfg = esper.component_for_entity(eid, WidgetConfig)

    # 映射锚点（比例值）—— press/release 使用
    # move 时偏移量传递给 widget handler 做累积计算
    base_rx, base_ry = cfg.pos_x, cfg.pos_y
    size_r = cfg.scale_size
    ox, oy = (offset_x, offset_y) if event == "move" else (0.0, 0.0)

    from src.core.world_instance.handlers.event_type_handler import generate_events
    events = generate_events(eid, cfg, event, ox, oy, base_rx, base_ry, size_r)

    if not events:
        return

    output_q = kms._output_queue
    if output_q is None:
        log.error("[InputCapture] output_queue 未初始化")
        return
    for ti in events:
        output_q.put(ti)
