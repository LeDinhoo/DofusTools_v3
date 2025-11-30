import tkinter as tk
from tkinter import scrolledtext
import time


class LoggerPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, width=250, bg="#121212")
        self.pack_propagate(False)

        tk.Label(self, text="LOGS", anchor="w", bg="#121212", fg="#666", font=("Segoe UI", 8, "bold")).pack(fill="x",
                                                                                                            pady=(10,
                                                                                                                  0))

        self.log_area = scrolledtext.ScrolledText(self, height=10, state='disabled',
                                                  bg="#000000", fg="#00ff00",
                                                  font=("Consolas", 9), relief="flat")
        self.log_area.pack(fill="both", expand=True, pady=5)

    def log(self, msg):
        """Affiche un message avec timestamp"""
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"> {msg}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')