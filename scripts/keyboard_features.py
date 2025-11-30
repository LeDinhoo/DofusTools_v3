import ctypes
import time

# --- DÉFINITIONS C (OBLIGATOIRES COMPLETES) ---
# Windows a besoin de la taille MAXIMALE de l'union (Souris + Clavier)
# Sinon SendInput échoue silencieusement.

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


# On DOIT définir MOUSEINPUT même si on ne l'utilise pas ici,
# car cela définit la taille mémoire de l'Union INPUT.
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT),
                ("mi", MOUSEINPUT),
                ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ui", INPUT_UNION)]


# --- CLASSE LOGIQUE ---

class KeyboardScripts:
    def __init__(self, logger_func, window_manager=None):
        self.log = logger_func
        self.user32 = ctypes.windll.user32
        self.window_manager = window_manager

    def _send_input(self, input_struct):
        # Cette fonction renvoie le nombre d'événements réussis.
        # Si 0, c'est que la struct est mal formée.
        self.user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(input_struct))

    def _prepare_context(self):
        if self.window_manager and self.window_manager.bound_handle:
            self.window_manager.ensure_focus()
            time.sleep(0.05)

    def press_key(self, hexKeyCode, duration=0.05, extended=False):
        """
        Appuie sur une touche (Mode Gamer : ScanCode)
        """
        self._prepare_context()

        # 1. Conversion Virtual Key -> Scan Code
        scan_code = self.user32.MapVirtualKeyW(hexKeyCode, 0)

        # Gestion des touches étendues (Flèches, Suppr, etc.)
        flags = KEYEVENTF_SCANCODE
        if extended:
            flags |= KEYEVENTF_EXTENDEDKEY

        # 2. Appui (Down)
        x = INPUT()
        x.type = INPUT_KEYBOARD
        x.ui.ki.wVk = 0
        x.ui.ki.wScan = scan_code
        x.ui.ki.dwFlags = flags
        self._send_input(x)

        # 3. Maintien
        time.sleep(duration)

        # 4. Relâchement (Up)
        x.ui.ki.dwFlags = flags | KEYEVENTF_KEYUP
        self._send_input(x)

    # --- MÉTHODES APPELABLES ---

    def press_enter(self):
        self.press_key(0x0D)

    def press_space(self):
        self.press_key(0x20)

    def press_escape(self):
        self.press_key(0x1B)

    def press_tab(self):
        self.press_key(0x09)

    def press_backspace(self):
        self.press_key(0x08)

    # Flèches (Nécessitent le flag extended=True pour ne pas être confondues avec le pavé num)
    def press_left(self):
        self.press_key(0x25, extended=True)

    def press_up(self):
        self.press_key(0x26, extended=True)

    def press_right(self):
        self.press_key(0x27, extended=True)

    def press_down(self):
        self.press_key(0x28, extended=True)

    # --- TEXTE (Unicode pour chat) ---
    def send_text(self, text):
        self._prepare_context()
        self.log(f"Clavier : Écriture de '{text}'")
        for char in text:
            # Pour le texte, on reste en Unicode (plus fiable pour les accents/chat)
            inp_down = INPUT()
            inp_down.type = INPUT_KEYBOARD
            inp_down.ui.ki.wScan = ord(char)
            inp_down.ui.ki.dwFlags = KEYEVENTF_UNICODE
            self._send_input(inp_down)

            inp_up = INPUT()
            inp_up.type = INPUT_KEYBOARD
            inp_up.ui.ki.wScan = ord(char)
            inp_up.ui.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
            self._send_input(inp_up)
            time.sleep(0.02)

    def demo_notepad(self):
        # Touche Windows
        self.press_key(0x5B, extended=True)
        time.sleep(0.2)
        self.send_text("notepad")
        self.press_enter()