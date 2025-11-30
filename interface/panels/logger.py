import tkinter as tk
from tkinter import scrolledtext
import logging


class TextHandler(logging.Handler):
    """
    Handler de logging personnalisé qui redirige les logs vers un widget Text Tkinter.
    Thread-safe grâce à l'utilisation de .after()
    """

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)

        def append():
            try:
                self.text_widget.config(state='normal')
                self.text_widget.insert(tk.END, f"{msg}\n")
                self.text_widget.see(tk.END)
                self.text_widget.config(state='disabled')
            except Exception:
                # Si le widget est détruit (fermeture app), on ignore
                pass

        # Planifie l'exécution sur le thread principal (UI)
        self.text_widget.after(0, append)


class LoggerPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, width=250, bg="#121212")
        self.pack_propagate(False)

        # Header
        tk.Label(self, text="LOGS SYSTEME", anchor="w",
                 bg="#121212", fg="#666", font=("Segoe UI", 8, "bold")).pack(fill="x", pady=(10, 0))

        # Zone de texte
        self.log_area = scrolledtext.ScrolledText(self, height=10, state='disabled',
                                                  bg="#000000", fg="#00ff00",
                                                  font=("Consolas", 9), relief="flat")
        self.log_area.pack(fill="both", expand=True, pady=5)

        # Création du Handler pour le module logging
        self.handler = TextHandler(self.log_area)
        # Format : [Heure] Message
        self.handler.setFormatter(logging.Formatter('> [%(asctime)s] %(message)s', datefmt='%H:%M:%S'))