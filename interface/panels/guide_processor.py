import re
from PyQt6.QtCore import QUrl


class GuideProcessor:
    def __init__(self):
        self.cb_counter = 0

    def preprocess_content(self, html, current_guide_id, current_step_id, checkbox_states, image_path_callback):
        """
        Traite le HTML brut pour injecter les liens interactifs, les images locales et les checkboxes.
        """
        self.cb_counter = 0

        # 1. Liens Guides & Tooltips
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

        # 2. Images Locales (Téléchargement & Cache)
        # Regex d'origine qui capture toutes les URLs d'images (http...png/jpg/gif)
        urls = set(re.findall(r'(https?://[^"\')\s]+\.(?:png|jpg|jpeg|gif))', html, re.IGNORECASE))
        for url in urls:
            local_path = image_path_callback(url)
            local_url = QUrl.fromLocalFile(local_path).toString()
            html = html.replace(url, local_url)

        # 3. Quest Blocks
        def quest_block_replacer(match):
            full_div = match.group(0)
            title_match = re.search(r'title="([^"]+)"', full_div)
            title = title_match.group(1) if title_match else "Détails"
            content_match = re.search(r'<div[^>]*class="quest-block"[^>]*>(.*?)</div>', full_div, flags=re.DOTALL)
            content = content_match.group(1) if content_match else ""

            # Nettoyage spécifique des balises parasites dans les quest-blocks (comme dans l'original)
            content = re.sub(r'^\s*<p>\s*<span[^>]*class="[^"]*tag-[^"]*"[^>]*>.*?</span>\s*:?\s*</p>', '', content,
                             flags=re.IGNORECASE | re.DOTALL)

            return (f'<div class="quest-block" data-tooltip="{title}">'
                    f'<div>{content}</div></div>')

        html = re.sub(r'(<div[^>]*class="quest-block"[^>]*>.*?</div>)', quest_block_replacer, html, flags=re.DOTALL)

        # 4. Checkboxes
        def checkbox_replacer(match):
            self.cb_counter += 1
            idx = self.cb_counter

            # match.group(1) est l'input, match.group(2) est le texte qui suit
            following_text = match.group(2).strip()
            unique_key = f"{current_step_id}_{idx}"

            is_checked = checkbox_states.get(unique_key, False)
            checked_attr = "checked" if is_checked else ""

            return (f'<div class="checkbox-row">'
                    f'<input type="checkbox" {checked_attr} onclick="onCheckboxClick(\'{idx}\', this.checked)">'
                    f'<span class="cb-text">{following_text}</span></div>')

        html = re.sub(
            r'(<input[^>]*type="checkbox"[^>]*>)(.*?)(?=<br>|<\/p>|<\/div>|<\/li>|$)',
            checkbox_replacer, html, flags=re.IGNORECASE | re.DOTALL
        )

        return html