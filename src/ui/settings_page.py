"""SettingsPage — qfluentwidgets 风格"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QFileDialog)
from PyQt5.QtCore import QThread, pyqtSignal
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
        self.bitrate = self._edit(cf, "码率 Mbps", str(int(self._config.scrcpy_bit_rate) // 1000))
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

        # === 设备信息 ===
        layout.addWidget(StrongBodyLabel("设备信息"))
        dev = CardWidget()
        df = QVBoxLayout(dev)
        df.setContentsMargins(20, 16, 20, 16)
        df.setSpacing(10)

        dev_row = QHBoxLayout()
        self.btn_fetch_device = QFPushButton(FluentIcon.WIFI, "获取设备信息")
        self.btn_fetch_device.clicked.connect(self._on_fetch_device)
        dev_row.addWidget(self.btn_fetch_device)
        self.lbl_device_status = BodyLabel("未获取")
        self.lbl_device_status.setStyleSheet("color: #888; font-size: 13px;")
        dev_row.addWidget(self.lbl_device_status)
        dev_row.addStretch()
        df.addLayout(dev_row)
        # SS 触控消费频率
        freq_vals = ["200","400","600","800","1000"]
        self.touch_freq = self._combo(df, "触控消费频率 Hz", freq_vals, str(self._config.touch_consume_freq))
        layout.addWidget(dev)

        # === 触控映射 ===
        layout.addWidget(StrongBodyLabel("触控映射"))
        mp = CardWidget()
        mf = QVBoxLayout(mp)
        mf.setContentsMargins(20, 16, 20, 16)
        mf.setSpacing(10)
        self.mapping_path = LineEdit(); self.mapping_path.setText(self._config.mapping_path)
        self.mapping_path.setFixedWidth(200)
        row = QHBoxLayout()
        row.addWidget(BodyLabel("映射文件路径"))
        row.addWidget(self.mapping_path)
        btn = QFPushButton(FluentIcon.FOLDER, "浏览")
        btn.clicked.connect(self._on_browse_mapping)
        row.addWidget(btn)
        apply_btn = QFPushButton(FluentIcon.ACCEPT, "应用")
        apply_btn.clicked.connect(self._on_apply_mapping)
        row.addWidget(apply_btn)
        row.addStretch()
        mf.addLayout(row)

        # COM 端口 + 波特率
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

    def _on_fetch_device(self):
        """后台线程获取 ADB 设备宽高/旋转角度 → 写入 DeviceComponent"""
        import esper
        from src.core.world_instance.world_bootstrap import get_device_meta_entity
        from src.core.world_instance.components.device_component import DeviceComponent

        ent = get_device_meta_entity()
        if ent == 0 or not esper.entity_exists(ent):
            log.error("[Settings] 设备元数据实体不存在")
            return

        self.btn_fetch_device.setEnabled(False)
        self.lbl_device_status.setText("查询中…")
        self.lbl_device_status.setStyleSheet("color: #f0a040; font-size: 13px;")

        cfg = load_config()
        adb_path = cfg.adb_path
        # 尝试从 DeviceConfig 获取当前 serial
        serial = ""
        try:
            from src.core.world_instance.world_bootstrap import get_current_device
            from src.core.world_instance.components.device_config import DeviceConfig as DevCfgComp
            dev_ent = get_current_device()
            if dev_ent and esper.entity_exists(dev_ent):
                dc = esper.component_for_entity(dev_ent, DevCfgComp)
                serial = dc.serial
        except Exception:
            pass

        self._fetch_thread = _FetchDeviceThread(adb_path, serial, ent)
        self._fetch_thread.finished.connect(self._on_fetch_finished)
        self._fetch_thread.start()

    def _on_fetch_finished(self, result: dict):
        """ADB 查询完成 → 写入 DeviceComponent"""
        import esper
        from src.core.world_instance.components.device_component import DeviceComponent

        self.btn_fetch_device.setEnabled(True)

        ent = result.get("entity", 0)
        if not ent or not esper.entity_exists(ent):
            return

        w = result.get("width", 0)
        h = result.get("height", 0)
        rotation = result.get("rotation", 0)
        serial = result.get("serial", "")
        error = result.get("error", "")

        if error:
            self.lbl_device_status.setText(f"失败: {error}")
            self.lbl_device_status.setStyleSheet("color: #e74c3c; font-size: 13px;")
            return

        dc = esper.component_for_entity(ent, DeviceComponent)
        dc.base_w = w
        dc.base_h = h
        dc.current_rotation = rotation
        dc.adb_serial = serial

        # 自动绑定：从配置中取当前 COM 端口
        dc.bound_com_port = self._config.serial_port or ""

        self.lbl_device_status.setText(f"{w}x{h} @{rotation}°")
        self.lbl_device_status.setStyleSheet("color: #4caf50; font-size: 13px;")
        log.info(f"[Settings] 设备信息已更新: {w}x{h} rot={rotation} serial={serial}")

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
        c.scrcpy_bit_rate = str(int(float(self.bitrate.text().strip()) * 1000))
        c.render_max_fps = int(self.render_fps.currentText())
        c.mapping_path = self.mapping_path.text().strip()
        c.serial_port = self.serial_port.currentText()
        try:
            c.serial_baud = int(self.baud.currentText())
        except ValueError:
            c.serial_baud = 115200
        try:
            c.touch_consume_freq = int(self.touch_freq.currentText())
        except ValueError:
            c.touch_consume_freq = 800
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


class _FetchDeviceThread(QThread):
    """后台线程：执行 ADB 查询，不阻塞 Qt 主事件循环"""
    finished = pyqtSignal(dict)

    def __init__(self, adb_path: str, serial: str, entity: int):
        super().__init__()
        self._adb = adb_path
        self._serial = serial
        self._entity = entity

    def run(self):
        result = {"entity": self._entity, "serial": self._serial}
        try:
            from src.core.world_instance.handlers.adb_handler import get_screen_size, query_rotation
            w, h = get_screen_size(self._adb, self._serial)
            rotation = query_rotation(self._adb, self._serial)
            result["width"] = w
            result["height"] = h
            result["rotation"] = rotation
        except Exception as e:
            result["error"] = str(e)
        self.finished.emit(result)


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
