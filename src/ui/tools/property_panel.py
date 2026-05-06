from PyQt5.QtWidgets import QWidget, QFormLayout, QLabel
from PyQt5.QtCore import Qt
from qfluentwidgets import LineEdit, ComboBox, Slider
from src.ui.tools.base_component import BaseComponent
from src.ui.tools.key_capture_button import KeyCaptureButton
from src.utils.enums import ComponentEvent, WidgetType


class PropertyPanel(BaseComponent):

    def __init__(self, parent=None, handler=None):
        super().__init__(x=0, y=0, size=280, name="属性面板", parent=parent, handler=handler)
        self._filling = False
        self._setup_widgets()

    def _setup_widgets(self):
        self._container = QWidget()
        self._container.setFixedWidth(280)

        self._form = QFormLayout(self._container)
        self._form.setContentsMargins(12, 12, 12, 12)
        self._form.setSpacing(8)

        self._comment_edit = LineEdit()
        self._comment_edit.textChanged.connect(self._on_changed)
        self._form.addRow("描述:", self._comment_edit)

        self._key_edit = KeyCaptureButton(handler=self.handler)
        self._key_edit.on(ComponentEvent.CHANGE, lambda c: self._on_changed())
        self._form.addRow("按键:", self._key_edit.widget())

        # 摇杆专用：4方向键绑定
        self._key_up_edit = KeyCaptureButton(handler=self.handler)
        self._key_up_edit.on(ComponentEvent.CHANGE, lambda c: self._on_changed())
        self._key_up_label = QLabel("上:")
        self._form.addRow(self._key_up_label, self._key_up_edit.widget())

        self._key_down_edit = KeyCaptureButton(handler=self.handler)
        self._key_down_edit.on(ComponentEvent.CHANGE, lambda c: self._on_changed())
        self._key_down_label = QLabel("下:")
        self._form.addRow(self._key_down_label, self._key_down_edit.widget())

        self._key_left_edit = KeyCaptureButton(handler=self.handler)
        self._key_left_edit.on(ComponentEvent.CHANGE, lambda c: self._on_changed())
        self._key_left_label = QLabel("左:")
        self._form.addRow(self._key_left_label, self._key_left_edit.widget())

        self._key_right_edit = KeyCaptureButton(handler=self.handler)
        self._key_right_edit.on(ComponentEvent.CHANGE, lambda c: self._on_changed())
        self._key_right_label = QLabel("右:")
        self._form.addRow(self._key_right_label, self._key_right_edit.widget())

        self._type_combo = ComboBox()
        self._type_combo.addItems(["CLICK", "HOLD", "JOYSTICK", "EYES", "RADIAL"])
        self._type_combo.currentTextChanged.connect(self._on_type_changed)
        self._form.addRow("类型:", self._type_combo)

        self._pos_x_slider = Slider(Qt.Horizontal)
        self._pos_x_slider.setRange(0, 10000)
        self._pos_x_slider.valueChanged.connect(self._on_slider_changed)
        self._pos_x_label = QLabel("0.0000")
        self._form.addRow("X 比例:", self._pos_x_slider)
        self._form.addRow("", self._pos_x_label)

        self._pos_y_slider = Slider(Qt.Horizontal)
        self._pos_y_slider.setRange(0, 10000)
        self._pos_y_slider.valueChanged.connect(self._on_slider_changed)
        self._pos_y_label = QLabel("0.0000")
        self._form.addRow("Y 比例:", self._pos_y_slider)
        self._form.addRow("", self._pos_y_label)

        self._scale_slider = Slider(Qt.Horizontal)
        self._scale_slider.setRange(190, 2500)
        self._scale_slider.valueChanged.connect(self._on_slider_changed)
        self._scale_label = QLabel("0.0000")
        self._form.addRow("大小:", self._scale_slider)
        self._form.addRow("", self._scale_label)

        self._turbo_key_edit = KeyCaptureButton(handler=self.handler)
        self._turbo_key_edit.on(ComponentEvent.CHANGE, lambda c: self._on_changed())
        self._turbo_key_label = QLabel("Turbo键:")
        self._form.addRow(self._turbo_key_label, self._turbo_key_edit.widget())

        self._turbo_offset_slider = Slider(Qt.Horizontal)
        self._turbo_offset_slider.setRange(0, 20000)
        self._turbo_offset_slider.valueChanged.connect(self._on_slider_changed)
        self._turbo_offset_label = QLabel("0.0000")
        self._turbo_offset_title = QLabel("Turbo偏移:")
        self._form.addRow(self._turbo_offset_title, self._turbo_offset_slider)
        self._form.addRow("", self._turbo_offset_label)

        self._creep_key_edit = KeyCaptureButton(handler=self.handler)
        self._creep_key_edit.on(ComponentEvent.CHANGE, lambda c: self._on_changed())
        self._creep_key_label = QLabel("Creep键:")
        self._form.addRow(self._creep_key_label, self._creep_key_edit.widget())

        self._creep_offset_slider = Slider(Qt.Horizontal)
        self._creep_offset_slider.setRange(0, 10000)
        self._creep_offset_slider.valueChanged.connect(self._on_slider_changed)
        self._creep_offset_label = QLabel("0.0000")
        self._creep_offset_title = QLabel("Creep偏移:")
        self._form.addRow(self._creep_offset_title, self._creep_offset_slider)
        self._form.addRow("", self._creep_offset_label)

        self._hint_label = QLabel("点击画布中的控件进行编辑")
        self._form.addRow(self._hint_label)

        self._current_data = None
        self._set_joystick_visible(False)

    def _set_joystick_visible(self, visible: bool):
        # 单键 ↔ 4方向键 切换
        self._key_edit.widget().setVisible(not visible)
        for w in [
            self._key_up_label, self._key_up_edit.widget(),
            self._key_down_label, self._key_down_edit.widget(),
            self._key_left_label, self._key_left_edit.widget(),
            self._key_right_label, self._key_right_edit.widget(),
        ]:
            w.setVisible(visible)
        # turbo / creep 摇杆专属
        for w in [
            self._turbo_key_label, self._turbo_key_edit.widget(),
            self._turbo_offset_title, self._turbo_offset_slider, self._turbo_offset_label,
            self._creep_key_label, self._creep_key_edit.widget(),
            self._creep_offset_title, self._creep_offset_slider, self._creep_offset_label,
        ]:
            w.setVisible(visible)

    def widget(self) -> QWidget:
        return self._container

    def fill_from_data(self, data):
        self._filling = True
        self._current_data = data
        if data is None:
            self._hint_label.setText("点击画布中的控件进行编辑")
            self._comment_edit.setText("")
            self._key_edit.set_raw_key("")
            for e in [self._key_up_edit, self._key_down_edit,
                       self._key_left_edit, self._key_right_edit]:
                e.set_raw_key("")
            self._pos_x_slider.setValue(0)
            self._pos_x_label.setText("0.0000")
            self._pos_y_slider.setValue(0)
            self._pos_y_label.setText("0.0000")
            self._scale_slider.setValue(0)
            self._scale_label.setText("0.0000")
            self._set_joystick_visible(False)
        else:
            self._hint_label.setText(f"当前控件: {data.comment or data.key}")
            self._comment_edit.setText(data.comment)
            is_joystick = data.widget_type == WidgetType.JOYSTICK
            self._set_joystick_visible(is_joystick)
            if is_joystick:
                keys = self._split_keys(data.key)
                self._key_up_edit.set_raw_key(keys[0])
                self._key_down_edit.set_raw_key(keys[1])
                self._key_left_edit.set_raw_key(keys[2])
                self._key_right_edit.set_raw_key(keys[3])
            else:
                self._key_edit.set_raw_key(data.key)
            self._type_combo.setCurrentText(data.widget_type.name)
            self._pos_x_slider.setValue(int(data.pos_x * 10000))
            self._pos_x_label.setText(f"{data.pos_x:.4f}")
            self._pos_y_slider.setValue(int(data.pos_y * 10000))
            self._pos_y_label.setText(f"{data.pos_y:.4f}")
            self._scale_slider.setValue(int(data.scale_size * 10000))
            self._scale_label.setText(f"{data.scale_size:.4f}")
            if is_joystick:
                self._turbo_key_edit.set_raw_key(data.turbo_key)
                self._turbo_offset_slider.setValue(int(data.turbo_offset * 10000))
                self._turbo_offset_label.setText(f"{data.turbo_offset:.4f}")
                self._creep_key_edit.set_raw_key(data.creep_key)
                self._creep_offset_slider.setValue(int(data.creep_offset * 10000))
                self._creep_offset_label.setText(f"{data.creep_offset:.4f}")
        self._filling = False

    def collect_data(self) -> dict:
        is_joystick = self._current_data.widget_type == WidgetType.JOYSTICK if self._current_data else False
        if is_joystick:
            key = "|".join([
                self._key_up_edit.raw_key,
                self._key_down_edit.raw_key,
                self._key_left_edit.raw_key,
                self._key_right_edit.raw_key,
            ])
        else:
            key = self._key_edit.raw_key
        result = {
            "comment": self._comment_edit.text(),
            "key": key,
            "widget_type": self._type_combo.currentText(),
            "pos_x": self._pos_x_slider.value() / 10000.0,
            "pos_y": self._pos_y_slider.value() / 10000.0,
            "scale_size": self._scale_slider.value() / 10000.0,
        }
        if is_joystick:
            result["turbo_key"] = self._turbo_key_edit.raw_key
            result["turbo_offset"] = self._turbo_offset_slider.value() / 10000.0
            result["creep_key"] = self._creep_key_edit.raw_key
            result["creep_offset"] = self._creep_offset_slider.value() / 10000.0
        return result

    @staticmethod
    def _split_keys(raw: str):
        """将 "Key_W|Key_S|Key_A|Key_D" 拆为 ["W","S","A","D"]，自适应补全4个空位"""
        parts = raw.split("|") if raw else ["", "", "", ""]
        while len(parts) < 4:
            parts.append("")
        return [p[4:] if p.startswith("Key_") else p for p in parts[:4]]

    def _on_type_changed(self, _text):
        if not self._filling:
            self._dispatch(ComponentEvent.CHANGE)

    def _on_changed(self):
        if self._filling:
            return
        self._dispatch(ComponentEvent.CHANGE)

    def _on_slider_changed(self, _value):
        if self._filling:
            return
        self._pos_x_label.setText(f"{self._pos_x_slider.value() / 10000.0:.4f}")
        self._pos_y_label.setText(f"{self._pos_y_slider.value() / 10000.0:.4f}")
        self._scale_label.setText(f"{self._scale_slider.value() / 10000.0:.4f}")
        if self._current_data and self._current_data.widget_type == WidgetType.JOYSTICK:
            self._turbo_offset_label.setText(f"{self._turbo_offset_slider.value() / 10000.0:.4f}")
            self._creep_offset_label.setText(f"{self._creep_offset_slider.value() / 10000.0:.4f}")
        self._dispatch(ComponentEvent.CHANGE)

    def _dispatch(self, event: ComponentEvent, *args):
        if self.handler:
            self.handler.dispatch(self, event, *args)