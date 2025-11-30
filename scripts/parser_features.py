import json
import os
import re


class ParserScripts:
    def __init__(self, logger_func):
        self.log = logger_func

    # --- PARSING & LECTURE ---

    def parse_string(self, json_content):
        """Transforme une chaîne JSON (Web) en dictionnaire Python"""
        try:
            data = json.loads(json_content)
            return data
        except json.JSONDecodeError as e:
            self.log(f"Parser Erreur : JSON invalide ({e})")
            return None

    def load_file(self, file_path):
        """Charge un fichier JSON depuis le disque"""
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            self.log(f"Parser Erreur lecture : {e}")
            return None

    # --- ÉCRITURE & SAUVEGARDE ---

    def save_file(self, file_path, data):
        """Sauvegarde un dictionnaire en JSON sur le disque"""
        try:
            # Création du dossier parent si inexistant
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            self.log(f"Erreur sauvegarde : {e}")
            return False

    def save_guide_to_library(self, data, folder="guides"):
        """Sauvegarde une copie propre du guide dans le dossier bibliothèque"""
        guide_id = data.get("id")
        name = data.get("name", "guide_inconnu")

        if guide_id:
            safe_filename = f"{guide_id}.json"
        else:
            safe_name = re.sub(r'[<>:"/\\|?*]', '', name).strip().replace(' ', '_').lower()
            safe_filename = f"{safe_name}.json"

        full_path = os.path.join(folder, safe_filename)

        if self.save_file(full_path, data):
            self.log(f"📚 Guide archivé : {safe_filename}")
            return full_path
        return None

    # --- NAVIGATION ET UTILITAIRES ---

    def get_steps_list(self, data):
        return data.get("steps", [])

    def get_step_web_text(self, step, clean_html=False):
        raw_text = step.get("web_text", "")
        if not raw_text: return "Aucune instruction."

        if clean_html:
            clean_text = re.sub(r'<[^>]+>', '', raw_text)
            return clean_text.strip()
        return raw_text

    def get_step_coords(self, step):
        x = step.get("pos_x")
        y = step.get("pos_y")
        if x is not None and y is not None:
            return (x, y)
        return None