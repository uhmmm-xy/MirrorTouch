from PyQt5.QtCore import Qt, QRectF, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QCursor
from PyQt5.QtWidgets import QWidget, QApplication
from src.ui.tools.base_component import BaseComponent
from src.ui.tools.base_widget import BaseWidget
from src.utils.widgets_data import WidgetsData, WidgetType
from src.utils.enums import IconType
from src.ui.tools.registry import register_component, create_component

import src.ui.tools.joystick_component
import src.ui.tools.button_widget
import src.ui.tools.eyes_widget
import src.ui.tools.radial_widget


@register_component(IconType.SCREEN)
class ScreenComponent(BaseComponent):

    DEFAULT_WIDTH = 2400
    DEFAULT_HEIGHT = 1080
    DEFAULT_RATIO = DEFAULT_WIDTH / DEFAULT_HEIGHT
    FORMAT_IDENTIFIER = "mirrorTouch"

    def __init__(self, x: int, y: int, size: int = 480,
                 name: str = "屏幕", icon_type=IconType.SCREEN, parent=None,
                 handler=None):
        super().__init__(x, y, size, name, icon_type, parent, handler)
        self.screen_width = self.DEFAULT_WIDTH
        self.screen_height = self.DEFAULT_HEIGHT
        self.mouse_move_start = None
        self.mouse_move_speed_x = 1.0
        self.mouse_move_speed_y = 1.0
        self.keymap_data = None
        self._selected_widget: BaseWidget | None = None
        self._parent_widget: QWidget | None = parent if isinstance(parent, QWidget) else None

        # 测试模式
        self._test_mode = False
        self._hold_states: dict[str, bool] = {}
        self._active_directions: set[str] = set()
        self._active_mod_keys: set[str] = set()
        self._joystick_widget = None
        self._active_radial = None

        # 鼠标锁定
        self._mouse_locked = False
        self._mouse_dx = 0
        self._mouse_dy = 0
        self._mouse_cx_local = 0   # Screen 中心在 Canvas 的局部坐标
        self._mouse_cy_local = 0
        self._mouse_trail: str = ""  # 轨迹日志

    # ── 测试模式 ──

    @property
    def test_mode(self):
        return self._test_mode

    def set_test_mode(self, enabled: bool):
        self._test_mode = enabled
        if enabled:
            self._enter_test_mode()
        else:
            self._exit_test_mode()
        self._request_update()

    def toggle_test_mode(self):
        self.set_test_mode(not self._test_mode)

    def _enter_test_mode(self):
        self._mouse_locked = True
        self._mouse_dx = 0
        self._mouse_dy = 0
        self._mouse_trail = ""
        self._resetting_mouse = False
        self._mouse_center_x = QCursor.pos().x()
        self._mouse_center_y = QCursor.pos().y()
        QApplication.setOverrideCursor(Qt.BlankCursor)

    def _exit_test_mode(self):
        """退出测试模式，恢复所有状态"""
        self._mouse_locked = False
        QApplication.restoreOverrideCursor()
        self._hold_states.clear()
        for child in self.children:
            if child.data and child.data.widget_type == WidgetType.HOLD:
                child.is_hold = False
        if self._joystick_widget:
            self._joystick_widget.is_turbo = False
            self._joystick_widget.is_creep = False
            self._joystick_widget.reset_knob()
            self._joystick_widget = None
        if self._active_radial:
            self._active_radial.deactivate()
            self._active_radial = None
        self._active_directions.clear()
        self._active_mod_keys.clear()
        self._request_update()

    def _find_joystick(self):
        if self._joystick_widget:
            return self._joystick_widget
        for child in self.children:
            if child.data and child.data.widget_type == WidgetType.JOYSTICK:
                self._joystick_widget = child
                return child
        return None

    def _get_joystick_key_parts(self) -> list:
        joy = self._find_joystick()
        if not joy or not joy.data:
            return []
        parts = joy.data.key.split("|")
        while len(parts) < 4:
            parts.append("")
        return parts[:4]

    def _update_joystick_from_directions(self):
        joy = self._find_joystick()
        if not joy:
            return
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
        self._request_update()

    def refresh_joystick(self):
        self._update_joystick_from_directions()

    def handle_key_press(self, key_str: str):
        if not self._test_mode:
            return False

        # 摇杆相关按键
        joy = self._find_joystick()
        if joy and joy.data:
            parts = self._get_joystick_key_parts()
            if key_str in parts:
                self._active_directions.add(key_str)
                self._update_joystick_from_directions()
                return True
            if key_str == joy.data.turbo_key:
                self._active_mod_keys.add(key_str)
                self._update_joystick_from_directions()
                return True
            if key_str == joy.data.creep_key:
                self._active_mod_keys.add(key_str)
                self._update_joystick_from_directions()
                return True

        # 转盘激活
        for child in self.children:
            if not child.data or child.data.widget_type != WidgetType.RADIAL:
                continue
            if child.data.key == key_str:
                child.activate()
                child.is_hold = True
                self._active_radial = child
                self._request_update()
                return True

        # 普通控件
        for child in self.children:
            if not child.data or child.data.widget_type == WidgetType.JOYSTICK:
                continue
            if child.data.key == key_str:
                if child.data.widget_type == WidgetType.HOLD:
                    current = self._hold_states.get(key_str, False)
                    child.is_hold = not current
                    self._hold_states[key_str] = not current
                elif child.data.widget_type in (WidgetType.CLICK, WidgetType.EYES):
                    child.is_hold = True
                self._request_update()
                return True

        return False

    def handle_key_release(self, key_str: str):
        if not self._test_mode:
            return False

        # 摇杆方向键释放
        joy = self._find_joystick()
        if joy and joy.data:
            parts = self._get_joystick_key_parts()
            if key_str in parts:
                self._active_directions.discard(key_str)
                self._update_joystick_from_directions()
                return True
            if key_str == joy.data.turbo_key:
                self._active_mod_keys.discard(key_str)
                self._update_joystick_from_directions()
                return True
            if key_str == joy.data.creep_key:
                self._active_mod_keys.discard(key_str)
                self._update_joystick_from_directions()
                return True

        # 转盘释放
        for child in self.children:
            if not child.data or child.data.widget_type != WidgetType.RADIAL:
                continue
            if child.data.key == key_str:
                child.deactivate()
                child.is_hold = False
                self._active_radial = None
                self._request_update()
                return True

        # 普通控件释放
        for child in self.children:
            if not child.data or child.data.widget_type == WidgetType.JOYSTICK:
                continue
            if child.data.key == key_str:
                if child.data.widget_type in (WidgetType.CLICK, WidgetType.EYES):
                    child.is_hold = False
                self._request_update()
                return True

        return False

    # ── 屏幕区域 ──

    @property
    def screen_rect(self) -> QRectF:
        ratio = self.screen_width / self.screen_height
        w = self.size
        h = self.size / ratio
        return QRectF(self.x - w / 2, self.y - h / 2, w, h)

    def screen_to_local(self, rx: float, ry: float) -> tuple:
        rect = self.screen_rect
        return int(rect.x() + rx * rect.width()), int(rect.y() + ry * rect.height())

    def local_to_screen(self, lx: int, ly: int) -> tuple:
        rect = self.screen_rect
        rx = (lx - rect.x()) / rect.width()
        ry = (ly - rect.y()) / rect.height()
        return max(0, min(1, rx)), max(0, min(1, ry))

    # ── 控件管理 ──

    def add_widget(self, widget: BaseWidget):
        if not isinstance(widget, BaseWidget):
            raise TypeError("ScreenComponent 只接受 BaseWidget 实例")
        widget.parent = self
        self.add_child(widget)
        if widget.data and widget.data.widget_type == WidgetType.JOYSTICK:
            self._joystick_widget = widget

    def remove_widget(self, widget: BaseWidget):
        if widget in self.children:
            self.children.remove(widget)
        if widget is self._joystick_widget:
            self._joystick_widget = None
        if widget is self._active_radial:
            self._active_radial = None

    def clear_widgets(self):
        self.children.clear()
        self._joystick_widget = None
        self._active_radial = None

    def relayout_widgets(self):
        for child in self.children:
            child.x, child.y = self.screen_to_local(
                child.data.pos_x, child.data.pos_y
            )
            child.size = int(self.size * child.data.scale_size)

    # ── 选中与微调 ──

    def select_widget_at(self, px: int, py: int):
        hit = None
        for child in reversed(self.children):
            if child.contains(px, py):
                hit = child
                break
        self.select_widget(hit)

    def select_widget(self, widget: BaseWidget | None):
        if self._selected_widget:
            self._selected_widget.is_hold = False
        self._selected_widget = widget
        if widget:
            widget.is_hold = True
        self._request_update()

    def move_selected(self, dx: int, dy: int):
        if self._selected_widget:
            self._selected_widget.move_to(
                self._selected_widget.x + dx,
                self._selected_widget.y + dy,
            )

    @property
    def selected_widget(self):
        return self._selected_widget

    # ── 组件工厂 ──

    def _create_widget(self, data: WidgetsData) -> BaseWidget:
        widget = create_component(
            data.widget_type.icon_type,
            x=0, y=0, size=36, name=data.comment,
            parent=self,
            handler=self.handler,
        )
        widget.data = data
        return widget

    def replace_widget(self, old: BaseWidget, new_data):
        self.remove_widget(old)
        new_widget = self._create_widget(new_data)
        self.add_widget(new_widget)
        self.relayout_widgets()
        self._request_update()

    # ── 加载 JSON ──

    def load_keymap(self, json_data: dict):
        self.keymap_data = json_data
        if json_data.get(self.FORMAT_IDENTIFIER) is True:
            self._load_mirror_format(json_data)
        else:
            self._load_scrcpy_format(json_data)
        self.relayout_widgets()
        self._request_update()
        print(f"[Screen] 加载完成: {self.screen_width}x{self.screen_height}, 控件: {len(self.children)}")

    def _load_mirror_format(self, json_data: dict):
        self.screen_width = json_data.get("width", self.DEFAULT_WIDTH)
        self.screen_height = json_data.get("height", self.DEFAULT_HEIGHT)
        mm = json_data.get("mouseMoveMap", {})
        if mm:
            sp = mm.get("startPos", {})
            self.mouse_move_start = (sp.get("x", 0.5), sp.get("y", 0.5))
            self.mouse_move_speed_x = mm.get("speedRatioX", 1.0)
            self.mouse_move_speed_y = mm.get("speedRatioY", 1.0)
        self.clear_widgets()
        for item in json_data.get("widgets", []):
            data = WidgetsData.from_dict(item)
            self.add_widget(self._create_widget(data))

    def _load_scrcpy_format(self, json_data: dict):
        self.screen_width = json_data.get("width", self.DEFAULT_WIDTH)
        self.screen_height = json_data.get("height", self.DEFAULT_HEIGHT)
        mm = json_data.get("mouseMoveMap", {})
        if mm:
            sp = mm.get("startPos", {})
            self.mouse_move_start = (sp.get("x", 0.5), sp.get("y", 0.5))
            self.mouse_move_speed_x = mm.get("speedRatioX", 1.0)
            self.mouse_move_speed_y = mm.get("speedRatioY", 1.0)
        self.clear_widgets()
        for node in json_data.get("keyMapNodes", []):
            ntype = node.get("type", "")
            if ntype == "KMT_STEER_WHEEL":
                pos = node.get("centerPos", {})
                key_str = "|".join([
                    node.get("upKey", "Key_W"),
                    node.get("downKey", "Key_S"),
                    node.get("leftKey", "Key_A"),
                    node.get("rightKey", "Key_D"),
                ])
                data = WidgetsData(
                    key=key_str,
                    comment=node.get("comment", "摇杆"),
                    switch_map=node.get("switchMap", False),
                    widget_type=WidgetType.JOYSTICK,
                    pos_x=pos.get("x", 0.17), pos_y=pos.get("y", 0.77),
                    scale_size=0.08,
                )
                data.turbo_key = node.get("upKey", "")
                data.turbo_offset = node.get("upOffset", 0.2)
            elif ntype == "KMT_CLICK":
                pos = node.get("pos", {})
                data = WidgetsData(
                    key=node.get("key", ""),
                    comment=node.get("comment", ""),
                    switch_map=node.get("switchMap", False),
                    widget_type=WidgetType.CLICK,
                    pos_x=pos.get("x", 0), pos_y=pos.get("y", 0),
                    scale_size=0.025,
                )
            else:
                continue
            self.add_widget(self._create_widget(data))

    # ── 导出 JSON ──

    def export_keymap(self) -> dict:
        return {
            self.FORMAT_IDENTIFIER: True,
            "width": self.screen_width,
            "height": self.screen_height,
            "mouseMoveMap": {
                "startPos": {
                    "x": self.mouse_move_start[0] if self.mouse_move_start else 0.5,
                    "y": self.mouse_move_start[1] if self.mouse_move_start else 0.5,
                },
                "speedRatioX": self.mouse_move_speed_x,
                "speedRatioY": self.mouse_move_speed_y,
            },
            "widgets": [w.data.to_dict() for w in self.children],
        }

    # ── 绘制 ──

    def draw(self, painter: QPainter):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.screen_rect
        rx, ry, rw, rh = rect.x(), rect.y(), rect.width(), rect.height()

        painter.setPen(QPen(QColor(60, 60, 60), 2))
        painter.setBrush(QBrush(QColor(18, 18, 18, 120)))
        painter.drawRoundedRect(int(rx), int(ry), int(rw), int(rh), 8, 8)

        if self._test_mode:
            painter.setPen(QPen(QColor(255, 180, 60), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(int(rx) - 2, int(ry) - 2, int(rw) + 4, int(rh) + 4, 10, 10)

        painter.setPen(QColor(130, 130, 130))
        font = QFont("Microsoft YaHei", 9)
        painter.setFont(font)
        status_text = f"{self.screen_width}×{self.screen_height}  控件:{len(self.children)}"
        if self._test_mode:
            trail = self._mouse_trail if self._mouse_trail else "无轨迹"
            status_text += f"  [测试] {trail}"
        label_rect = QRectF(rx, ry + rh - 20, rw, 16)
        painter.drawText(label_rect, Qt.AlignCenter, status_text)

        for child in self.children:
            child.draw(painter)

        painter.restore()

    # ── 事件转发 ──

    def handle_mouse_press(self, px: int, py: int, button):
        for child in reversed(self.children):
            if child.handle_mouse_press(px, py, button):
                return True
        return False

    def handle_mouse_move(self, px: int, py: int):
        if self._mouse_locked:
            if self._resetting_mouse:
                self._resetting_mouse = False
                return
            cur = QCursor.pos()
            self._mouse_dx = cur.x() - self._mouse_center_x
            self._mouse_dy = cur.y() - self._mouse_center_y
            self._mouse_trail = f"{self._mouse_dx:+d},{self._mouse_dy:+d}"
            if self._active_radial:
                self._active_radial.update_angle(self._mouse_dx, self._mouse_dy)
            self._resetting_mouse = True
            QCursor.setPos(self._mouse_center_x, self._mouse_center_y)
            self._request_update()
            return
        for child in self.children:
            child.handle_mouse_move(px, py)
        self._request_update()

    def handle_mouse_release(self, px: int, py: int, button):
        for child in self.children:
            child.handle_mouse_release(px, py, button)