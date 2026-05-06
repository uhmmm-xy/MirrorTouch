from dataclasses import dataclass, asdict
from src.utils.enums import WidgetType


@dataclass
class WidgetsData:
    """控件数据类，src/utils 共用"""

    key: str = ""
    comment: str = ""
    switch_map: bool = False
    widget_type: WidgetType = WidgetType.CLICK
    pos_x: float = 0.0
    pos_y: float = 0.0
    scale_size: float = 0.03
    _turbo_key: str = ""
    _turbo_offset: float = 0.2
    _creep_key: str = ""
    _creep_offset: float = 0.1

    # ── turbo ──

    @property
    def turbo_key(self) -> str:
        if self.widget_type != WidgetType.JOYSTICK:
            raise AttributeError(f"widget_type 为 {self.widget_type} 时不允许访问 turbo_key")
        return self._turbo_key

    @turbo_key.setter
    def turbo_key(self, value: str):
        if self.widget_type != WidgetType.JOYSTICK:
            raise AttributeError(f"widget_type 为 {self.widget_type} 时不允许设置 turbo_key")
        self._turbo_key = value

    @property
    def turbo_offset(self) -> float:
        if self.widget_type != WidgetType.JOYSTICK:
            raise AttributeError(f"widget_type 为 {self.widget_type} 时不允许访问 turbo_offset")
        return self._turbo_offset

    @turbo_offset.setter
    def turbo_offset(self, value: float):
        if self.widget_type != WidgetType.JOYSTICK:
            raise AttributeError(f"widget_type 为 {self.widget_type} 时不允许设置 turbo_offset")
        self._turbo_offset = value

    # ── creep ──

    @property
    def creep_key(self) -> str:
        if self.widget_type != WidgetType.JOYSTICK:
            raise AttributeError(f"widget_type 为 {self.widget_type} 时不允许访问 creep_key")
        return self._creep_key

    @creep_key.setter
    def creep_key(self, value: str):
        if self.widget_type != WidgetType.JOYSTICK:
            raise AttributeError(f"widget_type 为 {self.widget_type} 时不允许设置 creep_key")
        self._creep_key = value

    @property
    def creep_offset(self) -> float:
        if self.widget_type != WidgetType.JOYSTICK:
            raise AttributeError(f"widget_type 为 {self.widget_type} 时不允许访问 creep_offset")
        return self._creep_offset

    @creep_offset.setter
    def creep_offset(self, value: float):
        if self.widget_type != WidgetType.JOYSTICK:
            raise AttributeError(f"widget_type 为 {self.widget_type} 时不允许设置 creep_offset")
        self._creep_offset = value

    # ── 序列化 ──

    def to_dict(self) -> dict:
        d = asdict(self)
        is_joystick = self.widget_type == WidgetType.JOYSTICK
        d["turbo_key"] = self._turbo_key if is_joystick else ""
        d["turbo_offset"] = self._turbo_offset if is_joystick else 0.0
        d["creep_key"] = self._creep_key if is_joystick else ""
        d["creep_offset"] = self._creep_offset if is_joystick else 0.0
        d["widget_type"] = self.widget_type.name.lower()
        del d["_turbo_key"], d["_turbo_offset"]
        del d["_creep_key"], d["_creep_offset"]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "WidgetsData":
        d = dict(d)
        d["widget_type"] = WidgetType[d["widget_type"].upper()]
        d["_turbo_key"] = d.pop("turbo_key", "")
        d["_turbo_offset"] = d.pop("turbo_offset", 0.2)
        d["_creep_key"] = d.pop("creep_key", "")
        d["_creep_offset"] = d.pop("creep_offset", 0.1)
        return cls(**d)