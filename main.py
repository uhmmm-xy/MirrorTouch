import os

# 1. 用更底层的方式忽略警告（必须放在所有PyQt导入之前）
os.environ["QT_FLUENT_WIDGETS_NO_PRO_TIP"] = "1"
os.environ["QT_FLUENT_WIDGETS_DISABLE_PRO_TIP"] = "1"

import sys
import warnings
warnings.filterwarnings("ignore")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer, QObject, QEvent
from PyQt5.QtGui import QCursor
from qfluentwidgets import FluentWindow, NavigationItemPosition
from src.ui.mirror_page import MirrorPage
from src.ui.serial_page import SerialPage
from src.ui.settings_page import SettingsPage
from src.ui.touch_page import TouchPage
from src.ui.tools.qss_debugger import QssDebugger
from src.core.world_instance.world_bootstrap import init_world, shutdown_world
import esper
from src.utils.logger import log


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MirrorTouch - 镜触")
        self.resize(1280, 720)

        # 2. 暂时把“锁定窗口”相关功能放在一边，先确保窗口能稳定启动
        self.mouse_locked = False
        self._lock_center = None

        self.mirror_page = MirrorPage()
        self.serial_page = SerialPage()
        self.touch_page = TouchPage()
        self.settings_page = SettingsPage()

        self.addSubInterface(self.mirror_page, "mirror", "投屏")
        self.addSubInterface(self.serial_page, "serial", "串口")
        self.addSubInterface(self.touch_page, "touch", "触控")
        self.addSubInterface(self.settings_page, "settings", "设置", position=NavigationItemPosition.BOTTOM)

        # 初始化 ESC World
        init_world()

        self._lock_timer = QTimer(self)
        self._lock_timer.timeout.connect(self._force_mouse_center)
        self._lock_timer.setInterval(10)

    def toggle_mouse_lock(self):
        self.mouse_locked = not self.mouse_locked
        if self.mouse_locked:
            self._lock_center = self.mirror_page.mapToGlobal(
                self.mirror_page.rect().center()
            )
            QCursor.setPos(self._lock_center)
            self.mirror_page.setCursor(Qt.BlankCursor)
            self._lock_timer.start()
            log.info("[MirrorTouch] 鼠标已锁定")
        else:
            self._lock_timer.stop()
            self.mirror_page.setCursor(Qt.ArrowCursor)
            self._lock_center = None
            log.info("[MirrorTouch] 鼠标已解锁")

    def _force_mouse_center(self):
        if self.mouse_locked and self._lock_center:
            QCursor.setPos(self._lock_center)

    def closeEvent(self, event):
        """安全退出：停止 Session → 停止服务 → 关闭 World"""
        esper.dispatch_event("stream.stop.force")
        shutdown_world()
        event.accept()

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.AltModifier and event.key() == Qt.Key_QuoteLeft:
            self.toggle_mouse_lock()
        elif event.key() == Qt.Key_F12:
            dlg = QssDebugger(self)
            dlg.exec_()
        else:
            # 投屏页热键 → 触控
            # self._forward_to_mirror(event)
            super().keyPressEvent(event)

    def _forward_to_mirror(self, event):
        if self.stackedWidget.currentWidget() is not self.mirror_page:
            return
        ek = self.mirror_page._eyes_key
        t = event.text()
        if t and t == ek:
            if self.mirror_page._touch_active:
                self.mirror_page._deactivate_touch()
            else:
                self.mirror_page._activate_touch()


if __name__ == "__main__":
    # 3. 关键：加一个异常捕获，防止程序因未知错误直接退出
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"程序启动异常: {e}")
        import traceback
        traceback.print_exc()