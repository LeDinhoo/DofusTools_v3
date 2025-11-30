import customtkinter as ctk
import logging
import ctypes
import tkinter as tk
from PIL import Image, ImageTk
import os

from .controller import MainController
from .panels.sidebar import SidebarPanel
from .panels.guide_view import GuidePanel
from .panels.logger import LoggerPanel

logger = logging.getLogger(__name__)


class AppLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Automation Hub")
        self.root.geometry("1200x850")
        self.root.configure(bg="#121212")

        # Attribut pour toujours au premier plan
        self.root.attributes("-topmost", True)

        # Configuration de la grille principale
        # Colonne 0: Sidebar (Outils) - optionnelle/masquée au besoin
        # Colonne 1: Contenu principal (Guide)
        # Colonne 2: Logs - optionnelle/masquée au besoin

        # Ligne 0: Contenu principal + Sidebar + Logs
        # Ligne 1: Barre de statut (hauteur fixe)

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)  # Barre du bas fixe

        # État des panneaux
        self.show_sidebar = True
        self.show_logs = False  # Initialement masqués comme demandé

        # État clavier
        self.key_a_was_down = False
        self.key_d_was_down = False
        self.debug_window_ref = None

        # --- 1. CONTROLEUR ---
        self.controller = MainController(self)

        # --- 2. INTERFACE ---
        self.setup_ui()
        self.start_global_keyboard_listener()

        # --- 3. LOGGING ---
        self.setup_logging()

        # --- 4. START ---
        self.root.after(200, self.controller.startup)
        logger.info("Interface native chargée.")

    def setup_ui(self):
        # --- ZONE CENTRALE (Ligne 0) ---

        # 1. Sidebar (Gauche)
        self.ui_sidebar = SidebarPanel(self.root, self.controller)
        self.ui_sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # 2. Guide (Centre)
        self.ui_guide = GuidePanel(self.root, self.controller)
        self.ui_guide.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        # 3. Logs (Droite) - Initialement masqués
        self.ui_logger = LoggerPanel(self.root)
        # self.ui_logger.grid(...) # Masqué au démarrage

        # --- BARRE DU BAS (Ligne 1) ---
        self.status_bar = ctk.CTkFrame(self.root, height=45, corner_radius=0, fg_color="#1a1a1a", border_width=0)
        self.status_bar.grid(row=1, column=0, columnspan=3, sticky="ew")

        # Conteneur centré pour les boutons de contrôle
        self.controls_frame = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        self.controls_frame.pack(expand=True, pady=10)

        # Bouton Toggle Outils (Gauche)
        self.btn_tools = self.create_status_btn("🛠️ Outils", self.toggle_sidebar, True)
        self.btn_tools.pack(side="left", padx=15)

        # Bouton Toggle Logs (Droite)
        # Initialisé inactif (gris) car show_logs = False
        self.btn_logs = self.create_status_btn("📝 Logs", self.toggle_logs, False)
        self.btn_logs.pack(side="left", padx=15)

    def create_status_btn(self, text, command, is_active):
        color = "#4da6ff" if is_active else "#333333"
        text_col = "white" if is_active else "gray"
        return ctk.CTkButton(self.controls_frame, text=text, width=100, height=28,
                             fg_color=color, text_color=text_col, hover_color="#3a8ee6",
                             font=("Segoe UI", 11, "bold"),
                             command=command)

    def setup_logging(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.handlers.clear()

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S'))
        root_logger.addHandler(console_handler)

        if self.show_logs and hasattr(self, 'ui_logger'):
            root_logger.addHandler(self.ui_logger.handler)

    def toggle_sidebar(self):
        if self.show_sidebar:
            self.ui_sidebar.grid_remove()
            self.btn_tools.configure(fg_color="#333333", text_color="gray")
        else:
            self.ui_sidebar.grid()
            self.btn_tools.configure(fg_color="#4da6ff", text_color="white")
        self.show_sidebar = not self.show_sidebar

    def toggle_logs(self):
        root_logger = logging.getLogger()
        if self.show_logs:
            self.ui_logger.grid_remove()
            self.btn_logs.configure(fg_color="#333333", text_color="gray")
            root_logger.removeHandler(self.ui_logger.handler)
        else:
            # On l'affiche en colonne 2, ligne 0
            self.ui_logger.grid(row=0, column=2, sticky="ns", padx=0, pady=0)
            self.btn_logs.configure(fg_color="#4da6ff", text_color="white")
            root_logger.addHandler(self.ui_logger.handler)
        self.show_logs = not self.show_logs

    def show_debug_image(self, image_path):
        if not image_path or not os.path.exists(image_path): return

        if self.debug_window_ref and self.debug_window_ref.winfo_exists():
            self.debug_window_ref.destroy()

        top = ctk.CTkToplevel(self.root)
        top.title("Debug OCR")
        top.geometry("600x400")
        top.attributes("-topmost", True)

        try:
            pil_img = Image.open(image_path)
            my_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(600, 400))
            lbl = ctk.CTkLabel(top, text="", image=my_image)
            lbl.pack(fill="both", expand=True)
            self.debug_window_ref = top
        except Exception as e:
            logger.error(f"Erreur image: {e}")

    def start_global_keyboard_listener(self):
        self.poll_global_keys()

    def poll_global_keys(self):
        if not self._is_typing_in_app():
            if ctypes.windll.user32.GetAsyncKeyState(0x41) & 0x8000:
                if not self.key_a_was_down:
                    self.key_a_was_down = True
                    self.controller.nav_previous()
            else:
                self.key_a_was_down = False

            if ctypes.windll.user32.GetAsyncKeyState(0x44) & 0x8000:
                if not self.key_d_was_down:
                    self.key_d_was_down = True
                    self.controller.nav_next()
            else:
                self.key_d_was_down = False

        self.root.after(50, self.poll_global_keys)

    def _is_typing_in_app(self):
        try:
            widget = self.root.focus_get()
            if isinstance(widget, (tk.Entry, tk.Text)): return True
        except:
            pass
        return False