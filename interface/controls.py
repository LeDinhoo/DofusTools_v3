import tkinter as tk


class CustomCheckbox(tk.Canvas):
    """Case à cocher stylisée pour le thème sombre"""

    def __init__(self, master, size=14, bg_color="#1e1e2e"):
        super().__init__(master, width=size, height=size, bg=bg_color, highlightthickness=0, cursor="hand2")
        self.size = size
        self.checked = False

        # Binding du clic
        self.bind("<Button-1>", self.toggle)

        # Dessin initial
        self.draw()

    def toggle(self, event=None):
        self.checked = not self.checked
        self.draw()

    def draw(self):
        self.delete("all")
        # Marges internes
        pad = 1
        x1, y1 = pad, pad
        x2, y2 = self.size - pad, self.size - pad

        if self.checked:
            # ÉTAT COCHÉ : Fond Bleu + Coche Blanche
            # 1. Fond Bleu
            self.create_rectangle(x1, y1, x2, y2, fill="#4da6ff", outline="#4da6ff")
            # 2. Coche Blanche (Dessinée à la main)
            # Forme de "V" : (gauche, milieu-bas, droite-haut)
            check_points = [x1 + 3, y1 + 6, x1 + 6, y2 - 3, x2 - 2, y1 + 3]
            self.create_line(check_points, fill="white", width=2, capstyle="round")
        else:
            # ÉTAT NON COCHÉ : Fond Blanc
            self.create_rectangle(x1, y1, x2, y2, fill="white", outline="white")


class RoundedButton(tk.Canvas):
    """Bouton carré aux bords arrondis (Style App Mobile)"""

    def __init__(self, master, width=32, height=32, radius=12,
                 bg_color="#252535", hover_color="#3a3a4a",
                 fg_color="white", command=None, text=""):
        # On hérite la couleur de fond du parent pour la transparence
        super().__init__(master, width=width, height=height,
                         bg=master["bg"],
                         highlightthickness=0)
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.fg_color = fg_color

        # Couleurs état désactivé
        self.disabled_bg = "#1a1a25"
        self.disabled_fg = "#444444"

        self.radius = radius
        self.text = text
        self.state = "normal"

        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

        self.draw()

    def draw(self):
        self.delete("all")

        bg = self.bg_color if self.state == "normal" else self.disabled_bg
        fg = self.fg_color if self.state == "normal" else self.disabled_fg

        # Dessin du rectangle arrondi (4 cercles aux coins + 2 rectangles)
        x1, y1, x2, y2 = 0, 0, int(self["width"]), int(self["height"])
        r = self.radius
        d = 2 * r

        # Coins
        self.create_arc(x1, y1, x1 + d, y1 + d, start=90, extent=90, fill=bg, outline=bg, tags="bg")
        self.create_arc(x2 - d, y1, x2, y1 + d, start=0, extent=90, fill=bg, outline=bg, tags="bg")
        self.create_arc(x1, y2 - d, x1 + d, y2, start=180, extent=90, fill=bg, outline=bg, tags="bg")
        self.create_arc(x2 - d, y2 - d, x2, y2, start=270, extent=90, fill=bg, outline=bg, tags="bg")

        # Corps
        self.create_rectangle(x1 + r, y1, x2 - r, y2, fill=bg, outline=bg, tags="bg")
        self.create_rectangle(x1, y1 + r, x2, y2 - r, fill=bg, outline=bg, tags="bg")

        # Texte (Flèche)
        self.create_text(x2 / 2, y2 / 2, text=self.text, fill=fg, font=("Segoe UI", 11, "bold"), tags="text")

    def on_enter(self, e):
        if self.state == "normal":
            for item in self.find_withtag("bg"):
                self.itemconfig(item, fill=self.hover_color, outline=self.hover_color)
            self.config(cursor="hand2")

    def on_leave(self, e):
        if self.state == "normal":
            for item in self.find_withtag("bg"):
                self.itemconfig(item, fill=self.bg_color, outline=self.bg_color)
            self.config(cursor="")

    def on_click(self, e):
        if self.state == "normal" and self.command:
            self.command()

    def set_state(self, state):
        if self.state != state:
            self.state = state
            if state == "disabled":
                self.config(cursor="")
            self.draw()