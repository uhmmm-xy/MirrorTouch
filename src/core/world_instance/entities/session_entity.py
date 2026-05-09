"""SessionEntity — 一次投屏会话，启动时创建，停止/异常时销毁"""
import esper
from src.core.world_instance.components.stream_session import StreamSession
from src.core.world_instance.components.stream_config import StreamConfig


def create_session_entity(config: StreamConfig | None = None) -> int:
    e = esper.create_entity()
    esper.add_component(e, StreamSession(state="idle"))
    esper.add_component(e, config or StreamConfig())
    return e
