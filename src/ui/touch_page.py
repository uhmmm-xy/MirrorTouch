import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QFrame, QShortcut
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QFont, QMouseEvent, QPixmap, QKeyEvent, QKeySequence
from qfluentwidgets import PushButton
from src.ui.touch_canvas import TouchCanvas
from src.ui.tools.event_handler import EventHandler
from src.ui.tools.property_panel import PropertyPanel
from src.utils.enums import IconType, WidgetType, ComponentEvent
from src.ui.tools.registry import create_component
from src.ui.tools.screen_component import ScreenComponent
from src.utils.helpers import safe_ratio
from src.utils.logger import log
from src.core.handlers import SelectHandler, DragHandler, ResizeHandler, AddWidgetHandler, DeleteHandler, PropertyEditHandler, TestInputHandler, UndoHandler
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

        # ── 创建并注册 Handler ──
        self._select_handler = SelectHandler()
        self._drag_handler = DragHandler()
        self._resize_handler = ResizeHandler()
        self._add_handler = AddWidgetHandler()
        self._delete_handler = DeleteHandler(drag_handler=self._drag_handler)
        self._undo_handler = UndoHandler()
        self._test_input_handler = TestInputHandler()

        self._screen.register_handler(self._add_handler)
        self._screen.register_handler(self._undo_handler)
        self._screen.register_handler(self._delete_handler)
        self._screen.register_handler(self._select_handler)
        self._screen.register_handler(self._drag_handler)
        self._screen.register_handler(self._resize_handler)

        # 注入 TestInputHandler 到 Screen（键盘事件委托）
        self._screen.set_test_input_handler(self._test_input_handler)

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
        # 测试模式隐藏编辑 UI（Canvas 内按钮 + 删除区域）
        self._delete_handler.enabled = not self._test_mode
        self._add_handler.enabled = not self._test_mode
        self._undo_handler.enabled = not self._test_mode
        if self._test_mode:
            self.setFocus()
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
        self._prop_edit_handler = PropertyEditHandler(
            self._property_panel,
            on_changed=self._on_property_changed
        )
        main_layout.addWidget(self._property_panel.widget())

        # 属性面板创建完成后，绑定 SelectHandler 回调
        self._select_handler.set_callback(
            lambda w: self._property_panel.fill_from_data(w.data if w else None)
        )

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
        # 三区域布局：Header(48) + Content + Footer(72)
        header_h = TouchCanvas.HEADER_H
        footer_h = TouchCanvas.FOOTER_H
        content_h = ch - header_h - footer_h
        if content_h <= 0:
            return
        margin = 20
        aw = cw - margin * 2
        ah = content_h - margin * 2
        if self._background_pixmap and not self._background_pixmap.isNull():
            ratio = self._background_pixmap.width() / self._background_pixmap.height()
        elif self._screen.keymap_data:
            ratio = safe_ratio(self._screen.screen_width, self._screen.screen_height, ScreenComponent.DEFAULT_RATIO)
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
        self._screen.y = header_h + content_h // 2
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
                log.info(f"[TouchPage] 已加载: {path}")
            except Exception as e:
                log.error(f"[TouchPage] 加载失败: {e}")

    def _on_export_keymap(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出键鼠映射", "mapping.json", "JSON 文件 (*.json);;所有文件 (*)"
        )
        if path:
            try:
                data = self._screen.export_keymap()
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self._undo_handler.clear()
                self.canvas.update()
                log.info(f"[TouchPage] 已导出: {path}")
            except Exception as e:
                log.error(f"[TouchPage] 导出失败: {e}")

    def _on_load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*)"
        )
        if path:
            try:
                self._background_pixmap = QPixmap(path)
                if self._background_pixmap.isNull():
                    log.error("[TouchPage] 图片加载失败")
                    return
                self._fit_screen_to_window()
                if self._screen.keymap_data:
                    self._screen.relayout_widgets()
                self.canvas.update()
                log.info(f"[TouchPage] 已加载背景: {path}")
            except Exception as e:
                log.error(f"[TouchPage] 图片加载失败: {e}")

    def _on_scrcpy(self):
        log.info("[TouchPage] Scrcpy 投屏功能需要在设置页面配置参数后启用")

    @property
    def undo_handler(self):
        return self._undo_handler

    def _on_property_changed(self, changed: dict):
        """属性面板变更 → 应用到选中控件（由 PropertyEditHandler 回调）"""
        w = self._screen.selected_widget
        if not w or not w.data:
            return
        # 撤销记录：在变更之前保存快照
        self._undo_handler.record(self._screen)
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
        # EYES 不绑定按键
        if new_type == WidgetType.EYES:
            d.key = ""
        if new_type == WidgetType.JOYSTICK:
            d.turbo_key = changed.get("turbo_key", d.turbo_key)
            d.turbo_offset = changed.get("turbo_offset", d.turbo_offset)
            d.creep_key = changed.get("creep_key", d.creep_key)
            d.creep_offset = changed.get("creep_offset", d.creep_offset)
        if new_type != old_type:
            # EYES 单例：切换到 EYES 时移除旧 Eyes
            if new_type == WidgetType.EYES:
                from src.ui.tools.eyes_widget import EyesWidget
                for child in list(self._screen.children):
                    if isinstance(child, EyesWidget) and child is not w:
                        self._screen.remove_widget(child)
                d.key = ""  # EYES 不绑定按键
            # EYES → 其他类型：清除 mouseMoveMap
            if old_type == WidgetType.EYES:
                self._screen.mouse_move_start = None
            self._screen.replace_widget(w, d)
            new_selected = self._screen.children[-1] if self._screen.children else None
            self._screen.select_widget(new_selected)
            self._property_panel.fill_from_data(d)
        else:
            self._screen.relayout_widgets()
            # EYES 移动后同步 mouseMoveMap
            if new_type == WidgetType.EYES:
                self._screen.mouse_move_start = (d.pos_x, d.pos_y)
        self.canvas.update()

    # ── 键盘事件 ──

    def keyPressEvent(self, event: QKeyEvent):
        if self._test_mode:
            key_str = qt_key_to_str(event.key())
            if key_str and self._screen.process_key_press(key_str):
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
            if key_str and self._screen.process_key_release(key_str):
                self.canvas.update()
                return
        super().keyReleaseEvent(event)

    @property
    def screen(self):
        return self._screen

    @property
    def background_pixmap(self):
        return self._background_pixmap

    @property
    def property_panel(self):
        return self._property_panel