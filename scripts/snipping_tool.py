from PyQt6.QtWidgets import QWidget, QApplication, QRubberBand
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor


class SnippingWidget(QWidget):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.begin = QPoint()
        self.end = QPoint()
        self.is_selecting = False

        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Fond sombre semi-transparent
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.is_selecting:
            # Zone claire (la sélection)
            rect = QRect(self.begin, self.end).normalized()
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)

            # Bordure rouge
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QColor(255, 0, 0))
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = event.pos()
        self.is_selecting = True
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        self.is_selecting = False
        self.close()

        rect = QRect(self.begin, self.end).normalized()
        if rect.width() > 5 and rect.height() > 5:
            # Conversion en tuple (x, y, w, h)
            self.callback((rect.x(), rect.y(), rect.width(), rect.height()))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()


class SnippingTool:
    def __init__(self):
        self.widget = None

    def start_selection(self, callback):
        # Important: doit être exécuté dans le thread principal
        self.widget = SnippingWidget(callback)