"""QueuePopHandler — 取队头连续 3 帧"""
from src.core.world_instance.components.frame_queue import FrameQueue


def pop_batch(fq: "FrameQueue") -> list:
    with fq.lock:
        batch = []
        for _ in range(fq.batch_size):
            if fq.frames:
                batch.append(fq.frames.popleft())
            else:
                break
        fq.has_update = bool(fq.frames)
        return batch
