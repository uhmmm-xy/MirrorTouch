"""TestInputHandler — 测试模式键盘输入 Handler

优先级 35：接管 Alt+` 测试模式下的所有键盘输入。
通过 Activable / Directional 等 Ability 接口操作控件，
不直接依赖 ScreenComponent 内部状态。

从 ScreenComponent.handle_key_press/release 迁移而来。
"""

from src.core.handlers.base_handler import BaseHandler
from src.utils.widgets_data import WidgetType


class TestInputHandler(BaseHandler):
    """测试模式键盘输入处理器

    职责:
        - 摇杆方向键 → Directional.set_direction
        - Turbo/Creep 修饰键 → 动态范围切换
        - 转盘激活键 → RadialWidget.activate/deactivate
        - 普通控件键 → Activable.activate/deactivate
        - HOLD 类型切换状态管理
    """

    priority: int = 35

    def __init__(self):
        super().__init__()
        # 测试模式运行时状态
        self._hold_states: dict[str, bool] = {}
        self._active_directions: set[str] = set()
        self._active_mod_keys: set[str] = set()
        self._joystick_widget = None
        self._active_radial = None

    # ── 测试模式生命周期 ──

    def enter_test_mode(self, screen: "ScreenComponent"):
        """进入测试模式：扫描控件，初始化状态"""
        self._hold_states.clear()
        self._active_directions.clear()
        self._active_mod_keys.clear()
        self._active_radial = None
        self._joystick_widget = self._find_joystick(screen)
        # Eyes 无需按键绑定，由 ScreenComponent 直接管理鼠标锁定

    def exit_test_mode(self):
        """退出测试模式：恢复所有控件状态"""
        # 重置 HOLD 控件
        self._hold_states.clear()
        # 重置摇杆
        if self._joystick_widget:
            self._joystick_widget.is_turbo = False
            self._joystick_widget.is_creep = False
            self._joystick_widget.reset_knob()
            self._joystick_widget = None
        # 停用转盘
        if self._active_radial:
            self._active_radial.deactivate()
            self._active_radial.is_hold = False
            self._active_radial = None
        self._active_directions.clear()
        self._active_mod_keys.clear()

    # ── 键盘事件 ──

    def on_key_press(self, key_str: str,
                     screen: "ScreenComponent") -> bool:
        if not screen.test_mode:
            return self.PASS

        handled = (
            self._handle_joystick_press(key_str, screen) or
            self._handle_radial_press(key_str) or
            self._handle_normal_press(key_str, screen)
        )
        if handled:
            screen._request_update()
            _dispatch_touch(key_str, "press", screen)
        return handled

    def on_key_release(self, key_str: str,
                       screen: "ScreenComponent") -> bool:
        if not screen.test_mode:
            return self.PASS

        handled = (
            self._handle_joystick_release(key_str) or
            self._handle_radial_release(key_str) or
            self._handle_normal_release(key_str, screen)
        )
        if handled:
            screen._request_update()
            _dispatch_touch(key_str, "release", screen)
        return handled

    # ── 摇杆处理 ──

    def _handle_joystick_press(self, key_str: str,
                               screen: "ScreenComponent") -> bool:
        joy = self._joystick_widget
        if not joy or not joy.data:
            return False

        parts = self._get_joystick_key_parts()
        if key_str in parts:
            self._active_directions.add(key_str)
            self._update_joystick_direction(joy)
            return True
        if key_str == joy.data.turbo_key:
            self._active_mod_keys.add(key_str)
            self._update_joystick_direction(joy)
            return True
        if key_str == joy.data.creep_key:
            self._active_mod_keys.add(key_str)
            self._update_joystick_direction(joy)
            return True
        return False

    def _handle_joystick_release(self, key_str: str) -> bool:
        joy = self._joystick_widget
        if not joy or not joy.data:
            return False

        parts = self._get_joystick_key_parts()
        if key_str in parts:
            self._active_directions.discard(key_str)
            self._update_joystick_direction(joy)
            return True
        if key_str == joy.data.turbo_key:
            self._active_mod_keys.discard(key_str)
            self._update_joystick_direction(joy)
            return True
        if key_str == joy.data.creep_key:
            self._active_mod_keys.discard(key_str)
            self._update_joystick_direction(joy)
            return True
        return False

    def _update_joystick_direction(self, joy):
        """根据当前方向键 + 修饰键状态更新摇杆"""
        parts = self._get_joystick_key_parts()
        if not parts:
            return

        dx, dy = 0, 0
        if parts[0] and parts[0] in self._active_directions:
            dy = -1
        if parts[1] and parts[1] in self._active_directions:
            dy = 1
        if parts[2] and parts[2] in self._active_directions:
            dx = -1
        if parts[3] and parts[3] in self._active_directions:
            dx = 1

        turbo_key = joy.data.turbo_key if joy.data else ""
        creep_key = joy.data.creep_key if joy.data else ""
        joy.is_turbo = bool(turbo_key and turbo_key in self._active_mod_keys)
        joy.is_creep = bool(creep_key and creep_key in self._active_mod_keys)

        joy.set_direction(dx, dy)

    # ── 转盘处理 ──

    def _handle_radial_press(self, key_str: str) -> bool:
        if self._active_radial:
            return False  # 已有激活转盘，不切换
        if not self._joystick_widget:
            return False
        screen = self._joystick_widget.parent
        if not screen:
            return False
        for child in screen.children:
            if not child.data or child.data.widget_type != WidgetType.RADIAL:
                continue
            if child.data.key == key_str:
                child.activate()
                child.is_hold = True
                self._active_radial = child
                return True
        return False

    def _handle_radial_release(self, key_str: str) -> bool:
        if not self._active_radial:
            return False
        if self._active_radial.data and self._active_radial.data.key == key_str:
            self._active_radial.deactivate()
            self._active_radial.is_hold = False
            self._active_radial = None
            return True
        return False

    # ── 普通控件处理 ──

    def _handle_normal_press(self, key_str: str,
                             screen: "ScreenComponent") -> bool:
        for child in screen.children:
            if not child.data or child.data.widget_type == WidgetType.JOYSTICK:
                continue
            if child.data.key == key_str:
                if child.data.widget_type == WidgetType.HOLD:
                    current = self._hold_states.get(key_str, False)
                    child.is_hold = not current
                    self._hold_states[key_str] = not current
                elif child.data.widget_type in (WidgetType.CLICK, WidgetType.EYES):
                    child.is_hold = True
                return True
        return False

    def _handle_normal_release(self, key_str: str,
                               screen: "ScreenComponent") -> bool:
        for child in screen.children:
            if not child.data or child.data.widget_type == WidgetType.JOYSTICK:
                continue
            if child.data.key == key_str:
                if child.data.widget_type in (WidgetType.CLICK, WidgetType.EYES):
                    child.is_hold = False
                return True
        return False

    # ── 辅助方法 ──

    def _find_joystick(self, screen: "ScreenComponent"):
        """在 screen 子控件中查找摇杆"""
        for child in screen.children:
            if child.data and child.data.widget_type == WidgetType.JOYSTICK:
                return child
        return None

    def _get_joystick_key_parts(self) -> list:
        """解析摇杆 4 方向键字符串 → ['Up','Down','Left','Right']"""
        joy = self._joystick_widget
        if not joy or not joy.data:
            return []
        parts = joy.data.key.split("|")
        while len(parts) < 4:
            parts.append("")
        return parts[:4]

    def refresh_joystick(self):
        """外部调用：刷新摇杆方向（如属性面板修改按键后）"""
        if self._joystick_widget:
            self._update_joystick_direction(self._joystick_widget)

    @property
    def active_radial(self):
        return self._active_radial


def _dispatch_touch(key_str: str, event: str, screen):
    """测试模式按键 → 触控引擎"""
    try:
        import esper
        from src.core.world_instance.handlers.coordinate_calc_handler import calc_pixel
        widget = None
        for child in screen.children:
            if child.data and child.data.key == key_str:
                widget = child
                break
        if not widget or not widget.data:
            return
        rx, ry = widget.data.pos_x, widget.data.pos_y
        px, py = calc_pixel(rx, ry)
        esper.dispatch_event("touch.input", key_str, event, px, py)
    except Exception:
        pass
