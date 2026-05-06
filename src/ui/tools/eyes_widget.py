from src.ui.tools.base_widget import BaseWidget
from src.utils.enums import IconType
from src.ui.tools.registry import register_component
from src.utils.widgets_data import WidgetsData


@register_component(IconType.EYES)
class EyesWidget(BaseWidget):
    """视角控件：目前外观同按钮"""

    def __init__(self, data: WidgetsData, parent=None, handler=None):
        super().__init__(data, parent, handler)