"""FingerAssignHandler — 6 指先来后到分配"""
_available = list(range(6))  # 可用 ID 池
_active_order = []            # 按分配时间排序


def assign() -> int:
    """分配手指 ID，池满时释放最早分配的"""
    global _available, _active_order
    if not _available:
        # 池满：释放最早的手指
        fid = _active_order.pop(0)
        _available.append(fid)
        _available.sort()
    fid = _available.pop(0)
    _active_order.append(fid)
    return fid
