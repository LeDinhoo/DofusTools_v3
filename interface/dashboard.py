import tkinter as tk
from tkinter import filedialog
import threading
import time
import os
import re
import logging
from PIL import Image, ImageTk

# Imports des modules systèmes
from scripts.mouse_features import MouseScripts
from scripts.system_features import SystemScripts
from scripts.keyboard_features import KeyboardScripts
from scripts.window_features import WindowScripts
from scripts.parser_features import ParserScripts
from scripts.network_features import NetworkFeatures
from scripts.session_features import SessionFeatures
from scripts.ocr_features import OcrScripts
from scripts.overlay_features import OverlayScripts
from scripts.snipping_tool import SnippingTool

from .panels.sidebar import SidebarPanel
from .panels.guide_view import GuidePanel
from .panels.logger import LoggerPanel

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
        self.debug_window_ref = None

        self.ocr_zone_rect = None
        # Variable pour empêcher les boucles lors de l'init
        self.is_restoring_session = False
        self.is_macro_running = False

        # --- 1. INITIALISATION ---
        self.parser = ParserScripts()
        self.mouse = MouseScripts()
        self.system = SystemScripts()
        self.window = WindowScripts()
        self.network = NetworkFeatures()

        self.keyboard = KeyboardScripts(window_manager=self.window)
        self.session = SessionFeatures(parser_script=self.parser)
        self.ocr = OcrScripts()
        self.overlay = OverlayScripts(self.root)
        self.snipping = SnippingTool(self.root)

        # --- 2. SETUP UI ---
        self.setup_ui()

        # --- 3. SETUP LOGGING ---
        self.setup_logging()

        # --- 4. STARTUP ---
        # On laisse un peu plus de temps à Tkinter pour s'initialiser (200ms)
        self.root.after(200, self.restore_session_ui)
        logger.info("Système chargé (Architecture v2 + Overlay + Snipping + ZoneConfig).")

    def setup_logging(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.handlers.clear()

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(console_handler)

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

    def run_threaded(self, func):
        threading.Thread(target=func, daemon=True).start()

    def action_load_json_wrapper(self):
        self.action_charger_json()

    def action_bind_window_wrapper(self):
        target = self.ui_sidebar.bind_entry.get().strip()
        if not target:
            logger.warning("Liaison : Aucun nom de personnage saisi.")
            self.ui_sidebar.update_bind_status("error")
            return

        def _task():
            success = self.window.bind_window(target)
            if success:
                self.session.save_last_character(target)
                self.root.after(0, lambda: self.ui_sidebar.update_bind_status("success"))
            else:
                self.root.after(0, lambda: self.ui_sidebar.update_bind_status("error"))

        self.run_threaded(_task)

    def show_debug_image(self, image_path):
        if not image_path or not os.path.exists(image_path): return

        if self.debug_window_ref and self.debug_window_ref.winfo_exists():
            self.debug_window_ref.destroy()

        top = tk.Toplevel(self.root)
        top.title(f"Debug OCR : {os.path.basename(image_path)}")
        top.geometry("600x400")

        try:
            pil_img = Image.open(image_path)
            pil_img.thumbnail((800, 600))
            tk_img = ImageTk.PhotoImage(pil_img)

            lbl = tk.Label(top, image=tk_img, bg="black")
            lbl.image = tk_img
            lbl.pack(fill="both", expand=True)
            self.debug_window_ref = top
        except Exception as e:
            logger.error(f"Erreur affichage debug: {e}")

    def action_define_ocr_zone_wrapper(self):
        """Lance l'outil de sélection pour définir la zone d'écoute"""

        def on_zone_selected(zone_rect):
            self.ocr_zone_rect = zone_rect
            # Sauvegarde de la zone dans la session
            self.session.save_ocr_zone(zone_rect)

            self.overlay.draw_zone(zone_rect[0], zone_rect[1], zone_rect[2], zone_rect[3], color="#00ff00", alpha=0.2,
                                   duration=2000)
            logger.info(f"Zone OCR configurée et sauvegardée : {zone_rect}")

        logger.info("Veuillez sélectionner la zone de texte à surveiller...")
        self.snipping.start_selection(on_zone_selected)

    def action_ocr_wrapper(self):
        target = self.ui_sidebar.ocr_target_entry.get()
        raw_thresh = self.ui_sidebar.ocr_threshold_entry.get()
        is_grayscale = self.ui_sidebar.var_grayscale.get()

        try:
            threshold = int(raw_thresh)
        except ValueError:
            threshold = 200

        def _task():
            self.root.after(0, self.overlay.clear_all)

            if self.ocr_zone_rect:
                logger.info(f"Lancement OCR sur zone configurée : {self.ocr_zone_rect}")
            else:
                logger.info("Lancement OCR sur fenêtre complète (Aucune zone définie)")

            coords, debug_path = self.ocr.run_ocr_for_key_Z(
                self.window, self.keyboard,
                threshold=threshold,
                target=target,
                zone_rect=self.ocr_zone_rect,
                grayscale=is_grayscale
            )

            if debug_path:
                self.root.after(0, lambda: self.show_debug_image(debug_path))

            if coords:
                x, y = coords
                self.overlay.draw_dot(x, y, color="#ff0000", size=20, duration=10000)
                logger.info(f"📍 Cible localisée en ({x}, {y})")

        self.run_threaded(_task)

    def action_test_overlay_wrapper(self):
        self.overlay.draw_dot(960, 540, color="#00ff00", size=15, duration=2000)
        self.overlay.draw_zone(100, 100, 200, 100, color="red", duration=2000)

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
        # Sécurité pour éviter de rafraîchir en boucle pendant l'init
        if self.is_restoring_session: return

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
                # On ne logue la détection que si ce n'est pas le tout premier chargement silencieux
                # Mais c'est une info utile, donc on garde le log.
                logger.info(f"🔔 Commande détectée : {match.group(1).strip()}")

    def nav_previous(self):
        guide = self.session.get_active_guide()
        if guide and guide['current_idx'] > 0:
            guide['current_idx'] -= 1
            self.session.save_current_progress()
            self.refresh_ui_state()

    def nav_next(self):
        if self.is_macro_running:
            logger.warning("⏳ Macro en cours, veuillez patienter...")
            return

        guide = self.session.get_active_guide()
        if guide and guide['current_idx'] < len(guide['steps']) - 1:
            cmd_to_run = self.next_travel_command

            # --- MODIFICATION ---
            # On lance la macro UNIQUEMENT si l'utilisateur clique sur Suivant
            # et qu'une commande est prête.
            if cmd_to_run:
                self.run_threaded(lambda: self.macro_travel_to_stored_command(cmd_to_run))

            guide['current_idx'] += 1
            self.session.save_current_progress()
            self.refresh_ui_state()

        elif guide and guide['current_idx'] == len(guide['steps']) - 1:
            logger.info("ℹ️ Dernière étape du guide atteinte.")
            self.refresh_ui_state()

    def macro_travel_to_stored_command(self, cmd_string):
        if not cmd_string: return

        # Double vérification : Si on restaure la session, on interdit le travel automatique
        if self.is_restoring_session:
            return

        if not self.window.bound_handle:
            logger.warning("⚠️ MACRO ABANDONNÉE : Aucune fenêtre liée.")
            return

        self.is_macro_running = True  # Lock
        try:
            if not self.window.ensure_focus():
                logger.error("❌ MACRO ABANDONNÉE : Impossible de focus la fenêtre Dofus.")
                return

            logger.info(f"🚀 MACRO START ({cmd_string})")
            self.keyboard.press_space()
            time.sleep(0.1)
            self.keyboard.send_text(cmd_string)
            time.sleep(0.1)
            self.keyboard.press_enter()
            time.sleep(0.3)
            self.keyboard.press_enter()
            logger.info("✅ MACRO END")
        except Exception as e:
            logger.error(f"❌ Erreur Macro : {e}")
        finally:
            self.is_macro_running = False  # Unlock

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
        self.is_restoring_session = True
        try:
            guides, idx = self.session.load_last_session()
            if guides:
                for g in guides:
                    if g.get('file_path') and os.path.exists(g['file_path']):
                        d = self.parser.load_file(g['file_path'])
                        if d: self.session.add_guide(g['name'], self.parser.get_steps_list(d), g['file_path'], g['id'])
                self.session.set_active_index(idx)

                # Mise à jour manuelle unique de l'UI des guides après chargement
                self.ui_guide.update_tabs(self.session.open_guides, self.session.active_index)
                guide = self.session.get_active_guide()
                self.ui_guide.update_content(guide, self.parser)

            last_char = self.session.get_last_character()
            if last_char:
                logger.info(f"Tentative de liaison auto avec : {last_char}")
                self.ui_sidebar.bind_entry.delete(0, tk.END)
                self.ui_sidebar.bind_entry.insert(0, last_char)
                # On utilise un délai pour laisser le temps à l'UI d'être stable
                # et on ne bloque pas si ça échoue
                self.root.after(500, self.action_bind_window_wrapper)
            else:
                if not self.ui_sidebar.bind_entry.get():
                    self.ui_sidebar.bind_entry.insert(0, "Nom du perso")

            # RESTAURATION ZONE OCR (sécurisée)
            last_zone = self.session.get_last_ocr_zone()
            if last_zone and isinstance(last_zone, (list, tuple)) and len(last_zone) == 4:
                # Assurons-nous que ce sont des entiers
                try:
                    self.ocr_zone_rect = tuple(map(int, last_zone))
                    logger.info(f"Zone OCR restaurée : {self.ocr_zone_rect}")
                except ValueError:
                    logger.error(f"Zone OCR corrompue dans la session : {last_zone}")
                    self.ocr_zone_rect = None
            else:
                self.ocr_zone_rect = None

        finally:
            self.is_restoring_session = False
            # Une dernière mise à jour de l'état pour détecter les commandes travel
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