import ctypes
import logging

logger = logging.getLogger(__name__)

class SystemScripts:
    def __init__(self):
        # Initialisation simplifiée
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

    def msg_box_test(self):
        """Affiche une popup native"""
        logger.info("Système : Envoi d'une popup...")
        self.user32.MessageBoxW(0, "Ceci vient du fichier system_features.py", "Test Architecture", 64)
        logger.info("Système : Popup fermée.")

    def beep_test(self):
        """Fait un beep système"""
        logger.info("Système : Beep !")
        self.kernel32.Beep(750, 300)