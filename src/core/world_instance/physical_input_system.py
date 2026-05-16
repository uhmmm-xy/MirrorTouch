"""PhysicalInputSystem — 物理输入生命周期管理（Esper System）

[MIRROR-TOUCH-PHYSICAL] 职责：
  touch.start → 启动 KeyboardHook + MouseHook
  touch.stop  → 停止 MouseHook + KeyboardHook
  通过 InputAdapter 桥接 Hook 回调到 KMS.push_physical_input。
"""
import esper
from src.utils.logger import log


# ── 模块级单例 ──
_keyboard_hook = None
_mouse_hook = None
_adapter = None


def register():
    esper.set_handler("touch.start", _on_start)
    esper.set_handler("touch.stop", _on_stop)


def _on_start(config):
    """触控会话启动 → 加载映射，启动物理输入钩子"""
    global _keyboard_hook, _mouse_hook, _adapter

    if _keyboard_hook and _keyboard_hook._running:
        log.warning("[PhysicalInput] 钩子已在运行，跳过重复启动")
        return

    # ── 从 mapping.json 读取 Eyes key + 屏幕尺寸 ──
    eyes_key = ""
    screen_w, screen_h = 1920, 1080
    try:
        from src.core.config_manager import load_config
        import json
        cfg = load_config()
        if cfg.mapping_path:
            with open(cfg.mapping_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            screen_w = int(data.get("width", 1920))
            screen_h = int(data.get("height", 1080))
            for w in data.get("widgets", []):
                if w.get("widget_type") == "eyes":
                    eyes_key = w.get("key", "")
                    break
    except Exception as e:
        log.warning(f"[PhysicalInput] 映射加载失败: {e}")

    # 优先从 TouchConfig/DeviceComponent 获取真实屏幕尺寸
    try:
        from src.core.world_instance.world_bootstrap import get_device_meta_entity
        from src.core.world_instance.components.device_component import DeviceComponent
        ent = get_device_meta_entity()
        if ent and esper.entity_exists(ent):
            dc = esper.component_for_entity(ent, DeviceComponent)
            if dc.base_w > 0 and dc.base_h > 0:
                screen_w, screen_h = dc.base_w, dc.base_h
    except Exception:
        pass

    # ── 延迟导入 KMS（避免循环依赖）──
    from src.core.world_instance.key_mapping_system import push_physical_input
    from src.core.world_instance.handlers.input_adapter import InputAdapter
    from src.core.world_instance.handlers.keyboard_hook import KeyboardHook
    from src.core.world_instance.handlers.mouse_hook import MouseHook

    _adapter = InputAdapter(push_physical_input)
    _adapter.set_screen_size(screen_w, screen_h)
    if eyes_key:
        _adapter.set_eyes_key(eyes_key)

    _keyboard_hook = KeyboardHook(_adapter.on_key_event)
    _mouse_hook = MouseHook(_adapter.on_mouse_event)

    _keyboard_hook.start()
    _mouse_hook.start()

    log.info(f"[PhysicalInput] 钩子已启动 screen={screen_w}x{screen_h} eyes_key={eyes_key}")


def _on_stop():
    """触控会话停止 → 停止物理输入钩子"""
    global _keyboard_hook, _mouse_hook, _adapter

    if _mouse_hook:
        _mouse_hook.stop()
        _mouse_hook = None
    if _keyboard_hook:
        _keyboard_hook.stop()
        _keyboard_hook = None
    _adapter = None

    log.info("[PhysicalInput] 钩子已停止")
