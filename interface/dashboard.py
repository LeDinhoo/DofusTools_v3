import tkinter as tk
from tkinter import scrolledtext
from tkinter import filedialog
import threading
import time
import os
import re
import urllib.request
import json

# Imports des modules systèmes
from scripts.mouse_features import MouseScripts
from scripts.system_features import SystemScripts
from scripts.keyboard_features import KeyboardScripts
from scripts.window_features import WindowScripts
from scripts.parser_features import ParserScripts
from scripts.network_features import NetworkFeatures
from scripts.session_features import SessionFeatures
from scripts.ocr_features import OcrScripts

# --- IMPORT DES PANNEAUX ---
from .panels.sidebar import SidebarPanel
from .panels.guide_view import GuidePanel
from .panels.logger import LoggerPanel


class AppLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Automation Hub")
        self.root.geometry("1100x850")

        # Configuration des couleurs (Mode Sombre Standard)
        self.bg_color = "#121212"
        self.root.configure(bg=self.bg_color)

        # --- 1. BARRE DE TITRE WINDOWS STANDARD ---
        # Suppression du mode Borderless pour revenir à la barre native
        # self.root.overrideredirect(True) # Ligne commentée / supprimée

        # Suppression des attributs qui géraient la barre des tâches sans titre bar
        # self.root.wm_attributes('-topmost', True)
        # self.root.wm_attributes('-toolwindow', False)
        # self.root.wm_attributes('-alpha', 0.95)

        # Variables fenêtre (conservées mais inutiles pour le déplacement natif)
        self.offsetx = 0
        self.offsety = 0

        self.show_left = True
        self.show_right = True

        # --- 2. INITIALISATION DES CONTRÔLEURS ---
        self.ui_logger = None

        self.mouse = MouseScripts(self.log_message)
        self.system = SystemScripts(self.log_message)
        self.window = WindowScripts(self.log_message)
        self.keyboard = KeyboardScripts(self.log_message, window_manager=self.window)
        self.parser = ParserScripts(self.log_message)
        self.network = NetworkFeatures(self.log_message)
        self.session = SessionFeatures(self.log_message, self.parser)
        self.ocr = OcrScripts(self.log_message)

        # NOUVELLE VARIABLE DE MÉMOIRE POUR LA MACRO
        self.next_travel_command = None

        # --- 3. CONSTRUCTION DE L'INTERFACE ---
        self.setup_ui()

        # --- 4. STARTUP ---
        self.root.after(100, self.restore_session_ui)
        self.log_message("Système chargé (Macro Travel prête).")

    def log_message(self, msg):
        if self.ui_logger:
            self.ui_logger.log(msg)
        else:
            print(f"[INIT] {msg}")

    def setup_ui(self):
        # HEADER (On le recrée ici pour les boutons Toggle)
        header_toggle_frame = tk.Frame(self.root, bg="#1f1f1f", height=40)
        header_toggle_frame.pack(fill="x", side="top")
        header_toggle_frame.pack_propagate(False)

        # Titre central (Pour le style)
        lbl_title = tk.Label(header_toggle_frame, text=" DASHBOARD MODULAIRE", font=("Segoe UI", 11, "bold"),
                             bg="#1f1f1f", fg="#e0e0e0")
        lbl_title.pack(side="left", padx=10)

        # Les boutons Toggle
        tk.Frame(header_toggle_frame, width=1, bg="#333").pack(side="right", fill="y", padx=5)

        self.btn_logs = tk.Button(header_toggle_frame, text="📝 Logs", command=self.toggle_right_panel,
                                  bg="#1f1f1f", fg="#4da6ff", font=("Segoe UI", 9, "bold"),
                                  relief="flat", bd=0, activebackground="#333", activeforeground="#4da6ff")
        self.btn_logs.pack(side="right", padx=5)

        self.btn_actions = tk.Button(header_toggle_frame, text="⚡ Actions", command=self.toggle_left_panel,
                                     bg="#1f1f1f", fg="#4da6ff", font=("Segoe UI", 9, "bold"),
                                     relief="flat", bd=0, activebackground="#333", activeforeground="#4da6ff")
        self.btn_actions.pack(side="right", padx=5)

        # CORPS PRINCIPAL (Conteneur)
        self.main_frame = tk.Frame(self.root, bg=self.bg_color)
        self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # PANNEAUX (Injectés dans la grille)
        self.ui_sidebar = SidebarPanel(self.main_frame, self)
        self.ui_sidebar.grid(row=0, column=0, sticky="ns")

        self.ui_guide = GuidePanel(self.main_frame, self)
        self.ui_guide.grid(row=0, column=1, sticky="nsew")

        self.ui_logger = LoggerPanel(self.main_frame)
        self.ui_logger.grid(row=0, column=2, sticky="ns")

    # =========================================================================
    #                             LOGIQUE FENÊTRE
    # =========================================================================

    def toggle_left_panel(self):
        if self.show_left:
            self.ui_sidebar.grid_remove()
            self.btn_actions.config(fg="#666")
        else:
            self.ui_sidebar.grid()
            self.btn_actions.config(fg="#4da6ff")
        self.show_left = not self.show_left

    def toggle_right_panel(self):
        if self.show_right:
            self.ui_logger.grid_remove()
            self.btn_logs.config(fg="#666")
        else:
            self.ui_logger.grid()
            self.btn_logs.config(fg="#4da6ff")
        self.show_right = not self.show_right

    # =========================================================================
    #                             LOGIQUE MÉTIER (Relais)
    # =========================================================================

    def run_threaded(self, func):
        threading.Thread(target=func, daemon=True).start()

    # --- NAVIGATION ---
    def refresh_ui_state(self):
        """Met à jour l'affichage complet, vérifie l'auto-travel et met à jour la commande en mémoire."""
        self.ui_guide.update_tabs(self.session.open_guides, self.session.active_index)
        guide = self.session.get_active_guide()
        self.ui_guide.update_content(guide, self.parser)

        # --- GESTION DE LA COMMANDE EN MÉMOIRE (self.next_travel_command) ---
        self.next_travel_command = None  # Réinitialisation

        if guide:
            current_idx = guide['current_idx']
            current_step = guide['steps'][current_idx]
            current_text_html = self.parser.get_step_web_text(current_step)

            # Détection stricte : Cherche "allez en" et capture les coordonnées [x,y]
            travel_regex = r'(allez en.*?\[(-?\d+),(-?\d+)\])'  # Capturer les coordonnées X et Y
            match = re.search(travel_regex, current_text_html, re.IGNORECASE)

            if match:
                # 1. Mise en mémoire de la commande /travel X,Y (basée sur la capture de la regex)
                x = match.group(2)  # Premier groupe de capture (X)
                y = match.group(3)  # Deuxième groupe de capture (Y)

                self.next_travel_command = f"/travel {x},{y}"

                # 2. Affichage de l'alerte
                detected_command = match.group(1).strip()
                self.log_message(f"🔔 Étape réalisable automatiquement : {detected_command}")

        # -------------------------------------------------------------------

    def nav_previous(self):
        guide = self.session.get_active_guide()
        if guide and guide['current_idx'] > 0:
            guide['current_idx'] -= 1
            self.session.save_current_progress()
            self.refresh_ui_state()
            # Pas de travel auto quand on va en arrière

    def nav_next(self):
        """Action du bouton Suivant : Lance la macro SI une commande est en mémoire, puis avance l'étape."""
        guide = self.session.get_active_guide()

        if guide and guide['current_idx'] < len(guide['steps']) - 1:

            # 1. Exécution conditionnelle de la macro
            if self.next_travel_command:
                # On lance la macro en thread en utilisant la commande stockée en mémoire
                self.run_threaded(self.macro_travel_to_stored_command)

            # 2. Avance l'étape (vers N+1)
            guide['current_idx'] += 1
            self.session.save_current_progress()

            # 3. Met à jour l'affichage (ceci déclenche la détection pour l'étape N+1)
            self.refresh_ui_state()

        elif guide and guide['current_idx'] == len(guide['steps']) - 1:
            # Si c'est la dernière étape
            self.log_message("ℹ️ Dernière étape du guide atteinte.")
            self.refresh_ui_state()

    def macro_travel_to_stored_command(self):
        """
        Macro complète : utilise self.next_travel_command (stocké après extraction du texte)
        1. S'assure que la fenêtre du jeu a le focus.
        2. Envoie la touche Espace (pour ouvrir le chat).
        3. Envoie la commande stockée.
        4. Envoie la touche Entrée (x2).
        """
        if not self.next_travel_command:
            self.log_message("❌ MACRO ANNULÉE : Aucune commande de voyage en mémoire.")
            return

        if not self.window.bound_handle:
            self.log_message("⚠️ MACRO ÉCHOUÉE : Veuillez lier la fenêtre du jeu d'abord.")
            return

        try:
            travel_command = self.next_travel_command

            self.log_message(f"🚀 MACRO DÉPART ({travel_command})...")

            # 1. Espace (Ouvrir Chat)
            self.keyboard.press_space()
            time.sleep(0.1)

            # 2. Envoyer la commande /travel
            self.keyboard.send_text(travel_command)
            time.sleep(0.1)

            # 3. Entrée (Valider la commande)
            self.keyboard.press_enter()
            time.sleep(0.3)  # AJOUT DU DÉLAI DE 100MS ENTRE LES DEUX ENTRÉES

            # 4. Entrée (Fermer le chat ou revalider)
            self.keyboard.press_enter()

            self.log_message("✅ MACRO TERMINÉE. Déplacement initié.")

        except Exception as e:
            self.log_message(f"❌ Macro Erreur critique : {e}")

    # --- Reste du code (switch_tab, close_tab, etc.) inchangé ---

    def switch_tab(self, index):
        self.session.set_active_index(index)
        self.refresh_ui_state()

    def close_tab(self, index):
        self.session.remove_guide(index)
        self.refresh_ui_state()

    # --- CHARGEMENT ---
    def action_charger_json(self):
        filename = filedialog.askopenfilename(title="Ouvrir Config", filetypes=[("JSON", "*.json")])
        if filename:
            data = self.parser.load_file(filename)
            if data:
                archive = self.parser.save_guide_to_library(data)
                final = archive if archive else filename
                steps = self.parser.get_steps_list(data)
                if steps:
                    name = data.get("name", os.path.basename(filename))
                    gid = data.get("id")
                    self.session.add_guide(name, steps, final, gid)
                    self.log_message(f"✅ Chargé : {name}")
                    self.refresh_ui_state()

    def on_guide_link_clicked(self, link_string):
        if link_string.startswith("GUIDE:"):
            gid = link_string.split(":")[1]
            local = self.session.find_guide_in_library(gid)
            if local:
                self.run_threaded(lambda: self._load_local(local, gid))
            else:
                self.run_threaded(lambda: self._fetch_remote(gid))
        elif link_string.startswith("STEP:"):
            s = link_string.split(":")[1]
            try:
                t = int(s) - 1
                g = self.session.get_active_guide()
                if g and 0 <= t < len(g['steps']):
                    g['current_idx'] = t
                    self.session.save_current_progress()
                    self.refresh_ui_state()
                    self.log_message(f"📍 Saut étape {s}")
            except:
                pass

    def _load_local(self, path, gid):
        data = self.parser.load_file(path)
        if data: self.root.after(0, lambda: self._open_guide(data, path))

    def _fetch_remote(self, gid):
        data, err = self.network.fetch_guide_data(gid)
        if err:
            self.root.after(0, lambda: self.log_message(f"❌ {err}"))
        elif data:
            path = self.parser.save_guide_to_library(data)
            self.root.after(0, lambda: self._open_guide(data, path))

    def _open_guide(self, data, path):
        steps = self.parser.get_steps_list(data)
        if steps:
            name = data.get("name", f"Guide {data.get('id')}")
            gid = data.get("id")
            self.session.add_guide(name, steps, path, gid)
            self.refresh_ui_state()

    def restore_session_ui(self):
        guides, idx = self.session.load_last_session()
        if guides:
            for g in guides:
                if g.get('file_path') and os.path.exists(g['file_path']):
                    d = self.parser.load_file(g['file_path'])
                    if d: self.session.add_guide(g['name'], self.parser.get_steps_list(d), g['file_path'], g['id'])
            self.session.set_active_index(idx)
            self.refresh_ui_state()

    # --- ACTIONS NON LIÉES À LA NAVIGATION ---
    def action_lier(self):
        self.window.bind_window(self.ui_sidebar.bind_entry.get())

    def macro_dofus_space(self):
        self.keyboard.press_space()

    def copy_position(self, event):
        pos = self.ui_guide.var_position.get()
        if pos:
            self.root.clipboard_clear()
            self.root.clipboard_append(pos)
            self.log_message(f"📋 Copié : {pos}")
            lbl = self.ui_guide.lbl_position
            orig = lbl.cget("fg")
            lbl.config(fg="white")
            self.root.after(150, lambda: lbl.config(fg=orig))