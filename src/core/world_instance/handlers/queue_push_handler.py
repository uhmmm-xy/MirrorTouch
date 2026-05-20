"""QueuePushHandler — 事件分流核心（单队列版，无锁）

[MIRROR-TOUCH-T2/T3] 唯一入口：handle_push。

  分流规则（统一入 _frame_pool，deque FIFO 天然保序）:
    down → 查 _session_table:
           无 → 分配 fid → 入 _frame_pool[fid]
           有 → 新 down 入池（同一 fid）
    move → 查表 → 有session? 入 _frame_pool[fid] : 丢弃
           deque 满 9 帧时淘汰最旧 move（不淘汰 down/up）
    up   → 查表 → 标记 up_pending → 入 _frame_pool[fid]
"""
from collections import deque
from src.core.world_instance.components.touch_input import TouchInput
from src.utils.logger import log

# ── 状态常量（与 touch_queue_system 保持一致）──
STATE_UP_PENDING = 3   # up 已入队，等待 SS 消费后释放


def handle_push(ti: TouchInput, session_table: dict, frame_pool: list[deque],
                finger_pool: list[int]):
    """根据 event_type 统一入 _frame_pool

    Args:
        ti: 触控输入
        session_table: key_id → {fid, up_pending}
        frame_pool: 6 × deque(maxlen=9)
        finger_pool: 可用 fid 列表 [0-5]
    """
    etype = ti.event_type
    if etype == "down":
        _handle_down(ti, session_table, frame_pool, finger_pool)
    elif etype == "move":
        _handle_move(ti, session_table, frame_pool)
    elif etype == "up":
        _handle_up(ti, session_table, frame_pool)


def _handle_down(ti: TouchInput, session_table: dict, frame_pool: list[deque],
                 finger_pool: list[int]):
    key_id = ti.key_id
    session = session_table.get(key_id)

    # ── 新 session ──
    if session is None:
        if not finger_pool:
            # pool 空 → 淘汰最后入栈的 session → 释放旧 up 帧 → 复用其 fid
            if not session_table:
                log.error(f"[QueuePush] finger_pool 耗尽且无 session 可淘汰, down 拒绝: {key_id}")
                return
            old_key = next(reversed(session_table))
            old_fid = session_table[old_key]["fid"]
            up_ti = TouchInput(event_type="up", key_id=old_key)
            frame_pool[old_fid].append(up_ti)
            del session_table[old_key]
            log.warning(f"[QueuePush] pool空, 淘汰+释放: key={old_key} fid={old_fid}")
            session_table[key_id] = {"fid": old_fid, "up_pending": False}
            frame_pool[old_fid].append(ti)
            log.info(f"[QueuePush] session 创建(pool空,复用): key={key_id} fid={old_fid}")
            return
        fid = finger_pool.pop(0)
        session_table[key_id] = {"fid": fid, "up_pending": False}
        frame_pool[fid].append(ti)
        log.info(f"[QueuePush] session 创建: key={key_id} fid={fid}")
        return

    # ── 边界跳转 ──
    if session.get("up_pending"):
        old_fid = session["fid"]
        new_fid = None
        for f in finger_pool:
            if f != old_fid:
                new_fid = f
                break
        if new_fid is not None:
            finger_pool.remove(new_fid)
        else:
            new_fid = old_fid
            log.warning(f"[QueuePush] session 跳转不存在新fid 复用: key={key_id} fid={old_fid}")
        session_table[key_id] = {"fid": new_fid, "up_pending": False}
        frame_pool[new_fid].append(ti)
        log.info(f"[QueuePush] session 跳转: key={key_id} fid={old_fid}→{new_fid} pool={finger_pool}")
        return

    # ── 重复 down：静默丢弃 ──
    log.warning(f"[QueuePush] 重复down丢弃: key={key_id}")


def _handle_move(ti: TouchInput, session_table: dict, frame_pool: list[deque]):
    key_id = ti.key_id
    session = session_table.get(key_id)
    if session is None:
        return
    fid = session["fid"]
    if 0 <= fid < len(frame_pool):
        dq = frame_pool[fid]
        # 9 帧池满时淘汰最旧的 move 帧（保留 down/up）
        if len(dq) >= dq.maxlen:
            for i in range(len(dq)):
                if dq[i].event_type == "move":
                    del dq[i]
                    break
        dq.append(ti)


def _handle_up(ti: TouchInput, session_table: dict, frame_pool: list[deque]):
    key_id = ti.key_id
    session = session_table.get(key_id)

    if session is None:
        log.warning(f"[QueuePush] 无 session 丢弃 up: {key_id}")
        return

    session["up_pending"] = True
    fid = session["fid"]
    if 0 <= fid < len(frame_pool):
        frame_pool[fid].append(ti)
    log.info(f"[QueuePush] session 挂起: key={key_id}")
