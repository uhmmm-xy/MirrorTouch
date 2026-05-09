"""PriorityHandler — 优先级比较与入队裁决"""


def should_drop(new_priority: int, queue_max_priority: int) -> bool:
    """新帧是否应丢弃"""
    if new_priority > queue_max_priority:
        return False  # 更高优先级 → 清空队列入队
    elif new_priority == queue_max_priority:
        return False  # 同级追加
    return True  # 更低优先级丢弃
