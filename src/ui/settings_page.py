"""SettingsPage — qfluentwidgets 风格"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QFileDialog)
from qfluentwidgets import (ComboBox, LineEdit, PushButton as QFPushButton,
                             CardWidget, FluentIcon, BodyLabel, StrongBodyLabel,
                             SwitchButton)
from src.core.config_manager import load_config, save_config
from src.utils.logger import log

SIZES = [720, 1080, 1440, 2160]
FPS_VALUES = [30, 60, 90, 120, 144, 240]


def _detect_serial_ports() -> list[str]:
    try:
        import serial.tools.list_ports
        return [p.device for p in serial.tools.list_ports.comports()]
    except Exception:
        return []


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("settingsPage")
        self._config = load_config()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # === 视频捕获 ===
        layout.addWidget(StrongBodyLabel("视频捕获"))
        layout.addWidget(BodyLabel("传递给手机端的编码参数"))
        cap = CardWidget()
        cf = QVBoxLayout(cap)
        cf.setContentsMargins(20, 16, 20, 16)
        cf.setSpacing(10)
        self.cap_size = self._combo(cf, "分辨率", SIZES, str(self._config.scrcpy_max_size))
        self.cap_fps = self._combo(cf, "捕获帧率", FPS_VALUES, str(self._config.scrcpy_max_fps))
        self.bitrate = self._edit(cf, "码率 kbps", str(self._config.scrcpy_bit_rate))
        layout.addWidget(cap)

        # === 渲染输出 ===
        layout.addWidget(StrongBodyLabel("渲染输出"))
        layout.addWidget(BodyLabel("本机画面刷新率"))
        rdr = CardWidget()
        rf = QVBoxLayout(rdr)
        rf.setContentsMargins(20, 16, 20, 16)
        rf.setSpacing(10)
        self.render_fps = self._combo(rf, "渲染帧率", FPS_VALUES, str(self._config.render_max_fps))
        layout.addWidget(rdr)

        # === 触控映射 ===
        layout.addWidget(StrongBodyLabel("触控映射"))
        mp = CardWidget()
        mf = QVBoxLayout(mp)
        mf.setContentsMargins(20, 16, 20, 16)
        mf.setSpacing(10)
        self.mapping_path = self._edit(mf, "映射文件路径", self._config.mapping_path)
        row = QHBoxLayout()
        btn = QFPushButton(FluentIcon.FOLDER, "浏览")
        btn.clicked.connect(self._on_browse_mapping)
        row.addStretch()
        row.addWidget(btn)
        apply_btn = QFPushButton(FluentIcon.ACCEPT, "应用")
        apply_btn.clicked.connect(self._on_apply_mapping)
        row.addWidget(apply_btn)
        mf.addLayout(row)

        # 串口
        ports = _detect_serial_ports()
        if not ports:
            ports = ["COM1", "COM2", "COM3"]
        self.serial_port = self._combo(mf, "COM 端口", ports, self._config.serial_port or ports[0])
        bauds = ["9600","19200","38400","57600","115200","230400","460800","921600"]
        self.baud = self._combo(mf, "波特率", bauds, str(self._config.serial_baud))
        layout.addWidget(mp)

        # === 日志 ===
        layout.addWidget(StrongBodyLabel("日志与服务"))
        lg = CardWidget()
        lf = QVBoxLayout(lg)
        lf.setContentsMargins(20, 16, 20, 16)
        lf.setSpacing(10)
        self.sw_log = SwitchButton(); self.sw_log.setChecked(self._config.log_middleware_stdout)
        lf.addWidget(_row("记录中间件输出", self.sw_log))
        self.sw_keep = SwitchButton(); self.sw_keep.setChecked(self._config.keep_service_alive)
        lf.addWidget(_row("常驻服务", self.sw_keep))
        layout.addWidget(lg)
        layout.addStretch()

        row = QHBoxLayout(); row.addStretch()
        self.btn = QFPushButton(FluentIcon.SAVE, "保存配置")
        self.btn.clicked.connect(self._on_save)
        row.addWidget(self.btn); layout.addLayout(row)

    def _on_browse_mapping(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择映射文件", "", "JSON (*.json)")
        if path:
            self.mapping_path.setText(path)

    def _on_apply_mapping(self):
        """应用映射：加载 JSON → 提取 eyes key → 保存到 config"""
        import json, esper
        path = self.mapping_path.text().strip()
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            widgets = data.get("widgets", [])
            eyes_key = ""
            for w in widgets:
                if w.get("widget_type") == "eyes":
                    eyes_key = w.get("key", "")
                    break
            self._config.mapping_path = path
            save_config(self._config)
            log.info(f"[Settings] 映射已应用: {path} eyes_key={eyes_key}")
        except Exception as e:
            log.error(f"[Settings] 映射应用失败: {e}")

    def _on_save(self):
        c = self._config
        c.scrcpy_max_size = int(self.cap_size.currentText())
        c.scrcpy_max_fps = int(self.cap_fps.currentText())
        c.scrcpy_bit_rate = self.bitrate.text().strip()
        c.render_max_fps = int(self.render_fps.currentText())
        c.mapping_path = self.mapping_path.text().strip()
        c.serial_port = self.serial_port.currentText()
        try:
            c.serial_baud = int(self.baud.currentText())
        except ValueError:
            c.serial_baud = 115200
        c.log_middleware_stdout = self.sw_log.isChecked()
        c.keep_service_alive = self.sw_keep.isChecked()
        save_config(self._config)
        log.info(f"[Settings] 已保存")

    def _combo(self, parent, label, items, cur):
        w = ComboBox(); w.addItems([str(i) for i in items])
        if cur in [str(i) for i in items]: w.setCurrentText(cur)
        w.setFixedWidth(120)
        parent.addWidget(_row(label, w))
        return w

    def _edit(self, parent, label, txt):
        w = LineEdit(); w.setText(txt); w.setFixedWidth(200)
        parent.addWidget(_row(label, w))
        return w


def _row(label: str, widget) -> QWidget:
    from PyQt5.QtWidgets import QWidget, QHBoxLayout
    w = QWidget()
    r = QHBoxLayout(w)
    r.setContentsMargins(0, 0, 0, 0)
    lb = BodyLabel(label); lb.setFixedWidth(150)
    r.addWidget(lb)
    r.addWidget(widget)
    r.addStretch()
    return w
