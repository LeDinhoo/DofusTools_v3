import os
import json
import hashlib
import urllib.request
import threading
import re

# Import WebEngine
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QPushButton, QLineEdit, QScrollArea)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QObject, pyqtSlot

# --- CONFIGURATION GLOBALE ---
DEFAULT_CONFIG = {
    "font_family": "Segoe UI",
    "font_size": 14,
    "icon_size": 24,
    "img_large_width": 400
}


# --- PONT PYTHON <-> JAVASCRIPT ---
class Bridge(QObject):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    @pyqtSlot(str)
    def handleLink(self, link):
        # print(f"DEBUG JS -> Python : {link}")
        if link.startswith("GUIDE:") or link.startswith("STEP:"):
            self.controller.on_guide_link_clicked(link)
        elif link.startswith("CB:"):
            # Logique métier (sauvegarde) uniquement
            pass

    @pyqtSlot(str)
    def copyToClipboard(self, text):
        self.controller.copy_position()


class GuidePanel(QWidget):
    image_loaded = pyqtSignal()

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setStyleSheet("background-color: #1e1e2e;")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.config = DEFAULT_CONFIG.copy()
        self.assets_dir = os.path.join(os.getcwd(), "assets").replace("\\", "/")
        os.makedirs(self.assets_dir, exist_ok=True)
        self.download_queue = set()

        self.current_html_content = ""
        self.current_guide_id = None
        self.current_step_id = None

        # On garde l'état des checkboxes côté Python
        self.checkbox_states = {}

        self.setup_ui()

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
        self.tabs_layout.setSpacing(5)
        self.tabs_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.tabs_scroll.setWidget(self.tabs_container)
        self.layout.addWidget(self.tabs_scroll)

        # 2. Header
        nav_bar = QFrame()
        nav_bar.setFixedHeight(50)
        nav_bar.setStyleSheet("background-color: #252535;")
        nav_layout = QHBoxLayout(nav_bar)

        self.lbl_position = QLabel("")
        self.lbl_position.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffd700;")
        self.lbl_position.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_position.mousePressEvent = lambda e: self.controller.copy_position()

        nav_layout.addWidget(self.lbl_position)
        nav_layout.addStretch()

        self.btn_prev = self._create_nav_btn("◀", self.controller.nav_previous)

        self.entry_step = QLineEdit("--")
        self.entry_step.setFixedWidth(40)
        self.entry_step.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entry_step.setStyleSheet("background-color: #1a1a1a; color: #4da6ff; border: none; font-weight: bold;")
        self.entry_step.returnPressed.connect(self._on_step_submit)

        self.lbl_total = QLabel("/ --")
        self.lbl_total.setStyleSheet("color: #888888;")

        self.btn_next = self._create_nav_btn("▶", self.controller.nav_next)

        self.btn_auto = self._create_nav_btn("✈", self._toggle_auto)
        self.btn_auto.setCheckable(True)
        self.btn_auto.setChecked(True)
        self.update_auto_btn_color()

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.entry_step)
        nav_layout.addWidget(self.lbl_total)
        nav_layout.addWidget(self.btn_next)
        nav_layout.addSpacing(10)
        nav_layout.addWidget(self.btn_auto)

        self.layout.addWidget(nav_bar)

        # 3. Viewer (WebEngineView)
        self.browser = QWebEngineView()
        self.browser.setStyleSheet("background-color: #1a1a1a;")
        self.browser.page().setBackgroundColor(Qt.GlobalColor.transparent)

        self.layout.addWidget(self.browser)

    def _create_nav_btn(self, text, cmd):
        btn = QPushButton(text)
        btn.setFixedSize(30, 30)
        btn.clicked.connect(cmd)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { background-color: #333344; border-radius: 8px; color: white; }
            QPushButton:hover { background-color: #444455; }
            QPushButton:disabled { color: #555; background-color: #222; }
        """)
        return btn

    def _toggle_auto(self):
        is_enabled = self.controller.toggle_auto_travel()
        self.btn_auto.setChecked(is_enabled)
        self.update_auto_btn_color()

    def update_auto_btn_color(self):
        color = "#00ff00" if self.btn_auto.isChecked() else "#666666"
        self.btn_auto.setStyleSheet(f"QPushButton {{ background-color: #333344; border-radius: 8px; color: {color}; }}")

    def _on_step_submit(self):
        val = self.entry_step.text()
        self.controller.on_guide_link_clicked(f"STEP:{val}")
        self.setFocus()

        # --- HTML & CSS GENERATION ---

    def _generate_full_html(self, body_content):
        # CSS
        css = f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');

            body {{
                background-color: #1a1a1a;
                color: #c0c0c0;
                font-family: 'Segoe UI', sans-serif;
                font-size: {self.config['font_size']}px;
                margin: 20px;
                line-height: 1.5;
            }}

            a {{ color: #4da6ff; text-decoration: none; cursor: pointer; }}
            a:hover {{ text-decoration: underline; }}

            /* --- STYLES BASÉS SUR LE JSON --- */
            span[class*="tag-quest"] {{ color: #ff76d7; font-weight: bold; }}
            span[class*="tag-item"] {{ color: #ffcc00; font-weight: bold; }}
            span[class*="tag-monster"] {{ color: #ff5e5e; font-weight: bold; }}
            span[class*="tag-dungeon"] {{ color: #00ff00; font-weight: bold; }}
            span[style*="color: rgb(98, 172, 255)"] {{ color: #4da6ff !important; font-weight: bold; font-size: 1.1em; }}

            /* Images */
            span[class*="tag-quest"] img {{ width: 18px; height: auto; vertical-align: text-bottom; margin-right: 4px; }}
            span[class*="tag-item"] img {{ width: 24px; height: auto; vertical-align: middle; margin-right: 4px; }}
            span[class*="tag-monster"] img {{ width: 32px; height: auto; vertical-align: middle; margin-right: 4px; }}
            span[class*="tag-dungeon"] img {{ width: 24px; height: auto; vertical-align: middle; margin-right: 4px; }}
            img {{ vertical-align: middle; width: 20px; height: auto; }} 

            .img-large {{ 
                display: block; 
                margin: 15px auto; 
                max-width: 100%; 
                width: {self.config['img_large_width']}px; 
                border-radius: 8px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            }}

            /* --- LISTES & CHECKBOXES SIMPLIFIÉES --- */
            ul {{ list-style-type: none; padding-left: 0; margin-top: 10px; }}

            /* C'EST ICI QUE TOUT SE JOUE */
            li {{ 
                margin-bottom: 6px; 
                line-height: 1.5;
                /* Configuration Flexbox demandée */
                display: flex;
                justify-content: flex-start;
                align-items: center; 
            }}

            /* Checkbox Native Simple */
            input[type="checkbox"] {{
                width: 16px;
                height: 16px;
                cursor: pointer;
                /* Juste une marge à droite pour séparer du texte */
                margin-right: 12px; 
                /* Plus besoin de margin-top grâce à align-items: center */
            }}

            /* --- QUEST BLOCKS --- */
            .quest-block {{
                background-color: #202025;
                border: 1px solid #333;
                border-radius: 6px;
                margin: 10px 0;
                padding: 10px;
                position: relative;
            }}

            /* --- TOOLTIPS --- */
            .guide-step, [title] {{
                position: relative;
                cursor: help;
            }}
            .guide-step {{
                color: #b19cd9;
                font-weight: bold;
            }}
        </style>
        """

        script = """
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        <script>
            var backend;
            new QWebChannel(qt.webChannelTransport, function (channel) {
                backend = channel.objects.pyBridge;
            });

            function onLinkClick(link) {
                if (backend) backend.handleLink(link);
            }

            function onCheckboxClick(cbId, checked) {
                if (backend) backend.handleLink('CB:' + cbId + ':' + checked);
            }
        </script>
        """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            {css}
            {script}
        </head>
        <body>
            {body_content}
        </body>
        </html>
        """

    def _preprocess_content(self, html):
        import re

        # 1. Liens Guides (inchangé)
        def guide_replacer(match):
            full_span = match.group(0)
            content = match.group(2)
            attrs = match.group(1)

            gid_match = re.search(r'guideid="(\d+)"', attrs)
            step_match = re.search(r'stepnumber="(\d+)"', attrs)
            name_match = re.search(r'guidename="([^"]+)"', attrs)

            gid = gid_match.group(1) if gid_match else "0"
            step = step_match.group(1) if step_match else None
            gname = name_match.group(1) if name_match else "Guide"

            link_action = f"GUIDE:{gid}"
            if step and (gid == "0" or str(gid) == str(self.current_guide_id)):
                link_action = f"STEP:{step}"

            link_action = link_action.replace("'", "\\'")

            return (f'<span class="guide-step" title="{gname}" '
                    f'onclick="onLinkClick(\'{link_action}\')">{content}</span>')

        html = re.sub(r'(<span[^>]*class="[^"]*guide-step[^"]*"[^>]*>)(.*?)</span>', guide_replacer, html,
                      flags=re.DOTALL)

        # 2. Images (inchangé)
        urls = set(re.findall(r'(https?://[^"\')\s]+\.(?:png|jpg|jpeg|gif))', html, re.IGNORECASE))
        for url in urls:
            local_path = self._get_cached_image_path(url)
            local_url = QUrl.fromLocalFile(local_path).toString()
            html = html.replace(url, local_url)

        # 3. Quest Blocks (inchangé)
        def quest_block_replacer(match):
            full_div = match.group(0)
            title_match = re.search(r'title="([^"]+)"', full_div)
            title = title_match.group(1) if title_match else "Détails"
            content_match = re.search(r'<div[^>]*class="quest-block"[^>]*>(.*?)</div>', full_div, flags=re.DOTALL)
            content = content_match.group(1) if content_match else ""
            content = re.sub(r'^\s*<p>\s*<span[^>]*class="[^"]*tag-[^"]*"[^>]*>.*?</span>\s*:?\s*</p>', '', content,
                             flags=re.IGNORECASE | re.DOTALL)
            return (f'<div class="quest-block" title="{title}">'
                    f'<div>{content}</div>'
                    f'</div>')

        html = re.sub(r'(<div[^>]*class="quest-block"[^>]*>.*?</div>)', quest_block_replacer, html, flags=re.DOTALL)

        # 4. Checkboxes (VERSION ULTRA SIMPLE)
        self.cb_counter = 0

        def checkbox_replacer(match):
            self.cb_counter += 1
            idx = self.cb_counter
            unique_key = f"{self.current_step_id}_{idx}"

            # Restauration état
            is_checked = self.checkbox_states.get(unique_key, False)
            checked_attr = "checked" if is_checked else ""

            # On remplace juste l'input. L'alignement est géré par le CSS du LI parent.
            return f'<input type="checkbox" {checked_attr} onclick="onCheckboxClick(\'{idx}\', this.checked)">'

        # Regex simple qui ne capture que la balise input
        html = re.sub(r'<input[^>]*type="checkbox"[^>]*>', checkbox_replacer, html)

        return html

        # 3. Quest Blocks (inchangé)
        def quest_block_replacer(match):
            full_div = match.group(0)
            title_match = re.search(r'title="([^"]+)"', full_div)
            title = title_match.group(1) if title_match else "Détails"
            content_match = re.search(r'<div[^>]*class="quest-block"[^>]*>(.*?)</div>', full_div, flags=re.DOTALL)
            content = content_match.group(1) if content_match else ""
            content = re.sub(r'^\s*<p>\s*<span[^>]*class="[^"]*tag-[^"]*"[^>]*>.*?</span>\s*:?\s*</p>', '', content,
                             flags=re.IGNORECASE | re.DOTALL)
            return (f'<div class="quest-block" title="{title}">'
                    f'<div>{content}</div>'
                    f'</div>')

        html = re.sub(r'(<div[^>]*class="quest-block"[^>]*>.*?</div>)', quest_block_replacer, html, flags=re.DOTALL)

        # 4. Checkboxes (MODIFIÉ POUR ALIGNEMENT)
        self.cb_counter = 0

        def checkbox_replacer(match):
            self.cb_counter += 1
            idx = self.cb_counter

            # match.group(1) contient l'input original
            # match.group(2) contient le texte qui suit immédiatement
            input_tag = match.group(1)
            following_text = match.group(2).strip()

            unique_key = f"{self.current_step_id}_{idx}"

            # Restauration état
            is_checked = self.checkbox_states.get(unique_key, False)
            checked_attr = "checked" if is_checked else ""

            # On crée un conteneur Flex (.checkbox-row)
            # On met le texte dans un span (.cb-text) pour gérer le word-wrap
            return (f'<div class="checkbox-row">'
                    f'<input type="checkbox" {checked_attr} onclick="onCheckboxClick(\'{idx}\', this.checked)">'
                    f'<span class="cb-text">{following_text}</span>'
                    f'</div>')

        # Nouvelle Regex :
        # Elle capture l'input (groupe 1) ET le texte qui suit (groupe 2)
        # jusqu'à ce qu'elle rencontre une balise de bloc (<br>, </p>, </div>, </li>) ou la fin de chaine.
        html = re.sub(
            r'(<input[^>]*type="checkbox"[^>]*>)(.*?)(?=<br>|<\/p>|<\/div>|<\/li>|$)',
            checkbox_replacer,
            html,
            flags=re.IGNORECASE | re.DOTALL
        )

        return html

        def checkbox_replacer(match):
            self.cb_counter += 1
            idx = self.cb_counter
            unique_key = f"{self.current_step_id}_{idx}"

            # Restauration état
            is_checked = self.checkbox_states.get(unique_key, False)
            checked_attr = "checked" if is_checked else ""

            # On remplace l'input par notre version avec onclick direct
            return f'<input type="checkbox" {checked_attr} onclick="onCheckboxClick(\'{idx}\', this.checked)">'

        # On remplace tous les inputs checkbox, peu importe où ils sont (dans des li, label, p...)
        html = re.sub(r'<input[^>]*type="checkbox"[^>]*>', checkbox_replacer, html)

        return html

    def _get_cached_image_path(self, url):
        ext = ".png"
        if ".jpg" in url.lower():
            ext = ".jpg"
        elif ".jpeg" in url.lower():
            ext = ".jpeg"
        hash_name = hashlib.md5(url.encode()).hexdigest() + ext
        local_path = os.path.join(self.assets_dir, hash_name)
        if not os.path.exists(local_path):
            if url not in self.download_queue:
                self.download_queue.add(url)
                threading.Thread(target=self._download_worker, args=(url, local_path), daemon=True).start()
        return local_path

    def _download_worker(self, url, local_path):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                with open(local_path, "wb") as f:
                    f.write(response.read())
                self.image_loaded.emit()
        except:
            pass
        finally:
            if url in self.download_queue: self.download_queue.remove(url)

    def _refresh_display_content(self):
        if self.current_html_content:
            final = self._generate_full_html(self.current_html_content)
            self.browser.setHtml(final, QUrl("qrc:///"))

    # --- Mise à jour UI ---

    def update_tabs(self, guides, active_idx):
        for i in reversed(range(self.tabs_layout.count())):
            self.tabs_layout.itemAt(i).widget().setParent(None)

        for i, guide in enumerate(guides):
            is_active = (i == active_idx)
            bg = "#1e1e2e" if is_active else "#2d2d2d"
            fg = "#ffffff" if is_active else "#888888"

            tab_widget = QFrame()
            tab_widget.setStyleSheet(f"background-color: {bg}; border-radius: 4px;")
            tab_layout = QHBoxLayout(tab_widget)
            tab_layout.setContentsMargins(8, 2, 8, 2)

            name = guide['name'][:17] + "..." if len(guide['name']) > 20 else guide['name']

            btn_tab = QPushButton(name)
            btn_tab.setStyleSheet(
                f"text-align: left; border: none; background: transparent; color: {fg}; font-weight: {'bold' if is_active else 'normal'};")
            btn_tab.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_tab.clicked.connect(lambda _, x=i: self.controller.switch_tab(x))

            btn_close = QPushButton("✕")
            btn_close.setFixedSize(16, 16)
            btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_close.setStyleSheet("color: #ff5555; border: none; background: transparent; font-weight: bold;")
            btn_close.clicked.connect(lambda _, x=i: self.controller.close_tab(x))

            tab_layout.addWidget(btn_tab)
            tab_layout.addWidget(btn_close)
            self.tabs_layout.addWidget(tab_widget)

    def update_content(self, guide_data, parser):
        if not guide_data:
            self._reset_view()
            return

        steps = guide_data['steps']
        idx = guide_data['current_idx']

        if idx < 0 or idx >= len(steps):
            self.entry_step.setText("--")
            return

        self.entry_step.setText(str(idx + 1))
        self.lbl_total.setText(f"/ {len(steps)}")
        self.btn_prev.setDisabled(idx <= 0)
        self.btn_next.setDisabled(idx >= len(steps) - 1)

        step = steps[idx]
        self.current_guide_id = guide_data.get('id', 0)
        self.current_step_id = step.get('id', idx)

        coords = parser.get_step_coords(step)
        self.lbl_position.setText(f"[{coords[0]}, {coords[1]}]" if coords else "")

        raw_content = parser.get_step_web_text(step)

        self.current_html_content = self._preprocess_content(raw_content)
        final_html = self._generate_full_html(self.current_html_content)

        self.browser.setHtml(final_html, QUrl("file:///"))

    def _reset_view(self):
        self.entry_step.setText("--")
        self.lbl_total.setText("/ --")
        self.lbl_position.setText("")
        self.browser.setHtml("<div style='color:gray; text-align:center; margin-top:50px;'>Aucun guide chargé</div>")
        self.btn_prev.setDisabled(True)
        self.btn_next.setDisabled(True)