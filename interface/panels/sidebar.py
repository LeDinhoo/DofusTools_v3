from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit,
                             QPushButton, QHBoxLayout, QFrame, QCheckBox)
from PyQt6.QtCore import Qt


class SidebarPanel(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setFixedWidth(240)
        self.setStyleSheet("background-color: #1e1e2e;")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 20, 10, 20)
        self.layout.setSpacing(10)

        self.setup_widgets()
        self.layout.addStretch()  # Pousse tout vers le haut

    def setup_widgets(self):
        # TITRE
        title = QLabel("DASHBOARD")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(title)
        self.layout.addSpacing(10)

        # --- CIBLAGE ---
        self.add_section("CIBLAGE")

        bind_layout = QHBoxLayout()
        self.bind_entry = QLineEdit()
        self.bind_entry.setPlaceholderText("Nom du perso")
        self.bind_entry.setStyleSheet(self._input_style())

        btn_link = self._create_icon_btn("🔗", self.controller.action_bind_window_wrapper)

        bind_layout.addWidget(self.bind_entry)
        bind_layout.addWidget(btn_link)
        self.layout.addLayout(bind_layout)

        macro_btn = self._create_btn("⚔️ Macro Dofus", self.controller.action_macro_space_wrapper)
        self.layout.addWidget(macro_btn)

        # NOUVEAU BOUTON : Macro H + Clic
        macro_h_click_btn = self._create_btn("✨ Macro H + Clic", self.controller.action_macro_h_click_wrapper)
        self.layout.addWidget(macro_h_click_btn)

        # --- ACTIONS ---
        self.add_section("ACTIONS")
        self.layout.addWidget(self._create_btn("🖱️ Clic Centre", self.controller.action_click_center_wrapper))
        self.layout.addWidget(self._create_btn("🔴 Test Overlay", self.controller.action_test_overlay_wrapper))

        # --- OUTILS ---
        self.add_section("OUTILS & OCR")

        ocr_layout = QHBoxLayout()
        self.ocr_target_entry = QLineEdit("Lester")
        self.ocr_target_entry.setStyleSheet(self._input_style())

        self.ocr_threshold_entry = QLineEdit("190")
        self.ocr_threshold_entry.setFixedWidth(50)
        self.ocr_threshold_entry.setStyleSheet(self._input_style())

        ocr_layout.addWidget(self.ocr_target_entry)
        ocr_layout.addWidget(self.ocr_threshold_entry)
        self.layout.addLayout(ocr_layout)

        self.chk_grayscale = QCheckBox("Noir & Blanc")
        self.chk_grayscale.setChecked(True)
        self.chk_grayscale.setStyleSheet("color: white;")
        self.layout.addWidget(self.chk_grayscale)

        tools_layout = QHBoxLayout()
        btn_zone = self._create_btn("📐 Zone", self.controller.action_define_ocr_zone_wrapper)
        btn_zone.setStyleSheet(btn_zone.styleSheet().replace("#252535", "#E59937").replace("#3a3a4a", "#D48826"))

        btn_search = self._create_btn("🔎 Chercher", self.controller.action_ocr_wrapper)

        tools_layout.addWidget(btn_zone)
        tools_layout.addWidget(btn_search)
        self.layout.addLayout(tools_layout)

        # --- BAS ---
        self.layout.addStretch()
        self.layout.addWidget(self._create_btn("📂 Charger JSON", self.controller.action_load_json_wrapper))

    def add_section(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #888888; font-weight: bold; font-size: 11px; margin-top: 15px;")
        self.layout.addWidget(lbl)

    def _create_btn(self, text, command):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(command)
        btn.setFixedHeight(32)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #252535;
                border-radius: 6px;
                color: white;
                border: 1px solid #3a3a4a;
            }
            QPushButton:hover {
                background-color: #3a3a4a;
            }
        """)
        return btn

    def _create_icon_btn(self, text, command):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(command)
        btn.setFixedSize(32, 32)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #252535;
                border-radius: 6px;
                color: white;
            }
            QPushButton:hover { background-color: #3a3a4a; }
        """)
        return btn

    def _input_style(self):
        return """
            QLineEdit {
                background-color: #121212;
                border: 1px solid #3a3a4a;
                border-radius: 4px;
                padding: 4px;
                color: white;
            }
            QLineEdit:focus { border: 1px solid #4da6ff; }
        """

    # Helpers pour le controller
    def get_bind_entry_text(self): return self.bind_entry.text()

    def set_bind_entry_text(self, text): self.bind_entry.setText(text)

    def update_bind_status(self, status):
        color = "#00ff00" if status == "success" else "#ff0000" if status == "error" else "#3a3a4a"
        self.bind_entry.setStyleSheet(self._input_style().replace("#3a3a4a", color))