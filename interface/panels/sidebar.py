import tkinter as tk


class SidebarPanel(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, width=220, bg="#121212")
        self.controller = controller
        self.pack_propagate(False)
        self.setup_widgets()

    def setup_widgets(self):
        self.section_title("LIAISON JEU")

        self.bind_entry = tk.Entry(self, bg="#2b2b2b", fg="white", insertbackground="white", relief="flat")
        self.bind_entry.pack(fill="x", pady=2, ipady=3)
        self.bind_entry.insert(0, "Dofus")

        # Appel des wrappers du contrôleur
        self.add_btn("🔗 Lier la fenêtre", self.controller.action_bind_window_wrapper)
        self.add_btn("⚔️ Macro Dofus", self.controller.action_macro_space_wrapper)

        self.section_title("ACTIONS RAPIDES")
        self.add_btn("🖱️ Clic Centre", self.controller.action_click_center_wrapper)

        # Mini clavier
        keys_frame = tk.Frame(self, bg="#121212")
        keys_frame.pack(fill="x", pady=2)

        # Note: Pour ces lambdas simples, on peut garder l'appel direct au thread du controlleur ou créer un wrapper
        # Pour rester cohérent, on utilise run_threaded directement accessible via controller
        for txt, cmd in [("Enter", self.controller.keyboard.press_enter),
                         ("Space", self.controller.keyboard.press_space),
                         ("Esc", self.controller.keyboard.press_escape)]:
            btn = tk.Button(keys_frame, text=txt,
                            command=lambda c=cmd: self.controller.run_threaded(c),
                            bg="#333", fg="white", relief="flat", activebackground="#555")
            btn.pack(side="left", padx=1, expand=True, fill="x")

        self.section_title("OUTILS")

        tk.Label(self, text="Cible OCR (Ex: 'Tofu')", fg="#e0e0e0", bg="#121212", font=("Segoe UI", 9)).pack(
            pady=(5, 0), anchor="w")
        self.ocr_target_entry = tk.Entry(self, bg="#2b2b2b", fg="white", insertbackground="white", relief="flat")
        self.ocr_target_entry.pack(fill="x", pady=2, ipady=3)
        self.ocr_target_entry.insert(0, "Lester")

        self.add_btn("🔎 OCR (Touche Z + Fenêtre)", self.controller.action_ocr_wrapper)

        self.add_btn("📂 Charger JSON", self.controller.action_load_json_wrapper)
        self.add_btn("📜 Lister fenêtres", self.controller.action_list_windows_wrapper)

        tk.Button(self, text="Fermer App", command=self.controller.root.quit,
                  bg="#330000", fg="#ffcccc", relief="flat").pack(fill="x", pady=20)

    def section_title(self, text):
        tk.Label(self, text=text, fg="#4da6ff", bg="#121212", font=("Segoe UI", 9, "bold")).pack(pady=(15, 5),
                                                                                                 anchor="w")

    def add_btn(self, text, command):
        # Plus de logique conditionnelle "if 'Charger' in text" ici.
        # Le command passé doit déjà être le bon (wrapper).
        tk.Button(self, text=text, command=command,
                  bg="#333333", fg="white", relief="flat",
                  activebackground="#4da6ff", activeforeground="white",
                  font=("Segoe UI", 10)).pack(fill="x", pady=2, ipady=3)