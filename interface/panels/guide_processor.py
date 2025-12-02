import re
from PyQt6.QtCore import QUrl


class GuideProcessor:
    """
    Classe responsable du pré-traitement du contenu HTML/texte brut
    d'une étape de guide avant son injection dans le QWebEngineView.
    """

    def __init__(self):
        self.cb_counter = 0

    def _process_zaap_shortcut(self, content):
        """
        Détecte et marque une instruction Zaap.
        """
        pattern = re.compile(
            r'(Zaap.*?<span[^>]*style="color:\s*rgb\(98,\s*172,\s*255\);?"[^>]*>.*?</span>)',
            re.IGNORECASE | re.DOTALL
        )
        content = pattern.sub(r'<span class="zaap-shortcut" data-type="zaap-shortcut">\1</span>', content)
        return content

    def _process_coordinates(self, content):
        """
        Détecte les coordonnées [x,y] et les rend cliquables.
        Action JS : onLinkClick('TRAVEL:x,y')
        """
        # Regex pour trouver [x,y] avec gestion des espaces éventuels
        pattern = re.compile(r'\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]')

        def replace_match(match):
            x = match.group(1)
            y = match.group(2)
            # On ajoute un style inline pour montrer que c'est cliquable (bleu + curseur main)
            # Le onclick envoie la commande TRAVEL au contrôleur
            return (f'<span style="color: #4da6ff; cursor: pointer; font-weight: bold;" '
                    f'onclick="onLinkClick(\'TRAVEL:{x},{y}\')">[{x},{y}]</span>')

        return pattern.sub(replace_match, content)

    def preprocess_content(self, html, current_guide_id, current_step_id, checkbox_states, image_path_callback):
        self.cb_counter = 0

        # 1. Traitement spécifique des Zaap Shortcuts
        html = self._process_zaap_shortcut(html)

        # 2. Traitement des Coordonnées [x,y] (NOUVEAU)
        # Doit être fait après le Zaap pour être par-dessus (cliquable à l'intérieur du span Zaap)
        html = self._process_coordinates(html)

        # 3. Liens Guides & Tooltips
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
            if step and (gid == "0" or str(gid) == str(current_guide_id)):
                link_action = f"STEP:{step}"

            link_action = link_action.replace("'", "\\'")
            return (f'<span class="guide-step" data-tooltip="{gname}" '
                    f'onclick="onLinkClick(\'{link_action}\')">{content}</span>')

        html = re.sub(r'(<span[^>]*class="[^"]*guide-step[^"]*"[^>]*>)(.*?)</span>', guide_replacer, html,
                      flags=re.DOTALL)

        # 4. Images Locales
        html = re.sub(r'<img src="([^"]+)"',
                      lambda
                          m: f'<img src="{QUrl.fromLocalFile(image_path_callback(m.group(1))).toString()}" data-original-src="{m.group(1)}"',
                      html)

        # 5. Quest Blocks
        def quest_block_replacer(match):
            full_div = match.group(0)
            title_match = re.search(r'title="([^"]+)"', full_div)
            title = title_match.group(1) if title_match else "Détails"
            content_match = re.search(r'<div[^>]*class="quest-block"[^>]*>(.*?)</div>', full_div, flags=re.DOTALL)
            content = content_match.group(1) if content_match else ""
            content = re.sub(r'^\s*<p>\s*<span[^>]*class="[^"]*tag-[^"]*"[^>]*>.*?</span>\s*:?\s*</p>', '', content,
                             flags=re.IGNORECASE | re.DOTALL)
            return (f'<div class="quest-block" data-tooltip="{title}">'
                    f'<div>{content}</div></div>')

        html = re.sub(r'(<div[^>]*class="quest-block"[^>]*>.*?</div>)', quest_block_replacer, html, flags=re.DOTALL)

        # 6. Checkboxes
        def checkbox_replacer(match):
            self.cb_counter += 1
            idx = self.cb_counter
            following_text = match.group(2).strip()
            unique_key = f"{current_step_id}_{idx}"
            is_checked = checkbox_states.get(unique_key, False)
            checked_attr = "checked" if is_checked else ""
            return (f'<div class="checkbox-row">'
                    f'<input type="checkbox" {checked_attr} onclick="onCheckboxClick(\'{unique_key}\', this.checked)">'
                    f'<span class="cb-text">{following_text}</span></div>')

        html = re.sub(
            r'(<input[^>]*type="checkbox"[^>]*>)(.*?)(?=<br>|<\/p>|<\/div>|<\/li>|$)',
            checkbox_replacer, html, flags=re.IGNORECASE | re.DOTALL
        )

        return html