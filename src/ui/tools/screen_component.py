from PyQt5.QtCore import Qt, QRectF, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QCursor
from PyQt5.QtWidgets import QWidget, QApplication
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.core.handlers.test_input_handler import TestInputHandler
from src.ui.tools.base_component import BaseComponent
from src.ui.tools.base_widget import BaseWidget
from src.utils.widgets_data import WidgetsData
from src.utils.enums import IconType
from src.utils.mapping_io import MappingIO
from src.ui.tools.registry import register_component, create_component
from src.core.handlers.base_handler import BaseHandler

import src.ui.tools.joystick_component
import src.ui.tools.button_widget
import src.ui.tools.eyes_widget
import src.ui.tools.radial_widget


@register_component(IconType.SCREEN)
class ScreenComponent(BaseComponent):

    DEFAULT_RATIO = MappingIO.DEFAULT_WIDTH / MappingIO.DEFAULT_HEIGHT

    def __init__(self, x: int, y: int, size: int = 480,
                 name: str = "屏幕", icon_type=IconType.SCREEN, parent=None,
                 handler=None):
        super().__init__(x, y, size, name, icon_type, parent, handler)
        self.screen_width = MappingIO.DEFAULT_WIDTH
        self.screen_height = MappingIO.DEFAULT_HEIGHT
        self.mouse_move_start = None
        self.mouse_move_speed_x = 1.0
        self.mouse_move_speed_y = 1.0
        self.keymap_data = None
        self._selected_widget: BaseWidget | None = None

        # 测试模式（鼠标锁定由 Screen 管理，键盘输入由 TestInputHandler 管理）
        self._test_mode = False
        self._test_input_handler = None  # 由 TouchPage 注入

        # 鼠标锁定
        self._mouse_locked = False
        self._mouse_dx = 0
        self._mouse_dy = 0
        self._mouse_cx_local = 0   # Screen 中心在 Canvas 的局部坐标
        self._mouse_cy_local = 0
        self._mouse_trail: str = ""  # 轨迹日志

        # Handler 链（按 priority 排序后链式调用）
        self._handlers: list[BaseHandler] = []
        self._canvas: "QWidget | None" = None

    # ── Canvas 引用 ──

    def set_canvas(self, canvas: "QWidget"):
        """设置画布引用（TouchCanvas 初始化时调用）"""
        self._canvas = canvas

    # ── Handler 注册 ──

    @property
    def handlers(self) -> list:
        return sorted(self._handlers, key=lambda h: h.priority)

    def register_handler(self, handler: BaseHandler):
        """注册一个 Handler（自动按 priority 排序）"""
        if handler not in self._handlers:
            self._handlers.append(handler)

    def remove_handler(self, handler: BaseHandler):
        """移除一个 Handler"""
        if handler in self._handlers:
            self._handlers.remove(handler)

    # ── 事件入口（View → Handler 链） ──

    def process_mouse_press(self, pos: QPoint, button):
        """鼠标按下 → 遍历 Handler 链"""
        for handler in self.handlers:
            if handler.on_press(pos, button, self, self._canvas) == BaseHandler.HANDLED:
                break

    def process_mouse_move(self, pos: QPoint):
        """鼠标移动 → 遍历 Handler 链"""
        for handler in self.handlers:
            if handler.on_move(pos, self, self._canvas) == BaseHandler.HANDLED:
                break

    def process_mouse_release(self, pos: QPoint, button):
        """鼠标释放 → 遍历 Handler 链"""
        for handler in self.handlers:
            if handler.on_release(pos, button, self, self._canvas) == BaseHandler.HANDLED:
                break

    # ── 测试模式（键盘委托给 TestInputHandler，鼠标保留在 Screen） ──

    @property
    def test_mode(self):
        return self._test_mode

    def set_test_input_handler(self, handler: "TestInputHandler"):
        """注入 TestInputHandler（由 TouchPage 在初始化时调用）"""
        self._test_input_handler = handler

    def set_test_mode(self, enabled: bool):
        self._test_mode = enabled
        if enabled:
            self._enter_test_mode()
            if self._test_input_handler:
                self._test_input_handler.enter_test_mode(self)
        else:
            if self._test_input_handler:
                self._test_input_handler.exit_test_mode()
            self._exit_test_mode()
        self._request_update()

    def toggle_test_mode(self):
        self.set_test_mode(not self._test_mode)

    def _enter_test_mode(self):
        """进入测试模式：鼠标锁定 + 隐藏光标"""
        self._mouse_locked = True
        self._mouse_dx = 0
        self._mouse_dy = 0
        self._mouse_trail = ""
        self._resetting_mouse = False

        # 若有 Eyes 组件，以 Eyes 中心为基准（不强制跳转鼠标）
        eyes = self._find_eyes()
        if eyes:
            eyes.set_test_center(eyes.x, eyes.y)
            self._mouse_center_x = QCursor.pos().x()
            self._mouse_center_y = QCursor.pos().y()
        else:
            self._mouse_center_x = QCursor.pos().x()
            self._mouse_center_y = QCursor.pos().y()

        QApplication.setOverrideCursor(Qt.BlankCursor)

    def _exit_test_mode(self):
        """退出测试模式：鼠标解锁 + 恢复光标"""
        self._mouse_locked = False
        QApplication.restoreOverrideCursor()
        eyes = self._find_eyes()
        if eyes:
            eyes.reset_test_trail()

    # ── 键盘事件入口（委托给 TestInputHandler） ──

    def process_key_press(self, key_str: str) -> bool:
        """键盘按下 → 通知 TestInputHandler"""
        if self._test_input_handler:
            return self._test_input_handler.on_key_press(key_str, self) == BaseHandler.HANDLED
        return False

    def process_key_release(self, key_str: str) -> bool:
        """键盘释放 → 通知 TestInputHandler"""
        if self._test_input_handler:
            return self._test_input_handler.on_key_release(key_str, self) == BaseHandler.HANDLED
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

    def remove_widget(self, widget: BaseWidget):
        if widget in self.children:
            self.children.remove(widget)

    def clear_widgets(self):
        self.children.clear()

    def relayout_widgets(self):
        for child in self.children:
            child.x, child.y = self.screen_to_local(
                child.data.pos_x, child.data.pos_y
            )
            child.size = int(self.size * child.data.scale_size)
        # 同步 Eyes → mouseMoveMap
        eyes = self._find_eyes()
        if eyes and eyes.data:
            self.mouse_move_start = (eyes.data.pos_x, eyes.data.pos_y)

    # ── 选中与微调 ──

    @property
    def selected_widget(self) -> BaseWidget | None:
        return self._selected_widget

    @selected_widget.setter
    def selected_widget(self, widget: BaseWidget | None):
        """设置选中控件（由 Handler 调用）"""
        if self._selected_widget is widget:
            return
        if self._selected_widget:
            self._selected_widget.deselect()
        self._selected_widget = widget
        if widget:
            widget.select()

    def select_widget(self, widget: BaseWidget | None):
        """选择控件（兼容旧接口，内部调用 setter）"""
        self.selected_widget = widget
        self._request_update()

    def move_selected(self, dx: int, dy: int):
        """方向键微调（编辑模式）"""
        if self._selected_widget:
            self._selected_widget.move_to(
                self._selected_widget.x + dx,
                self._selected_widget.y + dy,
            )
            self._request_update()

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

    # ── 加载 / 导出 JSON（委托 MappingIO） ──

    def load_keymap(self, json_data: dict):
        self.keymap_data = json_data
        result = MappingIO.load(json_data)
        self.screen_width = result['width']
        self.screen_height = result['height']
        self.mouse_move_start = result['mouse_move_start']
        self.mouse_move_speed_x = result['mouse_move_speed_x']
        self.mouse_move_speed_y = result['mouse_move_speed_y']
        self.clear_widgets()
        for data in result['widgets_data']:
            self.add_widget(self._create_widget(data))
        self.relayout_widgets()
        self._request_update()
        print(f"[Screen] 加载完成: {self.screen_width}x{self.screen_height}, 控件: {len(self.children)}")

    def export_keymap(self) -> dict:
        return MappingIO.export(
            self.screen_width, self.screen_height,
            self.mouse_move_start,
            self.mouse_move_speed_x, self.mouse_move_speed_y,
            self.children,
        )

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

    # ── 测试模式鼠标锁定处理（保留在 ScreenComponent，后续迁移到 TestInputHandler） ──

    def handle_test_mouse_move(self):
        """测试模式下的鼠标锁定 + 转盘角度/视角轨迹更新"""
        if not self._mouse_locked:
            return
        if self._resetting_mouse:
            self._resetting_mouse = False
            return

        cur = QCursor.pos()
        dx = cur.x() - self._mouse_center_x
        dy = cur.y() - self._mouse_center_y

        # ── 视角模式：鼠标自由移动，记录轨迹，触碰边界跳转 ──
        eyes = self._find_eyes()
        if eyes:
            # 获取 Canvas 内的鼠标局部坐标用于轨迹绘制
            if self._canvas:
                local = self._canvas.mapFromGlobal(cur)
                eyes.test_update_trail(local.x(), local.y())
            else:
                eyes.test_update_trail(dx, dy)
            self._mouse_trail = f"{dx:+d},{dy:+d}"
            self._request_update()
            return

        # ── 普通模式：鼠标锁定 + 转盘角度更新 ──
        self._mouse_dx = dx
        self._mouse_dy = dy
        self._mouse_trail = f"{dx:+d},{dy:+d}"
        active_radial = self._test_input_handler.active_radial if self._test_input_handler else None
        if active_radial:
            active_radial.update_angle(self._mouse_dx, self._mouse_dy)

        self._resetting_mouse = True
        QCursor.setPos(self._mouse_center_x, self._mouse_center_y)
        self._request_update()

    def _find_eyes(self):
        """查找 Screen 中的 EyesWidget"""
        from src.ui.tools.eyes_widget import EyesWidget
        for child in self.children:
            if isinstance(child, EyesWidget):
                return child
        return None