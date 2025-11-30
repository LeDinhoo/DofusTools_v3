import customtkinter as ctk


class SidebarPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, width=220, corner_radius=0)
        self.controller = controller

        # Empêcher la sidebar de rétrécir
        self.grid_propagate(False)

        self.setup_widgets()

    def setup_widgets(self):
        # TITRE
        title = ctk.CTkLabel(self, text="DASHBOARD", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(20, 10))

        # --- CIBLAGE ---
        self.add_section("CIBLAGE")

        bind_frame = ctk.CTkFrame(self, fg_color="transparent")
        bind_frame.pack(fill="x", padx=10, pady=5)

        self.bind_entry = ctk.CTkEntry(bind_frame, placeholder_text="Nom du perso")
        self.bind_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_link = ctk.CTkButton(bind_frame, text="🔗", width=40, command=self.controller.action_bind_window_wrapper)
        btn_link.pack(side="right")

        macro_btn = ctk.CTkButton(self, text="⚔️ Macro Dofus", fg_color="transparent", border_width=1,
                                  command=self.controller.action_macro_space_wrapper)
        macro_btn.pack(fill="x", padx=10, pady=5)

        # --- ACTIONS ---
        self.add_section("ACTIONS")
        self.add_btn("🖱️ Clic Centre", self.controller.action_click_center_wrapper)
        self.add_btn("🔴 Test Overlay", self.controller.action_test_overlay_wrapper)

        # --- OUTILS ---
        self.add_section("OUTILS & OCR")

        ocr_frame = ctk.CTkFrame(self, fg_color="transparent")
        ocr_frame.pack(fill="x", padx=10, pady=5)

        self.ocr_target_entry = ctk.CTkEntry(ocr_frame, placeholder_text="Cible")
        self.ocr_target_entry.insert(0, "Lester")
        self.ocr_target_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.ocr_threshold_entry = ctk.CTkEntry(ocr_frame, width=50, placeholder_text="190")
        self.ocr_threshold_entry.insert(0, "190")
        self.ocr_threshold_entry.pack(side="right")

        self.var_grayscale = ctk.BooleanVar(value=True)
        cb_gray = ctk.CTkCheckBox(self, text="Noir & Blanc", variable=self.var_grayscale)
        cb_gray.pack(padx=10, pady=5, anchor="w")

        tools_frame = ctk.CTkFrame(self, fg_color="transparent")
        tools_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(tools_frame, text="📐 Zone", width=80, fg_color="#E59937", hover_color="#D48826",
                      command=self.controller.action_define_ocr_zone_wrapper).pack(side="left", padx=(0, 5))

        ctk.CTkButton(tools_frame, text="🔎 Chercher", width=80,
                      command=self.controller.action_ocr_wrapper).pack(side="right")

        # --- CHARGEMENT ---
        ctk.CTkButton(self, text="📂 Charger JSON", fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"),
                      command=self.controller.action_load_json_wrapper).pack(fill="x", padx=10, pady=(20, 10),
                                                                             side="bottom")

    def add_section(self, text):
        lbl = ctk.CTkLabel(self, text=text, text_color="gray", font=ctk.CTkFont(size=11, weight="bold"))
        lbl.pack(pady=(15, 0), padx=10, anchor="w")

    def add_btn(self, text, cmd):
        btn = ctk.CTkButton(self, text=text, fg_color="transparent", border_width=1, command=cmd)
        btn.pack(fill="x", padx=10, pady=2)

    def update_bind_status(self, status):
        color = "green" if status == "success" else "red" if status == "error" else "gray"
        self.bind_entry.configure(border_color=color)