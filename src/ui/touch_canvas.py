"""TouchCanvas — 投屏画布组件（三区域布局）

┌─────────────────────────────┐
│  Header (48px)  [+添加] [撤销]│  ← Handler 绘制按钮
├─────────────────────────────┤
│  Content                    │  ← Screen 适配区域
│  (screen_rect)              │
├─────────────────────────────┤
│  Footer (72px)  删除区域     │  ← DeleteHandler 绘制
└─────────────────────────────┘
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QFont, QMouseEvent, QResizeEvent


class TouchCanvas(QWidget):
    """投屏画布 —— View 层纯绘制 + 事件转发"""

    HEADER_H = 48
    FOOTER_H = 72

    def __init__(self, page: "TouchPage"):
        super().__init__()
        self._page = page
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: #1a1a1a; border-radius: 8px;")
        page.screen.set_canvas(self)

    def resizeEvent(self, event: QResizeEvent):
        """尺寸变化 → 同步删除区域 + Screen 布局"""
        super().resizeEvent(event)
        for h in self._page.screen._handlers:
            if hasattr(h, 'update_zone'):
                h.update_zone(self.width(), self.height())

    # ── 绘制 ──

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(26, 26, 26))

        # ── Header 区背景 ──
        screen = self._page.screen
        header_rect = self.rect().adjusted(0, 0, 0, -(self.height() - self.HEADER_H))
        painter.fillRect(header_rect, QColor(32, 32, 32))

        # ── Content 区：投屏帧 → 背景图 → Screen ──
        bg = self._page.background_pixmap
        live = self._page.live_pixmap
        rect = screen.screen_rect
        rx, ry, rw, rh = int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height())

        if live and not live.isNull():
            painter.drawPixmap(rx, ry, rw, rh, live)
        elif bg and not bg.isNull():
            painter.drawPixmap(rx, ry, rw, rh, bg)

        if not screen.keymap_data and (not bg or bg.isNull()) and (not live or live.isNull()):
            painter.setPen(QColor(120, 120, 120))
            font = QFont("Microsoft YaHei", 14)
            painter.setFont(font)
            painter.drawText(
                self.rect(), Qt.AlignCenter,
                "请点击上方按钮加载映射文件或导入背景图片"
            )

        # 绘制 Screen
        screen.draw(painter)

        # 绘制各 Handler 覆盖层（按钮、删除区域等）
        for handler in screen.handlers:
            handler.draw_overlay(painter, screen)

        painter.end()

    # ── 鼠标事件 → 转发给 Handler 链 ──

    def mousePressEvent(self, event: QMouseEvent):
        print(f"Mouse press at {event.pos().x()},{event.pos().y()}")  # 调试输出
        screen = self._page.screen
        screen.process_mouse_press(event.pos(), event.button())

        w = screen.selected_widget
        self._page.property_panel.fill_from_data(
            w.data if w else None
        )
        self._update_export_btn()
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        print(f"Mouse move at {event.pos().x()},{event.pos().y()}")  # 调试输出
        screen = self._page.screen
        if screen.test_mode:
            screen.handle_test_mouse_move()
        else:
            screen.process_mouse_move(event.pos())

        w = screen.selected_widget
        if w and w.data:
            self._page.property_panel.fill_from_data(w.data)

        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        print(f"Mouse release at {event.pos().x()},{event.pos().y()}")  # 调试输出
        screen = self._page.screen
        screen.process_mouse_release(event.pos(), event.button())

        w = screen.selected_widget
        if w and w.data:
            self._page.property_panel.fill_from_data(w.data)

        self._update_export_btn()
        self.update()

    def _update_export_btn(self):
        """有控件就启用导出按钮"""
        has_widgets = len(self._page.screen.children) > 0
        self._page.btn_export.setEnabled(has_widgets)
