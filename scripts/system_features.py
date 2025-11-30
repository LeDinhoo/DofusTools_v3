import ctypes

class SystemScripts:
    def __init__(self, logger_func):
        self.log = logger_func
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

    def msg_box_test(self):
        """Affiche une popup native"""
        self.log("Système : Envoi d'une popup...")
        self.user32.MessageBoxW(0, "Ceci vient du fichier system_features.py", "Test Architecture", 64)
        self.log("Système : Popup fermée.")

    def beep_test(self):
        """Fait un beep système"""
        self.log("Système : Beep !")
        self.kernel32.Beep(750, 300)