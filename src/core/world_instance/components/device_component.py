"""DeviceComponent — 设备元数据组件（ECS 世界中设备元数据的唯一数据源）

[MIRROR-TOUCH-T1] 职责：
  本组件承载设备的基础元数据（分辨率、旋转角度、串口绑定、就绪状态），
  与 DeviceConfig（serial/local_port 用于连接配置）职责严格分离。

  字段更新策略：
    - base_w / base_h：静态基准数据，仅首次拉取或手动重连时写入。
    - current_rotation：动态数据，仅在投屏分辨率变化事件触发时更新。
    - bound_com_port：串口绑定，由 UI 层写入或从持久化配置恢复。
    - is_ready：自动推导，当 base_w>0 且 base_h>0 且 bound_com_port 非空时为 True。

  全局数据流约束：
    所有系统必须通过 esper 获取 DeviceComponent 实例读取数据，
    严禁引入全局单例或跨层直接访问。
"""
from dataclasses import dataclass


@dataclass
class DeviceComponent:
    adb_serial: str = ""
    base_w: int = 0
    base_h: int = 0
    current_rotation: int = 0
    bound_com_port: str = ""
    is_ready: bool = False

    def __post_init__(self):
        self._refresh_status()

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        # 当影响 is_ready 判定的字段变更时，自动重算
        if name in ("base_w", "base_h", "bound_com_port"):
            self._refresh_status()

    def _refresh_status(self):
        """根据 base_w/base_h/bound_com_port 自动计算 is_ready。

        判定逻辑：base_w > 0 且 base_h > 0 且 bound_com_port 非空 → True
        """
        ready = (
            self.base_w > 0
            and self.base_h > 0
            and bool(self.bound_com_port)
        )
        # 使用 object.__setattr__ 避免触发自身 __setattr__ 无限递归
        super().__setattr__("is_ready", ready)
