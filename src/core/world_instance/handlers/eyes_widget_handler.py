"""EyesWidgetHandler — 视角组件完整交互流程

[MIRROR-TOUCH-EYES] 负责 eyes 组件的 session 创建、偏移累加、边界跳转、锚点定位。

  核心逻辑：
  1. activate:    以 (base_x,base_y) 为中心、size 为边长的正方形内随机 down
  2. on_move:     接收偏移增量 → base + offset → 矩形内自由 move
                  触碰边界 → up → 反方向象限随机点重新 down
  3. deactivate:  下发 up 结束会话
  4. 象限映射:    Q1→Q3, Q2→Q4, Q3→Q1, Q4→Q2

[MIRROR-TOUCH-ENTITY] generate() 是 Entity 驱动入口，event_type_handler 纯分发至此。
"""
import random
from src.core.world_instance.components.touch_input import TouchInput
from src.utils.logger import log

# key_id → {base_x, base_y, size, active}
_eyes_sessions: dict[str, dict] = {}


def generate(entity_id: int, cfg, event: str, ox: int, oy: int, bx: int, by: int, sz: int) -> list[TouchInput]:
    """Entity 驱动入口：event_type_handler 纯分发至此"""
    if event == "press":
        ti = activate(cfg.key_id, bx, by, sz)
        return [ti] if ti else []
    elif event == "move":
        return on_move(cfg.key_id, ox, oy)
    elif event == "release":
        ti = deactivate(cfg.key_id)
        return [ti] if ti else []
    return []


def activate(key_id: str, base_x: int, base_y: int, size: int) -> TouchInput:
    """激活视角会话：在正方形内随机取点，下发 down"""
    half = size / 2.0
    dx = (random.random() - 0.5) * size
    dy = (random.random() - 0.5) * size
    px = max(0, int(base_x + dx))
    py = max(0, int(base_y + dy))

    _eyes_sessions[key_id] = {
        "base_x": base_x,
        "base_y": base_y,
        "size": size,
        "active": True,
        "acc_x": 0,   # 累积偏移 X
        "acc_y": 0,   # 累积偏移 Y
    }
    return TouchInput(
        base_x=base_x, base_y=base_y,
        x=px, y=py,
        event_type="down", key_id=key_id, size=size,
    )


def on_move(key_id: str, offset_px: int, offset_py: int) -> list[TouchInput]:
    """处理鼠标偏移增量 → 累积偏移 → 锚点 + 累积 = 实际位置 → 边界检测

    Args:
        key_id:      按键标识
        offset_px/y: 本次鼠标移动的像素增量
    """
    session = _eyes_sessions.get(key_id)
    if not session or not session["active"]:
        return []

    # 累积偏移
    session["acc_x"] += offset_px
    session["acc_y"] += offset_py
    acc_x = session["acc_x"]
    acc_y = session["acc_y"]

    base_x = session["base_x"]
    base_y = session["base_y"]
    size = session["size"]
    half = size / 2.0

    # 锚点 + 累积偏移 = 实际触摸位置
    px = base_x + acc_x
    py = base_y + acc_y

    dx_from_base = px - base_x
    dy_from_base = py - base_y

    # 触碰边界？
    if abs(dx_from_base) >= half or abs(dy_from_base) >= half:
        return _jump_opposite(key_id, session, dx_from_base, dy_from_base)

    # 正常 move
    return [TouchInput(
        base_x=base_x, base_y=base_y,
        x=px, y=py,
        event_type="move", key_id=key_id, size=size,
    )]


def deactivate(key_id: str) -> TouchInput | None:
    """结束视角会话"""
    session = _eyes_sessions.pop(key_id, None)
    if not session:
        return None
    log.info(f"[EyesWidget] 停用: key={key_id}")
    return TouchInput(
        base_x=session["base_x"], base_y=session["base_y"],
        x=0, y=0,
        event_type="up", key_id=key_id, size=session["size"],
    )


def is_active(key_id: str) -> bool:
    session = _eyes_sessions.get(key_id)
    return session is not None and session.get("active", False)


def get_session(key_id: str) -> dict | None:
    """获取会话状态（只读）"""
    return _eyes_sessions.get(key_id)


# ── 内部 ──

def _jump_opposite(key_id: str, session: dict, dx: float, dy: float) -> list[TouchInput]:
    """触碰边界 → up + 反方向象限随机点 down"""
    base_x = session["base_x"]
    base_y = session["base_y"]
    size = session["size"]
    half = size / 2.0

    events = []
    # up
    events.append(TouchInput(
        base_x=base_x, base_y=base_y,
        x=0, y=0,
        event_type="up", key_id=key_id, size=size,
    ))

    # 反方向象限
    if dx >= 0 and dy < 0:          # Q1(右上) → Q3(左下)
        rx_min, rx_max = -half, 0
        ry_min, ry_max = 0, half
    elif dx < 0 and dy < 0:         # Q2(左上) → Q4(右下)
        rx_min, rx_max = 0, half
        ry_min, ry_max = 0, half
    elif dx < 0 and dy >= 0:        # Q3(左下) → Q1(右上)
        rx_min, rx_max = 0, half
        ry_min, ry_max = -half, 0
    else:                           # Q4(右下) → Q2(左上)
        rx_min, rx_max = -half, 0
        ry_min, ry_max = -half, 0

    new_dx = int(rx_min + random.random() * (rx_max - rx_min))
    new_dy = int(ry_min + random.random() * (ry_max - ry_min))
    px = max(0, int(base_x + new_dx))
    py = max(0, int(base_y + new_dy))

    events.append(TouchInput(
        base_x=base_x, base_y=base_y,
        x=px, y=py,
        event_type="down", key_id=key_id, size=size,
    ))
    # 重置累积偏移为新随机点的偏移
    session["acc_x"] = new_dx
    session["acc_y"] = new_dy
    log.info(f"[EyesWidget] 边界跳转: key={key_id} ({px},{py})")
    return events
