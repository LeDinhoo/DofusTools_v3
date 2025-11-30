import customtkinter as ctk
import logging

class TextHandler(logging.Handler):
    def __init__(self, textbox):
        super().__init__()
        self.textbox = textbox

    def emit(self, record):
        msg = self.format(record)
        self.textbox.after(0, self.append, msg)

    def append(self, msg):
        try:
            self.textbox.configure(state="normal")
            self.textbox.insert("end", msg + "\n")
            self.textbox.see("end")
            self.textbox.configure(state="disabled")
        except:
            pass

class LoggerPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, width=250)
        self.grid_propagate(False) # Garder la largeur fixe

        label = ctk.CTkLabel(self, text="LOGS SYSTÈME", text_color="gray", font=("Arial", 10, "bold"))
        label.pack(fill="x", pady=5)

        self.log_area = ctk.CTkTextbox(self, font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_area.configure(state="disabled", text_color="#00ff00")

        self.handler = TextHandler(self.log_area)
        self.handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))