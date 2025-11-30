import ctypes
import time


class MouseScripts:
    def __init__(self, logger_func):
        self.log = logger_func
        self.user32 = ctypes.windll.user32

    def demo_carre(self):
        """Fait bouger la souris en carré"""
        self.log("Souris : Début de la danse...")
        coords = [(500, 500), (600, 500), (600, 600), (500, 600)]

        for x, y in coords:
            self.user32.SetCursorPos(x, y)
            time.sleep(0.3)

        self.log("Souris : Terminé.")

    def click_centre(self):
        """Exemple de clic au centre de l'écran (1920x1080)"""
        self.log("Souris : Clic au centre (simulation)")
        # 960, 540
        self.user32.SetCursorPos(960, 540)
        # Mouse Event: 0x02=Down, 0x04=Up
        self.user32.mouse_event(0x02, 0, 0, 0, 0)
        self.user32.mouse_event(0x04, 0, 0, 0, 0)

    def click_on_chat(self):
        """Exemple de clic au chat"""
        self.log("Souris : Clic au chat (simulation)")
        # 339, 1409
        self.user32.SetCursorPos(339, 1409)
        self.user32.mouse_event(0x02, 0, 0, 0, 0)
        self.user32.mouse_event(0x04, 0, 0, 0, 0)