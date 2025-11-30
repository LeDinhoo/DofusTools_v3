import tkinter as tk
from interface.controls import CustomCheckbox  # Import de la checkbox perso


class SidebarPanel(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, width=220, bg="#121212")
        self.controller = controller
        self.pack_propagate(False)

        # Variable pour le mode Gris
        self.var_grayscale = tk.BooleanVar(value=True)  # Activé par défaut

        self.setup_widgets()

    def setup_widgets(self):
        # --- SECTION LIAISON ---
        self.section_title("CIBLAGE FENÊTRE")

        bind_frame = tk.Frame(self, bg="#121212")
        bind_frame.pack(fill="x", pady=2)

        # Entry avec highlightthickness pour permettre de changer la couleur de la bordure
        self.bind_entry = tk.Entry(
            bind_frame,
            bg="#2b2b2b",
            fg="white",
            insertbackground="white",
            relief="flat",
            highlightthickness=1,  # Epaisseur bordure
            highlightbackground="#2b2b2b",  # Couleur bordure repos (invisible au départ)
            highlightcolor="#4da6ff"  # Couleur bordure focus
        )
        self.bind_entry.pack(side="left", fill="both", expand=True, ipady=3, padx=(0, 2))

        btn_link = tk.Button(bind_frame, text="🔗", command=self.controller.action_bind_window_wrapper,
                             bg="#333333", fg="white", relief="flat", width=3,
                             activebackground="#4da6ff", activeforeground="white")
        btn_link.pack(side="right", fill="y")

        self.add_btn("⚔️ Activer Macro Dofus", self.controller.action_macro_space_wrapper)

        # --- ACTIONS ---
        self.section_title("ACTIONS")
        self.add_btn("🖱️ Clic Centre", self.controller.action_click_center_wrapper)
        self.add_btn("🔴 Test Overlay", self.controller.action_test_overlay_wrapper)

        if getattr(self.controller, "debug_mode", False):
            keys_frame = tk.Frame(self, bg="#121212")
            keys_frame.pack(fill="x", pady=2)
            for txt, cmd in [("Enter", self.controller.keyboard.press_enter),
                             ("Space", self.controller.keyboard.press_space),
                             ("Esc", self.controller.keyboard.press_escape)]:
                btn = tk.Button(keys_frame, text=txt,
                                command=lambda c=cmd: self.controller.run_threaded(c),
                                bg="#333", fg="white", relief="flat", activebackground="#555")
                btn.pack(side="left", padx=1, expand=True, fill="x")

        # --- OUTILS & OCR ---
        self.section_title("OUTILS & OCR")

        lbl_ocr = tk.Label(self, text="Cible (Texte + Seuil) :", fg="#888", bg="#121212", font=("Segoe UI", 8))
        lbl_ocr.pack(pady=(5, 0), anchor="w")

        ocr_frame = tk.Frame(self, bg="#121212")
        ocr_frame.pack(fill="x", pady=2)

        # 1. Input Cible (Texte)
        self.ocr_target_entry = tk.Entry(ocr_frame, bg="#2b2b2b", fg="white", insertbackground="white", relief="flat")
        self.ocr_target_entry.pack(side="left", fill="both", expand=True, ipady=3, padx=(0, 2))
        self.ocr_target_entry.insert(0, "Lester")

        # 2. Input Seuil (Numérique)
        self.ocr_threshold_entry = tk.Entry(ocr_frame, bg="#2b2b2b", fg="#4da6ff", insertbackground="white",
                                            relief="flat", width=4, justify="center")
        self.ocr_threshold_entry.pack(side="left", fill="y", ipady=3, padx=(0, 2))
        self.ocr_threshold_entry.insert(0, "200")

        # --- Option Grayscale ---
        gray_frame = tk.Frame(self, bg="#121212")
        gray_frame.pack(fill="x", pady=(5, 2))

        # On utilise checkbutton natif pour simplicité ici, ou CustomCheckbox si tu préfères
        cb_gray = tk.Checkbutton(gray_frame, text="Noir & Blanc (Gris)", variable=self.var_grayscale,
                                 bg="#121212", fg="#cccccc", selectcolor="#2b2b2b",
                                 activebackground="#121212", activeforeground="#ffffff",
                                 font=("Segoe UI", 9))
        cb_gray.pack(side="left")

        # 3. Boutons (Zone + Recherche)
        # Btn Zone
        # ... (reste inchangé)
        btn_zone = tk.Button(ocr_frame, text="📐", command=self.controller.action_define_ocr_zone_wrapper,
                             bg="#333333", fg="white", relief="flat", width=3,
                             activebackground="#4da6ff", activeforeground="white")
        btn_zone.pack(side="right", fill="y", padx=(2, 0))

        # Btn Recherche
        btn_ocr = tk.Button(ocr_frame, text="🔎", command=self.controller.action_ocr_wrapper,
                            bg="#333333", fg="white", relief="flat", width=3,
                            activebackground="#4da6ff", activeforeground="white")
        btn_ocr.pack(side="right", fill="y")

        self.add_btn("📂 Charger JSON", self.controller.action_load_json_wrapper)

    def section_title(self, text):
        tk.Label(self, text=text, fg="#4da6ff", bg="#121212", font=("Segoe UI", 8, "bold")).pack(pady=(15, 5),
                                                                                                 anchor="w")

    def add_btn(self, text, command):
        tk.Button(self, text=text, command=command,
                  bg="#333333", fg="white", relief="flat",
                  activebackground="#4da6ff", activeforeground="white",
                  font=("Segoe UI", 9)).pack(fill="x", pady=2, ipady=4)

    def update_bind_status(self, status):
        """Met à jour la couleur de la bordure selon le statut (success/error/none)"""
        if status == "success":
            color = "#00ff00"  # Vert
        elif status == "error":
            color = "#ff0000"  # Rouge
        else:
            color = "#2b2b2b"  # Défaut

        self.bind_entry.config(highlightbackground=color, highlightcolor=color)