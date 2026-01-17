from scripts.window_features import WindowScripts
from scripts.mouse_features import MouseScripts
from scripts.keyboard_features import KeyboardScripts
from scripts.system_features import SystemScripts
from scripts.navigation_manager import NavigationManager


class GameContext:
    """
    Centralise tous les scripts d'interaction avec le jeu.
    Sert de point d'entrée unique pour le contrôleur.
    """

    def __init__(self):
        # 1. Initialisation des outils bas niveau
        self.window = WindowScripts()
        self.mouse = MouseScripts()
        self.system = SystemScripts()

        # Le clavier a besoin du window_manager pour gérer le focus
        self.keyboard = KeyboardScripts(window_manager=self.window)

        # 2. Initialisation des Managers Haut Niveau
        # On passe 'self' pour qu'ils aient accès à window/mouse/keyboard
        self.navigation = NavigationManager(self)

    def ensure_focus(self):
        """Raccourci pratique pour vérifier et forcer le focus sur la fenêtre de jeu"""
        return self.window.ensure_focus()