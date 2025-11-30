import ctypes
import time
import logging

logger = logging.getLogger(__name__)

class MouseScripts:
    def __init__(self):
        self.user32 = ctypes.windll.user32

    def demo_carre(self):
        logger.info("Souris : Début de la danse...")
        coords = [(500, 500), (600, 500), (600, 600), (500, 600)]
        for x, y in coords:
            self.user32.SetCursorPos(x, y)
            time.sleep(0.3)
        logger.info("Souris : Terminé.")

    def click_centre(self):
        logger.info("Souris : Clic centre (simulé)")
        self.user32.SetCursorPos(960, 540)
        self.user32.mouse_event(0x02, 0, 0, 0, 0) # Down
        self.user32.mouse_event(0x04, 0, 0, 0, 0) # Up