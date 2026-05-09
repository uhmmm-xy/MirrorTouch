"""DeviceEntity — 一个被控设备，随 Session 创建"""
import esper
from src.core.world_instance.components.connection_component import ConnectionComponent
from src.core.world_instance.components.latest_frame import LatestFrame
from src.core.world_instance.components.frame_stats import FrameStats
from src.core.world_instance.components.device_status import DeviceStatus
from src.core.world_instance.components.device_config import DeviceConfig


def create_device_entity(middleware_entity_id: int, serial: str = "",
                         local_port: int = 1234) -> int:
    e = esper.create_entity()
    esper.add_component(e, ConnectionComponent(middleware_entity_id=middleware_entity_id))
    esper.add_component(e, LatestFrame())
    esper.add_component(e, FrameStats())
    esper.add_component(e, DeviceStatus())
    esper.add_component(e, DeviceConfig(serial=serial, local_port=local_port))
    return e
