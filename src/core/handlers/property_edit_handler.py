"""PropertyEditHandler — 属性面板变更统一处理

监听 PropertyPanel 的 CHANGE 事件，收集数据后通过回调通知外部。
解耦 PropertyPanel（纯 View）和 TouchPage（业务逻辑）。
"""

from src.core.handlers.base_handler import BaseHandler
from src.utils.enums import ComponentEvent
from src.utils.logger import log


class PropertyEditHandler(BaseHandler):
    """属性面板变更处理器

    职责:
        - 监听 PropertyPanel 的 CHANGE 事件
        - 调用 panel.collect_data() 收集当前数据
        - 通过 on_changed 回调通知外部应用变更

    PropertyPanel 只保留:
        - 控件布局 (_setup_widgets)
        - fill_from_data() — 从数据填充 UI
        - collect_data() — 从 UI 收集数据
        - 内部信号转发到 EventHandler
    """

    priority: int = 40

    def __init__(self, panel: "PropertyPanel",
                 on_changed: "callable | None" = None):
        """
        Args:
            panel: 属性面板实例
            on_changed: 变更回调，签名为 (collected_data: dict) -> None
        """
        super().__init__()
        self._panel = panel
        self._on_changed = on_changed
        panel.on(ComponentEvent.CHANGE, self._on_panel_change)

    def set_callback(self, callback: "callable"):
        """设置变更回调"""
        self._on_changed = callback

    def _on_panel_change(self, _component):
        """PropertyPanel CHANGE 事件 → 收集数据 → 回调"""
        if self._on_changed is None:
            return
        try:
            data = self._panel.collect_data()
            self._on_changed(data)
        except Exception as e:
            log.error(f"[PropertyEditHandler] 收集数据失败: {e}")
