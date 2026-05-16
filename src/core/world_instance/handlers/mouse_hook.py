"""MouseHook — pynput 鼠标全局监听

[MIRROR-TOUCH-PHYSICAL] 职责：
  捕获物理鼠标 move/button press/button release，通过回调输出位移 + 事件类型。
  不持有：屏幕尺寸、映射表、Adapter引用、KMS引用、任何业务逻辑。
"""
from pynput.mouse import Listener, Button
from src.utils.logger import log

class MouseHook:
    """物理鼠标全局钩子。

    callback(dx: int, dy: int, event: str, button: str | None)
        dx, dy:  相对位移（首次回调时置 0 防跳变）
        event:   "move" | "press" | "release"
        button:  "left" | "right" | "middle" | None (move时为None)
    """

    def __init__(self, callback):
        self._callback = callback
        self._listener: Listener | None = None
        self._running = False
        self._last_x: int | None = None
        self._last_y: int | None = None

    # ── 生命周期 ──

    def start(self) -> None:
        """启动鼠标监听（pynput 内部 daemon 线程）"""
        if self._running:
            return
        self._last_x = None
        self._last_y = None
        self._listener = Listener(
            on_move=self._on_move,
            on_click=self._on_click,
        )
        self._listener.start()
        self._running = True

    def stop(self) -> None:
        """停止鼠标监听"""
        self._running = False
        if self._listener and self._listener.is_alive():
            self._listener.stop()

    # ── pynput 回调 ──

    def _on_move(self, x: int, y: int) -> None:
        """鼠标移动 → 计算相对位移"""
        if self._last_x is None:
            self._last_x, self._last_y = x, y
            return
        dx = x - self._last_x
        dy = y - self._last_y
        self._last_x, self._last_y = x, y
        self._callback(dx, dy, "move", None)

    def _on_click(self, x: int, y: int, button: Button, pressed: bool) -> None:
        """鼠标按键 → press/release"""
        btn_name = self._button_name(button)
        if btn_name is None:
            return
        event = "press" if pressed else "release"
        self._callback(0, 0, event, btn_name)

    # ── 按键名映射 ──

    @staticmethod
    def _button_name(button: Button) -> str | None:
        """pynput Button → 字符串"""
        _MAP = {
            Button.left: "left",
            Button.right: "right",
            Button.middle: "middle",
        }
        return _MAP.get(button, None)
