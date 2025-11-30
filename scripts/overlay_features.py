import tkinter as tk
import logging

logger = logging.getLogger(__name__)


class OverlayScripts:
    def __init__(self, root):
        self.root = root
        self.active_overlays = []

    def _create_overlay_window(self, x, y, width, height, duration=0):
        """
        Crée une base de fenêtre transparente et 'click-through' (les clics passent au travers).
        """
        top = tk.Toplevel(self.root)
        top.overrideredirect(True)  # Pas de bordure
        top.wm_attributes("-topmost", True)  # Toujours au dessus
        top.wm_attributes("-disabled", True)  # IGNORER les clics souris (Windows)
        top.wm_attributes("-transparentcolor", "black")  # Le noir devient 100% transparent
        top.config(bg="black")

        # Positionnement
        top.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

        # Auto-destruction
        if duration > 0:
            self.root.after(duration, top.destroy)

        # Nettoyage de la liste
        def on_destroy(event):
            if top in self.active_overlays:
                self.active_overlays.remove(top)

        top.bind("<Destroy>", on_destroy)

        self.active_overlays.append(top)
        return top

    def draw_dot(self, x, y, color="#00ff00", size=10, duration=2000):
        """
        Dessine un point (cercle) à l'écran aux coordonnées absolues X,Y.
        Thread-safe : Peut être appelé depuis n'importe quel thread.
        """
        logger.info(f"Overlay: Point {color} à ({x}, {y})")

        def _gui_task():
            # Centrer le point sur X, Y
            win_x = x - size // 2
            win_y = y - size // 2

            top = self._create_overlay_window(win_x, win_y, size, size, duration)

            # Canvas transparent
            canvas = tk.Canvas(top, bg="black", highlightthickness=0)
            canvas.pack(fill="both", expand=True)

            # Dessin du cercle
            canvas.create_oval(0, 0, size, size, fill=color, outline=color)

        # Exécution sur le thread principal (obligatoire pour GUI)
        self.root.after(0, _gui_task)

    def draw_zone(self, x, y, w, h, color="red", alpha=0.3, duration=2000):
        """
        Dessine une zone rectangulaire semi-transparente (ex: pour debugger une zone OCR).
        """
        logger.info(f"Overlay: Zone {w}x{h} à ({x}, {y})")

        def _gui_task():
            top = tk.Toplevel(self.root)
            top.overrideredirect(True)
            top.wm_attributes("-topmost", True)
            top.wm_attributes("-disabled", True)
            top.wm_attributes("-alpha", alpha)  # Transparence globale (0.0 à 1.0)
            top.config(bg=color)
            top.geometry(f"{w}x{h}+{int(x)}+{int(y)}")

            if duration > 0:
                self.root.after(duration, top.destroy)
            self.active_overlays.append(top)

        self.root.after(0, _gui_task)

    def clear_all(self):
        """Nettoie tous les overlays actifs immédiatement"""
        for top in self.active_overlays:
            try:
                top.destroy()
            except:
                pass
        self.active_overlays.clear()