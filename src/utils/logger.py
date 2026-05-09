"""统一日志模块

开发模式（默认）正常输出。打包模式（-O 或 MIRRORTOUCH_PROD=1）静默。
用法:
    from src.utils.logger import log
    log.info("[Screen] 加载完成")
    log.warning("[TouchPage] 配置缺失")
    log.error("[Serial] 连接失败")
"""

import os
import sys


class _Logger:
    """条件日志器"""

    def __init__(self):
        # 打包模式: __debug__==False (python -O) 或 环境变量 MIRRORTOUCH_PROD=1
        self._prod = (not __debug__) or os.environ.get("MIRRORTOUCH_PROD", "0") == "1"

    @property
    def is_dev(self) -> bool:
        return not self._prod

    @property
    def is_prod(self) -> bool:
        return self._prod

    def info(self, msg: str):
        if self._prod:
            return
        try:
            print(msg, file=sys.stderr, flush=True)
        except OSError:
            os.write(2, (msg + "\n").encode())

    def warning(self, msg: str):
        if self._prod:
            return
        try:
            print(f"⚠ {msg}", file=sys.stderr, flush=True)
        except OSError:
            os.write(2, (f"⚠ {msg}\n").encode())

    def error(self, msg: str):
        # 错误始终输出
        try:
            print(f"✗ {msg}", file=sys.stderr, flush=True)
        except OSError:
            os.write(2, (f"✗ {msg}\n").encode())


log = _Logger()
