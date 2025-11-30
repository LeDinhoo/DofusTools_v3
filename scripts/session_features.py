import os
import time
import re


class SessionFeatures:
    def __init__(self, logger_func, parser_script, saves_dir="saves"):
        self.log = logger_func
        self.parser = parser_script
        self.saves_dir = saves_dir
        self.session_file = os.path.join(saves_dir, "session.json")

        # Le Modèle de données (Data)
        self.open_guides = []
        self.active_index = -1

    # --- GESTION LISTE ---

    def add_guide(self, name, steps, filename="", guide_id=None):
        """Ajoute un guide à la liste ou active l'existant s'il est déjà ouvert"""

        # 1. VERIFICATION DOUBLON
        for i, guide in enumerate(self.open_guides):
            # On vérifie d'abord par ID (plus fiable)
            if guide_id and str(guide.get('id')) == str(guide_id):
                self.log(f"⚡ Guide déjà ouvert, bascule sur l'onglet {i + 1}.")
                self.active_index = i
                self.save_session_to_disk()
                return i

            # Sinon par nom (fallback pour les guides locaux sans ID)
            if not guide_id and guide['name'] == name:
                self.log(f"⚡ Guide déjà ouvert, bascule sur l'onglet {i + 1}.")
                self.active_index = i
                self.save_session_to_disk()
                return i

        # 2. AJOUT SI NOUVEAU
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
        """Supprime un guide de la liste"""
        if 0 <= index < len(self.open_guides):
            del self.open_guides[index]

            # Recalcul de l'index actif
            if index == self.active_index:
                self.active_index = max(0, len(self.open_guides) - 1)
            elif index < self.active_index:
                self.active_index -= 1

            if not self.open_guides:
                self.active_index = -1

            self.save_session_to_disk()

    def get_active_guide(self):
        if 0 <= self.active_index < len(self.open_guides):
            return self.open_guides[self.active_index]
        return None

    def set_active_index(self, index):
        if 0 <= index < len(self.open_guides):
            self.active_index = index
            self.save_session_to_disk()

    # --- PERSISTANCE (SAUVEGARDE/CHARGEMENT) ---

    def _get_progression_path(self, identifier):
        """Chemin du fichier de progression pour un guide spécifique"""
        if str(identifier).isdigit():
            return os.path.join(self.saves_dir, f"{identifier}.json")

        safe_name = re.sub(r'[<>:"/\\|?*]', '', str(identifier)).replace(' ', '_').lower()
        return os.path.join(self.saves_dir, f"{safe_name}.json")

    def _load_progress_index(self, identifier):
        """Charge l'index de l'étape sauvegardée"""
        path = self._get_progression_path(identifier)
        data = self.parser.load_file(path)
        return data.get("current_idx", 0) if data else 0

    def find_guide_in_library(self, guide_id):
        """Vérifie si un guide existe déjà dans le dossier guides/ (cache local)"""
        # Le dossier 'guides' est le standard utilisé par parser.save_guide_to_library
        expected_path = os.path.join("guides", f"{guide_id}.json")
        if os.path.exists(expected_path):
            return expected_path
        return None

    def save_current_progress(self):
        """Sauvegarde l'avancement du guide actif uniquement"""
        guide = self.get_active_guide()
        if not guide: return

        unique_key = guide['id'] if guide['id'] else guide['name']
        path = self._get_progression_path(unique_key)

        data = {
            "guide_id": guide['id'],
            "guide_name": guide['name'],
            "current_idx": guide['current_idx'],
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.parser.save_file(path, data)

    def save_session_to_disk(self):
        """Sauvegarde la liste des onglets ouverts pour la prochaine fois"""
        session_data = {
            "active_tab": self.active_index,
            "open_guides": []
        }
        for guide in self.open_guides:
            session_data["open_guides"].append({
                "file_path": guide['file'],
                "id": guide['id'],
                "name": guide['name']
            })
        self.parser.save_file(self.session_file, session_data)

    def load_last_session(self):
        """Retourne les infos pour restaurer la session (liste de fichiers à ouvrir)"""
        data = self.parser.load_file(self.session_file)
        if not data: return None, -1
        return data.get("open_guides", []), data.get("active_tab", -1)