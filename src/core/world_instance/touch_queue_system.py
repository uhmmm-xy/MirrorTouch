"""TouchQueueSystem — 会话锁 + 帧队列池 + 内部类型路由

[MIRROR-TOUCH-T2/T4] 核心职责：
  1. 会话管理：_session_table 维护 key_id → {fid, state, down_consumed, up_consumed}
  2. 帧池：6 × deque(maxlen=9) 静态预分配，运行时禁止扩容
  3. 分流：move → 9 帧窗口；down/up → _control_queue 直推
  4. 双 down 补偿：接收侧补偿虚拟 up 再重新上锁，不释放 fid
  5. 锁机制：down 后上锁丢弃 move；up 后 state→UP_PENDING 拒绝一切新事件
  6. fid 生命周期：分配 → 使用 → 消费确认 → 回收

  状态流转:
    (无) ──down──▶ DOWN_PENDING ──消费──▶ ACTIVE ──up──▶ UP_PENDING ──消费──▶ 释放
                  move丢弃              move入帧池     拒绝一切事件       fid回池
                  双down补偿(保持状态)
"""
import esper
import queue
import threading
from collections import deque
from src.utils.logger import log

# ── 状态常量 ──
STATE_IDLE = 0        # 无 session
STATE_ACTIVE = 1      # down 已入队但未消费，锁生效，move 丢弃
STATE_STREAMING = 2   # down 已消费，锁解除，move 可入帧池
STATE_UP_PENDING = 3  # up 已入队，拒绝一切新事件

_running: bool = False
_thread: threading.Thread | None = None

# KMS 统一入口队列
_input_queue: queue.Queue | None = None
# 内部控制帧直推队列 → SerialSystem
_control_queue: queue.Queue | None = None
# SerialSystem 消费通知 → TQS (已废弃, 改用 mark_consumed 回调)
_update_queue: queue.Queue | None = None

# 会话表: key_id → {fid, state, down_consumed, up_consumed}
_session_table: dict[str, dict] = {}
# 手指分配池 [0,1,2,3,4,5]
_finger_pool: list[int] = [0, 1, 2, 3, 4, 5]
# 6 × deque(maxlen=9) 静态帧池, 按 finger_id 索引
_frame_pool: list[deque] = []


def register():
    esper.set_handler("queue.start", _on_start)
    esper.set_handler("queue.stop", _on_stop)


def _on_start(in_q: queue.Queue, control_q: queue.Queue, update_q: queue.Queue):
    """接收 KMS 输出队列，初始化帧池，启动消费线程"""
    global _running, _thread, _input_queue, _control_queue, _update_queue
    global _session_table, _finger_pool, _frame_pool

    _input_queue = in_q
    _control_queue = control_q
    _update_queue = update_q

    # 重置状态
    _session_table.clear()
    _finger_pool = [0, 1, 2, 3, 4, 5]

    # 静态预分配 6 个 deque(maxlen=9)
    _frame_pool = [deque(maxlen=9) for _ in range(6)]

    _running = True
    _thread = threading.Thread(target=_run, daemon=True, name="TouchQueueSystem")
    _thread.start()
    log.info("[TouchQueue] 线程启动, 6×9 帧池已预分配")


def _on_stop():
    """停止线程，清空所有状态"""
    global _running, _thread, _session_table, _finger_pool, _frame_pool
    _running = False
    _session_table.clear()
    _finger_pool = [0, 1, 2, 3, 4, 5]
    _frame_pool = []
    log.info("[TouchQueue] 线程停止, 状态已清空")


def mark_consumed(key_id: str, event_type: str):
    """SerialSystem 回调：标记 down/up 已被消费

    down 消费后 → ACTIVE→STREAMING，move 可流入帧池
    up 消费后且 state==UP_PENDING → session 释放
    """
    session = _session_table.get(key_id)
    if session is None:
        return

    if event_type == "down":
        session["down_consumed"] = True
        if session.get("state") == STATE_ACTIVE:
            session["state"] = STATE_STREAMING
            log.info(f"[TouchQueue] down 已消费, 锁释放: key={key_id}")

    elif event_type == "up":
        session["up_consumed"] = True
        if session.get("state") == STATE_UP_PENDING:
            _release_session(key_id)


def _release_session(key_id: str):
    """释放 session：fid 回池，删除 session 记录"""
    session = _session_table.pop(key_id, None)
    if session is None:
        return
    fid = session.get("fid", -1)
    if 0 <= fid <= 5:
        _finger_pool.append(fid)
        _finger_pool.sort()
        # 清空对应帧窗口
        _frame_pool[fid].clear()
    log.info(f"[TouchQueue] session 释放: key={key_id} fid={fid}")


def _run():
    """主消费循环：从 _input_queue 取出 TouchInput → 分流处理"""
    while _running:
        try:
            ti = _input_queue.get(timeout=0.005)
            from src.core.world_instance.handlers.queue_push_handler import handle_push
            handle_push(ti, _session_table, _frame_pool, _control_queue, _finger_pool, _update_queue)
        except queue.Empty:
            pass
        except Exception as e:
            log.error(f"[TouchQueue] 消费异常: {e}")
            _emergency_stop(str(e))
            break


def _emergency_stop(reason: str = ""):
    """[T7] 异常停机：清空所有状态，通知 UI"""
    global _running
    _running = False
    _session_table.clear()
    _finger_pool[:] = [0, 1, 2, 3, 4, 5]
    for dq in _frame_pool:
        dq.clear()
    log.info(f"[TouchQueue] 紧急停机: {reason}")
    esper.dispatch_event("touch.error", f"TouchQueueSystem: {reason}")
