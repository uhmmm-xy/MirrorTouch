"""MirrorTouch 自定义异常"""


class MappingRatioMismatchError(Exception):
    """映射比例与设备比例不匹配时抛出"""

    def __init__(self, expected_ratio: str, actual_ratio: str):
        self.expected_ratio = expected_ratio
        self.actual_ratio = actual_ratio
        super().__init__(
            f"映射比例不匹配：设备比例 {actual_ratio}，"
            f"映射期望 {expected_ratio}。"
            f"请调整映射文件或旋转设备后重试。"
        )
