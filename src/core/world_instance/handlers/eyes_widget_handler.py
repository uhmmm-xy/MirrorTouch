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
import threading
import random
import time
from src.core.world_instance.components.touch_input import TouchInput
from src.utils.logger import log

# key_id → {base_x, base_y, size, active, acc_x, acc_y, _lazy_down_pending}
_eyes_sessions: dict[str, dict] = {}
# 超时定时器：key_id → threading.Timer
_timeout_timers: dict[str, threading.Timer] = {}
EYES_TIMEOUT = 0.50  # 50ms


def _half_xy(size: float) -> tuple[float, float]:
    """返回 (half_x, half_y) — X 按宽，Y 按高，根据设备实际分辨率独立计算"""
    from src.core.world_instance.key_mapping_system import _map_width, _map_height
    w, h = _map_width, _map_height
    if w <= 0 or h <= 0:
        w, h = 1080, 1920
    hx = size / 2.0
    hy = hx * (h / w)
    return hx, hy


def generate(entity_id: int, cfg, event: str, ox: float, oy: float, bx: float, by: float, sz: float) -> list[TouchInput]:
    """Entity 驱动入口：event_type_handler 纯分发至此"""
    if event == "press":
        # press 事件：惰性激活（只建 session，不发 down）
        activate_lazy(cfg.key_id, bx, by, sz)
        return []
    elif event == "move":
        return on_move(cfg.key_id, ox, oy)
    elif event == "release":
        ti = deactivate(cfg.key_id)
        return [ti] if ti else []
    return []


def activate(key_id: str, base_x: float, base_y: float, size: float) -> TouchInput:
    """激活视角会话：在正方形内随机取点，下发 down

    保留供外部直接调用（如 KMS _activate_eyes_session）。
    """
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
        "acc_x": dx,
        "acc_y": dy,
    }
    return TouchInput(
        base_x=base_x, base_y=base_y,
        x=px, y=py,
        event_type="down", key_id=key_id, size=size,
    )


def activate_lazy(key_id: str, base_x: float, base_y: float, size: float):
    """惰性激活：只建 session，不发 down 帧。

    首次 on_move 被调用时自动生成 down。
    """
    _eyes_sessions[key_id] = {
        "base_x": base_x,
        "base_y": base_y,
        "size": size,
        "active": True,
        "acc_x": 0,
        "acc_y": 0,
        "_lazy_down_pending": True,  # 标记：首次 move 时发 down
    }


def on_move(key_id: str, offset_x: float, offset_y: float) -> list[TouchInput]:
    """处理鼠标偏移增量 → 累积偏移 → 锚点 + 累积 = 实际位置 → 边界检测"""
    session = _eyes_sessions.get(key_id)
    if not session or not session["active"]:
        return []


    base_x = session["base_x"]
    base_y = session["base_y"]
    size = session["size"]
    half = size / 2.0
    timeout_num = session.get("timeout_num", 0) + 1  # 超时计数，配合 timer 验证过期
    # 重置超时 timer
    _refresh_timer(key_id, timeout_num)
    session["timeout_num"] = timeout_num

    # 首次 move：惰性激活 → 按 XY 独立比例在方形内随机取点 → 发 down
    events = []
    if session.get("_lazy_down_pending"):
        del session["_lazy_down_pending"]
        hx, hy = _half_xy(size)
        
        # 边界余量，避免初始位置贴边
        margin = 0.45  # 留15%的边距
        safe_hx = hx * (1 - margin)
        safe_hy = hy * (1 - margin)
        
        dx = (random.random() - 0.5) * 2 * safe_hx  # X 范围: -safe_hx ~ +safe_hx
        dy = (random.random() - 0.5) * 2 * safe_hy  # Y 范围: -safe_hy ~ +safe_hy
        
        px = max(0.0, min(1.0, base_x + dx))
        py = max(0.0, min(1.0, base_y + dy))
        session["acc_x"] = dx
        session["acc_y"] = dy
        events.append(TouchInput(
            base_x=base_x, base_y=base_y,
            x=px, y=py,
            event_type="down", key_id=key_id, size=size,
        ))
        # 如果首次偏移就触碰边界 → 不处理，返回 down 即可
        return events

    next_acc_x = session["acc_x"] + offset_x
    next_acc_y = session["acc_y"] + offset_y

    # 预测越界 → 触发跳转（不积累本次偏移）
    hx, hy = _half_xy(size)
    if abs(next_acc_x) >= hx or abs(next_acc_y) >= hy:
        events.extend(_jump_opposite(key_id, session, next_acc_x, next_acc_y))
        return events

    # 未越界：正常累积 + move
    session["acc_x"] = next_acc_x
    session["acc_y"] = next_acc_y

    px = base_x + next_acc_x
    py = base_y + next_acc_y
    events.append(TouchInput(
        base_x=base_x, base_y=base_y,
        x=px, y=py,
        event_type="move", key_id=key_id, size=size,
    ))
    return events


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
    """触碰边界 → up + 基于入射角度映射的对向跳转 down + 清空旧 move 帧"""
    base_x = session["base_x"]
    base_y = session["base_y"]
    size = session["size"]
    hx, hy = _half_xy(size)

    events = []
    # up
    events.append(TouchInput(
        base_x=base_x, base_y=base_y,
        x=0, y=0,
        event_type="up", key_id=key_id, size=size,
    ))

    import math
    
    # 计算入射角度 (-π ~ π)
    angle_in = math.atan2(dy, dx)
    
    # 角度分区的容忍范围（±22.5° = π/8，总共45°的容忍区间）
    tolerance = math.pi / 8  # 22.5°
    
    # 判断入射方向属于哪个主方向，映射到对向主方向
    # 右半平面：角度在 -π/2 ~ π/2
    # 上：-π/2 ~ -π/4 → 跳转到下
    # 右上：-π/4 ~ 0 → 跳转到左下
    # 右下：0 ~ π/4 → 跳转到左上
    # 下：π/4 ~ π/2 → 跳转到上
    # 左半平面：角度在 π/2 ~ π 或 -π ~ -π/2
    # 左上：π/2 ~ 3π/4 或 -3π/4 ~ -π/2 → 跳转到右下
    # 左下：3π/4 ~ π 或 -π ~ -3π/4 → 跳转到右上
    
    # 用象限+容忍区间来映射对向角度
    # 将角度分为8个扇区（每45°一个）
    # 扇区0: -22.5° ~ 22.5° (右) → 对向扇区4: 157.5° ~ -157.5° (左)
    # 扇区1: 22.5° ~ 67.5° (右下) → 对向扇区5: -157.5° ~ -112.5° (左上)
    # 扇区2: 67.5° ~ 112.5° (下) → 对向扇区6: -112.5° ~ -67.5° (上)
    # 扇区3: 112.5° ~ 157.5° (左下) → 对向扇区7: -67.5° ~ -22.5° (右上)
    
    # 将角度转为0~2π范围便于计算
    angle_norm = angle_in % (2 * math.pi)
    if angle_norm < 0:
        angle_norm += 2 * math.pi
    
    # 8扇区划分，每扇区 π/4
    sector_size = math.pi / 4
    sector = int((angle_norm + sector_size / 2) // sector_size) % 8
    
    # 对向扇区（+4 然后取模8）
    opposite_sector = (sector + 4) % 8
    
    # 在对向扇区内随机取角度
    sector_start = opposite_sector * sector_size - sector_size / 2
    sector_end = sector_start + sector_size
    
    # 在对向扇区内加高斯扰动，使角度不完全固定
    sector_center = sector_start + sector_size / 2
    angle_jitter = random.gauss(0, sector_size / 4)  # 标准差为扇区宽度的1/4
    final_angle = sector_center + angle_jitter
    # 确保不超出扇区范围
    final_angle = max(sector_start, min(sector_end, final_angle))
    
    # 转回 -π~π 范围
    if final_angle > math.pi:
        final_angle -= 2 * math.pi
    
    # 跳转距离：在目标扇区内取随机距离
    jump_distance = min(hx, hy) * random.uniform(0.3, 0.7)
    
    # 计算对向位置
    new_dx = math.cos(final_angle) * jump_distance
    new_dy = math.sin(final_angle) * jump_distance
    
    # 边界余量
    margin = 0.25 * max(hx, hy)
    new_dx = max(-hx + margin, min(hx - margin, new_dx))
    new_dy = max(-hy + margin, min(hy - margin, new_dy))
    
    px = max(0.0, min(1.0, base_x + new_dx))
    py = max(0.0, min(1.0, base_y + new_dy))

    events.append(TouchInput(
        base_x=base_x, base_y=base_y,
        x=px, y=py,
        event_type="down", key_id=key_id, size=size,
    ))
    
    session["acc_x"] = new_dx
    session["acc_y"] = new_dy
    
    log.info(f"[EyesWidget] 边界跳转: key={key_id} "
             f"入射扇区={sector} → 对向扇区={opposite_sector} "
             f"({px:.3f},{py:.3f})")
    
    return events

def _refresh_timer(key_id: str,timeout):
    """重置超时定时器：取消旧的，起新的 50ms timer。到期自动释放 session"""
    old = _timeout_timers.get(key_id, None)
    if old:
        old.cancel()
    t = threading.Timer(EYES_TIMEOUT, _on_timeout, args=[key_id,timeout])
    t.daemon = True
    t.start()
    _timeout_timers[key_id] = t


def _on_timeout(key_id: str,timeout):
    """超时回调：发送 up 帧 → 释放 eyes session → 标记下次 move 需惰性激活"""
    session = _eyes_sessions.get(key_id)
    if not session or not session.get("active"):
        return
    if(session.get("timeout_num",0) != timeout):
        return
    # 构造 up 帧并推入 KMS 输出队列
    from src.core.world_instance.key_mapping_system import _output_queue
    if _output_queue:
        up_ti = TouchInput(
            base_x=session["base_x"], base_y=session["base_y"],
            x=0, y=0,
            event_type="up", key_id=key_id, size=session["size"],
        )
        _output_queue.put(up_ti)
        log.info(f"[EyesWidget] 超时发送up: key={key_id}")
    # 重置为惰性状态
    session["_lazy_down_pending"] = True
    session["acc_x"] = 0
    session["acc_y"] = 0
    # 超时后 session 标记为非活跃，下次 move 通过 _lazy_down_pending 重建
    log.info(f"[EyesWidget] 超时: key={key_id}")
