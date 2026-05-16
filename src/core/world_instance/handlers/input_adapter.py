"""InputAdapter — 原始输入 → KMS 标准格式转换

[MIRROR-TOUCH-PHYSICAL] 职责:
  纯转换层，无副作用。
  VK→hotkey 查表 + 鼠标Δ→ratio 转换 + 事件类型标准化。
  不持有：Hook、KMS、线程、任何状态。
"""
from typing import Callable


class InputAdapter:
    """物理输入适配器。

    接收 KeyboardHook/MouseHook 回调，转换为 KMS 标准格式后调用 kms_callback。
    """

    # ── Windows VK_CODE → hotkey 映射表 ──
    VK_TO_HOTKEY: dict[int, str] = {
        # 字母
        0x41: "A", 0x42: "B", 0x43: "C", 0x44: "D", 0x45: "E",
        0x46: "F", 0x47: "G", 0x48: "H", 0x49: "I", 0x4A: "J",
        0x4B: "K", 0x4C: "L", 0x4D: "M", 0x4E: "N", 0x4F: "O",
        0x50: "P", 0x51: "Q", 0x52: "R", 0x53: "S", 0x54: "T",
        0x55: "U", 0x56: "V", 0x57: "W", 0x58: "X", 0x59: "Y", 0x5A: "Z",
        # 数字
        0x30: "0", 0x31: "1", 0x32: "2", 0x33: "3", 0x34: "4",
        0x35: "5", 0x36: "6", 0x37: "7", 0x38: "8", 0x39: "9",
        # F1-F12
        0x70: "F1", 0x71: "F2", 0x72: "F3", 0x73: "F4",
        0x74: "F5", 0x75: "F6", 0x76: "F7", 0x77: "F8",
        0x78: "F9", 0x79: "F10", 0x7A: "F11", 0x7B: "F12",
        # 修饰键
        0x10: "Shift", 0x11: "Control", 0x12: "Alt",
        0xA0: "Shift", 0xA1: "Shift", 0xA2: "Control", 0xA3: "Control",
        0xA4: "Alt", 0xA5: "Alt",
        # 特殊键
        0x20: "Space", 0x09: "Tab", 0x1B: "Escape", 0x0D: "Enter",
        0x08: "Backspace", 0x2E: "Delete",
        0xDC: "\\",
        # 方向键
        0x26: "Up", 0x28: "Down", 0x25: "Left", 0x27: "Right",
    }

    # ── pynput Button → hotkey ──
    BUTTON_MAP: dict[str, str] = {
        "left": "LeftButton",
        "right": "RightButton",
        "middle": "MiddleButton",
    }

    def __init__(self, kms_callback: Callable[[str, str, float, float], None]):
        """
        Args:
            kms_callback: KMS.push_physical_input(hotkey, event, rx, ry)
        """
        self._kms = kms_callback
        self._screen_w: int = 1920
        self._screen_h: int = 1080
        self._eyes_key: str = ""

    def set_screen_size(self, w: int, h: int) -> None:
        """设置屏幕像素尺寸，供鼠标 Δ→ratio 转换"""
        self._screen_w = w
        self._screen_h = h

    def set_eyes_key(self, key: str) -> None:
        """设置 Eyes 控件的 hotkey（从 mapping.json 读取）"""
        self._eyes_key = key

    # ── Hook 回调入口 ──

    def on_key_event(self, vk_code: int, event: str) -> None:
        """键盘回调：VK→hotkey → KMS"""
        hotkey = self.VK_TO_HOTKEY.get(vk_code)
        if hotkey:
            self._kms(hotkey, event, 0.0, 0.0)

    def on_mouse_event(self, dx: int, dy: int, event: str, button: str | None) -> None:
        """鼠标回调：Δ→ratio / button→hotkey → KMS"""
        if event == "move":
            if not self._eyes_key:
                return
            from src.utils.logger import log
            rx = dx / max(1, self._screen_w)
            ry = dy / max(1, self._screen_h)
            # log.info(f"[Adapter] mouse move → KMS({self._eyes_key}, move, {rx:.6f}, {ry:.6f})")
            self._kms(self._eyes_key, "move", rx, ry)
        elif event in ("press", "release"):
            hotkey = self.BUTTON_MAP.get(button or "")
            if hotkey:
                self._kms(hotkey, event, 0.0, 0.0)
