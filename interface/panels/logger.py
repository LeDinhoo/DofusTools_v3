import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt6.QtCore import QObject, pyqtSignal


class QtLogHandler(logging.Handler, QObject):
    new_record = pyqtSignal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.new_record.emit(msg)


class LoggerPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(300)
        self.setStyleSheet("background-color: #1a1a1a; border-left: 1px solid #333;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("LOGS SYSTÈME")
        title.setStyleSheet("color: gray; font-weight: bold;")
        layout.addWidget(title)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("""
            QTextEdit { background-color: #121212; color: #00ff00; font-family: Consolas; font-size: 11px; border: none; }
        """)
        layout.addWidget(self.text_area)

        self.log_handler = QtLogHandler()
        self.log_handler.new_record.connect(self.append_log)
        self.log_handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))

    def append_log(self, msg):
        self.text_area.append(msg)