import threading
import time
import os
import re
import logging
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog  # <--- CORRECTION : Import explicite nécessaire

# Imports des scripts fonctionnels
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

logger = logging.getLogger(__name__)


class MainController:
    """
    Contrôleur principal qui gère la communication entre l'UI (View) et les Scripts (Model).
    """

    def __init__(self, view_app):
        self.view = view_app

        # État interne
        self.next_travel_command = None
        self.ocr_zone_rect = None
        self.is_restoring_session = False
        self.is_macro_running = False
        self.debug_window_ref = None

        # --- NOUVEAU : État du déplacement automatique ---
        self.is_auto_travel_enabled = True

        # --- INITIALISATION DES SCRIPTS ---
        self.parser = ParserScripts()
        self.mouse = MouseScripts()
        self.system = SystemScripts()
        self.window = WindowScripts()
        self.network = NetworkFeatures()

        self.keyboard = KeyboardScripts(window_manager=self.window)
        self.session = SessionFeatures(parser_script=self.parser)
        self.ocr = OcrScripts()
        self.overlay = OverlayScripts(self.view.root)
        self.snipping = SnippingTool(self.view.root)

    def startup(self):
        """Appelé une fois que l'UI est prête"""
        logger.info("Contrôleur démarré. Restauration de la session...")
        self.restore_session()

    def run_threaded(self, func):
        threading.Thread(target=func, daemon=True).start()

    # --- NOUVEAU : Toggle Auto-Travel ---
    def toggle_auto_travel(self):
        self.is_auto_travel_enabled = not self.is_auto_travel_enabled
        status = "ACTIVÉ" if self.is_auto_travel_enabled else "DÉSACTIVÉ"
        logger.info(f"Déplacement automatique {status}")
        return self.is_auto_travel_enabled

    # =========================================================================
    #                             WRAPPERS D'ACTIONS
    # =========================================================================

    def action_load_json_wrapper(self):
        # CORRECTION : Utilisation directe de 'filedialog' importé explicitement
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

    def action_bind_window_wrapper(self):
        target = self.view.ui_sidebar.bind_entry.get().strip()
        if not target:
            logger.warning("Liaison : Aucun nom de personnage saisi.")
            self.view.ui_sidebar.update_bind_status("error")
            return

        def _task():
            success = self.window.bind_window(target)
            if success:
                self.session.save_last_character(target)
                self.view.root.after(0, lambda: self.view.ui_sidebar.update_bind_status("success"))
            else:
                self.view.root.after(0, lambda: self.view.ui_sidebar.update_bind_status("error"))

        self.run_threaded(_task)

    def action_define_ocr_zone_wrapper(self):
        def on_zone_selected(zone_rect):
            self.ocr_zone_rect = zone_rect
            self.session.save_ocr_zone(zone_rect)
            self.overlay.draw_zone(zone_rect[0], zone_rect[1], zone_rect[2], zone_rect[3],
                                   color="#00ff00", alpha=0.2, duration=2000)
            logger.info(f"Zone OCR configurée : {zone_rect}")

        logger.info("Veuillez sélectionner la zone de texte à surveiller...")
        self.snipping.start_selection(on_zone_selected)

    def action_ocr_wrapper(self):
        target = self.view.ui_sidebar.ocr_target_entry.get()
        raw_thresh = self.view.ui_sidebar.ocr_threshold_entry.get()
        is_grayscale = self.view.ui_sidebar.var_grayscale.get()

        try:
            threshold = int(raw_thresh)
        except ValueError:
            threshold = 190  # Valeur par défaut mise à jour

        def _task():
            self.view.root.after(0, self.overlay.clear_all)

            if self.ocr_zone_rect:
                logger.info(f"Lancement OCR sur zone : {self.ocr_zone_rect}")
            else:
                logger.info("Lancement OCR sur fenêtre complète")

            coords, debug_path = self.ocr.run_ocr_for_key_Z(
                self.window, self.keyboard,
                threshold=threshold,
                target=target,
                zone_rect=self.ocr_zone_rect,
                grayscale=is_grayscale
            )

            if debug_path:
                self.view.root.after(0, lambda: self.view.show_debug_image(debug_path))

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

    def action_macro_space_wrapper(self):
        self.run_threaded(self.keyboard.press_space)

    # =========================================================================
    #                             LOGIQUE MÉTIER & NAVIGATION
    # =========================================================================

    def refresh_ui_state(self):
        if self.is_restoring_session: return

        self.view.ui_guide.update_tabs(self.session.open_guides, self.session.active_index)
        guide = self.session.get_active_guide()
        self.view.ui_guide.update_content(guide, self.parser)

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
        if self.is_macro_running:
            logger.warning("⏳ Macro en cours, veuillez patienter...")
            return

        guide = self.session.get_active_guide()
        if guide and guide['current_idx'] < len(guide['steps']) - 1:
            cmd_to_run = self.next_travel_command

            # --- MODIFICATION : Vérification du flag auto-travel ---
            if cmd_to_run and self.is_auto_travel_enabled:
                self.run_threaded(lambda: self.macro_travel_to_stored_command(cmd_to_run))
            elif cmd_to_run:
                logger.info(f"⚠️ Auto-travel désactivé. Commande ignorée : {cmd_to_run}")

            guide['current_idx'] += 1
            self.session.save_current_progress()
            self.refresh_ui_state()

        elif guide and guide['current_idx'] == len(guide['steps']) - 1:
            logger.info("ℹ️ Dernière étape du guide atteinte.")
            self.refresh_ui_state()

    def macro_travel_to_stored_command(self, cmd_string):
        if not cmd_string or self.is_restoring_session: return

        if not self.window.bound_handle:
            logger.warning("⚠️ MACRO ABANDONNÉE : Aucune fenêtre liée.")
            return

        self.is_macro_running = True
        try:
            if not self.window.ensure_focus():
                logger.error("❌ MACRO ABANDONNÉE : Impossible de focus Dofus.")
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
            self.is_macro_running = False

    def switch_tab(self, index):
        self.session.set_active_index(index)
        self.refresh_ui_state()

    def close_tab(self, index):
        self.session.remove_guide(index)
        self.refresh_ui_state()

    def copy_position(self, event=None):
        pos = self.view.ui_guide.var_position.get()
        if pos:
            self.view.root.clipboard_clear()
            self.view.root.clipboard_append(pos)
            logger.info(f"📋 Copié : {pos}")
            lbl = self.view.ui_guide.lbl_position
            orig = lbl.cget("fg")
            lbl.config(fg="white")
            self.view.root.after(150, lambda: lbl.config(fg=orig))

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
        if data: self.view.root.after(0, lambda: self._open_guide(data, path))

    def _fetch_remote(self, gid):
        data, err = self.network.fetch_guide_data(gid)
        if err:
            logger.error(f"❌ {err}")
        elif data:
            path = self.parser.save_guide_to_library(data)
            self.view.root.after(0, lambda: self._open_guide(data, path))

    def _open_guide(self, data, path):
        steps = self.parser.get_steps_list(data)
        if steps:
            name = data.get("name", f"Guide {data.get('id')}")
            gid = data.get("id")
            self.session.add_guide(name, steps, path, gid)
            self.refresh_ui_state()

    def restore_session(self):
        self.is_restoring_session = True
        try:
            guides, idx = self.session.load_last_session()
            if guides:
                for g in guides:
                    if g.get('file_path') and os.path.exists(g['file_path']):
                        d = self.parser.load_file(g['file_path'])
                        if d: self.session.add_guide(g['name'], self.parser.get_steps_list(d), g['file_path'], g['id'])
                self.session.set_active_index(idx)

                self.view.ui_guide.update_tabs(self.session.open_guides, self.session.active_index)
                guide = self.session.get_active_guide()
                self.view.ui_guide.update_content(guide, self.parser)

            last_char = self.session.get_last_character()
            if last_char:
                logger.info(f"Tentative de liaison auto avec : {last_char}")
                self.view.ui_sidebar.bind_entry.delete(0, tk.END)
                self.view.ui_sidebar.bind_entry.insert(0, last_char)
                self.view.root.after(500, self.action_bind_window_wrapper)
            else:
                if not self.view.ui_sidebar.bind_entry.get():
                    self.view.ui_sidebar.bind_entry.insert(0, "Nom du perso")

            last_zone = self.session.get_last_ocr_zone()
            if last_zone and isinstance(last_zone, (list, tuple)) and len(last_zone) == 4:
                try:
                    self.ocr_zone_rect = tuple(map(int, last_zone))
                    logger.info(f"Zone OCR restaurée : {self.ocr_zone_rect}")
                except ValueError:
                    self.ocr_zone_rect = None
            else:
                self.ocr_zone_rect = None

        finally:
            self.is_restoring_session = False
            self.refresh_ui_state()