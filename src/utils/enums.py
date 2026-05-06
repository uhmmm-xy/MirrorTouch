from enum import Enum, auto


class TipStatus(Enum):
    CLICK = auto()
    DRAG = auto()
    RIGHT_CLICK = auto()
    UNSELECTED = auto()


class IconType(Enum):
    JOYSTICK = auto()
    EYES = auto()
    BUTTON = auto()
    SCREEN = auto()
    RADIAL = auto()        # 径向转盘


class WidgetType(Enum):
    CLICK = auto()
    HOLD = auto()
    JOYSTICK = auto()
    EYES = auto()
    RADIAL = auto()        # 径向转盘

    @property
    def icon_type(self) -> "IconType":
        _WIDGET_TO_ICON = {
            WidgetType.CLICK: IconType.BUTTON,
            WidgetType.HOLD: IconType.BUTTON,
            WidgetType.JOYSTICK: IconType.JOYSTICK,
            WidgetType.EYES: IconType.EYES,
            WidgetType.RADIAL: IconType.RADIAL,
        }
        return _WIDGET_TO_ICON[self]


class ComponentEvent(Enum):
    CLICK = auto()
    CHANGE = auto()
    DRAG_START = auto()
    DRAG_MOVE = auto()
    DRAG_END = auto()
    RIGHT_CLICK = auto()
    RIGHT_DRAG = auto()
    RIGHT_RELEASE = auto()
    HOVER_ENTER = auto()
    HOVER_LEAVE = auto()