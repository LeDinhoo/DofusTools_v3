import threading
import time
import os
import logging
from PyQt6.QtWidgets import QFileDialog, QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

# Import du Moteur de Bot
from scripts.bot_engine import BotEngine
# NOUVEAU : Import des commandes de jeu
from scripts.game_commands import GameCommands

# Les scripts "utilitaires"
from scripts.parser_features import ParserScripts
from scripts.network_features import NetworkFeatures
from scripts.session_features import SessionFeatures
from scripts.ocr_features import OcrScripts
from scripts.overlay_features import OverlayScripts
from scripts.snipping_tool import SnippingTool

# Import du parser sémantique
from interface.panels.guide_parser import GuideParser

logger = logging.getLogger(__name__)


class MainController(QObject):
    """
    Contrôleur principal (UI Logic).
    Rôle : Gérer l'état de l'application (Guides, Session) et transmettre les ordres au BotEngine.
    """

    # --- DÉFINITION DES SIGNAUX ---
    sig_open_guide = pyqtSignal(dict, str)
    sig_refresh_ui = pyqtSignal()
    sig_log_error = pyqtSignal(str)
    sig_show_debug = pyqtSignal(str)
    sig_bind_result = pyqtSignal(bool, str)

    def __init__(self, view_app):
        super().__init__()
        self.view = view_app

        # États de navigation
        self.next_travel_command = None
        self.next_travel_type = "classic"
        self.next_travel_zaap_name = None
        self.next_travel_arg2 = None

        self.ocr_zone_rect = None
        self.is_restoring_session = False
        self.is_auto_travel_enabled = True
        self.is_keyboard_nav_enabled = True

        # --- SEPARATION DES LOGIQUES ---
        # 1. Le Moteur (Séquences complexes)
        self.bot = BotEngine()
        # 2. Les Commandes (Actions unitaires : Travel, Space, etc.)
        self.commands = GameCommands(self.bot)

        # Outils Utilitaires
        self.parser_io = ParserScripts()
        self.semantic_parser = GuideParser()
        self.network = NetworkFeatures()
        self.session = SessionFeatures(parser_script=self.parser_io)
        self.ocr = OcrScripts()
        self.overlay = OverlayScripts()
        self.snipping = SnippingTool()

        # Connexions Signaux
        self.sig_open_guide.connect(self._open_guide_slot)
        self.sig_refresh_ui.connect(self.refresh_ui_state)
        self.sig_log_error.connect(lambda msg: logger.error(msg))
        self.sig_show_debug.connect(lambda p: self.view.show_debug_image(p))
        self.sig_bind_result.connect(self._handle_bind_result_slot)

    def startup(self):
        logger.info("Contrôleur démarré. Restauration de la session...")
        self.restore_session()

    def run_threaded(self, func):
        """Helper pour lancer une tâche sans geler l'UI"""

        def safe_wrapper():
            try:
                func()
            except Exception as e:
                logger.error(f"Erreur dans le thread {func.__name__} : {e}", exc_info=True)

        threading.Thread(target=safe_wrapper, daemon=True).start()

    # --- ACTIONS UI (Liées aux boutons) ---

    def toggle_auto_travel(self):
        self.is_auto_travel_enabled = not self.is_auto_travel_enabled
        status = "ACTIVÉ" if self.is_auto_travel_enabled else "DÉSACTIVÉ"
        logger.info(f"Déplacement automatique {status}")
        return self.is_auto_travel_enabled

    def toggle_keyboard_nav(self):
        self.is_keyboard_nav_enabled = not self.is_keyboard_nav_enabled
        status = "ACTIVÉ" if self.is_keyboard_nav_enabled else "DÉSACTIVÉ"
        logger.info(f"Navigation clavier (A/D) {status}")
        return self.is_keyboard_nav_enabled

    def action_load_json_wrapper(self):
        try:
            filename, _ = QFileDialog.getOpenFileName(self.view, "Ouvrir Config", "", "JSON Files (*.json)")
            if filename:
                data = self.parser_io.load_file(filename)
                if data:
                    archive = self.parser_io.save_guide_to_library(data)
                    final = archive if archive else filename
                    steps = self.parser_io.get_steps_list(data)
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
            if hasattr(self.view.ui_sidebar, 'bind_entry'):
                target = self.view.ui_sidebar.bind_entry.text()
            else:
                target = ""
            if not target:
                logger.warning("Liaison : Aucun nom de personnage saisi.")
                self.view.ui_sidebar.update_bind_status("error")
                return

            def _task():
                success = self.bot.ctx.window.bind_window(target)
                self.sig_bind_result.emit(success, target)

            self.run_threaded(_task)
        except Exception as e:
            logger.error(f"Erreur bind wrapper: {e}")

    def _handle_bind_result_slot(self, success, target):
        if success:
            self.session.save_last_character(target)
            self.view.ui_sidebar.update_bind_status("success")
        else:
            self.view.ui_sidebar.update_bind_status("error")

    def action_define_ocr_zone_wrapper(self):
        def on_zone_selected(zone_rect):
            self.ocr_zone_rect = zone_rect
            self.session.save_ocr_zone(zone_rect)
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
                QTimer.singleShot(0, self.overlay.clear_all)
                if self.ocr_zone_rect:
                    logger.info(f"Lancement OCR sur zone : {self.ocr_zone_rect}")
                else:
                    logger.info("Lancement OCR sur fenêtre complète")

                coords, debug_path = self.ocr.run_ocr_for_key_Z(
                    self.bot.ctx.window, self.bot.ctx.keyboard,
                    threshold=threshold,
                    target=target,
                    zone_rect=self.ocr_zone_rect,
                    grayscale=is_grayscale
                )
                if debug_path:
                    self.sig_show_debug.emit(debug_path)
                if coords:
                    x, y = coords
                    QTimer.singleShot(0, lambda: self.overlay.draw_dot(x, y, color="#ff0000", size=20, duration=5000))
                    logger.info(f"📍 Cible localisée en ({x}, {y})")

            self.run_threaded(_task)
        except Exception as e:
            logger.error(f"Erreur OCR Wrapper: {e}")

    def action_test_overlay_wrapper(self):
        self.overlay.draw_dot(960, 540, color="#00ff00", size=15, duration=2000)
        self.overlay.draw_zone(100, 100, 200, 100, color="red", duration=2000)

    # --- WRAPPERS NETTOYÉS : DÉLÉGATION À GAME_COMMANDS ---

    def action_click_center_wrapper(self):
        self.run_threaded(self.commands.click_center)

    def action_macro_space_wrapper(self):
        self.run_threaded(self.commands.press_space)

    def action_macro_h_click_wrapper(self):
        self.run_threaded(self.commands.go_to_havre_sac)

    def macro_travel_to_stored_command(self, cmd_string):
        """Méthode de compatibilité pour les appels directs"""
        if not cmd_string: return
        self.run_threaded(lambda: self.commands.travel_to(cmd_string))

    # --- LOGIQUE PRINCIPALE ---

    def refresh_ui_state(self):
        """Met à jour l'affichage en fonction de l'étape courante du guide"""
        if self.is_restoring_session: return
        try:
            guide = self.session.get_active_guide()
            self.view.ui_guide.update_tabs(self.session.open_guides, self.session.active_index)

            if guide:
                self.view.ui_guide.update_content(guide, self.parser_io)

                # Reset des variables temporaires d'analyse
                self.next_travel_command = None
                self.next_travel_type = "classic"
                self.next_travel_zaap_name = None
                self.next_travel_arg2 = None

                current_idx = guide.get('current_idx', 0)
                steps = guide.get('steps', [])

                if 0 <= current_idx < len(steps):
                    current_step = steps[current_idx]

                    analysis = self.semantic_parser.parse_step(current_step)

                    self.next_travel_command = analysis['travel_cmd']
                    self.next_travel_type = analysis['macro_type']
                    self.next_travel_zaap_name = analysis['macro_arg']
                    self.next_travel_arg2 = analysis['macro_arg2']

                    if self.next_travel_command or self.next_travel_type != "classic":
                        logger.info(f"Étape analysée : Type={self.next_travel_type}, "
                                    f"Arg={self.next_travel_zaap_name}, "
                                    f"Ctx={self.next_travel_arg2}")
            else:
                self.view.ui_guide.update_content(None, self.parser_io)
        except Exception as e:
            logger.error(f"Erreur refresh UI: {e}", exc_info=True)

    def nav_previous(self):
        guide = self.session.get_active_guide()
        if guide and guide['current_idx'] > 0:
            guide['current_idx'] -= 1
            self.session.save_current_progress()
            self.refresh_ui_state()

    def nav_next(self):
        if self.bot.is_running:
            logger.warning("⏳ Bot déjà en cours d'exécution...")
            return

        guide = self.session.get_active_guide()
        if guide and guide['current_idx'] < len(guide['steps']) - 1:

            if self.is_auto_travel_enabled:
                t_type = self.next_travel_type
                arg1 = self.next_travel_zaap_name
                arg2 = self.next_travel_arg2
                cmd = self.next_travel_command

                # Exécution complexe via BotEngine
                self.run_threaded(lambda: self.bot.run_sequence(t_type, arg1, arg2, cmd))

            guide['current_idx'] += 1
            self.session.save_current_progress()
            self.refresh_ui_state()

        elif guide and guide['current_idx'] == len(guide['steps']) - 1:
            logger.info("ℹ️ Fin du guide atteinte.")
            self.refresh_ui_state()

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

    def on_guide_link_clicked(self, link_string):
        logger.info(f"Traitement lien : {link_string}")
        link_string = link_string.strip()
        if link_string.upper().startswith("GUIDE:"):
            gid = link_string.split(":")[1].strip()
            if not gid or not gid.isdigit(): return
            local_path = self.session.find_guide_in_library(gid)
            if local_path:
                self.run_threaded(lambda: self._load_local(local_path, gid))
            else:
                self.run_threaded(lambda: self._fetch_remote(gid))

        elif link_string.upper().startswith("STEP:"):
            s_val = link_string.split(":")[1].strip()
            try:
                t_idx = int(s_val) - 1
                g = self.session.get_active_guide()
                if g and 0 <= t_idx < len(g['steps']):
                    g['current_idx'] = t_idx
                    self.session.save_current_progress()
                    self.refresh_ui_state()
            except ValueError:
                pass

        elif link_string.upper().startswith("TRAVEL:"):
            try:
                # Utilisation du nouveau gestionnaire de commandes
                coords = link_string.split(":")[1].strip()
                self.run_threaded(lambda: self.commands.travel_to(coords))
            except Exception as e:
                logger.error(f"Erreur clic travel: {e}")

    def _load_local(self, path, gid):
        try:
            data = self.parser_io.load_file(path)
            if data: self.sig_open_guide.emit(data, path)
        except Exception as e:
            self.sig_log_error.emit(f"Erreur load local: {e}")

    def _fetch_remote(self, gid):
        try:
            data, err = self.network.fetch_guide_data(gid)
            if err:
                self.sig_log_error.emit(f"❌ Erreur téléchargement : {err}")
                return
            if data:
                path = self.parser_io.save_guide_to_library(data)
                if path: self.sig_open_guide.emit(data, path)
        except Exception as e:
            self.sig_log_error.emit(f"Erreur fetch remote: {e}")

    def _open_guide_slot(self, data, path):
        try:
            steps = self.parser_io.get_steps_list(data)
            if not steps: return
            name = data.get("name", f"Guide {data.get('id')}")
            gid = data.get("id")
            idx = self.session.add_guide(name, steps, path, gid)
            self.session.set_active_index(idx)
            self.refresh_ui_state()
        except Exception as e:
            logger.error(f"Erreur open slot: {e}")

    def restore_session(self):
        self.is_restoring_session = True
        try:
            guides, idx = self.session.load_last_session()
            if guides:
                for g in guides:
                    if g.get('file_path') and os.path.exists(g['file_path']):
                        d = self.parser_io.load_file(g['file_path'])
                        if d: self.session.add_guide(g['name'], self.parser_io.get_steps_list(d), g['file_path'],
                                                     g['id'])
                self.session.set_active_index(idx)

            last_char = self.session.get_last_character()

            def _restore_ui():
                if last_char and hasattr(self.view, 'ui_sidebar'):
                    self.view.ui_sidebar.bind_entry.setText(last_char)
                    QTimer.singleShot(500, self.action_bind_window_wrapper)

            QTimer.singleShot(0, _restore_ui)
        except Exception as e:
            logger.error(f"Erreur restore: {e}")
        finally:
            self.is_restoring_session = False
            self.refresh_ui_state()