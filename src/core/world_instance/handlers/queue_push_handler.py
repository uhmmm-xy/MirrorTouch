"""QueuePushHandler — 事件分流核心（单队列版，无锁）

[MIRROR-TOUCH-T2/T3] 唯一入口：handle_push。

  分流规则（统一入 _frame_pool，deque FIFO 天然保序）:
    down → 查 _session_table:
           无 → 分配 fid → 入 _frame_pool[fid]
           有 → 双down补偿: 虚拟up入池 → 新down入池（同一fid）
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

    if session is None:
        if not finger_pool:
            log.error(f"[QueuePush] finger_pool 耗尽, down 拒绝: {key_id}")
            return
        fid = finger_pool.pop(0)
        session_table[key_id] = {"fid": fid, "up_pending": False}
        frame_pool[fid].append(ti)
        log.info(f"[QueuePush] session 创建: key={key_id} fid={fid}")
    else:
        # 双 down 补偿：构虚拟 up → 入池 → 新 down 入池（保持同一 fid，不释放）
        log.warning(f"[QueuePush] 双down补偿: key={key_id}")
        fid = session["fid"]
        virt_up = TouchInput(
            base_x=ti.base_x, base_y=ti.base_y,
            x=0, y=0,
            event_type="up", key_id=key_id,
            size=ti.size,
        )
        frame_pool[fid].append(virt_up)
        session["up_pending"] = False
        frame_pool[fid].append(ti)


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
