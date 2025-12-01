import sys
import logging
import traceback
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QColor, QPalette
from PyQt6.QtCore import Qt  # Ajout de l'import manquant
from interface.dashboard import AppLauncher

# Configuration du logging global
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Main")


def exception_hook(exctype, value, tb):
    """Capture les exceptions non gérées pour éviter le crash 0xC0000409"""
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"🔥 ERREUR CRITIQUE NON GÉRÉE :\n{error_msg}")
    sys.__excepthook__(exctype, value, tb)


def set_dark_theme(app):
    """Applique un thème sombre global style 'Material/Dracula'"""
    app.setStyle("Fusion")
    palette = QPalette()

    dark_bg = QColor("#121212")
    panel_bg = QColor("#1e1e2e")
    text_col = QColor("#ffffff")
    accent = QColor("#4da6ff")

    palette.setColor(QPalette.ColorRole.Window, dark_bg)
    palette.setColor(QPalette.ColorRole.WindowText, text_col)
    palette.setColor(QPalette.ColorRole.Base, QColor("#1a1a1a"))
    palette.setColor(QPalette.ColorRole.AlternateBase, panel_bg)
    palette.setColor(QPalette.ColorRole.ToolTipBase, text_col)
    palette.setColor(QPalette.ColorRole.ToolTipText, text_col)
    palette.setColor(QPalette.ColorRole.Text, text_col)
    palette.setColor(QPalette.ColorRole.Button, panel_bg)
    palette.setColor(QPalette.ColorRole.ButtonText, text_col)
    palette.setColor(QPalette.ColorRole.Link, accent)
    palette.setColor(QPalette.ColorRole.Highlight, accent)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("black"))

    app.setPalette(palette)

    font = QFont("Segoe UI", 10)
    app.setFont(font)


if __name__ == "__main__":
    # 1. Installation du hook AVANT tout le reste
    sys.excepthook = exception_hook

    app = QApplication(sys.argv)
    set_dark_theme(app)

    window = AppLauncher()
    window.show()

    # Exécution protégée
    try:
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Crash fatal dans la boucle d'événements : {e}")