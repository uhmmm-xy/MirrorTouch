"""KeyMappingSystem — 键鼠映射核心（纯生产者）

[MIRROR-TOUCH-T2] 职责边界：
  本系统仅负责：加载映射 → 创建 Esper Entity → 查映射 → 计算像素 → 生成帧 → 推入队列。
  不持有：_route_map、_finger_pool、会话状态、通道锁。

[MIRROR-TOUCH-ENTITY] 实体管理：
  启动时从 mapping.json 创建 Esper Entity，每个按键对应一个 Entity 挂载 WidgetConfig。
  查询通过 esper.get_components(WidgetConfig) 遍历匹配 key_id。
"""
import json
import queue
import esper
from src.utils.logger import log

# 唯一出口队列 → TouchQueueSystem
_output_queue: queue.Queue | None = None
# 活跃标志
_running: bool = False
# 映射画布尺寸（加载 mapping.json 时赋值）
_map_width: int = 0
_map_height: int = 0


def register():
    esper.set_handler("touch.start", _on_start)
    esper.set_handler("touch.stop", _on_stop)
    esper.set_handler("touch.input", _on_input)


def _on_start(config):
    """加载映射 → 创建 Entity → 启动 TQS + SerialSystem"""
    global _output_queue, _running
    try:
        _load_entities()
    except Exception as e:
        log.error(f"[KMS] 映射加载失败: {e}")
        return

    _output_queue = queue.Queue()
    _running = True

    from src.core.world_instance.handlers.session_control_handler import handle_start
    handle_start(config, _output_queue)
    log.info("[KMS] 已启动")


def _on_stop():
    """停止顺序: KMS → Serial排空 → Serial停机 → TQS停机 → KMS清理"""
    global _running, _output_queue
    _running = False  # 1. 停止生产

    # 2. 停止 SerialSystem（先停消费、排空控制队列）
    import esper
    esper.dispatch_event("serial.stop")

    # 3. 停止 TouchQueueSystem（清空帧池与会话）
    esper.dispatch_event("queue.stop")

    # 4. 清理 Entity
    _destroy_all_entities()
    _output_queue = None
    log.info("[KMS] 已停止")


def _on_input(hotkey: str, event: str, x: float = 0.0, y: float = 0.0):
    """UI 按键事件入口 → 委托 InputCaptureHandler"""
    if not _running:
        return
    from src.core.world_instance.handlers.input_capture_handler import handle_input
    handle_input(hotkey, event, x, y)


# ── Entity 生命周期 ──

def _load_entities():
    """从 mapping.json 创建 Esper Entity，每种按键类型调用对应 create_xxx_entity()"""
    global _map_width, _map_height
    from src.core.config_manager import load_config
    from src.core.world_instance.components.widget_config import WidgetConfig

    cfg = load_config()
    mapping_path = cfg.mapping_path
    if not mapping_path:
        log.warning("[KMS] mapping_path 未配置")
        return
    with open(mapping_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # [MIRROR-TOUCH-T2] 存储映射画布尺寸供坐标转换使用
    _map_width = int(data.get("width", 1080))
    _map_height = int(data.get("height", 1920))

    type_to_creator = {
        "click":    _create_button,
        "hold":     _create_hold,
        "joystick": _create_joystick,
        "eyes":     _create_eyes,
        "radial":   _create_radial,
    }
    count = 0
    for w in data.get("widgets", []):
        key = w.get("key", "")
        if not key:
            continue
        wt = w.get("widget_type", "").lower()
        creator = type_to_creator.get(wt)
        if creator is None:
            log.warning(f"[KMS] 未知 widget_type: {wt}")
            continue
        wc = WidgetConfig(
            widget_type=wt,
            key_id=key,
            pos_x=float(w.get("pos_x", 0)),
            pos_y=float(w.get("pos_y", 0)),
            scale_size=float(w.get("scale_size", 0.03)),
        )
        creator(wc)
        count += 1
    log.info(f"[KMS] 加载 {count} 个按键实体")


def _create_button(cfg):
    from src.core.world_instance.entities.button_entity import create_button_entity
    create_button_entity(cfg)


def _create_hold(cfg):
    from src.core.world_instance.entities.hold_entity import create_hold_entity
    create_hold_entity(cfg)


def _create_joystick(cfg):
    from src.core.world_instance.entities.joystick_entity import create_joystick_entity
    create_joystick_entity(cfg)


def _create_eyes(cfg):
    from src.core.world_instance.entities.eyes_entity import create_eyes_entity
    create_eyes_entity(cfg)


def _create_radial(cfg):
    from src.core.world_instance.entities.radial_entity import create_radial_entity
    create_radial_entity(cfg)


def _destroy_all_entities():
    """销毁所有 WidgetConfig 实体（先收集 ID 再删除，避免迭代器污染）"""
    from src.core.world_instance.components.widget_config import WidgetConfig
    ids = [ent for ent, _ in esper.get_components(WidgetConfig)]
    for eid in ids:
        if esper.entity_exists(eid):
            esper.delete_entity(eid)
    if ids:
        log.info(f"[KMS] 销毁 {len(ids)} 个按键实体")


# ── 查询 ──

def find_config(hotkey: str):
    """通过 Esper 查找指定 key_id 的 WidgetConfig"""
    from src.core.world_instance.components.widget_config import WidgetConfig
    for ent, (wc,) in esper.get_components(WidgetConfig):
        if wc.key_id == hotkey:
            return wc
    return None


def find_entity_id(hotkey: str) -> int:
    """通过 Esper 查找指定 key_id 的 Entity ID"""
    from src.core.world_instance.components.widget_config import WidgetConfig
    for ent, (wc,) in esper.get_components(WidgetConfig):
        if wc.key_id == hotkey:
            return ent
    return 0
