from src.ui.tools.base_widget import BaseWidget
from src.utils.enums import IconType
from src.ui.tools.registry import register_component
from src.utils.widgets_data import WidgetsData


@register_component(IconType.BUTTON)
class ButtonWidget(BaseWidget):
    """按钮控件：圆形按键"""

    def __init__(self, data: WidgetsData, parent=None, handler=None):
        super().__init__(data, parent, handler)