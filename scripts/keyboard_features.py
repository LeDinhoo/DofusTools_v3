import ctypes
import time
import logging
from .win32_structs import INPUT, INPUT_KEYBOARD, KEYEVENTF_SCANCODE, KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, \
    KEYEVENTF_UNICODE

logger = logging.getLogger(__name__)


class KeyboardScripts:
    def __init__(self, window_manager=None):
        # Plus de logger_func, window_manager est optionnel mais recommandé
        self.user32 = ctypes.windll.user32
        self.window_manager = window_manager

    def _send_input(self, input_struct):
        self.user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(input_struct))

    def _prepare_context(self):
        if self.window_manager and self.window_manager.bound_handle:
            self.window_manager.ensure_focus()
            time.sleep(0.05)

    def _get_key_input(self, hexKeyCode, extended=False):
        scan_code = self.user32.MapVirtualKeyW(hexKeyCode, 0)
        flags = KEYEVENTF_SCANCODE
        if extended:
            flags |= KEYEVENTF_EXTENDEDKEY

        x = INPUT()
        x.type = INPUT_KEYBOARD
        x.ui.ki.wVk = 0
        x.ui.ki.wScan = scan_code
        x.ui.ki.dwFlags = flags
        return x

    def send_key_action(self, hexKeyCode, is_down=True, extended=False):
        self._prepare_context()
        x = self._get_key_input(hexKeyCode, extended)
        if not is_down:
            x.ui.ki.dwFlags |= KEYEVENTF_KEYUP
        self._send_input(x)

    def press_key(self, hexKeyCode, duration=0.05, extended=False):
        self.send_key_action(hexKeyCode, is_down=True, extended=extended)
        time.sleep(duration)
        self.send_key_action(hexKeyCode, is_down=False, extended=extended)

    # --- Raccourcis ---
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

    def press_left(self):
        self.press_key(0x25, extended=True)

    def press_up(self):
        self.press_key(0x26, extended=True)

    def press_right(self):
        self.press_key(0x27, extended=True)

    def press_down(self):
        self.press_key(0x28, extended=True)

    def send_text(self, text):
        self._prepare_context()
        logger.debug(f"Typing: {text}")
        for char in text:
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