"""EyesSessionHandler — 视角映射会话管理

[MIRROR-TOUCH-EYES] 核心逻辑：
  激活时 down 到以 (base_x,base_y) 为中心、size 为边长的正方形内任意一点。
  move 跟随鼠标轨迹，触碰正方形边缘时：
    → up 当前点 → 在向量反方向象限随机一点重新 down → 继续 move。
  即：Q1→Q3, Q2→Q4, Q3→Q1, Q4→Q2
"""
import math
import random
from src.core.world_instance.components.touch_input import TouchInput
from src.utils.logger import log

# key_id → {base_x, base_y, size, active}
_eyes_sessions: dict[str, dict] = {}


def activate(key_id: str, base_x: int, base_y: int, size: int) -> TouchInput:
    """激活视角会话：在正方形内随机取点，下发 down

    Args:
        key_id:   按键标识 (如 "\\")
        base_x/y: 正方形中心像素坐标
        size:     正方形边长（像素）
    Returns:
        down 事件的 TouchInput
    """
    half = size / 2.0
    # 正方形内随机一点
    dx = (random.random() - 0.5) * size
    dy = (random.random() - 0.5) * size
    px = max(0, int(base_x + dx))
    py = max(0, int(base_y + dy))

    _eyes_sessions[key_id] = {
        "base_x": base_x,
        "base_y": base_y,
        "size": size,
        "active": True,
    }
    log.info(f"[EyesSession] 激活: key={key_id} base=({base_x},{base_y}) size={size} start=({px},{py})")
    return TouchInput(
        base_x=base_x, base_y=base_y,
        x=px, y=py,
        event_type="down", key_id=key_id, size=size,
    )


def on_move(key_id: str, pixel_x: int, pixel_y: int) -> list[TouchInput]:
    """处理鼠标移动 → 返回 TouchInput 序列

    若触碰正方形边界 → 返回 [up, 新down(反方向象限随机点)]
    正常移动        → 返回 [move]

    Args:
        key_id:   按键标识
        pixel_x/y: 当前鼠标在手机屏幕上的像素坐标
    """
    session = _eyes_sessions.get(key_id)
    if not session or not session["active"]:
        return []

    base_x = session["base_x"]
    base_y = session["base_y"]
    size = session["size"]
    half = size / 2.0

    dx = pixel_x - base_x
    dy = pixel_y - base_y

    # 检查是否触碰边界
    if abs(dx) >= half or abs(dy) >= half:
        return _jump_opposite(key_id, session, dx, dy)

    # 正常 move
    return [TouchInput(
        base_x=base_x, base_y=base_y,
        x=pixel_x, y=pixel_y,
        event_type="move", key_id=key_id, size=size,
    )]


def deactivate(key_id: str) -> TouchInput | None:
    """结束视角会话，下发 up"""
    session = _eyes_sessions.pop(key_id, None)
    if not session:
        return None
    log.info(f"[EyesSession] 停用: key={key_id}")
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

    # 确定反方向象限范围
    if dx >= 0 and dy < 0:          # Q1(右上) → Q3(左下)
        rx_min, rx_max = -half, 0
        ry_min, ry_max = 0, half
        q_name = "Q3"
    elif dx < 0 and dy < 0:         # Q2(左上) → Q4(右下)
        rx_min, rx_max = 0, half
        ry_min, ry_max = 0, half
        q_name = "Q4"
    elif dx < 0 and dy >= 0:        # Q3(左下) → Q1(右上)
        rx_min, rx_max = 0, half
        ry_min, ry_max = -half, 0
        q_name = "Q1"
    else:                           # Q4(右下) → Q2(左上)
        rx_min, rx_max = -half, 0
        ry_min, ry_max = -half, 0
        q_name = "Q2"

    # 随机取点
    new_dx = int(rx_min + random.random() * (rx_max - rx_min))
    new_dy = int(ry_min + random.random() * (ry_max - ry_min))
    px = max(0, int(base_x + new_dx))
    py = max(0, int(base_y + new_dy))

    events.append(TouchInput(
        base_x=base_x, base_y=base_y,
        x=px, y=py,
        event_type="down", key_id=key_id, size=size,
    ))
    log.info(f"[EyesSession] 边界跳转: key={key_id} → {q_name} ({px},{py})")
    return events
