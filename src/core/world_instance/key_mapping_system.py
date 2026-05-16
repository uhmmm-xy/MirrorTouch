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


# ========== PUBLIC API ==========

def push_physical_input(hotkey: str, event: str, ratio_x: float = 0.0, ratio_y: float = 0.0):
    """物理设备管道入口 — 纯生产者。

    职责：查映射 → 生成 TouchInput → 推入统一队列。
    不持有会话状态、锁、fid生命周期（全部在 TQS 内部管理）。

    Args:
        hotkey:  按键标识 (如 "W", "LeftButton", "\\")
        event:   事件类型 'press' | 'release' | 'move'
        ratio_x: 比例坐标 X (0.0~1.0), press/release 传 0
        ratio_y: 比例坐标 Y (0.0~1.0), press/release 传 0
    """
    if not _running:
        return
    try:
        # log.info(f"[KMS] push: key={hotkey} event={event} ratio=({ratio_x:.6f},{ratio_y:.6f})")
        from src.core.world_instance.handlers.input_capture_handler import handle_input
        handle_input(hotkey, event, ratio_x, ratio_y)
    except Exception as e:
        log.error(f"[KMS] push异常: key={hotkey} event={event} err={e}")
        _emergency_stop(str(e))


def _on_input(hotkey: str, event: str, offset_x: float = 0.0, offset_y: float = 0.0):
    """UI 管道入口 — 纯转发到 input_capture_handler

    offset_x/offset_y: 鼠标移动增量比例 (move), press/release 传 (0,0)
    """
    if not _running:
        return
    try:
        from src.core.world_instance.handlers.input_capture_handler import handle_input
        handle_input(hotkey, event, offset_x, offset_y)
    except Exception as e:
        log.error(f"[KMS] 异常: key={hotkey} event={event} err={e}")
        _emergency_stop(str(e))


def _on_start(config):
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

    # ── 启动后自动激活 Eyes 组件 ──
    _activate_eyes_session()

    log.info("[KMS] 已启动")


def _on_stop():
    """停止顺序: 关闭 Eyes → KMS停生产 → Serial排空 → Serial停机 → TQS停机 → KMS清理"""
    global _running, _output_queue
    _running = False  # 1. 停止生产

    # 1.5 关闭 Eyes session
    _deactivate_eyes_session()

    # 2. 停止 SerialSystem（先停消费、排空控制队列）
    import esper
    esper.dispatch_event("serial.stop")

    # 3. 停止 TouchQueueSystem（清空帧池与会话）
    esper.dispatch_event("queue.stop")

    # 4. 清理 Entity
    _destroy_all_entities()
    _output_queue = None
    log.info("[KMS] 已停止")


def _emergency_stop(reason: str = ""):
    """[T7] KMS 层异常停机：置 running=False，通知 UI"""
    global _running
    _running = False
    log.info(f"[KMS] 紧急停机: {reason}")
    esper.dispatch_event("touch.error", f"KeyMappingSystem: {reason}")


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


# ── Eyes Session 生命周期 ──

def _activate_eyes_session():
    """KMS 启动时自动激活 Eyes 组件，创建 touch session。

    从 Esper 查找 widget_type==eyes 的第一个实体，
    调用 activate() 下发 down 帧，eyes key 从 WidgetConfig 读取。
    """
    from src.core.world_instance.components.widget_config import WidgetConfig
    from src.core.world_instance.handlers.eyes_widget_handler import activate, is_active

    for ent, (wc,) in esper.get_components(WidgetConfig):
        if wc.widget_type == "eyes":
            if not is_active(wc.key_id):
                ti = activate(wc.key_id, wc.pos_x, wc.pos_y, wc.scale_size)
                if _output_queue and ti:
                    _output_queue.put(ti)
                    log.info(f"[KMS] Eyes 已激活: key={wc.key_id}")
            return
    log.warning("[KMS] 未找到 Eyes 实体，跳过激活")


def _deactivate_eyes_session():
    """KMS 停止时关闭 Eyes session，下发 up 帧。"""
    from src.core.world_instance.components.widget_config import WidgetConfig
    from src.core.world_instance.handlers.eyes_widget_handler import deactivate, is_active

    for ent, (wc,) in esper.get_components(WidgetConfig):
        if wc.widget_type == "eyes":
            if is_active(wc.key_id):
                ti = deactivate(wc.key_id)
                if _output_queue and ti:
                    _output_queue.put(ti)
                    log.info(f"[KMS] Eyes 已停用: key={wc.key_id}")
            return


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
