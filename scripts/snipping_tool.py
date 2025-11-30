import tkinter as tk
import logging

logger = logging.getLogger(__name__)


class SnippingTool:
    def __init__(self, root):
        self.root = root
        self.top_level = None
        self.canvas = None
        self.start_x = 0
        self.start_y = 0
        self.cur_x = 0
        self.cur_y = 0
        self.rect_id = None
        self.selection = None  # (left, top, width, height)
        self.callback = None  # Fonction à appeler une fois la sélection faite

    def start_selection(self, callback):
        """Lance l'outil de sélection. Appelle callback((x, y, w, h)) à la fin."""
        self.callback = callback
        self.selection = None

        # Création de la fenêtre overlay plein écran
        self.top_level = tk.Toplevel(self.root)
        self.top_level.attributes("-fullscreen", True)
        self.top_level.attributes("-alpha", 0.3)  # Semi-transparent
        self.top_level.attributes("-topmost", True)
        self.top_level.config(cursor="cross")  # Curseur croix

        # Canvas pour dessiner
        self.canvas = tk.Canvas(self.top_level, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Bindings souris
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        # Echap pour annuler
        self.top_level.bind("<Escape>", self.cancel_selection)

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        # Création du rectangle (initialement vide)
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y,
                                                    outline="red", width=2)

    def on_move_press(self, event):
        self.cur_x, self.cur_y = event.x, event.y
        # Mise à jour du rectangle
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, self.cur_x, self.cur_y)

    def on_button_release(self, event):
        # Calcul des coordonnées finales (x, y, w, h)
        x1 = min(self.start_x, self.cur_x)
        y1 = min(self.start_y, self.cur_y)
        x2 = max(self.start_x, self.cur_x)
        y2 = max(self.start_y, self.cur_y)

        w = x2 - x1
        h = y2 - y1

        # Fermeture overlay
        self.top_level.destroy()
        self.top_level = None

        # Validation : on ignore les clics minuscules (< 5px)
        if w > 5 and h > 5:
            self.selection = (x1, y1, w, h)
            logger.info(f"Zone sélectionnée : {self.selection}")
            if self.callback:
                self.callback(self.selection)
        else:
            logger.info("Sélection annulée (zone trop petite).")

    def cancel_selection(self, event=None):
        if self.top_level:
            self.top_level.destroy()
            self.top_level = None
        logger.info("Sélection annulée par l'utilisateur.")