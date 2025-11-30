import os
import time
import re
import logging

logger = logging.getLogger(__name__)


class SessionFeatures:
    def __init__(self, parser_script, saves_dir="saves"):
        self.parser = parser_script
        self.saves_dir = saves_dir
        self.session_file = os.path.join(saves_dir, "session.json")
        self.open_guides = []
        self.active_index = -1
        # Caches
        self.last_char_name = ""
        self.last_ocr_zone = None  # (x, y, w, h)

    # --- GESTION PREFERENCES ---

    def save_last_character(self, char_name):
        self.last_char_name = char_name
        self.save_session_to_disk()

    def get_last_character(self):
        return self.last_char_name

    def save_ocr_zone(self, zone_rect):
        """Sauvegarde la zone OCR définie (x, y, w, h)"""
        self.last_ocr_zone = zone_rect
        self.save_session_to_disk()

    def get_last_ocr_zone(self):
        return self.last_ocr_zone

    # --- GESTION LISTE GUIDES ---

    def add_guide(self, name, steps, filename="", guide_id=None):
        for i, guide in enumerate(self.open_guides):
            if (guide_id and str(guide.get('id')) == str(guide_id)) or \
                    (not guide_id and guide['name'] == name):
                logger.info(f"Guide existant, focus onglet {i + 1}.")
                self.active_index = i
                self.save_session_to_disk()
                return i

        unique_key = guide_id if guide_id else name
        start_idx = self._load_progress_index(unique_key)

        new_guide = {
            'name': name,
            'id': guide_id,
            'steps': steps,
            'current_idx': start_idx,
            'file': filename
        }
        self.open_guides.append(new_guide)
        self.active_index = len(self.open_guides) - 1
        self.save_session_to_disk()
        return self.active_index

    def remove_guide(self, index):
        if 0 <= index < len(self.open_guides):
            del self.open_guides[index]
            if index == self.active_index:
                self.active_index = max(0, len(self.open_guides) - 1)
            elif index < self.active_index:
                self.active_index -= 1
            if not self.open_guides: self.active_index = -1
            self.save_session_to_disk()

    def get_active_guide(self):
        if 0 <= self.active_index < len(self.open_guides):
            return self.open_guides[self.active_index]
        return None

    def set_active_index(self, index):
        if 0 <= index < len(self.open_guides):
            self.active_index = index
            self.save_session_to_disk()

    # --- IO ---

    def _get_progression_path(self, identifier):
        if str(identifier).isdigit():
            return os.path.join(self.saves_dir, f"{identifier}.json")
        safe_name = re.sub(r'[<>:"/\\|?*]', '', str(identifier)).replace(' ', '_').lower()
        return os.path.join(self.saves_dir, f"{safe_name}.json")

    def _load_progress_index(self, identifier):
        path = self._get_progression_path(identifier)
        data = self.parser.load_file(path)
        return data.get("current_idx", 0) if data else 0

    def find_guide_in_library(self, guide_id):
        expected_path = os.path.join("guides", f"{guide_id}.json")
        return expected_path if os.path.exists(expected_path) else None

    def save_current_progress(self):
        guide = self.get_active_guide()
        if not guide: return
        unique_key = guide['id'] if guide['id'] else guide['name']
        data = {
            "guide_id": guide['id'],
            "guide_name": guide['name'],
            "current_idx": guide['current_idx'],
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.parser.save_file(self._get_progression_path(unique_key), data)

    def save_session_to_disk(self):
        session_data = {
            "character_name": self.last_char_name,
            "ocr_zone": self.last_ocr_zone,  # Sauvegarde de la zone
            "active_tab": self.active_index,
            "open_guides": [{"file_path": g['file'], "id": g['id'], "name": g['name']} for g in self.open_guides]
        }
        self.parser.save_file(self.session_file, session_data)

    def load_last_session(self):
        data = self.parser.load_file(self.session_file)
        if not data: return None, -1

        self.last_char_name = data.get("character_name", "")

        # Chargement sécurisé de la zone (doit être une liste/tuple de 4 éléments)
        zone = data.get("ocr_zone")
        if zone and isinstance(zone, list) and len(zone) == 4:
            self.last_ocr_zone = tuple(zone)
        else:
            self.last_ocr_zone = None

        return data.get("open_guides", []), data.get("active_tab", -1)