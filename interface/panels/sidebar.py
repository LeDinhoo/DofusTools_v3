from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit,
                             QPushButton, QHBoxLayout, QFrame)
from PyQt6.QtCore import Qt


class SidebarPanel(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setFixedWidth(220)
        self.setStyleSheet("background-color: #1e1e2e; border-right: 1px solid #111;")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 20, 15, 20)
        self.layout.setSpacing(15)

        self.setup_widgets()

    def setup_widgets(self):
        # --- TITRE ---
        title = QLabel("DofusTools v3")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4da6ff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(title)

        self.layout.addSpacing(10)

        # --- SECTION CONFIGURATION ---
        self.add_section_label("CONFIGURATION")

        # Input Nom du personnage
        lbl_char = QLabel("Personnage à lier :")
        lbl_char.setStyleSheet("color: #aaa; font-size: 11px;")
        self.layout.addWidget(lbl_char)

        bind_layout = QHBoxLayout()
        bind_layout.setSpacing(5)

        self.bind_entry = QLineEdit()
        self.bind_entry.setPlaceholderText("Nom Dofus")
        self.bind_entry.setStyleSheet(self._input_style())

        btn_link = QPushButton("🔗")
        btn_link.setFixedSize(32, 30)
        btn_link.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_link.setStyleSheet("background: #252535; color: white; border: 1px solid #3a3a4a; border-radius: 4px;")
        btn_link.clicked.connect(self.controller.action_bind_window_wrapper)

        bind_layout.addWidget(self.bind_entry)
        bind_layout.addWidget(btn_link)
        self.layout.addLayout(bind_layout)

        # Zone OCR (Un seul bouton pour définir la zone, essentiel pour le fonctionnement)
        btn_zone = self._create_btn("📐 Définir Zone OCR", self.controller.action_define_ocr_zone_wrapper)
        self.layout.addWidget(btn_zone)

        self.layout.addSpacing(20)

        # --- SECTION GUIDES ---
        self.add_section_label("GESTION GUIDES")

        btn_load = self._create_btn("📂 Charger JSON", self.controller.action_load_json_wrapper)
        btn_load.setStyleSheet(
            btn_load.styleSheet().replace("#252535", "#2a4a35").replace("#3a3a4a", "#3a6a45"))  # Vert foncé
        self.layout.addWidget(btn_load)

        # Pousse le tout vers le haut
        self.layout.addStretch()

        # Version ou infos bas de page
        lbl_ver = QLabel("v3.0 - Clean")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_ver.setStyleSheet("color: #444;")
        self.layout.addWidget(lbl_ver)

    def add_section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #666; font-weight: bold; font-size: 10px; letter-spacing: 1px;")
        self.layout.addWidget(lbl)
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: #2d2d2d;")
        self.layout.addWidget(line)

    def _create_btn(self, text, command):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(command)
        btn.setFixedHeight(35)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #252535;
                border-radius: 5px;
                color: #e0e0e0;
                border: 1px solid #3a3a4a;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #353545;
                border-color: #4da6ff;
                color: white;
            }
        """)
        return btn

    def _input_style(self):
        return """
            QLineEdit {
                background-color: #121212;
                border: 1px solid #3a3a4a;
                border-radius: 4px;
                padding: 4px 8px;
                color: white;
            }
            QLineEdit:focus { border: 1px solid #4da6ff; }
        """

    def update_bind_status(self, status):
        color = "#2ecc71" if status == "success" else "#e74c3c" if status == "error" else "#3a3a4a"
        self.bind_entry.setStyleSheet(self._input_style().replace("#3a3a4a", color))