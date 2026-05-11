"""MirrorPage — 投屏页面：启动/停止 + 视频帧渲染"""
import esper
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QMouseEvent, QPainter, QPixmap, QColor, QFont
from qfluentwidgets import PushButton
from src.utils.logger import log
from src.core.world_instance.world_bootstrap import get_current_session, get_current_device
from src.core.world_instance.components.latest_frame import LatestFrame
from src.core.world_instance.components.stream_session import StreamSession
from src.core.world_instance.components.frame_stats import FrameStats
from src.core.config_manager import load_config
from src.core.world_instance.components.stream_config import StreamConfig


_QT_KEY_MAP = {
    Qt.Key_A: "A", Qt.Key_B: "B", Qt.Key_C: "C", Qt.Key_D: "D", Qt.Key_E: "E",
    Qt.Key_F: "F", Qt.Key_G: "G", Qt.Key_H: "H", Qt.Key_I: "I", Qt.Key_J: "J",
    Qt.Key_K: "K", Qt.Key_L: "L", Qt.Key_M: "M", Qt.Key_N: "N", Qt.Key_O: "O",
    Qt.Key_P: "P", Qt.Key_Q: "Q", Qt.Key_R: "R", Qt.Key_S: "S", Qt.Key_T: "T",
    Qt.Key_U: "U", Qt.Key_V: "V", Qt.Key_W: "W", Qt.Key_X: "X", Qt.Key_Y: "Y",
    Qt.Key_Z: "Z",
    Qt.Key_0: "0", Qt.Key_1: "1", Qt.Key_2: "2", Qt.Key_3: "3", Qt.Key_4: "4",
    Qt.Key_5: "5", Qt.Key_6: "6", Qt.Key_7: "7", Qt.Key_8: "8", Qt.Key_9: "9",
    Qt.Key_F1: "F1", Qt.Key_F2: "F2", Qt.Key_F3: "F3", Qt.Key_F4: "F4",
    Qt.Key_Shift: "Shift", Qt.Key_Control: "Control", Qt.Key_Alt: "Alt",
    Qt.Key_Space: "Space", Qt.Key_Up: "Up", Qt.Key_Down: "Down",
    Qt.Key_Left: "Left", Qt.Key_Right: "Right",
    Qt.Key_Backslash: "Backslash", Qt.Key_Slash: "Slash",
    Qt.Key_Minus: "Minus", Qt.Key_Equal: "Equal",
    Qt.Key_BracketLeft: "BracketLeft", Qt.Key_BracketRight: "BracketRight",
    Qt.Key_Semicolon: "Semicolon", Qt.Key_Apostrophe: "Apostrophe",
    Qt.Key_Comma: "Comma", Qt.Key_Period: "Period",
    Qt.Key_QuoteLeft: "Grave", Qt.Key_Tab: "Tab",
}

def qt_key_to_str(qt_key: int) -> str:
    """将 Qt.Key_XXX 转为字符串（与 PropertyPanel raw_key 格式一致）"""
    return _QT_KEY_MAP.get(qt_key, "")


def _dispatch_touch(key_str: str, event: str, offset_x: float = 0.0, offset_y: float = 0.0):
    """转发 UI 按键事件到 KeyMappingSystem — 纯转发，不查映射

    offset_x/offset_y: 鼠标增量比例 (move)，press/release 传 (0,0)
    """
    esper.dispatch_event("touch.input", key_str, event, offset_x, offset_y)


class MirrorPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("mirrorPage")
        self.setFocusPolicy(Qt.StrongFocus)
        self._streaming = False
        self._touch_active = False
        self._render_timer = QTimer(self)
        self.setMouseTracking(True)
        self._render_timer.timeout.connect(self._render_frame)
        self._render_timer.setInterval(16)
        self._touch_count = 0
        self._setup_ui()
        # [T7] 注册触控异常事件监听
        esper.set_handler("touch.error", self._on_touch_error)

    def _load_eyes_key(self) -> str:
        cfg = load_config()
        if not cfg.mapping_path:
            return ""
        try:
            with open(cfg.mapping_path, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)
            for w in data.get("widgets", []):
                if w.get("widget_type") == "eyes":
                    return w.get("key", "")
        except Exception:
            pass
        return ""

    @property
    def _eyes_key(self):
        return self._load_eyes_key()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 工具栏
        toolbar = QHBoxLayout()
        self.btn_start = PushButton("启动投屏")
        self.btn_start.setFixedWidth(120)
        self.btn_start.clicked.connect(self._on_start)
        toolbar.addWidget(self.btn_start)

        self.btn_stop = PushButton("停止投屏")
        self.btn_stop.setFixedWidth(120)
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_stop.setEnabled(False)
        toolbar.addWidget(self.btn_stop)
        toolbar.addStretch()

        self.label_status = QLabel("就绪")
        self.label_status.setStyleSheet("color: #888; font-size: 13px;")
        toolbar.addWidget(self.label_status)
        layout.addLayout(toolbar)

        # 视频画面区域
        self.video_view = VideoView(self)
        layout.addWidget(self.video_view, 1)

    # ── 启停 ──

    def _on_start(self):
        cfg = load_config()
        sc = StreamConfig(
            max_size=cfg.scrcpy_max_size,
            max_fps=cfg.scrcpy_max_fps,
            bit_rate=cfg.scrcpy_bit_rate,
        )
        esper.dispatch_event("stream.start", sc)
        self._streaming = True
        interval = max(4, int(1000 / cfg.render_max_fps))
        self._render_timer.start(interval)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        log.info(f"[MirrorPage] 投屏 {cfg.scrcpy_max_size}p 推流{cfg.scrcpy_max_fps}fps 渲染{cfg.render_max_fps}fps")

    def _on_stop(self):
        esper.dispatch_event("stream.stop")
        self._streaming = False
        self._render_timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.video_view.update()
        log.info("[MirrorPage] 投屏已停止")

    def _activate_touch(self):
        """Eyes key 激活触控 + 鼠标锁定"""
        from src.core.world_instance.components.touch_config import TouchConfig
        cfg = load_config()
        tc = TouchConfig(port=cfg.serial_port, baudrate=cfg.serial_baud)
        esper.dispatch_event("touch.start", tc)
        self._touch_active = True
        self._lock_mouse()
        self.setFocus()
        log.info(f"[MirrorPage] 触控已激活 eyes={self._eyes_key}")

    def _deactivate_touch(self):
        esper.dispatch_event("touch.stop")
        self._touch_active = False
        self._unlock_mouse()
        log.info("[MirrorPage] 触控已停用")

    # ── [T7] 异常错误处理 ──

    def _on_touch_error(self, error_msg: str = ""):
        """[T7] 触控系统异常停机回调"""
        log.error(f"[MirrorPage] 触控异常: {error_msg}")
        self._touch_active = False
        self._unlock_mouse()
        self.label_status.setText(f"异常停机")
        self.label_status.setStyleSheet("color: #e74c3c; font-size: 13px;")
        # 弹窗提示
        QMessageBox.critical(
            self, "触控系统异常",
            f"触控服务已异常停机：\n\n{error_msg}\n\n请检查串口连接和设备状态后，重新点击[启动投屏]按钮。",
            QMessageBox.Ok
        )
        # 恢复按钮，允许手动重启
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _lock_mouse(self):
        from PyQt5.QtGui import QCursor
        self._lock_ctr = self.mapToGlobal(self.rect().center())
        self.setCursor(Qt.BlankCursor)
        self._lock_timer = QTimer(self)
        self._lock_timer.timeout.connect(lambda: QCursor.setPos(self._lock_ctr))
        self._lock_timer.start(5)

    def _unlock_mouse(self):
        self.setCursor(Qt.ArrowCursor)
        if hasattr(self, '_lock_timer'):
            self._lock_timer.stop()

    def keyPressEvent(self, event):
        t = event.text()
        if t and t == self._eyes_key:
            if not self._touch_active:
                self._activate_touch()
                _dispatch_touch(t, "press")
            else:
                _dispatch_touch(t, "up")
                self._deactivate_touch()
            return
        if self._touch_active and t:
            _dispatch_touch(t, "press")

    def keyReleaseEvent(self, event):
        t = event.text()
        if not self._touch_active or t == self._eyes_key:
            return
        if t:
            _dispatch_touch(t, "release")

    def mouseMoveEvent(self, event: QMouseEvent):
        """[MIRROR-TOUCH-EYES] 鼠标移动增量 → Eyes 触控注入"""
        
        if not self._touch_active:
            return
        vw, vh = self.width(), self.height()
        if vw <= 0 or vh <= 0:
            return
        if hasattr(self, '_frame_w') and self._frame_w > 0:
            ratio = self._frame_w / max(1, self._frame_h)
            dst_w = min(vw, int(vh * ratio))
            dst_h = min(vh, int(vw / ratio))
        else:
            dst_w, dst_h = vw, vh
        # 增量 = 鼠标位置相对窗口中心的偏移 → 比例
        cx, cy = self.rect().center().x(), self.rect().center().y()
        dx = (event.pos().x() - cx) / max(1, dst_w)
        dy = (event.pos().y() - cy) / max(1, dst_h)
        _dispatch_touch(self._eyes_key, "move", dx, dy)

    # ── 帧渲染 ──

    def _render_frame(self):
        """QTimer 回调：读取 LatestFrame → 渲染"""
        try:
            device = get_current_device()
            if device == 0 or not esper.entity_exists(device):
                return
            if not esper.has_component(device, LatestFrame):
                return
            lf = esper.component_for_entity(device, LatestFrame)
            if lf.qimage and not lf.qimage.isNull():
                self.video_view.set_frame(QPixmap.fromImage(lf.qimage))
                if not hasattr(self, '_first_frame_logged'):
                    self._first_frame_logged = True
                    log.info(f"[MirrorPage] 首帧渲染: {lf.width}x{lf.height}")

            # 状态更新
            session = get_current_session()
            if session and esper.has_component(session, StreamSession):
                ss = esper.component_for_entity(session, StreamSession)
                text = f"{ss.state}"
                if esper.has_component(device, FrameStats):
                    stats = esper.component_for_entity(device, FrameStats)
                    if stats.fps > 0:
                        text += f" | {stats.fps:.0f} fps"
                self.label_status.setText(text)
        except Exception:
            pass

    def closeEvent(self, event):
        if self._touch_active:
            self._deactivate_touch()
        if self._streaming:
            self._on_stop()
        super().closeEvent(event)


class VideoView(QLabel):
    """视频帧渲染区域"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._frame_w: int = 0
        self._frame_h: int = 0
        self.setMouseTracking(True)
        self.setMinimumSize(240, 180)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #666;
                font-size: 16px;
                border: 2px dashed #444;
                border-radius: 8px;
            }
        """)

    def set_frame(self, pixmap: QPixmap):
        # [MIRROR-TOUCH-T5] 分辨率变化检测：帧尺寸改变时触发触控系统熔断停机
        new_w, new_h = pixmap.width(), pixmap.height()
        if hasattr(self, '_frame_w') and hasattr(self, '_frame_h'):
            if (new_w != self._frame_w or new_h != self._frame_h) and self._frame_w > 0:
                from src.utils.logger import log
                log.warning(f"[MirrorPage] 分辨率变化: {self._frame_w}x{self._frame_h} → {new_w}x{new_h}，触发触控熔断")
                # 触发触控系统停机
                parent = self.parent()
                if isinstance(parent, MirrorPage) and parent._touch_active:
                    parent._deactivate_touch()
        self._pixmap = pixmap
        self._frame_w = new_w
        self._frame_h = new_h
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._pixmap and not self._pixmap.isNull():
            painter = QPainter(self)
            vw, vh = self.width(), self.height()
            if self._frame_w > 0 and self._frame_h > 0:
                ratio = self._frame_w / self._frame_h
                dst_w = min(vw, int(vh * ratio))
                dst_h = min(vh, int(vw / ratio))
            else:
                dst_w, dst_h = vw, vh
            scaled = self._pixmap.scaled(dst_w, dst_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            x = (vw - scaled.width()) // 2
            y = (vh - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()
        else:
            painter = QPainter(self)
            painter.setPen(QColor(140, 140, 140))
            font = QFont("Microsoft YaHei", 14)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "...")
            painter.end()

    def mouseMoveEvent(self, event: QMouseEvent):
        super().mouseMoveEvent(event)