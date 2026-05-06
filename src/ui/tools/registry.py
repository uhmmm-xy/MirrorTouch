from src.utils.enums import IconType
from src.ui.tools.base_component import BaseComponent
from src.ui.tools.base_widget import BaseWidget
from src.utils.widgets_data import WidgetsData

_COMPONENT_REGISTRY = {}


def register_component(icon_type: IconType):
    def wrapper(cls):
        _COMPONENT_REGISTRY[icon_type] = cls
        return cls
    return wrapper


def create_component(icon_type: IconType, x: int, y: int,
                     size: int = 80, name: str = "", parent=None,
                     handler=None) -> BaseComponent:
    """
    工厂方法。统一基础参数签名。
    - BaseWidget 子类：自动将基础参数包装为 WidgetsData，再传入构造
    - BaseComponent 子类：直接透传
    """
    cls = _COMPONENT_REGISTRY.get(icon_type)
    if cls is None:
        return BaseComponent(x, y, size, name, icon_type, parent, handler)

    if issubclass(cls, BaseWidget):
        data = WidgetsData(
            key=name,
            comment=name,
            widget_type=_icon_to_widget_type(icon_type),
        )
        return cls(data, parent=parent, handler=handler)

    return cls(x, y, size, name, icon_type, parent, handler)


def _icon_to_widget_type(icon_type: IconType):
    from src.utils.enums import WidgetType
    _MAP = {
        IconType.BUTTON: WidgetType.CLICK,
        IconType.JOYSTICK: WidgetType.JOYSTICK,
        IconType.EYES: WidgetType.EYES,
        IconType.RADIAL: WidgetType.RADIAL,    # 新增
    }
    return _MAP.get(icon_type, WidgetType.CLICK)