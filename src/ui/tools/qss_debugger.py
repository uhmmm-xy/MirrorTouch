import re
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QComboBox, QLabel, QSplitter, QTreeWidget, QTreeWidgetItem, QApplication, QWidget,
)
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont


class QssHighlighter(QSyntaxHighlighter):
    """QSS 语法高亮"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []

        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#d55fde"))
        fmt.setFontWeight(QFont.Bold)
        self._rules.append((QRegExp(r"[#.]?\w+[\s,{]+"), fmt))

        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#6ea8fe"))
        self._rules.append((QRegExp(r"[\w-]+(?=\s*:)"), fmt))

        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#f1a845"))
        self._rules.append((QRegExp(r"#[0-9a-fA-F]{3,8}|\d+(?:px|em|%)?"), fmt))

        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#98c379"))
        self._rules.append((QRegExp(r'"[^"]*"'), fmt))

        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#6c757d"))
        fmt.setFontItalic(True)
        self._rules.append((QRegExp(r"/\*.*\*/"), fmt))

        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#adb5bd"))
        fmt.setFontWeight(QFont.Bold)
        self._rules.append((QRegExp(r"[{}]"), fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, fmt)
                index = expression.indexIn(text, index + length)


class QssDebugger(QDialog):
    """浏览器风格 QSS 调试器 + 控件树"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QSS 调试器")
        self.resize(900, 600)
        self.setStyleSheet("""
            QDialog { background: #1e1e1e; color: #ddd; }
            QLabel { color: #aaa; font-size: 12px; }
            QComboBox { background: #2a2a2a; color: #eee; border: 1px solid #555;
                border-radius: 4px; padding: 3px 8px; font-size: 12px; }
            QPushButton { background: #0d6efd; color: #fff; border: none;
                border-radius: 4px; padding: 5px 16px; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background: #0b5ed7; }
            QTextEdit { background: #252526; color: #d4d4d4; border: 1px solid #3c3c3c;
                border-radius: 4px; font-family: "Consolas", monospace; font-size: 13px; }
            QTreeWidget { background: #252526; color: #d4d4d4; border: 1px solid #3c3c3c;
                border-radius: 4px; font-size: 12px; }
            QTreeWidget::item:hover { background: #2a2d2e; }
            QTreeWidget::item:selected { background: #094771; }
        """)

        self._app = QApplication.instance()
        self._original_qss = self._app.styleSheet()

        layout = QVBoxLayout(self)

        # 工具栏
        toolbar = QHBoxLayout()
        self._selector_combo = QComboBox()
        self._selector_combo.setEditable(True)
        self._selector_combo.setMinimumWidth(200)
        self._selector_combo.setPlaceholderText("输入选择器...")
        toolbar.addWidget(QLabel("选择器:"))
        toolbar.addWidget(self._selector_combo)
        toolbar.addStretch()

        self._apply_btn = QPushButton("应用 (Ctrl+S)")
        self._apply_btn.clicked.connect(self._apply)
        toolbar.addWidget(self._apply_btn)

        self._reset_btn = QPushButton("重置")
        self._reset_btn.clicked.connect(self._reset)
        toolbar.addWidget(self._reset_btn)

        layout.addLayout(toolbar)

        # 左右分栏：控件树 | 编辑器
        splitter = QSplitter(Qt.Horizontal)

        # 控件树
        self._tree = QTreeWidget()
        self._tree.setHeaderLabel("控件树 (类名#objectName)")
        self._tree.itemClicked.connect(self._on_tree_item_clicked)
        self._populate_tree()
        splitter.addWidget(self._tree)

        # 编辑器
        self._editor = QTextEdit()
        self._editor.setPlainText(self._original_qss)
        self._editor.setTabStopWidth(20)
        self._highlighter = QssHighlighter(self._editor.document())
        splitter.addWidget(self._editor)

        splitter.setSizes([300, 600])
        layout.addWidget(splitter)

        self._populate_selectors()

        self._editor.keyPressEvent = self._editor_key_press

    def _editor_key_press(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_S:
            self._apply()
        else:
            QTextEdit.keyPressEvent(self._editor, event)

    def _populate_tree(self, widget=None, parent_item=None):
        """递归构建控件树"""
        if widget is None:
            widget = self._app.activeWindow() or self.parent() or self
        cls = type(widget).__name__
        obj_name = widget.objectName()
        text = f"{cls}"
        if obj_name:
            text += f"  #{obj_name}"
        item = QTreeWidgetItem(parent_item or self._tree, [text])
        item.setData(0, Qt.UserRole, widget)

        if parent_item is None:
            self._tree.addTopLevelItem(item)

        for child in widget.children():
            if isinstance(child, QWidget):
                self._populate_tree(child, item)

    def _on_tree_item_clicked(self, item, column):
        widget = item.data(0, Qt.UserRole)
        if widget is None:
            return
        obj_name = widget.objectName()
        cls = type(widget).__name__

        selectors = []
        if obj_name:
            selectors.append(f"#{obj_name}")
        selectors.append(cls)

        selector = ", ".join(selectors)
        self._selector_combo.setCurrentText(selector)

        # 显示当前样式
        current_qss = widget.styleSheet()
        if current_qss:
            self._editor.setPlainText(current_qss)
        else:
            self._editor.setPlainText(f"/* 控件 {selector} 无内联样式 */\n\n{self._app.styleSheet()}")

        # 高亮控件：设置临时红色边框
        self._clear_highlight()
        widget.setProperty("__debug_highlight", widget.styleSheet())
        widget.setStyleSheet(widget.styleSheet() + f"\n{cls}#{obj_name} {{ border: 2px solid #ff4444 !important; }}")

    def _clear_highlight(self):
        for widget in self._app.allWidgets():
            orig = widget.property("__debug_highlight")
            if orig is not None:
                widget.setStyleSheet(orig)
                widget.setProperty("__debug_highlight", None)

    def _populate_selectors(self):
        seen = set()
        for widget in self._app.allWidgets():
            name = widget.objectName()
            if name and name not in seen:
                seen.add(name)
                cls = type(widget).__name__
                self._selector_combo.addItem(f"#{name}  ({cls})")
                self._selector_combo.addItem(f"{cls}#{name}")

    def _apply(self):
        qss = self._editor.toPlainText()
        self._app.setStyleSheet(qss)

    def _reset(self):
        self._clear_highlight()
        self._editor.setPlainText(self._original_qss)
        self._app.setStyleSheet(self._original_qss)

    def closeEvent(self, event):
        self._clear_highlight()
        self._reset()
        super().closeEvent(event)