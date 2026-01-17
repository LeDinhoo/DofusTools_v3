import logging

logger = logging.getLogger(__name__)


class GameCommands:
    """
    Gère les commandes directes et actions unitaires du jeu.
    Permet de sortir la logique d'exécution (Travel, Clics, Touches) du contrôleur UI.
    """

    def __init__(self, bot_engine):
        self.bot = bot_engine

    def click_center(self):
        """Simule un clic au centre de la fenêtre."""
        self.bot.ctx.mouse.click_centre()

    def press_space(self):
        """Simule l'appui sur Espace."""
        self.bot.ctx.keyboard.press_space()

    def go_to_havre_sac(self):
        """Action pour aller au Havre-Sac (ou ouvrir l'interface Zaap HS)."""
        # On utilise la méthode zaap du manager sans nom pour déclencher l'accès
        self.bot.ctx.navigation.zaap("")

    def travel_to(self, command_or_coords):
        """
        Gère la commande de voyage.
        Accepte soit "x,y", soit "/travel x,y".
        """
        if not command_or_coords:
            return

        # Nettoyage de la chaîne (enlève /travel si présent)
        coords = command_or_coords.replace("/travel ", "").strip()

        logger.info(f"🏃 Exécution commande Travel -> {coords}")
        self.bot.ctx.navigation.auto_travel(coords)