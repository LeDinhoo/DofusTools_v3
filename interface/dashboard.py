import tkinter as tk
import logging
from PIL import Image, ImageTk
import os
import ctypes  # Nécessaire pour détecter les touches hors focus

from .controller import MainController
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

        # --- FENÊTRE TOUJOURS AU PREMIER PLAN ---
        self.root.attributes("-topmost", True)

        self.show_left = True
        self.show_right = True
        self.debug_window_ref = None

        # État pour les raccourcis globaux
        self.key_a_was_down = False
        self.key_d_was_down = False

        # --- 1. INITIALISATION DU CONTROLEUR ---
        self.controller = MainController(self)

        # --- 2. SETUP UI ---
        self.setup_ui()

        # --- 3. DÉMARRAGE POLLING CLAVIER (GLOBAL) ---
        self.start_global_keyboard_listener()

        # --- 4. SETUP LOGGING ---
        self.setup_logging()

        # --- 5. DÉMARRAGE ---
        self.root.after(200, self.controller.startup)
        logger.info("Système UI chargé (Optimisation Logs + Topmost).")

    def setup_logging(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.handlers.clear()

        # Handler Console (Toujours actif)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(console_handler)

        # Handler UI (Actif au démarrage car le panneau est visible)
        if hasattr(self, 'ui_logger'):
            root_logger.addHandler(self.ui_logger.handler)

    def setup_ui(self):
        # HEADER
        header_toggle_frame = tk.Frame(self.root, bg="#1f1f1f", height=40)
        header_toggle_frame.pack(fill="x", side="top")
        header_toggle_frame.pack_propagate(False)

        # Boutons de toggle
        tk.Frame(header_toggle_frame, width=1, bg="#333").pack(side="right", fill="y", padx=5)

        self.btn_logs = tk.Button(header_toggle_frame, text="📝 Logs", command=self.toggle_right_panel,
                                  bg="#1f1f1f", fg="#4da6ff", font=("Segoe UI", 9, "bold"),
                                  relief="flat", bd=0, activebackground="#333", activeforeground="#4da6ff")
        self.btn_logs.pack(side="right", padx=5)

        self.btn_actions = tk.Button(header_toggle_frame, text="⚡ Actions", command=self.toggle_left_panel,
                                     bg="#1f1f1f", fg="#4da6ff", font=("Segoe UI", 9, "bold"),
                                     relief="flat", bd=0, activebackground="#333", activeforeground="#4da6ff")
        self.btn_actions.pack(side="right", padx=5)

        # CORPS PRINCIPAL
        self.main_frame = tk.Frame(self.root, bg=self.bg_color)
        self.main_frame.pack(fill="both", expand=True)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # PANNEAUX
        self.ui_sidebar = SidebarPanel(self.main_frame, self.controller)
        self.ui_sidebar.grid(row=0, column=0, sticky="ns")

        self.ui_guide = GuidePanel(self.main_frame, self.controller)
        self.ui_guide.grid(row=0, column=1, sticky="nsew")

        self.ui_logger = LoggerPanel(self.main_frame)
        self.ui_logger.grid(row=0, column=2, sticky="ns")

    # =========================================================================
    #                    GESTION CLAVIER GLOBALE (SANS FOCUS)
    # =========================================================================

    def start_global_keyboard_listener(self):
        self.poll_global_keys()

    def poll_global_keys(self):
        """Boucle qui vérifie l'état des touches A et D physiquement"""
        if not self._is_typing_in_app():
            # Touche A
            if ctypes.windll.user32.GetAsyncKeyState(0x41) & 0x8000:
                if not self.key_a_was_down:
                    self.key_a_was_down = True
                    self.controller.nav_previous()
            else:
                self.key_a_was_down = False

            # Touche D
            if ctypes.windll.user32.GetAsyncKeyState(0x44) & 0x8000:
                if not self.key_d_was_down:
                    self.key_d_was_down = True
                    self.controller.nav_next()
            else:
                self.key_d_was_down = False

        self.root.after(50, self.poll_global_keys)

    def _is_typing_in_app(self):
        """Empêche les raccourcis si on écrit dans l'interface"""
        try:
            widget = self.root.focus_get()
            if widget:
                if isinstance(widget, (tk.Entry, tk.Text)):
                    return True
                if widget.winfo_class() in ['Entry', 'Text']:
                    return True
        except:
            pass
        return False

    # =========================================================================
    #                             LOGIQUE UI PURE
    # =========================================================================

    def show_debug_image(self, image_path):
        if not image_path or not os.path.exists(image_path): return

        if self.debug_window_ref and self.debug_window_ref.winfo_exists():
            self.debug_window_ref.destroy()

        top = tk.Toplevel(self.root)
        top.title(f"Debug OCR : {os.path.basename(image_path)}")
        top.geometry("600x400")
        top.attributes("-topmost", True)

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

    def toggle_left_panel(self):
        if self.show_left:
            self.ui_sidebar.grid_remove()
            self.btn_actions.config(fg="#666")
        else:
            self.ui_sidebar.grid()
            self.btn_actions.config(fg="#4da6ff")
        self.show_left = not self.show_left

    def toggle_right_panel(self):
        # --- MODIFICATION : GESTION DYNAMIQUE DU LOGGING ---
        root_logger = logging.getLogger()

        if self.show_right:
            # ON MASQUE LE PANNEAU -> ON DÉSACTIVE LE LOGGING UI
            self.ui_logger.grid_remove()
            self.btn_logs.config(fg="#666")

            # On retire le handler pour arrêter d'envoyer des messages à la GUI
            if hasattr(self.ui_logger, 'handler'):
                root_logger.removeHandler(self.ui_logger.handler)
        else:
            # ON AFFICHE LE PANNEAU -> ON RÉACTIVE LE LOGGING UI
            self.ui_logger.grid()
            self.btn_logs.config(fg="#4da6ff")

            # On remet le handler
            if hasattr(self.ui_logger, 'handler'):
                root_logger.addHandler(self.ui_logger.handler)

        self.show_right = not self.show_right