"""ScrcpySystem — 投屏会话管理"""
import esper
from src.core.world_instance.handlers.intent_dispatch_handler import handle_start, handle_stop


def register():
    esper.set_handler("stream.start", _on_stream_start)
    esper.set_handler("stream.stop", _on_stream_stop)
    esper.set_handler("stream.stop.force", _on_force_stop)


def _on_stream_start(config):
    handle_start(config)


def _on_stream_stop():
    handle_stop(force=False)


def _on_force_stop():
    handle_stop(force=True)
