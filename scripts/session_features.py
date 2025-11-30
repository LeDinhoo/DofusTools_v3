import os
import time
import re
import logging

logger = logging.getLogger(__name__)

class SessionFeatures:
    def __init__(self, parser_script, saves_dir="saves"):
        # self.log supprimé, utilisation de 'logger' global au module
        self.parser = parser_script
        self.saves_dir = saves_dir
        self.session_file = os.path.join(saves_dir, "session.json")
        self.open_guides = []
        self.active_index = -1

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
            "active_tab": self.active_index,
            "open_guides": [{"file_path": g['file'], "id": g['id'], "name": g['name']} for g in self.open_guides]
        }
        self.parser.save_file(self.session_file, session_data)

    def load_last_session(self):
        data = self.parser.load_file(self.session_file)
        if not data: return None, -1
        return data.get("open_guides", []), data.get("active_tab", -1)