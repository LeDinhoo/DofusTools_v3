import tkinter as tk


class SidebarPanel(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, width=220, bg="#121212")
        self.controller = controller

        # Empêche le redimensionnement automatique par les enfants
        self.pack_propagate(False)

        self.setup_widgets()

    def setup_widgets(self):
        self.section_title("LIAISON JEU")

        self.bind_entry = tk.Entry(self, bg="#2b2b2b", fg="white", insertbackground="white", relief="flat")
        self.bind_entry.pack(fill="x", pady=2, ipady=3)
        self.bind_entry.insert(0, "Dofus")

        self.add_btn("🔗 Lier la fenêtre", self.controller.action_lier)
        self.add_btn("⚔️ Macro Dofus", self.controller.macro_dofus_space)

        self.section_title("ACTIONS RAPIDES")
        self.add_btn("🖱️ Clic Centre", self.controller.mouse.click_centre)

        # Mini clavier
        keys_frame = tk.Frame(self, bg="#121212")
        keys_frame.pack(fill="x", pady=2)
        for txt, cmd in [("Enter", self.controller.keyboard.press_enter),
                         ("Space", self.controller.keyboard.press_space),
                         ("Esc", self.controller.keyboard.press_escape)]:
            btn = tk.Button(keys_frame, text=txt,
                            command=lambda c=cmd: self.controller.run_threaded(c),
                            bg="#333", fg="white", relief="flat", activebackground="#555")
            btn.pack(side="left", padx=1, expand=True, fill="x")

        self.section_title("OUTILS")

        # --- NOUVEAU CHAMP INPUT OCR ---
        tk.Label(self, text="Cible OCR (Ex: 'Tofu')", fg="#e0e0e0", bg="#121212", font=("Segoe UI", 9)).pack(
            pady=(5, 0), anchor="w")
        self.ocr_target_entry = tk.Entry(self, bg="#2b2b2b", fg="white", insertbackground="white", relief="flat")
        self.ocr_target_entry.pack(fill="x", pady=2, ipady=3)
        self.ocr_target_entry.insert(0, "Lester")  # Valeur par défaut
        # -------------------------------

        # Mise à jour de la commande OCR pour utiliser la valeur du champ
        # La lambda doit lire le contenu de l'entrée au moment du clic.
        ocr_command = lambda: self.controller.ocr.run_ocr_for_key_Z(
            self.controller.window,
            self.controller.keyboard,
            target=self.ocr_target_entry.get()  # Passage de la valeur lue
        )
        self.add_btn("🔎 OCR (Touche Z + Fenêtre)", ocr_command)

        self.add_btn("📂 Charger JSON", self.controller.action_charger_json)
        self.add_btn("📜 Lister fenêtres", self.controller.window.demo_lister_tout)

        tk.Button(self, text="Fermer App", command=self.controller.root.quit,
                  bg="#330000", fg="#ffcccc", relief="flat").pack(fill="x", pady=20)

    def section_title(self, text):
        tk.Label(self, text=text, fg="#4da6ff", bg="#121212", font=("Segoe UI", 9, "bold")).pack(pady=(15, 5),
                                                                                                 anchor="w")

    def add_btn(self, text, command):
        # Si c'est une fonction 'interne' (comme charger json), on lance direct, sinon thread
        cmd = command if "Charger" in text else lambda: self.controller.run_threaded(command)

        tk.Button(self, text=text, command=cmd,
                  bg="#333333", fg="white", relief="flat",
                  activebackground="#4da6ff", activeforeground="white",
                  font=("Segoe UI", 10)).pack(fill="x", pady=2, ipady=3)