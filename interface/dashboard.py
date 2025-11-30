import tkinter as tk
from tkinter import filedialog
import threading
import time
import os
import re
import logging

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

# Configuration du logger pour ce fichier
logger = logging.getLogger(__name__)


class AppLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Automation Hub")
        self.root.geometry("1100x850")
        self.bg_color = "#121212"
        self.root.configure(bg=self.bg_color)

        self.show_left = True
        self.show_right = True
        self.next_travel_command = None

        # --- 1. INITIALISATION DES CONTROLEURS ---
        # (Déplacé AVANT setup_ui pour que la Sidebar puisse accéder à self.keyboard/mouse)
        self.parser = ParserScripts()
        self.mouse = MouseScripts()
        self.system = SystemScripts()
        self.window = WindowScripts()
        self.network = NetworkFeatures()

        # Injection de dépendances spécifiques
        self.keyboard = KeyboardScripts(window_manager=self.window)
        self.session = SessionFeatures(parser_script=self.parser)
        self.ocr = OcrScripts()

        # --- 2. SETUP UI ---
        # (Crée les panneaux, dont la Sidebar qui utilise les contrôleurs)
        self.setup_ui()

        # --- 3. SETUP LOGGING ---
        # (Configure le logger et l'attache au LoggerPanel maintenant créé)
        self.setup_logging()

        # --- 4. STARTUP ---
        self.root.after(100, self.restore_session_ui)
        logger.info("Système chargé (Architecture v2).")

    def setup_logging(self):
        """Configure le système de log global"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        # Nettoyage des handlers existants pour éviter les doublons si rappelée
        root_logger.handlers.clear()

        # Handler Console (Debug)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(console_handler)

        # Handler UI (Panel)
        if hasattr(self, 'ui_logger'):
            root_logger.addHandler(self.ui_logger.handler)

    def setup_ui(self):
        # HEADER
        header_toggle_frame = tk.Frame(self.root, bg="#1f1f1f", height=40)
        header_toggle_frame.pack(fill="x", side="top")
        header_toggle_frame.pack_propagate(False)

        lbl_title = tk.Label(header_toggle_frame, text=" DASHBOARD MODULAIRE", font=("Segoe UI", 11, "bold"),
                             bg="#1f1f1f", fg="#e0e0e0")
        lbl_title.pack(side="left", padx=10)

        tk.Frame(header_toggle_frame, width=1, bg="#333").pack(side="right", fill="y", padx=5)

        self.btn_logs = tk.Button(header_toggle_frame, text="📝 Logs", command=self.toggle_right_panel,
                                  bg="#1f1f1f", fg="#4da6ff", font=("Segoe UI", 9, "bold"),
                                  relief="flat", bd=0, activebackground="#333", activeforeground="#4da6ff")
        self.btn_logs.pack(side="right", padx=5)

        self.btn_actions = tk.Button(header_toggle_frame, text="⚡ Actions", command=self.toggle_left_panel,
                                     bg="#1f1f1f", fg="#4da6ff", font=("Segoe UI", 9, "bold"),
                                     relief="flat", bd=0, activebackground="#333", activeforeground="#4da6ff")
        self.btn_actions.pack(side="right", padx=5)

        # CORPS
        self.main_frame = tk.Frame(self.root, bg=self.bg_color)
        self.main_frame.pack(fill="both", expand=True)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # PANNEAUX
        self.ui_sidebar = SidebarPanel(self.main_frame, self)
        self.ui_sidebar.grid(row=0, column=0, sticky="ns")

        self.ui_guide = GuidePanel(self.main_frame, self)
        self.ui_guide.grid(row=0, column=1, sticky="nsew")

        self.ui_logger = LoggerPanel(self.main_frame)
        self.ui_logger.grid(row=0, column=2, sticky="ns")

    # =========================================================================
    #                             WRAPPERS D'ACTIONS
    # =========================================================================
    # Ces méthodes sont appelées par la Sidebar. Elles décident du Threading.

    def run_threaded(self, func):
        threading.Thread(target=func, daemon=True).start()

    def action_load_json_wrapper(self):
        # Exécuté sur le thread principal car ouvre une popup système
        self.action_charger_json()

    def action_bind_window_wrapper(self):
        target = self.ui_sidebar.bind_entry.get()
        self.run_threaded(lambda: self.window.bind_window(target))

    def action_ocr_wrapper(self):
        target = self.ui_sidebar.ocr_target_entry.get()
        self.run_threaded(lambda: self.ocr.run_ocr_for_key_Z(
            self.window, self.keyboard, target=target
        ))

    def action_click_center_wrapper(self):
        self.run_threaded(self.mouse.click_centre)

    def action_list_windows_wrapper(self):
        self.run_threaded(self.window.demo_lister_tout)

    def action_macro_space_wrapper(self):
        self.run_threaded(self.keyboard.press_space)

    # =========================================================================
    #                             LOGIQUE UI
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

    def refresh_ui_state(self):
        self.ui_guide.update_tabs(self.session.open_guides, self.session.active_index)
        guide = self.session.get_active_guide()
        self.ui_guide.update_content(guide, self.parser)

        self.next_travel_command = None
        if guide:
            current_idx = guide['current_idx']
            current_step = guide['steps'][current_idx]
            current_text_html = self.parser.get_step_web_text(current_step)

            travel_regex = r'(allez en.*?\[(-?\d+),(-?\d+)\])'
            match = re.search(travel_regex, current_text_html, re.IGNORECASE)

            if match:
                x, y = match.group(2), match.group(3)
                self.next_travel_command = f"/travel {x},{y}"
                logger.info(f"🔔 Commande détectée : {match.group(1).strip()}")

    def nav_previous(self):
        guide = self.session.get_active_guide()
        if guide and guide['current_idx'] > 0:
            guide['current_idx'] -= 1
            self.session.save_current_progress()
            self.refresh_ui_state()

    def nav_next(self):
        guide = self.session.get_active_guide()
        if guide and guide['current_idx'] < len(guide['steps']) - 1:
            if self.next_travel_command:
                self.run_threaded(self.macro_travel_to_stored_command)

            guide['current_idx'] += 1
            self.session.save_current_progress()
            self.refresh_ui_state()
        elif guide and guide['current_idx'] == len(guide['steps']) - 1:
            logger.info("ℹ️ Dernière étape du guide atteinte.")
            self.refresh_ui_state()

    def macro_travel_to_stored_command(self):
        if not self.next_travel_command: return
        if not self.window.bound_handle:
            logger.warning("⚠️ Fenêtre non liée pour la macro.")
            return

        try:
            cmd = self.next_travel_command
            logger.info(f"🚀 MACRO START ({cmd})")

            self.keyboard.press_space()
            time.sleep(0.1)
            self.keyboard.send_text(cmd)
            time.sleep(0.1)
            self.keyboard.press_enter()
            time.sleep(0.3)
            self.keyboard.press_enter()

            logger.info("✅ MACRO END")
        except Exception as e:
            logger.error(f"❌ Erreur Macro : {e}")

    def switch_tab(self, index):
        self.session.set_active_index(index)
        self.refresh_ui_state()

    def close_tab(self, index):
        self.session.remove_guide(index)
        self.refresh_ui_state()

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
                    logger.info(f"✅ Chargé : {name}")
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
            except:
                pass

    def _load_local(self, path, gid):
        data = self.parser.load_file(path)
        if data: self.root.after(0, lambda: self._open_guide(data, path))

    def _fetch_remote(self, gid):
        data, err = self.network.fetch_guide_data(gid)
        if err:
            logger.error(f"❌ {err}")
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

    def copy_position(self, event):
        pos = self.ui_guide.var_position.get()
        if pos:
            self.root.clipboard_clear()
            self.root.clipboard_append(pos)
            logger.info(f"📋 Copié : {pos}")

            lbl = self.ui_guide.lbl_position
            orig = lbl.cget("fg")
            lbl.config(fg="white")
            self.root.after(150, lambda: lbl.config(fg=orig))