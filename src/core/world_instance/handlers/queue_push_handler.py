"""QueuePushHandler — 事件分流核心

[MIRROR-TOUCH-T2/T3] 唯一入口：handle_push。

  分流规则:
    down → 查 _session_table:
           无 → 分配 fid → state=ACTIVE → 入 _control_queue
           有(state=ACTIVE) → 双down补偿: 虚拟up → _control_queue → 重置 → 新down → _control_queue
    move → 查表 → state=ACTIVE? 入 _frame_pool[fid] : 丢弃并告警
    up   → 查表 → state=ACTIVE → state=UP_PENDING → 入 _control_queue

  会话锁: down 后 move 丢弃, up 后拒绝一切新事件。
"""
from collections import deque
from src.core.world_instance.components.touch_input import TouchInput
from src.utils.logger import log

# ── 状态常量（与 touch_queue_system 保持一致）──
STATE_IDLE = 0
STATE_ACTIVE = 1       # down 已入队但未消费，move 丢弃
STATE_STREAMING = 2    # down 已消费，move 可入帧池
STATE_UP_PENDING = 3   # up 已入队，拒绝一切事件


def handle_push(ti: TouchInput, session_table: dict, frame_pool: list[deque],
                control_queue, finger_pool: list[int], update_queue=None):
    """根据 event_type 分流至控制队列或帧窗口

    Args:
        ti: 触控输入
        session_table: key_id → {fid, state, down_consumed, up_consumed}
        frame_pool: 6 × deque(maxlen=9)
        control_queue: 控制帧直推队列 → SerialSystem
        finger_pool: 可用 fid 列表 [0-5]
        update_queue: SerialSystem 消费通知队列（move 时推送 fid）
    """
    etype = ti.event_type
    if etype == "down":
        _handle_down(ti, session_table, control_queue, finger_pool)

    elif etype == "move":
        _handle_move(ti, session_table, frame_pool, update_queue)

    elif etype == "up":
        _handle_up(ti, session_table, control_queue)


def _handle_down(ti: TouchInput, session_table: dict, control_queue,
                 finger_pool: list[int]):
    key_id = ti.key_id
    session = session_table.get(key_id)

    if session is None:
        if not finger_pool:
            log.error(f"[QueuePush] finger_pool 耗尽, down 拒绝: {key_id}")
            return
        fid = finger_pool.pop(0)
        session_table[key_id] = {
            "fid": fid,
            "state": STATE_ACTIVE,
            "down_consumed": False,
            "up_consumed": False,
        }
        control_queue.put(ti)
        log.info(f"[QueuePush] session 创建: key={key_id} fid={fid}")

    elif session["state"] in (STATE_ACTIVE, STATE_STREAMING):
        # 双 down 补偿：构虚拟 up → 重新上锁（保持同一 fid，不释放）
        log.warning(f"[QueuePush] 双down补偿: key={key_id}")
        virt_up = TouchInput(
            base_x=ti.base_x, base_y=ti.base_y,
            x=0, y=0,
            event_type="up", key_id=key_id,
            size=ti.size,
        )
        control_queue.put(virt_up)
        session["state"] = STATE_ACTIVE
        session["down_consumed"] = False
        session["up_consumed"] = False
        control_queue.put(ti)

    elif session["state"] == STATE_UP_PENDING:
        log.error(f"[QueuePush] UP_PENDING 状态拒绝 down: {key_id}")


def _handle_move(ti: TouchInput, session_table: dict, frame_pool: list[deque],
                  update_queue=None):
    key_id = ti.key_id
    session = session_table.get(key_id)

    if session is None:
        return

    state = session["state"]

    if state == STATE_ACTIVE:
        log.warning(f"[QueuePush] ACTIVE 状态拒绝 move: {key_id}")
        return  # down 未消费，锁生效，丢弃

    if state == STATE_STREAMING:
        # down 已消费，move 可入帧池
        fid = session["fid"]
        if 0 <= fid < len(frame_pool):
            frame_pool[fid].append(ti)
            if update_queue is not None:
                try:
                    update_queue.put_nowait(fid)
                except Exception:
                    pass
        return

    if state == STATE_UP_PENDING:
        log.warning(f"[QueuePush] UP_PENDING 拒绝 move: {key_id}")
        return


def _handle_up(ti: TouchInput, session_table: dict, control_queue):
    key_id = ti.key_id
    session = session_table.get(key_id)

    if session is None:
        log.warning(f"[QueuePush] 无 session 丢弃 up: {key_id}")
        return

    state = session["state"]

    if state in (STATE_ACTIVE, STATE_STREAMING):
        session["state"] = STATE_UP_PENDING
        control_queue.put(ti)
        log.info(f"[QueuePush] session 挂起: key={key_id}")

    elif state == STATE_UP_PENDING:
        log.warning(f"[QueuePush] 重复 up: {key_id}")

    else:
        log.warning(f"[QueuePush] 未知状态收到 up: {key_id}")
