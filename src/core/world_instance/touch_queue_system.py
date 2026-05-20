"""TouchQueueSystem — 帧队列池 + 内部类型路由

[MIRROR-TOUCH-T2/T4] 核心职责：
  1. 会话管理：_session_table 维护 key_id → {fid, up_pending}
  2. 帧池：6 × deque(maxlen=9) 静态预分配，运行时禁止扩容
  3. 分流：down/up/move 统一入 _frame_pool（deque FIFO 天然保序）
  4. 双 down 补偿：接收侧补偿虚拟 up，不释放 fid
  5. 锁机制：已移除——deque FIFO 即天然帧序保障
  6. fid 生命周期：分配 → 使用 → up消费确认 → 回收

  状态流转:
    (无) ──down──▶ session创建 ──up──▶ UP_PENDING ──消费──▶ 释放
                  move入deque       move仍入deque      fid回池
                  双down补偿(保持状态)
"""
import esper
import queue
import threading
from collections import deque
from src.utils.logger import log
from src.core.world_instance.components.touch_input import TouchInput

# ── 状态常量 ──
STATE_UP_PENDING = 3  # up 已入队，等待 SS 消费后释放

_running: bool = False
_thread: threading.Thread | None = None

# KMS 统一入口队列
_input_queue: queue.Queue | None = None

# 会话表: key_id → {fid, up_pending}
_session_table: dict[str, dict] = {}
# 手指分配池 [0,1,2,3,4,5]
_finger_pool: list[int] = [0, 1, 2, 3, 4, 5]
# 6 × deque(maxlen=9) 静态帧池, 按 finger_id 索引
_frame_pool: list[deque] = []
# 每个 fid 的最后一帧缓存（6×1），初始为 release 空帧，入池时更新
_last_frame: list[TouchInput] = []


def register():
    esper.set_handler("queue.start", _on_start)
    esper.set_handler("queue.stop", _on_stop)


def _on_start(in_q: queue.Queue):
    """接收 KMS 输出队列，初始化帧池，启动消费线程"""
    global _running, _thread, _input_queue
    global _session_table, _finger_pool, _frame_pool, _last_frame

    _input_queue = in_q

    # 重置状态
    _session_table.clear()
    _finger_pool = [0, 1, 2, 3, 4, 5]

    # 静态预分配 6 个 deque(maxlen=9)
    _frame_pool = [deque(maxlen=9) for _ in range(6)]
    # 每 fid 最后一帧缓存，初始 release(0,0)
    _last_frame = [TouchInput(x=0, y=0, event_type="up") for _ in range(6)]

    _running = True
    _thread = threading.Thread(target=_run, daemon=True, name="TouchQueueSystem")
    _thread.start()
    log.info("[TouchQueue] 线程启动, 6×9 帧池已预分配")


def _on_stop():
    """停止线程，确保活跃 session 以 up 结尾，清空所有状态"""
    global _running, _thread, _session_table, _finger_pool, _frame_pool
    _running = False
    # 为所有活跃 session 补充虚拟 up 帧（确保 SerialSystem 能正常消费完）
    for key_id, session in _session_table.items():
        fid = session.get("fid", -1)
        if 0 <= fid < len(_frame_pool):
            dq = _frame_pool[fid]
            if not dq or dq[-1].event_type != "up":
                from src.core.world_instance.components.touch_input import TouchInput
                virt_up = TouchInput(event_type="up", key_id=key_id)
                dq.append(virt_up)
                log.info(f"[TouchQueue] 停机补虚拟up: key={key_id} fid={fid}")
    _session_table.clear()
    _finger_pool = [0, 1, 2, 3, 4, 5]
    _frame_pool = []
    log.info("[TouchQueue] 线程停止, 状态已清空")


def mark_consumed_fid(fid: int):
    """SerialSystem 回调：某个 fid 的 up 帧已被消费 → 释放对应的 session"""
    for key_id, session in list(_session_table.items()):
        if session.get("fid") == fid:
            if session.get("up_pending"):
                _release_session(key_id)
            return
    # session_table 里没有匹配的 fid → 旧 fid 直接回池
    if 0 <= fid <= 5 and fid not in _finger_pool:
        _finger_pool.append(fid)
        _finger_pool.sort()
        log.info(f"[TouchQueue] fid直接回池: fid={fid} pool={_finger_pool}")


def _release_session(key_id: str):
    """释放 session：fid 回池（去重），删除 session 记录"""
    session = _session_table.pop(key_id, None)
    if session is None:
        return
    fid = session.get("fid", -1)
    if 0 <= fid <= 5 and fid not in _finger_pool:
        _finger_pool.append(fid)
        _finger_pool.sort()
        # 清空对应帧窗口
        _frame_pool[fid].clear()
    log.info(f"[TouchQueue] session 释放: key={key_id} fid={fid} pool={_finger_pool}")


def _run():
    """主消费循环：从 _input_queue 取出 TouchInput → 分流处理"""
    while _running:
        try:
            ti = _input_queue.get(timeout=0.005)
            from src.core.world_instance.handlers.queue_push_handler import handle_push
            handle_push(ti, _session_table, _frame_pool, _finger_pool)
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


def maintain_press_state(fid: int):
    """SS 取帧后调用：若 deque 空 → 用 _last_frame[fid] 补帧"""
    if fid < 0 or fid >= len(_frame_pool):
        return
    dq = _frame_pool[fid]
    if dq:
        return
    if 0 <= fid < len(_last_frame):
        dq.append(_last_frame[fid])
