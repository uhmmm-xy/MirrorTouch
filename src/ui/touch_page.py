import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QFrame, QShortcut
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QFont, QMouseEvent, QPixmap, QKeyEvent, QKeySequence
from qfluentwidgets import PushButton
from src.ui.tools.event_handler import EventHandler
from src.ui.tools.property_panel import PropertyPanel
from src.utils.enums import IconType, WidgetType, ComponentEvent
from src.ui.tools.registry import create_component
from src.ui.tools.screen_component import ScreenComponent
import src.ui.tools.joystick_component
import src.ui.tools.button_widget
import src.ui.tools.eyes_widget
import src.ui.tools.screen_component


# Qt 按键 → 字符串映射（与 KeyCaptureButton.raw_key 格式一致）
_QT_KEY_TO_STR = {
    # 字母
    Qt.Key_A: "A", Qt.Key_B: "B", Qt.Key_C: "C", Qt.Key_D: "D", Qt.Key_E: "E",
    Qt.Key_F: "F", Qt.Key_G: "G", Qt.Key_H: "H", Qt.Key_I: "I", Qt.Key_J: "J",
    Qt.Key_K: "K", Qt.Key_L: "L", Qt.Key_M: "M", Qt.Key_N: "N", Qt.Key_O: "O",
    Qt.Key_P: "P", Qt.Key_Q: "Q", Qt.Key_R: "R", Qt.Key_S: "S", Qt.Key_T: "T",
    Qt.Key_U: "U", Qt.Key_V: "V", Qt.Key_W: "W", Qt.Key_X: "X", Qt.Key_Y: "Y",
    Qt.Key_Z: "Z",
    # 数字
    Qt.Key_0: "0", Qt.Key_1: "1", Qt.Key_2: "2", Qt.Key_3: "3", Qt.Key_4: "4",
    Qt.Key_5: "5", Qt.Key_6: "6", Qt.Key_7: "7", Qt.Key_8: "8", Qt.Key_9: "9",
    # 功能键
    Qt.Key_F1: "F1", Qt.Key_F2: "F2", Qt.Key_F3: "F3", Qt.Key_F4: "F4",
    Qt.Key_F5: "F5", Qt.Key_F6: "F6", Qt.Key_F7: "F7", Qt.Key_F8: "F8",
    Qt.Key_F9: "F9", Qt.Key_F10: "F10", Qt.Key_F11: "F11", Qt.Key_F12: "F12",
    # 修饰键
    Qt.Key_Shift: "Shift", Qt.Key_Control: "Control", Qt.Key_Alt: "Alt",
    Qt.Key_CapsLock: "CapsLock", Qt.Key_Tab: "Tab", Qt.Key_Escape: "Escape",
    # 导航
    Qt.Key_Up: "Up", Qt.Key_Down: "Down", Qt.Key_Left: "Left", Qt.Key_Right: "Right",
    Qt.Key_Home: "Home", Qt.Key_End: "End",
    Qt.Key_PageUp: "PageUp", Qt.Key_PageDown: "PageDown",
    # 编辑
    Qt.Key_Insert: "Insert", Qt.Key_Delete: "Delete",
    Qt.Key_Backspace: "Backspace", Qt.Key_Enter: "Enter",
    Qt.Key_Return: "Return", Qt.Key_Space: "Space",
    # 符号
    Qt.Key_Minus: "Minus", Qt.Key_Equal: "Equal",
    Qt.Key_BracketLeft: "BracketLeft", Qt.Key_BracketRight: "BracketRight",
    Qt.Key_Backslash: "Backslash", Qt.Key_Semicolon: "Semicolon",
    Qt.Key_Apostrophe: "Apostrophe", Qt.Key_Comma: "Comma",
    Qt.Key_Period: "Period", Qt.Key_Slash: "Slash",
    Qt.Key_QuoteLeft: "Grave",
    # 小键盘
    Qt.Key_NumLock: "NumLock", Qt.Key_Slash: "NumDivide",
    Qt.Key_Asterisk: "NumMultiply", Qt.Key_Minus: "NumSubtract",
    Qt.Key_Plus: "NumAdd",
}


def qt_key_to_str(qt_key: int) -> str:
    """将 Qt.Key_XXX 转为字符串（与 PropertyPanel raw_key 格式一致）"""
    return _QT_KEY_TO_STR.get(qt_key, "")


class TouchPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("touchPage")
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self._handler = EventHandler()
        self._screen = create_component(
            IconType.SCREEN,
            x=0, y=0, size=400, name="投屏画面",
            parent=self, handler=self._handler
        )
        self._background_pixmap: QPixmap | None = None
        self._test_mode = False

        self._setup_ui()
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        """注册全局热键"""
        # Alt+` 切换测试模式
        self._shortcut_test = QShortcut(QKeySequence("Alt+`"), self)
        self._shortcut_test.activated.connect(self._toggle_test_mode)

    def _toggle_test_mode(self):
        self._test_mode = not self._test_mode
        self._screen.set_test_mode(self._test_mode)
        if self._test_mode:
            self.setFocus()  # 确保接收键盘事件
        self.canvas.update()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(12, 12, 0, 12)

        toolbar = QHBoxLayout()
        self.btn_load = PushButton("加载映射")
        self.btn_load.setFixedWidth(110)
        self.btn_load.clicked.connect(self._on_load_keymap)
        toolbar.addWidget(self.btn_load)
        toolbar.addSpacing(6)

        self.btn_export = PushButton("导出映射")
        self.btn_export.setFixedWidth(110)
        self.btn_export.clicked.connect(self._on_export_keymap)
        self.btn_export.setEnabled(False)
        toolbar.addWidget(self.btn_export)
        toolbar.addSpacing(6)

        self.btn_image = PushButton("导入图片")
        self.btn_image.setFixedWidth(110)
        self.btn_image.clicked.connect(self._on_load_image)
        toolbar.addWidget(self.btn_image)
        toolbar.addSpacing(6)

        self.btn_scrcpy = PushButton("Scrcpy投屏")
        self.btn_scrcpy.setFixedWidth(110)
        self.btn_scrcpy.clicked.connect(self._on_scrcpy)
        toolbar.addWidget(self.btn_scrcpy)
        toolbar.addStretch()
        left_layout.addLayout(toolbar)

        line_h = QFrame()
        line_h.setFrameShape(QFrame.HLine)
        line_h.setFrameShadow(QFrame.Sunken)
        left_layout.addWidget(line_h)

        self.canvas = TouchCanvas(self)
        self.canvas.setMouseTracking(True)
        left_layout.addWidget(self.canvas, 1)

        main_layout.addLayout(left_layout, 1)

        line_v = QFrame()
        line_v.setFrameShape(QFrame.VLine)
        line_v.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line_v)

        self._property_panel = PropertyPanel(parent=self, handler=self._handler)
        self._property_panel.on(ComponentEvent.CHANGE, self._on_property_changed)
        main_layout.addWidget(self._property_panel.widget())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_screen_to_window()
        if self._screen.keymap_data:
            self._screen.relayout_widgets()

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_screen_to_window()
        if self._screen.keymap_data:
            self._screen.relayout_widgets()

    def _fit_screen_to_window(self):
        cw = self.canvas.width()
        ch = self.canvas.height()
        if cw <= 0 or ch <= 0:
            return
        margin = 20
        aw = cw - margin * 2
        ah = ch - margin * 2
        if self._background_pixmap and not self._background_pixmap.isNull():
            ratio = self._background_pixmap.width() / self._background_pixmap.height()
        else:
            ratio = ScreenComponent.DEFAULT_RATIO
        if aw / ah > ratio:
            screen_w = int(ah * ratio)
            screen_h = ah
        else:
            screen_w = aw
            screen_h = int(aw / ratio)
        self._screen.size = screen_w
        self._screen.x = cw // 2
        self._screen.y = ch // 2
        if self._background_pixmap and not self._background_pixmap.isNull():
            self._screen.screen_width = self._background_pixmap.width()
            self._screen.screen_height = self._background_pixmap.height()

    def _on_load_keymap(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择键鼠映射文件", "", "JSON 文件 (*.json);;所有文件 (*)"
        )
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._screen.load_keymap(data)
                self._fit_screen_to_window()
                self._screen.relayout_widgets()
                self.btn_export.setEnabled(True)
                self.canvas.update()
                print(f"[TouchPage] 已加载: {path}")
            except Exception as e:
                print(f"[TouchPage] 加载失败: {e}")

    def _on_export_keymap(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出键鼠映射", "mapping.json", "JSON 文件 (*.json);;所有文件 (*)"
        )
        if path:
            try:
                data = self._screen.export_keymap()
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"[TouchPage] 已导出: {path}")
            except Exception as e:
                print(f"[TouchPage] 导出失败: {e}")

    def _on_load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*)"
        )
        if path:
            try:
                self._background_pixmap = QPixmap(path)
                if self._background_pixmap.isNull():
                    print("[TouchPage] 图片加载失败")
                    return
                self._fit_screen_to_window()
                if self._screen.keymap_data:
                    self._screen.relayout_widgets()
                self.canvas.update()
                print(f"[TouchPage] 已加载背景: {path}")
            except Exception as e:
                print(f"[TouchPage] 图片加载失败: {e}")

    def _on_scrcpy(self):
        print("[TouchPage] Scrcpy 投屏功能需要在设置页面配置参数后启用")

    def _on_property_changed(self, _component):
        w = self._screen.selected_widget
        if not w or not w.data:
            return
        changed = self._property_panel.collect_data()
        d = w.data
        old_type = d.widget_type
        d.comment = changed.get("comment", d.comment)
        d.key = changed.get("key", d.key)
        new_type_str = changed.get("widget_type", old_type.name)
        try:
            new_type = WidgetType[new_type_str]
        except KeyError:
            new_type = old_type
        d.widget_type = new_type
        d.pos_x = changed.get("pos_x", d.pos_x)
        d.pos_y = changed.get("pos_y", d.pos_y)
        d.scale_size = changed.get("scale_size", d.scale_size)
        if new_type == WidgetType.JOYSTICK:
            d.turbo_key = changed.get("turbo_key", d.turbo_key)
            d.turbo_offset = changed.get("turbo_offset", d.turbo_offset)
            d.creep_key = changed.get("creep_key", d.creep_key)
            d.creep_offset = changed.get("creep_offset", d.creep_offset)
        if new_type != old_type:
            self._screen.replace_widget(w, d)
            new_selected = self._screen.children[-1] if self._screen.children else None
            self._screen.select_widget(new_selected)
            self._property_panel.fill_from_data(d)
        else:
            self._screen.relayout_widgets()
        self.canvas.update()

    # ── 键盘事件 ──

    def keyPressEvent(self, event: QKeyEvent):
        if self._test_mode:
            key_str = qt_key_to_str(event.key())
            if key_str and self._screen.handle_key_press(key_str):
                self.canvas.update()
                return
        # 编辑模式：方向键微调
        if event.key() == Qt.Key_Up:
            self._screen.move_selected(0, -1)
        elif event.key() == Qt.Key_Down:
            self._screen.move_selected(0, 1)
        elif event.key() == Qt.Key_Left:
            self._screen.move_selected(-1, 0)
        elif event.key() == Qt.Key_Right:
            self._screen.move_selected(1, 0)
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if self._test_mode:
            key_str = qt_key_to_str(event.key())
            if key_str and self._screen.handle_key_release(key_str):
                self.canvas.update()
                return
        super().keyReleaseEvent(event)

    @property
    def screen(self):
        return self._screen

    @property
    def background_pixmap(self):
        return self._background_pixmap


class TouchCanvas(QWidget):
    def __init__(self, touch_page: TouchPage):
        super().__init__()
        self._page = touch_page
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: #1a1a1a; border-radius: 8px;")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(26, 26, 26))
        if self._page.background_pixmap and not self._page.background_pixmap.isNull():
            rect = self._page.screen.screen_rect
            painter.drawPixmap(
                int(rect.x()), int(rect.y()),
                int(rect.width()), int(rect.height()),
                self._page.background_pixmap
            )
        if not self._page.screen.keymap_data and not self._page.background_pixmap:
            painter.setPen(QColor(120, 120, 120))
            font = QFont("Microsoft YaHei", 14)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter,
                             "请点击上方按钮加载映射文件或导入背景图片")
        self._page.screen.draw(painter)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        self._page.screen.select_widget_at(event.x(), event.y())
        self._page.screen.handle_mouse_press(event.x(), event.y(), event.button())
        self._page._property_panel.fill_from_data(
            self._page.screen.selected_widget.data if self._page.screen.selected_widget else None
        )
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        self._page.screen.handle_mouse_move(event.x(), event.y())
        self.update()
        w = self._page.screen.selected_widget
        if w and w.data:
            self._page._property_panel.fill_from_data(w.data)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._page.screen.handle_mouse_release(event.x(), event.y(), event.button())
        self.update()
        w = self._page.screen.selected_widget
        if w and w.data:
            self._page._property_panel.fill_from_data(w.data)