from src.ui.tools.base_widget import BaseWidget
from src.ui.abilities import Selectable, Draggable, Activable
from src.utils.enums import IconType
from src.ui.tools.registry import register_component
from src.utils.widgets_data import WidgetsData


@register_component(IconType.BUTTON)
class ButtonWidget(BaseWidget, Selectable, Draggable, Activable):
    """按钮控件：点击/长按，支持选中、拖拽、测试模式激活"""

    def __init__(self, data: WidgetsData, parent=None, handler=None):
        super().__init__(data, parent, handler)