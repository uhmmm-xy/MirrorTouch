"""ConfigManager — 持久化配置管理"""
import json
import os
from dataclasses import dataclass, asdict, field
from src.utils.logger import log


@dataclass
class AppConfig:
    adb_path: str = ""            # 空=自动检测
    serial_port: str = ""
    serial_baud: int = 115200
    scrcpy_max_size: int = 1080
    scrcpy_max_fps: int = 120      # 中间件推流帧率
    scrcpy_bit_rate: str = "16000"
    render_max_fps: int = 120
    touch_consume_freq: int = 800     # SS 触控消费频率 Hz
    log_middleware_stdout: bool = False  # 记录中间件 stdout 到日志文件
    keep_service_alive: bool = False     # 常驻服务
    mapping_path: str = ""              # 触控映射 JSON 路径
    device_profiles: dict = field(default_factory=dict)  # {adb_serial: com_port} 跨会话设备绑定记忆


_CONFIG_DIR = os.path.join("resources", "config")
_CONFIG_PATH = os.path.join(_CONFIG_DIR, "default.json")


def load_config() -> AppConfig:
    cfg = AppConfig()
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
        except Exception as e:
            log.warning(f"[Config] 加载失败: {e}")
    if not cfg.adb_path:
        cfg.adb_path = _detect_adb()
    return cfg


def save_config(cfg: AppConfig):
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)


def _detect_adb() -> str:
    import shutil
    builtin = os.path.join("resources", "libs", "adb", "adb.exe")
    if os.path.exists(builtin):
        log.info(f"[Config] ADB: {builtin}")
        return builtin
    found = shutil.which("adb")
    if found:
        log.info(f"[Config] ADB(PATH): {found}")
        return found
    log.warning("[Config] ADB 未找到")
    return "adb"
