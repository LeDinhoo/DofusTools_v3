import tkinter as tk


class HeaderPanel(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#1f1f1f", height=40)
        self.controller = controller
        self.pack_propagate(False)

        # -- LOGIQUE DE DÉPLACEMENT (DRAG) --
        self.bind('<Button-1>', self.controller.start_move)
        self.bind('<B1-Motion>', self.controller.do_move)

        # 1. Titre
        lbl_title = tk.Label(self, text=" DASHBOARD MODULAIRE", font=("Segoe UI", 11, "bold"), bg="#1f1f1f",
                             fg="#e0e0e0")
        lbl_title.pack(side="left", padx=10)
        lbl_title.bind('<Button-1>', self.controller.start_move)
        lbl_title.bind('<B1-Motion>', self.controller.do_move)

        # 2. Boutons Système

        # Bouton FERMER (X) - Tout à droite
        btn_close = tk.Button(self, text="✕", command=self.controller.root.quit,
                              bg="#1f1f1f", fg="#ff5555", font=("Arial", 12),
                              relief="flat", bd=0, activebackground="#cc0000", activeforeground="white", width=4)
        btn_close.pack(side="right", fill="y")

        # Séparateur
        tk.Frame(self, width=1, bg="#333").pack(side="right", fill="y", padx=5)

        # 3. Boutons Toggle
        self.btn_logs = tk.Button(self, text="📝 Logs", command=self.controller.toggle_right_panel,
                                  bg="#1f1f1f", fg="#4da6ff", font=("Segoe UI", 9, "bold"),
                                  relief="flat", bd=0, activebackground="#333", activeforeground="#4da6ff")
        self.btn_logs.pack(side="right", padx=5)

        self.btn_actions = tk.Button(self, text="⚡ Actions", command=self.controller.toggle_left_panel,
                                     bg="#1f1f1f", fg="#4da6ff", font=("Segoe UI", 9, "bold"),
                                     relief="flat", bd=0, activebackground="#333", activeforeground="#4da6ff")
        self.btn_actions.pack(side="right", padx=5)

    def update_toggle_btn(self, btn_name, is_visible):
        """Met à jour l'apparence des boutons toggle"""
        if btn_name == "left":
            color = "#4da6ff" if is_visible else "#666"
            self.btn_actions.config(fg=color)
        elif btn_name == "right":
            color = "#4da6ff" if is_visible else "#666"
            self.btn_logs.config(fg=color)