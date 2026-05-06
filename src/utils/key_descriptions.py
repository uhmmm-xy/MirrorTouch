"""
键鼠按键描述映射表
压缩格式，用于 MirrorTouch 自己的 JSON
"""

from PyQt5.QtCore import Qt

MOUSE_MAP = {
    "LeftButton": "LMB",
    "RightButton": "RMB",
    "MiddleButton": "CMB",
    "LM1": "LM1",
    "LM2": "LM2",
    "MouseMove": "MOV",
    "WheelUp": "MWU",
    "WheelDown": "MWD",
}

KEY_MAP = {
    # 字母 — 直接存自身
    "A": "A", "B": "B", "C": "C", "D": "D", "E": "E",
    "F": "F", "G": "G", "H": "H", "I": "I", "J": "J",
    "K": "K", "L": "L", "M": "M", "N": "N", "O": "O",
    "P": "P", "Q": "Q", "R": "R", "S": "S", "T": "T",
    "U": "U", "V": "V", "W": "W", "X": "X", "Y": "Y",
    "Z": "Z",

    # 数字
    "0": "0", "1": "1", "2": "2", "3": "3", "4": "4",
    "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",

    # 功能键
    "F1": "F1", "F2": "F2", "F3": "F3", "F4": "F4",
    "F5": "F5", "F6": "F6", "F7": "F7", "F8": "F8",
    "F9": "F9", "F10": "F10", "F11": "F11", "F12": "F12",

    # 修饰键
    "Shift": "SFT",
    "Control": "CTL",
    "Alt": "ALT",
    "CapsLock": "CAPS",
    "Tab": "TAB",
    "Escape": "ESC",

    # 导航
    "Up": "UP",
    "Down": "DN",
    "Left": "LT",
    "Right": "RT",
    "Home": "HOME",
    "End": "END",
    "PageUp": "PGUP",
    "PageDown": "PGDN",

    # 编辑
    "Insert": "INS",
    "Delete": "DEL",
    "Backspace": "BKS",
    "Enter": "ENT",
    "Return": "ENT",
    "Space": "SPC",

    # 符号
    "Minus": "-",
    "Equal": "=",
    "BracketLeft": "[",
    "BracketRight": "]",
    "Backslash": "\\",
    "Semicolon": ";",
    "Apostrophe": "'",
    "Comma": ",",
    "Period": ".",
    "Slash": "/",
    "Grave": "`",

    # 小键盘
    "NumLock": "NUM",
    "NumDivide": "N/",
    "NumMultiply": "N*",
    "NumSubtract": "N-",
    "NumAdd": "N+",
    "NumEnter": "NENT",
    "Num0": "N0", "Num1": "N1", "Num2": "N2",
    "Num3": "N3", "Num4": "N4", "Num5": "N5",
    "Num6": "N6", "Num7": "N7", "Num8": "N8", "Num9": "N9",
    "NumDecimal": "N.",

    # 其他
    "Print": "PRT",
    "ScrollLock": "SCRLK",
    "Pause": "PAUSE",
    "Meta": "WIN",
}

# 反向映射：缩写 → 键名
REVERSE_MAP = {v: k for k, v in {**MOUSE_MAP, **KEY_MAP}.items()}


def describe(key: str) -> str:
    """键名 → 缩写"""
    if key in MOUSE_MAP:
        return MOUSE_MAP[key]
    if key in KEY_MAP:
        return KEY_MAP[key]
    # 去掉 Key_ 前缀再试
    if key.startswith("Key_"):
        return KEY_MAP.get(key[4:], key[4:])
    return key


def normalize(key: str) -> str:
    """缩写 → 键名"""
    return REVERSE_MAP.get(key, key)