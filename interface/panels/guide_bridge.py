from PyQt6.QtCore import QObject, pyqtSlot

class Bridge(QObject):
    """
    Assure la communication entre le JavaScript (WebEngine) et le Controller Python.
    """
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    @pyqtSlot(str)
    def handleLink(self, link):
        # Redirige les liens GUIDE:, STEP: et TRAVEL: vers le contrôleur
        if link.startswith("GUIDE:") or link.startswith("STEP:") or link.startswith("TRAVEL:"):
            self.controller.on_guide_link_clicked(link)
        elif link.startswith("CB:"):
            # Ici on pourrait sauvegarder l'état des checkboxes si nécessaire
            pass

    @pyqtSlot(str)
    def copyToClipboard(self, text):
        self.controller.copy_position()