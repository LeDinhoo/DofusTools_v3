import logging
import os
import ctypes
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QFrame, QLabel, QApplication, QLineEdit)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap

from .controller import MainController
from .panels.sidebar import SidebarPanel
from .panels.guide_view import GuidePanel
from .panels.logger import LoggerPanel

logger = logging.getLogger(__name__)


class AppLauncher(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Python Automation Hub (PyQt6)")
        self.resize(1200, 850)

        # Toujours au dessus
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        # Widget central et Layout principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # État clavier
        self.key_a_was_down = False
        self.key_d_was_down = False
        self.debug_window_ref = None

        # --- 1. CONTROLEUR ---
        self.controller = MainController(self)

        # --- 2. INTERFACE ---
        self.setup_ui()

        # Démarrage du polling clavier
        self.timer_keys = QTimer()
        self.timer_keys.timeout.connect(self.poll_global_keys)
        self.timer_keys.start(50)

        # --- 3. LOGGING ---
        self.setup_logging()

        # --- 4. START ---
        # On sécurise le démarrage différé
        QTimer.singleShot(200, self.safe_startup)
        logger.info("Interface PyQt6 chargée.")

    def safe_startup(self):
        try:
            self.controller.startup()
        except Exception as e:
            logger.error(f"Erreur au démarrage du contrôleur : {e}", exc_info=True)

    def setup_ui(self):
        # 1. Sidebar (Gauche)
        self.ui_sidebar = SidebarPanel(self.controller)
        self.main_layout.addWidget(self.ui_sidebar)

        # 2. Zone Centrale
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self.ui_guide = GuidePanel(self.controller)
        center_layout.addWidget(self.ui_guide)

        # Barre du bas
        self.status_bar = QFrame()
        self.status_bar.setFixedHeight(45)
        self.status_bar.setStyleSheet("background-color: #1a1a1a;")
        sb_layout = QHBoxLayout(self.status_bar)
        sb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_tools = self.create_status_btn("🛠️ Outils", self.toggle_sidebar, True)
        self.btn_logs = self.create_status_btn("📝 Logs", self.toggle_logs, False)

        sb_layout.addWidget(self.btn_tools)
        sb_layout.addWidget(self.btn_logs)

        center_layout.addWidget(self.status_bar)
        self.main_layout.addWidget(center_container)

        # 3. Logs (Droite)
        self.ui_logger = LoggerPanel()
        self.ui_logger.hide()
        self.main_layout.addWidget(self.ui_logger)

        self.show_sidebar = True
        self.show_logs = False

    def create_status_btn(self, text, command, is_active):
        btn = QPushButton(text)
        btn.setFixedSize(120, 30)
        btn.clicked.connect(command)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn_style(btn, is_active)
        return btn

    def update_btn_style(self, btn, is_active):
        color = "#4da6ff" if is_active else "#333333"
        text_col = "white" if is_active else "gray"
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: {text_col};
                border-radius: 5px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #3a8ee6;
                color: white;
            }}
        """)

    def setup_logging(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        for h in root_logger.handlers[:]:
            root_logger.removeHandler(h)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S'))
        root_logger.addHandler(console_handler)
        root_logger.addHandler(self.ui_logger.log_handler)

    def toggle_sidebar(self):
        self.show_sidebar = not self.show_sidebar
        self.ui_sidebar.setVisible(self.show_sidebar)
        self.update_btn_style(self.btn_tools, self.show_sidebar)

    def toggle_logs(self):
        self.show_logs = not self.show_logs
        self.ui_logger.setVisible(self.show_logs)
        self.update_btn_style(self.btn_logs, self.show_logs)

    def show_debug_image(self, image_path):
        if not image_path or not os.path.exists(image_path): return
        self.debug_window_ref = QWidget()
        self.debug_window_ref.setWindowTitle("Debug OCR")
        self.debug_window_ref.resize(600, 400)
        self.debug_window_ref.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        layout = QVBoxLayout(self.debug_window_ref)
        lbl = QLabel()
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            lbl.setPixmap(pixmap.scaled(600, 400, Qt.AspectRatioMode.KeepAspectRatio))
        layout.addWidget(lbl)
        self.debug_window_ref.show()

    def poll_global_keys(self):
        """Boucle de vérification clavier sécurisée"""
        try:
            # Vérification si focus sur un champ texte
            focus_widget = QApplication.focusWidget()
            if focus_widget and isinstance(focus_widget, QLineEdit):
                return

            # Vérification Touches Globales
            if ctypes.windll.user32.GetAsyncKeyState(0x41) & 0x8000:  # Touche A
                if not self.key_a_was_down:
                    self.key_a_was_down = True
                    self.controller.nav_previous()
            else:
                self.key_a_was_down = False

            if ctypes.windll.user32.GetAsyncKeyState(0x44) & 0x8000:  # Touche D
                if not self.key_d_was_down:
                    self.key_d_was_down = True
                    self.controller.nav_next()
            else:
                self.key_d_was_down = False

        except Exception as e:
            # On log l'erreur mais on ne crash pas l'app
            logger.error(f"Erreur polling clavier : {e}")