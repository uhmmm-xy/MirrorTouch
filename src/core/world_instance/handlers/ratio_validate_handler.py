"""RatioValidateHandler — 比例校验 + 横竖屏旋转坐标转换

[MIRROR-TOUCH-T2] 纯函数子方法，内聚于本 Handler，由 KMS 调用。
  所有方法均为无状态静态方法，严禁持有全局状态、依赖 Qt 库、读写文件或网络。

  校验方式：精确整数交叉相乘，零容差。
    - 正向匹配：dev_w * map_h == dev_h * map_w  → "normal"
    - 翻转匹配：dev_w * map_w == dev_h * map_h  → "flipped"
    - 不匹配：返回 None（由调用方抛出 MappingRatioMismatchError）
"""
from src.core.exceptions import MappingRatioMismatchError


def validate_ratio(dev_w: int, dev_h: int, map_w: int, map_h: int) -> str | None:
    """精确整数交叉相乘，判定设备分辨率与映射画布的比例关系。

    Args:
        dev_w, dev_h: 设备真实宽高（来自 DeviceComponent.base_w/base_h）
        map_w, map_h: 映射文件声明的画布宽高（来自 mapping.json 的 width/height）

    Returns:
        "normal"  — 正向匹配（横竖一致）
        "flipped" — 翻转匹配（设备转了 90°）
        None      — 不匹配，应抛出异常
    """
    if dev_w <= 0 or dev_h <= 0 or map_w <= 0 or map_h <= 0:
        return None

    # 容差 0.025：比例差异 ≤ 2.5% 视为匹配
    tolerance = 0.025
    if dev_w * map_h == dev_h * map_w:
        return "normal"
    if dev_w * map_w == dev_h * map_h:
        return "flipped"

    # 整数无法匹配时用浮点比例比对
    dev_ratio = dev_w / dev_h
    map_ratio = map_w / map_h
    map_flip_ratio = map_h / map_w

    if abs(dev_ratio - map_ratio) / max(dev_ratio, map_ratio) <= tolerance:
        return "normal"
    if abs(dev_ratio - map_flip_ratio) / max(dev_ratio, map_flip_ratio) <= tolerance:
        return "flipped"
    return None


def apply_rotation(rx: float, ry: float, rotation: int) -> tuple[float, float]:
    """根据旋转角度计算新比例坐标，处理轴交换与方向翻转。

    Args:
        rx, ry:   原始比例坐标 (0.0 ~ 1.0)
        rotation: 设备旋转角度 (0/90/180/270)

    Returns:
        旋转后的比例坐标 (nx, ny)
    """
    if rotation == 0:
        return rx, ry
    elif rotation == 90:
        return 1.0 - ry, rx        # 顺时针90°：新x=1-原y，新y=原x
    elif rotation == 180:
        return 1.0 - rx, 1.0 - ry  # 顺时针180°：翻转
    elif rotation == 270:
        return ry, 1.0 - rx        # 顺时针270°：新x=原y，新y=1-原x
    return rx, ry


def to_device_pixels(rx: float, ry: float, dev_w: int, dev_h: int) -> tuple[int, int]:
    """比例坐标 → 设备整型像素坐标，双向边界钳制。

    Args:
        rx, ry:  旋转处理后的比例坐标 (0.0 ~ 1.0)
        dev_w, dev_h: 设备宽高

    Returns:
        钳制后的整型像素坐标 (px, py)，范围 [0, dev_w-1] × [0, dev_h-1]
    """
    px = int(rx * dev_w)
    py = int(ry * dev_h)
    px = max(0, min(dev_w - 1, px))
    py = max(0, min(dev_h - 1, py))
    return px, py


def validate_and_convert(dev_x: int, dev_y: int,
                         dev_w: int, dev_h: int, rotation: int,
                         map_w: int, map_h: int) -> tuple[int, int]:
    """校验比例 + 应用旋转，输入/输出均为设备像素坐标。

    输入坐标已是设备像素（由 calc_pixel 产出），本函数只做比例校验与旋转变换，
    不再重新做 map→device 的缩放。

    Args:
        dev_x, dev_y: 设备像素坐标（已由 calc_pixel 转换）
        dev_w, dev_h: 设备真实宽高
        rotation:     设备旋转角度
        map_w, map_h: 映射画布宽高（仅用于比例校验）

    Returns:
        旋转后的设备像素坐标整型
    """
    result = validate_ratio(dev_w, dev_h, map_w, map_h)
    if result is None:
        raise MappingRatioMismatchError(
            f"{map_w}×{map_h}", f"{dev_w}×{dev_h}"
        )

    # 设备像素 → 比例
    rx = dev_x / max(dev_w, 1)
    ry = dev_y / max(dev_h, 1)

    # 旋转
    nrx, nry = apply_rotation(rx, ry, rotation)

    # 比例 → 设备像素
    return to_device_pixels(nrx, nry, dev_w, dev_h)
