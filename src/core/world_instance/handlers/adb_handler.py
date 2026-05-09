"""AdbHandler — ADB 设备检测 + 端口转发"""
import subprocess
import esper
from src.utils.logger import log


def register():
    esper.set_handler("adb.start", _on_start)
    esper.set_handler("adb.stop", _on_stop)


def _on_start(device_entity: int):
    from src.core.world_instance.components.device_config import DeviceConfig
    from src.core.config_manager import load_config

    dc = esper.component_for_entity(device_entity, DeviceConfig)
    app_cfg = load_config()
    adb = app_cfg.adb_path

    if not dc.serial:
        dc.serial = detect_device(adb)
        if not dc.serial:
            log.error("[AdbHandler] 未检测到设备")
            return

    # ADB forward
    ret = subprocess.run([adb, "forward", f"tcp:{dc.local_port}", f"tcp:{dc.local_port}"],
                         capture_output=True, text=True)
    if ret.returncode == 0:
        log.info(f"[AdbHandler] 端口转发: {dc.serial} → tcp:{dc.local_port}")
    else:
        log.error(f"[AdbHandler] 转发失败: {ret.stderr}")


def _on_stop(device_entity: int):
    from src.core.world_instance.components.device_config import DeviceConfig
    from src.core.config_manager import load_config

    dc = esper.component_for_entity(device_entity, DeviceConfig)
    adb = load_config().adb_path

    subprocess.run([adb, "forward", "--remove", f"tcp:{dc.local_port}"],
                   capture_output=True)
    log.info(f"[AdbHandler] 已移除转发: tcp:{dc.local_port}")


def detect_device(adb_path: str) -> str:
    try:
        ret = subprocess.run([adb_path, "devices"], capture_output=True, text=True, timeout=5)
        for line in ret.stdout.strip().split("\n")[1:]:
            if "\tdevice" in line:
                serial = line.split("\t")[0].strip()
                log.info(f"[AdbHandler] 检测到设备: {serial}")
                return serial
    except Exception as e:
        log.error(f"[AdbHandler] 设备检测失败: {e}")
    return ""


def get_screen_size(adb_path: str, serial: str = "") -> tuple[int, int]:
    """adb shell wm size → (width, height)"""
    cmd = [adb_path]
    if serial:
        cmd += ["-s", serial]
    cmd += ["shell", "wm", "size"]
    try:
        ret = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        for line in ret.stdout.strip().split("\n"):
            if "Override size:" in line:
                line = line.split("Override size:")[-1]
            elif "Physical size:" in line:
                line = line.split("Physical size:")[-1]
            else:
                continue
            w, h = line.strip().split("x")
            log.info(f"[AdbHandler] 屏幕分辨率: {w}x{h}")
            return int(w), int(h)
    except Exception as e:
        log.error(f"[AdbHandler] 分辨率获取失败: {e}")
    return 1080, 1920
