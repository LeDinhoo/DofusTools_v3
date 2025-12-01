import logging
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen

logger = logging.getLogger(__name__)


class OverlayDot(QWidget):
    def __init__(self, x, y, size, color, duration):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # Clic à travers

        self.setGeometry(x - size // 2, y - size // 2, size, size)
        self.color = QColor(color)
        self.size_px = size

        self.show()
        if duration > 0:
            QTimer.singleShot(duration, self.close)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self.color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, self.size_px, self.size_px)


class OverlayZone(QWidget):
    def __init__(self, x, y, w, h, color, alpha, duration):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.setGeometry(x, y, w, h)
        col = QColor(color)
        col.setAlphaF(alpha)
        self.color = col

        self.show()
        if duration > 0:
            QTimer.singleShot(duration, self.close)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.color)
        pen = QPen(self.color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)


class OverlayScripts:
    def __init__(self):
        self.overlays = []

    def draw_dot(self, x, y, color="#00ff00", size=10, duration=2000):
        # Doit être appelé depuis le thread principal via QTimer/Signal si hors thread
        # Mais le controller gère ça via _run_on_main_thread
        ov = OverlayDot(x, y, size, color, duration)
        self.overlays.append(ov)
        # Nettoyage auto de la liste
        QTimer.singleShot(duration + 100, lambda: self.overlays.remove(ov) if ov in self.overlays else None)

    def draw_zone(self, x, y, w, h, color="red", alpha=0.3, duration=2000):
        ov = OverlayZone(x, y, w, h, color, alpha, duration)
        self.overlays.append(ov)
        QTimer.singleShot(duration + 100, lambda: self.overlays.remove(ov) if ov in self.overlays else None)

    def clear_all(self):
        for ov in self.overlays:
            ov.close()
        self.overlays.clear()