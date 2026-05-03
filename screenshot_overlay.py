"""全屏半透明叠加层 + 区域截图"""

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QCursor


class ScreenshotOverlay(QWidget):
    """全屏半透明截图叠加层，拖选区域截图"""

    screenshot_taken = Signal(QPixmap)
    cancelled = Signal()

    def __init__(self):
        super().__init__()
        self._start = QPoint()
        self._end = QPoint()
        self._selecting = False
        self._full_screenshot = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)

    def start(self):
        """捕获全屏截图并显示叠加层（支持多显示器）"""
        screen = QApplication.screenAt(QCursor.pos())
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            screen = QApplication.screens()[0]
        self._full_screenshot = screen.grabWindow(0)
        self.setGeometry(screen.geometry())
        self.showFullScreen()

    def paintEvent(self, event):
        if self._full_screenshot is None:
            return

        p = QPainter(self)
        # 绘制变暗的全屏截图
        p.drawPixmap(self.rect(), self._full_screenshot)

        # 半透明遮罩
        mask_color = QColor(0, 0, 0, 140)
        p.fillRect(self.rect(), mask_color)

        if self._selecting and self._start != self._end:
            r = self._selection_rect()
            # 挖空选区：显示原始截图
            p.drawPixmap(r, self._full_screenshot, r)
            # 选区边框
            p.setPen(QPen(QColor(30, 144, 255), 2))
            p.drawRect(r)

    def _selection_rect(self):
        return QRect(
            min(self._start.x(), self._end.x()),
            min(self._start.y(), self._end.y()),
            abs(self._end.x() - self._start.x()),
            abs(self._end.y() - self._start.y()),
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.position().toPoint()
            self._end = self._start
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._selecting = False
            self._end = event.position().toPoint()
            r = self._selection_rect()
            self.hide()
            if r.width() > 10 and r.height() > 10 and self._full_screenshot:
                cropped = self._full_screenshot.copy(r)
                self.screenshot_taken.emit(cropped)
            else:
                self.cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.cancelled.emit()
