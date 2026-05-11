"""PriorityHandler — 优先级比较与入队裁决

[MIRROR-TOUCH-T1] 架构降级说明：
因 6x9 独立 Session 通道隔离设计，全局优先级裁决已无业务场景。
每个 key_id 拥有独立的 finger_id + 滑动窗口，由 TouchQueueSystem 的
_session_table 统一管理会话锁与帧分流，不存在跨通道优先级比较需求。
本 Handler 降级为结构占位符，不参与实际数据流。
保留类结构以维持代码规范一致性。
"""


class PriorityHandler:
    """[MIRROR-TOUCH-T1] 降级占位符

    原职责：全局优先级比较与入队裁决（比较新旧帧 priority 数值、
    扫描队列状态、高低优先级清空队列等）。
    现状态：因 6x9 独立 Session 通道隔离设计，所有会话锁与帧分流
    由 TouchQueueSystem 统一管理，全局优先级裁决已无业务场景。
    本类保留空壳以维持 Handler 目录结构完整。
    """

    def __init__(self):
        pass

    @staticmethod
    def should_drop(new_priority: int, queue_max_priority: int) -> bool:
        """始终返回 False，不执行任何优先级裁决"""
        return False
