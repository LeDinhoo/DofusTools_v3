import sys
import logging
import traceback
import os  # Ajout de os pour la gestion du chemin de l'icône
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon  # Ajout de QIcon
from PyQt6.QtCore import Qt
from interface.dashboard import AppLauncher

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s : %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Main")


def exception_hook(exctype, value, tb):
    """Capture globale des erreurs pour éviter le crash silencieux"""
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"🔥 CRASH NON GÉRÉ :\n{error_msg}")
    sys.__excepthook__(exctype, value, tb)


def apply_dracula_theme(app):
    """Thème sombre moderne"""
    app.setStyle("Fusion")
    palette = QPalette()

    # Couleurs basées sur le thème Dracula/Material
    colors = {
        QPalette.ColorRole.Window: "#121212",
        QPalette.ColorRole.WindowText: "#ffffff",
        QPalette.ColorRole.Base: "#1a1a1a",
        QPalette.ColorRole.AlternateBase: "#1e1e2e",
        QPalette.ColorRole.ToolTipBase: "#ffffff",
        QPalette.ColorRole.ToolTipText: "#ffffff",
        QPalette.ColorRole.Text: "#ffffff",
        QPalette.ColorRole.Button: "#1e1e2e",
        QPalette.ColorRole.ButtonText: "#ffffff",
        QPalette.ColorRole.Link: "#4da6ff",
        QPalette.ColorRole.Highlight: "#4da6ff",
        QPalette.ColorRole.HighlightedText: "#000000",
    }

    for role, color_code in colors.items():
        palette.setColor(role, QColor(color_code))

    app.setPalette(palette)
    app.setFont(QFont("Segoe UI", 10))


if __name__ == "__main__":
    sys.excepthook = exception_hook

    app = QApplication(sys.argv)

    # NOUVEAU : Tentative de chargement de l'icône PNG
    try:
        # Cherche 'app_icon.png' à la racine du projet
        app_icon_path = os.path.join(os.path.dirname(__file__), "app_icon.png")
        if os.path.exists(app_icon_path):
            app.setWindowIcon(QIcon(app_icon_path))
    except Exception as e:
        logger.error(f"Erreur lors du chargement de l'icône : {e}")

    apply_dracula_theme(app)

    window = AppLauncher()
    window.show()

    sys.exit(app.exec())