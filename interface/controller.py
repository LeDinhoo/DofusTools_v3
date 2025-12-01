import threading
import time
import os
import re
import logging
from PyQt6.QtWidgets import QFileDialog, QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

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


class MainController(QObject):
    """
    Contrôleur principal adapté pour PyQt6 avec gestion des signaux pour le Thread-Safety.
    """

    # --- DÉFINITION DES SIGNAUX ---
    # Ces signaux permettent de communiquer du Background Thread -> Main UI Thread
    sig_open_guide = pyqtSignal(dict, str)  # data, path
    sig_refresh_ui = pyqtSignal()
    sig_log_error = pyqtSignal(str)
    sig_show_debug = pyqtSignal(str)  # path image
    sig_bind_result = pyqtSignal(bool, str)  # success, target_name

    def __init__(self, view_app):
        super().__init__()  # Init QObject
        self.view = view_app

        self.next_travel_command = None
        self.ocr_zone_rect = None
        self.is_restoring_session = False
        self.is_macro_running = False
        self.is_auto_travel_enabled = True

        self.parser = ParserScripts()
        self.mouse = MouseScripts()
        self.system = SystemScripts()
        self.window = WindowScripts()
        self.network = NetworkFeatures()

        self.keyboard = KeyboardScripts(window_manager=self.window)
        self.session = SessionFeatures(parser_script=self.parser)
        self.ocr = OcrScripts()
        self.overlay = OverlayScripts()
        self.snipping = SnippingTool()

        # --- CONNEXION DES SIGNAUX ---
        # Quand le signal est émis, la méthode connectée s'exécutera sur le Thread Principal
        self.sig_open_guide.connect(self._open_guide_slot)
        self.sig_refresh_ui.connect(self.refresh_ui_state)
        self.sig_log_error.connect(lambda msg: logger.error(msg))
        self.sig_show_debug.connect(lambda p: self.view.show_debug_image(p))
        self.sig_bind_result.connect(self._handle_bind_result_slot)

    def startup(self):
        logger.info("Contrôleur démarré (PyQt6). Restauration de la session...")
        self.restore_session()

    def run_threaded(self, func):
        """Lance une fonction dans un thread séparé (daemon)"""

        def safe_wrapper():
            try:
                func()
            except Exception as e:
                logger.error(f"Erreur dans le thread {func.__name__} : {e}", exc_info=True)

        threading.Thread(target=safe_wrapper, daemon=True).start()

    def toggle_auto_travel(self):
        self.is_auto_travel_enabled = not self.is_auto_travel_enabled
        status = "ACTIVÉ" if self.is_auto_travel_enabled else "DÉSACTIVÉ"
        logger.info(f"Déplacement automatique {status}")
        return self.is_auto_travel_enabled

    # =========================================================================
    #                             WRAPPERS D'ACTIONS
    # =========================================================================

    def action_load_json_wrapper(self):
        try:
            filename, _ = QFileDialog.getOpenFileName(self.view, "Ouvrir Config", "", "JSON Files (*.json)")
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
        except Exception as e:
            logger.error(f"Erreur load json: {e}")

    def action_bind_window_wrapper(self):
        try:
            # On lit le texte depuis l'UI (Main Thread)
            if hasattr(self.view.ui_sidebar, 'bind_entry'):
                target = self.view.ui_sidebar.bind_entry.text()
            else:
                target = ""

            if not target:
                logger.warning("Liaison : Aucun nom de personnage saisi.")
                self.view.ui_sidebar.update_bind_status("error")
                return

            # Travail lourd en thread
            def _task():
                success = self.window.bind_window(target)
                # Résultat renvoyé au main thread via signal
                self.sig_bind_result.emit(success, target)

            self.run_threaded(_task)
        except Exception as e:
            logger.error(f"Erreur bind wrapper: {e}")

    def _handle_bind_result_slot(self, success, target):
        """Exécuté sur le Main Thread après le bind"""
        if success:
            self.session.save_last_character(target)
            self.view.ui_sidebar.update_bind_status("success")
        else:
            self.view.ui_sidebar.update_bind_status("error")

    def action_define_ocr_zone_wrapper(self):
        def on_zone_selected(zone_rect):
            self.ocr_zone_rect = zone_rect
            self.session.save_ocr_zone(zone_rect)
            # Overlay doit être appelé sur le main thread, mais draw_zone utilise QTimer en interne ou est safe
            # Dans le doute, on peut utiliser QTimer ici car on est déjà sur le main thread (callback UI)
            self.overlay.draw_zone(zone_rect[0], zone_rect[1], zone_rect[2], zone_rect[3],
                                   color="#00ff00", alpha=0.3, duration=2000)
            logger.info(f"Zone OCR configurée : {zone_rect}")

        logger.info("Veuillez sélectionner la zone de texte à surveiller...")
        self.snipping.start_selection(on_zone_selected)

    def action_ocr_wrapper(self):
        try:
            target = self.view.ui_sidebar.ocr_target_entry.text()
            raw_thresh = self.view.ui_sidebar.ocr_threshold_entry.text()
            is_grayscale = self.view.ui_sidebar.chk_grayscale.isChecked()
            threshold = int(raw_thresh) if raw_thresh.isdigit() else 190

            def _task():
                # Overlay doit être nettoyé sur le main thread
                QTimer.singleShot(0, self.overlay.clear_all)

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
                    self.sig_show_debug.emit(debug_path)

                if coords:
                    x, y = coords
                    # Overlay thread-safe via QTimer interne ou signal
                    QTimer.singleShot(0, lambda: self.overlay.draw_dot(x, y, color="#ff0000", size=20, duration=5000))
                    logger.info(f"📍 Cible localisée en ({x}, {y})")

            self.run_threaded(_task)
        except Exception as e:
            logger.error(f"Erreur OCR Wrapper: {e}")

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
        """Met à jour l'interface. Doit être appelé sur le Main Thread."""
        if self.is_restoring_session: return

        try:
            guide = self.session.get_active_guide()

            # Mise à jour des onglets
            self.view.ui_guide.update_tabs(self.session.open_guides, self.session.active_index)

            if guide:
                if not guide.get('steps'):
                    logger.warning(f"Le guide '{guide.get('name')}' ne contient aucune étape valide.")

                self.view.ui_guide.update_content(guide, self.parser)

                self.next_travel_command = None
                current_idx = guide.get('current_idx', 0)
                steps = guide.get('steps', [])

                if 0 <= current_idx < len(steps):
                    current_step = steps[current_idx]
                    current_text_html = self.parser.get_step_web_text(current_step)

                    travel_regex = r'(allez en.*?\[(-?\d+),(-?\d+)\])'
                    match = re.search(travel_regex, current_text_html, re.IGNORECASE)

                    if match:
                        x, y = match.group(2), match.group(3)
                        self.next_travel_command = f"/travel {x},{y}"
                        logger.info(f"🔔 Commande détectée : {match.group(1).strip()}")
            else:
                self.view.ui_guide.update_content(None, self.parser)

        except Exception as e:
            logger.error(f"Erreur refresh UI: {e}", exc_info=True)

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

    def copy_position(self):
        try:
            pos = self.view.ui_guide.lbl_position.text()
            if pos:
                clipboard = QApplication.clipboard()
                clipboard.setText(pos)
                logger.info(f"📋 Copié : {pos}")

                orig_style = self.view.ui_guide.lbl_position.styleSheet()
                self.view.ui_guide.lbl_position.setStyleSheet("color: white;")
                QTimer.singleShot(150, lambda: self.view.ui_guide.lbl_position.setStyleSheet(orig_style))
        except Exception as e:
            logger.error(f"Erreur copie: {e}")

    # --- LOGIQUE PRINCIPALE DE CHARGEMENT DE GUIDE ---

    def on_guide_link_clicked(self, link_string):
        """
        Gère les clics sur les liens GUIDE:ID et STEP:ID
        """
        logger.info(f"Traitement lien : {link_string}")
        link_string = link_string.strip()

        # Cas 1 : Changement de GUIDE (ex: "GUIDE:123")
        if link_string.upper().startswith("GUIDE:"):
            gid = link_string.split(":")[1].strip()
            if not gid or not gid.isdigit():
                logger.error(f"ID de guide invalide : {gid}")
                return

            local_path = self.session.find_guide_in_library(gid)
            if local_path:
                logger.info(f"Guide {gid} trouvé en local -> Chargement...")
                self.run_threaded(lambda: self._load_local(local_path, gid))
            else:
                logger.info(f"Guide {gid} non trouvé en local -> Téléchargement...")
                self.run_threaded(lambda: self._fetch_remote(gid))

        # Cas 2 : Changement d'ÉTAPE
        elif link_string.upper().startswith("STEP:"):
            s_val = link_string.split(":")[1].strip()
            try:
                t_idx = int(s_val) - 1
                g = self.session.get_active_guide()
                if g and 0 <= t_idx < len(g['steps']):
                    g['current_idx'] = t_idx
                    self.session.save_current_progress()
                    self.refresh_ui_state()  # Déjà sur main thread car appelé depuis UI
                    logger.info(f"Saut vers l'étape {t_idx + 1}")
            except ValueError:
                pass

    def _load_local(self, path, gid):
        """Exécuté dans un thread secondaire"""
        try:
            data = self.parser.load_file(path)
            if data:
                # Émission du signal pour exécuter _open_guide_slot sur le Main Thread
                self.sig_open_guide.emit(data, path)
            else:
                self.sig_log_error.emit(f"Impossible de lire le fichier local : {path}")
        except Exception as e:
            self.sig_log_error.emit(f"Erreur load local: {e}")

    def _fetch_remote(self, gid):
        """Exécuté dans un thread secondaire"""
        try:
            data, err = self.network.fetch_guide_data(gid)
            if err:
                self.sig_log_error.emit(f"❌ Erreur téléchargement guide {gid} : {err}")
                return

            if data:
                path = self.parser.save_guide_to_library(data)
                if path:
                    logger.info(f"Guide {gid} sauvegardé dans : {path}")
                    # Émission du signal
                    self.sig_open_guide.emit(data, path)
                else:
                    self.sig_log_error.emit("Erreur à la sauvegarde du guide téléchargé.")
        except Exception as e:
            self.sig_log_error.emit(f"Erreur fetch remote: {e}")

    def _open_guide_slot(self, data, path):
        """
        SLOT exécuté sur le Main Thread via le signal sig_open_guide.
        C'est ici qu'on manipule l'UI et la Session.
        """
        try:
            steps = self.parser.get_steps_list(data)
            if not steps:
                logger.error(f"Le guide téléchargé/chargé ne contient aucune étape valide ! Path: {path}")
                return

            name = data.get("name", f"Guide {data.get('id')}")
            gid = data.get("id")

            # Ajout/Focus du guide
            idx = self.session.add_guide(name, steps, path, gid)

            # Mise à jour index
            self.session.set_active_index(idx)

            logger.info(f"Ouverture réussie : {name} (Index {idx})")

            # Rafraîchissement UI
            self.refresh_ui_state()

        except Exception as e:
            logger.error(f"Erreur fatale dans _open_guide_slot: {e}", exc_info=True)

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

            last_char = self.session.get_last_character()

            # Utilisation d'un timer simple ici car on est déjà sur le main thread lors du startup
            # (appelé via QTimer.singleShot depuis dashboard)
            def _restore_ui():
                try:
                    if last_char:
                        logger.info(f"Tentative de liaison auto avec : {last_char}")
                        if hasattr(self.view, 'ui_sidebar'):
                            if hasattr(self.view.ui_sidebar, 'bind_entry'):
                                self.view.ui_sidebar.bind_entry.setText(last_char)
                            QTimer.singleShot(500, self.action_bind_window_wrapper)

                    last_zone = self.session.get_last_ocr_zone()
                    if last_zone and isinstance(last_zone, (list, tuple)) and len(last_zone) == 4:
                        try:
                            self.ocr_zone_rect = tuple(map(int, last_zone))
                            logger.info(f"Zone OCR restaurée : {self.ocr_zone_rect}")
                        except ValueError:
                            self.ocr_zone_rect = None
                except Exception as e:
                    logger.error(f"Erreur restore UI: {e}", exc_info=True)

            QTimer.singleShot(0, _restore_ui)

        except Exception as e:
            logger.error(f"Erreur fatale restore_session: {e}", exc_info=True)
        finally:
            self.is_restoring_session = False
            self.refresh_ui_state()