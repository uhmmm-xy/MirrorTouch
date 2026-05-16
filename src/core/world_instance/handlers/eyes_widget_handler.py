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
import time
from src.core.world_instance.components.touch_input import TouchInput
from src.utils.logger import log

# key_id → {base_x, base_y, size, active}
_eyes_sessions: dict[str, dict] = {}


def generate(entity_id: int, cfg, event: str, ox: float, oy: float, bx: float, by: float, sz: float) -> list[TouchInput]:
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


def activate(key_id: str, base_x: float, base_y: float, size: float) -> TouchInput:
    """激活视角会话：在正方形内随机取点，下发 down"""
    half = size / 2.0
    dx = (random.random() - 0.5) * size
    dy = (random.random() - 0.5) * size
    px = max(0.0, min(1.0, base_x + dx))
    py = max(0.0, min(1.0, base_y + dy))

    _eyes_sessions[key_id] = {
        "base_x": base_x,
        "base_y": base_y,
        "size": size,
        "active": True,
        "acc_x": dx,   # 累积偏移 = 随机偏移量（与 down 点对齐）
        "acc_y": dy,
    }
    return TouchInput(
        base_x=base_x, base_y=base_y,
        x=px, y=py,
        event_type="down", key_id=key_id, size=size,
    )


def on_move(key_id: str, offset_x: float, offset_y: float) -> list[TouchInput]:
    """处理鼠标偏移增量 → 累积偏移 → 锚点 + 累积 = 实际位置 → 边界检测

    Args:
        key_id:      按键标识
        offset_px/y: 本次鼠标移动的像素增量
    """
    session = _eyes_sessions.get(key_id)
    if not session or not session["active"]:
        return []

    # [DEBUG]
    # log.info(f"[EyesWidget] on_move: key={key_id} offset=({offset_x:.6f},{offset_y:.6f}) "
    #          f"acc_before=({session['acc_x']:.6f},{session['acc_y']:.6f})")

    # 预测：本次偏移后是否会触碰边界？
    base_x = session["base_x"]
    base_y = session["base_y"]
    size = session["size"]
    half = size / 2.0

    next_acc_x = session["acc_x"] + offset_x
    next_acc_y = session["acc_y"] + offset_y

    # 预测越界 → 触发跳转（不积累本次偏移）
    if abs(next_acc_x) >= half or abs(next_acc_y) >= half:
        return _jump_opposite(key_id, session, next_acc_x, next_acc_y)

    # 未越界：正常累积 + move
    session["acc_x"] = next_acc_x
    session["acc_y"] = next_acc_y

    px = base_x + next_acc_x
    py = base_y + next_acc_y
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
    """触碰边界 → up + 反方向象限随机点 down + 清空旧 move 帧"""
    base_x = session["base_x"]
    base_y = session["base_y"]
    size = session["size"]
    half = size / 2.0

    events = []
    # up
    # events.append(TouchInput(
    #     base_x=base_x, base_y=base_y,
    #     x=0, y=0,
    #     event_type="up", key_id=key_id, size=size,
    # ))
    log.info(f"event time {time.time()}")

    # 反方向象限（与 UI EyesWidget 对齐）
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

    import math
    angle = random.uniform(0, math.pi / 2)
    new_dx = rx_min + abs(math.cos(angle)) * (rx_max - rx_min)
    new_dy = ry_min + abs(math.sin(angle)) * (ry_max - ry_min)
    new_dx = max(rx_min, min(rx_max, new_dx))
    new_dy = max(ry_min, min(ry_max, new_dy))
    px = max(0.0, min(1.0, base_x + new_dx))
    py = max(0.0, min(1.0, base_y + new_dy))

    events.append(TouchInput(
        base_x=base_x, base_y=base_y,
        x=px, y=py,
        event_type="down", key_id=key_id, size=size,
    ))
    # 重置累积偏移为新随机点的偏移
    session["acc_x"] = new_dx
    session["acc_y"] = new_dy
    log.info(f"event time {time.time()}")
    log.info(f"[EyesWidget] 边界跳转: key={key_id} ({px},{py})")
    return events
