import ctypes
import time
# --- NOUVEAUX IMPORTS ---
import win32gui
import win32ui
import win32con
from PIL import Image


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

    def get_window_rect(self):
        """Retourne les coordonnées (left, top, right, bottom) de la fenêtre liée"""
        if not self.bound_handle:
            self.log("Erreur : Aucune fenêtre n'est liée pour obtenir la zone.")
            return None
        try:
            rect = win32gui.GetWindowRect(self.bound_handle)
            # win32gui.GetWindowRect retourne (left, top, right, bottom)
            return rect
        except Exception as e:
            self.log(f"Erreur lors de la récupération des coordonnées : {e}")
            return None

    def capture_window(self):
        """
        Capture l'image de la fenêtre liée et la retourne au format PIL.
        """
        if not self.bound_handle:
            self.log("Erreur : Aucune fenêtre n'est liée pour la capture.")
            return None

        hwnd = self.bound_handle
        left, top, right, bottom = self.get_window_rect()
        w = right - left
        h = bottom - top

        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

        saveDC.SelectObject(saveBitMap)

        # Copie le contenu de la fenêtre dans le bitmap (Utilise BDRCOPY pour exclure les bords)
        result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)  # 3 = PW_CLIENT (Client area only)

        if result != 1:
            self.log("Erreur de PrintWindow, tentative de GetWindowDC/BitBlt...")
            # Tentative de BitBlt si PrintWindow échoue
            saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)

        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)

        im = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1)

        # Nettoyage
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)

        if w > 0 and h > 0:
            return im
        else:
            self.log("Erreur : La fenêtre n'est pas affichée (taille 0).")
            return None

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