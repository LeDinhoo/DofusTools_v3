import os
import hashlib
import urllib.request
import threading
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QLineEdit, QScrollArea)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal

# Imports des modules découpés
from .guide_bridge import Bridge
from .guide_renderer import generate_full_html
from .guide_processor import GuideProcessor

DEFAULT_CONFIG = {"font_family": "Segoe UI", "font_size": 14, "icon_size": 24, "img_large_width": 400}


class GuidePanel(QWidget):
    image_loaded = pyqtSignal()

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setStyleSheet("background-color: #1e1e2e;")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.config = DEFAULT_CONFIG.copy()
        self.assets_dir = os.path.join(os.getcwd(), "assets").replace("\\", "/")
        os.makedirs(self.assets_dir, exist_ok=True)
        self.download_queue = set()

        self.processor = GuideProcessor()
        self.current_html_content = ""
        self.current_guide_id = None
        self.current_step_id = None
        self.checkbox_states = {}

        self.setup_ui()

        # Setup WebEngine & Bridge
        self.channel = QWebChannel()
        self.bridge = Bridge(self.controller)
        self.channel.registerObject("pyBridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)
        self.image_loaded.connect(self._refresh_display_content)

    def setup_ui(self):
        # 1. Onglets
        self.tabs_scroll = QScrollArea()
        self.tabs_scroll.setFixedHeight(40)
        self.tabs_scroll.setWidgetResizable(True)
        self.tabs_scroll.setStyleSheet("background-color: #121212; border: none;")
        self.tabs_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tabs_container = QWidget()
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(5, 0, 5, 0)
        self.tabs_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.tabs_scroll.setWidget(self.tabs_container)
        self.layout.addWidget(self.tabs_scroll)

        # 2. Header
        nav_bar = QFrame()
        nav_bar.setFixedHeight(50)
        nav_bar.setStyleSheet("background-color: #252535;")
        nav_layout = QHBoxLayout(nav_bar)

        self.lbl_position = QLabel("")
        self.lbl_position.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffd700; cursor: pointer;")
        self.lbl_position.mousePressEvent = lambda e: self.controller.copy_position()
        nav_layout.addWidget(self.lbl_position)
        nav_layout.addStretch()

        self.btn_prev = self._create_btn("◀", self.controller.nav_previous)
        self.entry_step = QLineEdit("--")
        self.entry_step.setFixedWidth(40)
        self.entry_step.setStyleSheet("background: #1a1a1a; color: #4da6ff; border: none; font-weight: bold;")
        self.entry_step.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entry_step.returnPressed.connect(
            lambda: self.controller.on_guide_link_clicked(f"STEP:{self.entry_step.text()}"))

        self.lbl_total = QLabel("/ --")
        self.lbl_total.setStyleSheet("color: #888;")
        self.btn_next = self._create_btn("▶", self.controller.nav_next)

        self.btn_auto = self._create_btn("✈", self._toggle_auto)
        self.btn_auto.setCheckable(True)
        self.btn_auto.setChecked(True)
        self.update_auto_btn_color()

        for w in [self.btn_prev, self.entry_step, self.lbl_total, self.btn_next, self.btn_auto]:
            nav_layout.addWidget(w)
            if w == self.btn_next: nav_layout.addSpacing(10)
        self.layout.addWidget(nav_bar)

        # 3. Viewer
        self.browser = QWebEngineView()
        self.browser.setStyleSheet("background: #1a1a1a;")
        self.browser.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.layout.addWidget(self.browser)

    def _create_btn(self, text, cmd):
        btn = QPushButton(text)
        btn.setFixedSize(30, 30)
        btn.clicked.connect(cmd)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { background: #333344; border-radius: 8px; color: white; } QPushButton:hover { background: #444455; }")
        return btn

    def _toggle_auto(self):
        self.btn_auto.setChecked(self.controller.toggle_auto_travel())
        self.update_auto_btn_color()

    def update_auto_btn_color(self):
        c = "#00ff00" if self.btn_auto.isChecked() else "#666"
        self.btn_auto.setStyleSheet(f"QPushButton {{ background: #333344; border-radius: 8px; color: {c}; }}")

    # --- IMAGE CACHING ---
    def _get_cached_image_path(self, url):
        ext = ".jpg" if ".jpg" in url.lower() or ".jpeg" in url.lower() else ".png"
        hash_name = hashlib.md5(url.encode()).hexdigest() + ext
        local_path = os.path.join(self.assets_dir, hash_name)
        if not os.path.exists(local_path) and url not in self.download_queue:
            self.download_queue.add(url)
            threading.Thread(target=self._download_worker, args=(url, local_path), daemon=True).start()
        return local_path

    def _download_worker(self, url, local_path):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as r, open(local_path, "wb") as f:
                f.write(r.read())
            self.image_loaded.emit()
        except:
            pass
        finally:
            if url in self.download_queue: self.download_queue.remove(url)

    # --- LOGIQUE D'AFFICHAGE ---
    def _refresh_display_content(self):
        if self.current_html_content:
            final = generate_full_html(self.current_html_content, self.config)
            # CORRECTION ICI : "file:///" au lieu de "qrc:///"
            self.browser.setHtml(final, QUrl("file:///"))

    def update_tabs(self, guides, active_idx):
        while self.tabs_layout.count(): item = self.tabs_layout.takeAt(0); item.widget().deleteLater()
        for i, guide in enumerate(guides):
            is_active = (i == active_idx)
            bg, fg, fw = ("#1e1e2e", "#fff", "bold") if is_active else ("#2d2d2d", "#888", "normal")

            tab = QFrame()
            tab.setStyleSheet(f"background: {bg}; border-radius: 4px;")
            l = QHBoxLayout(tab);
            l.setContentsMargins(8, 2, 8, 2)

            btn = QPushButton((guide['name'][:17] + "...") if len(guide['name']) > 20 else guide['name'])
            btn.setStyleSheet(f"border:none; background:transparent; color:{fg}; font-weight:{fw};")
            btn.clicked.connect(lambda _, x=i: self.controller.switch_tab(x))

            close = QPushButton("✕")
            close.setFixedSize(16, 16)
            close.setStyleSheet("color:#ff5555; border:none; font-weight:bold;")
            close.clicked.connect(lambda _, x=i: self.controller.close_tab(x))

            l.addWidget(btn);
            l.addWidget(close)
            self.tabs_layout.addWidget(tab)

    def update_content(self, guide_data, parser):
        if not guide_data:
            self._reset_view()
            return

        steps, idx = guide_data['steps'], guide_data['current_idx']
        self.entry_step.setText(str(idx + 1))
        self.lbl_total.setText(f"/ {len(steps)}")
        self.btn_prev.setDisabled(idx <= 0)
        self.btn_next.setDisabled(idx >= len(steps) - 1)

        step = steps[idx]
        self.current_guide_id = guide_data.get('id', 0)
        self.current_step_id = step.get('id', idx)

        c = parser.get_step_coords(step)
        self.lbl_position.setText(f"[{c[0]}, {c[1]}]" if c else "")

        # Utilisation du Processor externe
        raw = parser.get_step_web_text(step)
        self.current_html_content = self.processor.preprocess_content(
            raw, self.current_guide_id, self.current_step_id,
            self.checkbox_states, self._get_cached_image_path
        )
        self._refresh_display_content()

    def _reset_view(self):
        self.entry_step.setText("--")
        self.lbl_total.setText("/ --")
        self.lbl_position.setText("")
        self.browser.setHtml("<div style='color:gray; text-align:center; margin-top:50px;'>Aucun guide chargé</div>")
        self.btn_prev.setDisabled(True);
        self.btn_next.setDisabled(True)