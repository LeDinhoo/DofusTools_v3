import ctypes
import time
import win32gui
import win32ui
import win32con
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class WindowScripts:
    def __init__(self):
        self.user32 = ctypes.windll.user32
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
        window_list = {}

        def foreach_window(hwnd, lParam):
            if self.user32.IsWindowVisible(hwnd):
                title = self._get_window_text(hwnd)
                if title: window_list[hwnd] = title
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        self.user32.EnumWindows(WNDENUMPROC(foreach_window), 0)
        return window_list

    def bind_window(self, partial_title):
        logger.info(f"Binding : Recherche de '{partial_title}'...")
        windows = self.list_open_windows()
        for hwnd, title in windows.items():
            if partial_title.lower() in title.lower():
                self.bound_handle = hwnd
                self.bound_title = title
                logger.info(f"-> LIÉ À : '{title}' (ID: {hwnd})")
                return True
        logger.warning("-> Fenêtre introuvable.")
        return False

    def get_window_rect(self):
        if not self.bound_handle: return None
        try:
            return win32gui.GetWindowRect(self.bound_handle)
        except Exception as e:
            logger.error(f"Erreur coord : {e}")
            return None

    def capture_window(self):
        if not self.bound_handle: return None
        hwnd = self.bound_handle
        try:
            rect = self.get_window_rect()
            if not rect: return None
            left, top, right, bottom = rect
            w, h = right - left, bottom - top

            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
            saveDC.SelectObject(saveBitMap)

            result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)
            if result != 1:
                saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)

            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)

            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            return im
        except Exception as e:
            logger.error(f"Capture échouée: {e}")
            return None

    def ensure_focus(self):
        if not self.bound_handle:
            logger.warning("Focus impossible : Fenêtre non liée.")
            return False
        if not self.user32.IsWindow(self.bound_handle):
            logger.error("Fenêtre liée fermée.")
            self.bound_handle = None
            return False

        if self.user32.GetForegroundWindow() == self.bound_handle:
            return True

        self.user32.ShowWindow(self.bound_handle, 9)
        self.user32.SetForegroundWindow(self.bound_handle)
        time.sleep(0.2)
        return True

    def demo_lister_tout(self):
        logger.info("--- LISTE DES FENÊTRES ---")
        for hwnd, title in self.list_open_windows().items():
            logger.info(f"[{hwnd}] {title}")