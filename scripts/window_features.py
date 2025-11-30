import ctypes
import time


class WindowScripts:
    def __init__(self, logger_func):
        self.log = logger_func
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

        # --- NOUVEAU : Mémoire de la fenêtre liée ---
        self.bound_handle = None
        self.bound_title = ""

    def _get_window_text(self, hwnd):
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        return ""

    def list_open_windows(self):
        """Retourne un dictionnaire {Handle: Titre}"""
        window_list = {}

        def foreach_window(hwnd, lParam):
            if self.user32.IsWindowVisible(hwnd):
                title = self._get_window_text(hwnd)
                if title:
                    window_list[hwnd] = title
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        self.user32.EnumWindows(WNDENUMPROC(foreach_window), 0)
        return window_list

    # --- MÉTHODES DE LIAISON (BINDING) ---

    def bind_window(self, partial_title):
        """Cherche une fenêtre et mémorise son ID (Handle)"""
        self.log(f"Binding : Recherche de '{partial_title}'...")
        windows = self.list_open_windows()

        for hwnd, title in windows.items():
            if partial_title.lower() in title.lower():
                self.bound_handle = hwnd
                self.bound_title = title
                self.log(f"-> LIÉ À : '{title}' (ID: {hwnd})")
                return True

        self.log("-> Erreur : Fenêtre introuvable.")
        self.bound_handle = None
        self.bound_title = ""
        return False

    def ensure_focus(self):
        """Vérifie si la fenêtre liée est active, sinon l'active"""
        if not self.bound_handle:
            self.log("Erreur : Aucune fenêtre n'est liée ! Utilisez 'bind_window' d'abord.")
            return False

        # Vérifie si la fenêtre existe toujours
        if not self.user32.IsWindow(self.bound_handle):
            self.log("Erreur : La fenêtre liée a été fermée.")
            self.bound_handle = None
            return False

        # Vérifie si elle est déjà au premier plan
        foreground_hwnd = self.user32.GetForegroundWindow()
        if foreground_hwnd == self.bound_handle:
            return True  # Déjà active, on gagne du temps

        # Sinon, on l'active
        # SW_RESTORE = 9
        self.user32.ShowWindow(self.bound_handle, 9)
        self.user32.SetForegroundWindow(self.bound_handle)

        # Petite pause technique pour laisser Windows faire l'animation
        time.sleep(0.2)
        return True

    # --- ANCIENNES MÉTHODES ---

    def win_activate(self, partial_title):
        self.log(f"WinActivate: Recherche de '{partial_title}'...")
        windows = self.list_open_windows()
        target_hwnd = None
        for hwnd, title in windows.items():
            if partial_title.lower() in title.lower():
                target_hwnd = hwnd
                break

        if target_hwnd:
            self.user32.ShowWindow(target_hwnd, 9)
            self.user32.SetForegroundWindow(target_hwnd)
            return True
        else:
            self.log("-> Fenêtre introuvable.")
            return False

    def win_wait_active(self, partial_title, timeout=10):
        self.log(f"WinWaitActive: Attente de '{partial_title}'...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            foreground_hwnd = self.user32.GetForegroundWindow()
            current_title = self._get_window_text(foreground_hwnd)
            if partial_title.lower() in current_title.lower():
                self.log(f"-> Succès ! Active : {current_title}")
                return True
            time.sleep(0.5)
        self.log("-> Timeout.")
        return False

    def demo_lister_tout(self):
        self.log("--- LISTE DES FENÊTRES ---")
        windows = self.list_open_windows()
        for hwnd, title in windows.items():
            self.log(f"[{hwnd}] {title}")
        self.log("--------------------------")

    def demo_activate_notepad(self):
        self.win_activate("Notepad")

    def demo_wait_notepad(self):
        self.win_wait_active("Notepad", timeout=5)