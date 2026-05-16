"""KeyboardHook — pynput 键盘全局监听

[MIRROR-TOUCH-PHYSICAL] 职责：
  捕获物理键盘 press/release，通过回调输出原始键码 + 事件类型。
  不持有：映射表、KMS引用、Adapter引用、任何业务逻辑。
"""
from pynput.keyboard import Listener, Key, KeyCode


class KeyboardHook:
    """物理键盘全局钩子。

    callback(vk_code: int, event: str)
        vk_code: Windows 虚拟键码 (如 W=0x57, Shift=0x10)
        event:   "press" | "release"
    """

    def __init__(self, callback):
        self._callback = callback
        self._listener: Listener | None = None
        self._running = False

    # ── 生命周期 ──

    def start(self) -> None:
        """启动键盘监听（pynput 内部 daemon 线程，不阻塞调用方）"""
        if self._running:
            return
        self._listener = Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()
        self._running = True

    def stop(self) -> None:
        """停止键盘监听"""
        self._running = False
        if self._listener and self._listener.is_alive():
            self._listener.stop()

    # ── pynput 回调 ──

    def _on_press(self, key) -> None:
        vk = self._key_to_vk(key)
        if vk:
            self._callback(vk, "press")

    def _on_release(self, key) -> None:
        vk = self._key_to_vk(key)
        if vk:
            self._callback(vk, "release")

    # ── 键码转换 ──

    @staticmethod
    def _key_to_vk(key) -> int | None:
        """pynput Key/KeyCode → Windows VK_CODE"""
        # 普通字符键 (KeyCode)
        if isinstance(key, KeyCode):
            if key.vk is not None:
                return key.vk
            # fallback: 从 char 推断
            if key.char and len(key.char) == 1:
                return ord(key.char.upper())
            return None

        # 特殊功能键 (Key)
        _SPECIAL_MAP = {
            Key.shift: 0x10, Key.shift_l: 0xA0, Key.shift_r: 0xA1,
            Key.ctrl: 0x11, Key.ctrl_l: 0xA2, Key.ctrl_r: 0xA3,
            Key.alt: 0x12, Key.alt_l: 0xA4, Key.alt_r: 0xA5,
            Key.space: 0x20, Key.tab: 0x09, Key.enter: 0x0D,
            Key.esc: 0x1B, Key.backspace: 0x08, Key.delete: 0x2E,
            Key.up: 0x26, Key.down: 0x28, Key.left: 0x25, Key.right: 0x27,
            Key.home: 0x24, Key.end: 0x23,
            Key.page_up: 0x21, Key.page_down: 0x22,
            Key.insert: 0x2D,
            Key.f1: 0x70, Key.f2: 0x71, Key.f3: 0x72, Key.f4: 0x73,
            Key.f5: 0x74, Key.f6: 0x75, Key.f7: 0x76, Key.f8: 0x77,
            Key.f9: 0x78, Key.f10: 0x79, Key.f11: 0x7A, Key.f12: 0x7B,
            Key.caps_lock: 0x14, Key.num_lock: 0x90,
            Key.print_screen: 0x2C,
        }
        return _SPECIAL_MAP.get(key, None)
