import os
import hashlib
import urllib.request
import threading
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QLineEdit, QScrollArea,
                             QSizePolicy, QMenu)
from PyQt6.QtGui import QAction
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
        # Fond global harmonisé
        self.setStyleSheet("background-color: #1a1a1a;")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Supprime l'espace par défaut (souvent ~6px) entre les widgets empilés
        self.layout.setSpacing(0)

        self.config = DEFAULT_CONFIG.copy()
        self.assets_dir = os.path.join(os.getcwd(), "assets").replace("\\", "/")
        os.makedirs(self.assets_dir, exist_ok=True)
        self.download_queue = set()

        self.processor = GuideProcessor()
        self.current_html_content = ""
        self.current_guide_id = None
        self.current_step_id = None
        self.checkbox_states = {}

        # Stockage local des guides pour le redimensionnement
        self.cached_guides = []
        self.cached_active_idx = -1

        self.setup_ui()

        # Setup WebEngine & Bridge
        self.channel = QWebChannel()
        self.bridge = Bridge(self.controller)
        self.channel.registerObject("pyBridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)
        self.image_loaded.connect(self._refresh_display_content)

    def setup_ui(self):
        # 1. Zone des Onglets (Conteneur principal)
        self.tabs_main_widget = QWidget()
        self.tabs_main_widget.setFixedHeight(40)
        self.tabs_main_widget.setStyleSheet("background-color: #121212;")

        # Layout horizontal pour la zone des onglets
        self.tabs_header_layout = QHBoxLayout(self.tabs_main_widget)
        self.tabs_header_layout.setContentsMargins(5, 10, 5, 0)
        self.tabs_header_layout.setSpacing(5)

        # -- Bouton Burger (Caché par défaut) --
        self.btn_burger = QPushButton("☰")
        self.btn_burger.setFixedSize(30, 30)
        self.btn_burger.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_burger.setStyleSheet("""
            QPushButton { 
                background-color: #2d2d2d; 
                color: #888; 
                border: none; 
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a3a3a; color: white; }
        """)
        self.btn_burger.hide()  # On le cache au début
        self.btn_burger.clicked.connect(self._show_guides_menu)
        self.tabs_header_layout.addWidget(self.btn_burger)

        # -- Conteneur des onglets (Tabs) --
        self.tabs_container = QWidget()
        # IMPORTANT : On permet au conteneur de rétrécir autant que nécessaire
        self.tabs_container.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.setSpacing(1)

        # Le conteneur d'onglets prend tout l'espace restant
        self.tabs_header_layout.addWidget(self.tabs_container)

        self.layout.addWidget(self.tabs_main_widget)

        # 2. Header (Barre de navigation)
        nav_bar = QFrame()
        nav_bar.setFixedHeight(50)
        nav_bar.setStyleSheet("background-color: #1a1a1a;")
        nav_layout = QHBoxLayout(nav_bar)

        # MODIFICATION: Ajout de l'alignement vertical au centre
        nav_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_position = QLabel("")
        self.lbl_position.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffd700; cursor: pointer;")
        self.lbl_position.mousePressEvent = lambda e: self.controller.copy_position()
        nav_layout.addWidget(self.lbl_position)
        nav_layout.addStretch()

        self.btn_prev = self._create_btn("◀", self.controller.nav_previous)
        self.entry_step = QLineEdit("--")
        self.entry_step.setFixedWidth(40)
        # MODIFICATION: Ajout de font-size: 14px pour la cohérence
        self.entry_step.setStyleSheet(
            "background: #1a1a1a; color: #4da6ff; border: none; font-weight: bold; font-size: 14px;")
        self.entry_step.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entry_step.returnPressed.connect(
            lambda: self.controller.on_guide_link_clicked(f"STEP:{self.entry_step.text()}"))

        self.lbl_total = QLabel("/ --")
        # MODIFICATION: Ajout de font-size: 14px pour la cohérence
        self.lbl_total.setStyleSheet("color: #888; font-size: 14px;")
        self.btn_next = self._create_btn("▶", self.controller.nav_next)

        self.btn_auto = self._create_btn("✈", self._toggle_auto)
        self.btn_auto.setCheckable(True)
        self.btn_auto.setChecked(True)
        self.update_auto_btn_color()

        # NOUVEAU BOUTON CLAVIER
        self.btn_keyboard = self._create_btn("⌨️", self._toggle_keyboard)
        self.btn_keyboard.setCheckable(True)
        self.btn_keyboard.setChecked(True)
        self.update_keyboard_btn_color()

        for w in [self.btn_prev, self.entry_step, self.lbl_total, self.btn_next, self.btn_auto, self.btn_keyboard]:
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

    # NOUVELLES METHODES POUR LE BOUTON CLAVIER
    def _toggle_keyboard(self):
        self.btn_keyboard.setChecked(self.controller.toggle_keyboard_nav())
        self.update_keyboard_btn_color()

    def update_keyboard_btn_color(self):
        c = "#00ff00" if self.btn_keyboard.isChecked() else "#666"
        self.btn_keyboard.setStyleSheet(f"QPushButton {{ background: #333344; border-radius: 8px; color: {c}; }}")

    # --- MENU BURGER ---
    def _show_guides_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #252535; color: white; border: 1px solid #4da6ff; }
            QMenu::item { padding: 5px 20px; }
            QMenu::item:selected { background-color: #4da6ff; color: white; }
        """)

        for i, guide in enumerate(self.cached_guides):
            name = guide['name']
            action = QAction(name, self)
            # Marquer l'action si c'est le guide actif
            if i == self.cached_active_idx:
                font = action.font()
                font.setBold(True)
                action.setFont(font)
                action.setText(f"➤ {name}")

            action.triggered.connect(lambda _, x=i: self.controller.switch_tab(x))
            menu.addAction(action)

        menu.exec(self.btn_burger.mapToGlobal(self.btn_burger.rect().bottomLeft()))

    # --- GESTION REDIMENSIONNEMENT ---
    def resizeEvent(self, event):
        # Recalcule l'affichage des onglets lors du redimensionnement
        if self.cached_guides:
            self._render_tabs_logic()
        super().resizeEvent(event)

    def _render_tabs_logic(self):
        """
        Logique intelligente :
        1. Estime la largeur nécessaire pour afficher TOUS les onglets.
        2. Si ça rentre -> Affiche tous les onglets, cache le burger.
        3. Si ça ne rentre pas -> Affiche Burger + Onglet Actif (qui prend toute la place).
        """
        if not self.cached_guides: return

        # Largeur disponible pour les onglets (largeur totale de la fenêtre - marges)
        available_width = self.tabs_main_widget.width() - 20

        # Estimation largeur requise (min 150px par onglet pour être lisible + espacement)
        min_width_per_tab = 150
        required_width = len(self.cached_guides) * min_width_per_tab

        # Si la largeur requise est plus grande que la largeur dispo, on passe en mode burger
        should_collapse = required_width > available_width

        # Nettoyage layout
        while self.tabs_layout.count():
            item = self.tabs_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        if should_collapse:
            # MODE COMPACT : Burger + 1 Onglet (Actif)
            self.btn_burger.show()

            # On affiche uniquement l'onglet actif
            if 0 <= self.cached_active_idx < len(self.cached_guides):
                self._add_tab_widget(self.cached_guides[self.cached_active_idx], self.cached_active_idx, is_active=True,
                                     allow_close=True)
            else:
                pass
        else:
            # MODE NORMAL : Tous les onglets
            self.btn_burger.hide()
            for i, guide in enumerate(self.cached_guides):
                is_active = (i == self.cached_active_idx)
                self._add_tab_widget(guide, i, is_active=is_active, allow_close=True)

    def _add_tab_widget(self, guide, index, is_active, allow_close):
        bg, fg, fw = ("#1a1a1a", "#4da6ff", "bold") if is_active else ("#2d2d2d", "#888", "normal")

        tab = QFrame()
        # Expanding permet à l'onglet de prendre toute la place dispo en mode burger
        tab.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tab.setStyleSheet(
            f"QFrame {{ background-color: {bg}; border-top-left-radius: 6px; border-top-right-radius: 6px; }}")

        l = QHBoxLayout(tab)
        l.setContentsMargins(10, 2, 5, 2)
        l.setSpacing(5)

        name_text = (guide['name'][:25] + "...") if len(guide['name']) > 28 else guide['name']
        btn = QPushButton(name_text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        btn.setStyleSheet(
            f"text-align: left; border: none; background: transparent; color: {fg}; font-weight: {fw}; font-size: 13px;")
        btn.clicked.connect(lambda _, x=index: self.controller.switch_tab(x))

        l.addWidget(btn)

        if allow_close:
            close = QPushButton("✕")
            close.setFixedSize(20, 20)
            close.setCursor(Qt.CursorShape.PointingHandCursor)
            close.setStyleSheet(
                "QPushButton { color: #666; border: none; background: transparent; font-weight: bold; } QPushButton:hover { color: #ff5555; background-color: #3a1a1a; border-radius: 10px; }")
            close.clicked.connect(lambda _, x=index: self.controller.close_tab(x))
            l.addWidget(close)

        self.tabs_layout.addWidget(tab)

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
            self.browser.setHtml(final, QUrl("file:///"))

    def update_tabs(self, guides, active_idx):
        """
        Met à jour la liste locale et déclenche le rendu intelligent.
        """
        self.cached_guides = guides
        self.cached_active_idx = active_idx
        self._render_tabs_logic()

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