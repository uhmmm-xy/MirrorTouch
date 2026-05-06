import os

# 1. 用更底层的方式忽略警告（必须放在所有PyQt导入之前）
os.environ["QT_FLUENT_WIDGETS_NO_PRO_TIP"] = "1"
os.environ["QT_FLUENT_WIDGETS_DISABLE_PRO_TIP"] = "1"

import sys
import warnings
warnings.filterwarnings("ignore")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCursor
from qfluentwidgets import FluentWindow, NavigationItemPosition
from src.ui.mirror_page import MirrorPage
from src.ui.serial_page import SerialPage
from src.ui.settings_page import SettingsPage
from src.ui.touch_page import TouchPage
from src.ui.tools.qss_debugger import QssDebugger


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
            self.mirror_page.set_locked(True)
            print("[MirrorTouch] 鼠标已锁定到窗口中心")
        else:
            self._lock_timer.stop()
            self.mirror_page.setCursor(Qt.ArrowCursor)
            self._lock_center = None
            self.mirror_page.set_locked(False)
            print("[MirrorTouch] 鼠标已解锁")

    def _force_mouse_center(self):
        if self.mouse_locked and self._lock_center:
            QCursor.setPos(self._lock_center)

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.AltModifier and event.key() == Qt.Key_QuoteLeft:
            self.toggle_mouse_lock()
        super().keyPressEvent(event)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F12:
            dlg = QssDebugger(self)
            dlg.exec_()
        else:
            super().keyPressEvent(event)


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