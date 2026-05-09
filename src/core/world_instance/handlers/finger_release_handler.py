"""FingerReleaseHandler — up 回收手指 ID"""


def release(fid: int):
    """回收手指 ID 到分配池"""
    import src.core.world_instance.handlers.finger_assign_handler as fa
    if fid in fa._active_order:
        fa._active_order.remove(fid)
    if fid not in fa._available:
        fa._available.append(fid)
        fa._available.sort()
