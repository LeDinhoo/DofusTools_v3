import tkinter as tk
from interface.html_engine import RichTextDisplay
from interface.controls import RoundedButton


class GuidePanel(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, width=500, bg="#1e1e2e")
        self.controller = controller

        # Variables liées à l'affichage
        self.var_position = tk.StringVar(value="")
        self.var_current_step = tk.StringVar(value="--")
        # Suppression du slash initial
        self.var_total_steps = tk.StringVar(value="--")
        self.var_guide_name = tk.StringVar(value="Aucun guide")

        self.setup_layout()

    def setup_layout(self):
        # 1. Barre des Onglets
        self.tabs_container = tk.Frame(self, bg="#121212", height=30)
        self.tabs_container.pack(fill="x", side="top")

        # 2. Header de Navigation
        nav_bar = tk.Frame(self, bg="#252535", height=50)
        nav_bar.pack(fill="x", side="top")
        nav_bar.pack_propagate(False)

        nav_bar.grid_columnconfigure(0, weight=0, minsize=140)
        nav_bar.grid_columnconfigure(1, weight=1)
        nav_bar.grid_columnconfigure(2, weight=0)
        nav_bar.grid_rowconfigure(0, weight=1)

        # Position (Gauche)
        self.lbl_position = tk.Label(nav_bar, textvariable=self.var_position,
                                     bg="#252535", fg="#ffd700", font=("Segoe UI", 12, "bold"), cursor="hand2")
        self.lbl_position.grid(row=0, column=0, padx=12, sticky="w")
        self.lbl_position.bind("<Button-1>", self.controller.copy_position)

        # Navigation (Droite)
        nav_group = tk.Frame(nav_bar, bg="#252535")
        nav_group.grid(row=0, column=2, padx=10, sticky="e")

        # Bouton Précédent (Arrondi)
        self.btn_prev = RoundedButton(nav_group, text="◀", command=self.controller.nav_previous,
                                      width=30, height=30, radius=8,
                                      bg_color="#252535", hover_color="#3a3a4a", fg_color="white")
        self.btn_prev.pack(side="left", padx=2)

        # Container central pour Input Etape / Total Etapes (Vertical)
        step_info_frame = tk.Frame(nav_group, bg="#252535")
        step_info_frame.pack(side="left", padx=5)

        # Input Etape (Au-dessus)
        self.entry_step = tk.Entry(step_info_frame, textvariable=self.var_current_step,
                                   width=4, bg="#252535", fg="#4da6ff",
                                   insertbackground="white", relief="flat",
                                   justify="center", font=("Consolas", 10, "bold"))
        self.entry_step.pack(side="top", fill="x", pady=0)
        self.entry_step.bind("<Return>", self.on_step_submit)

        # Total Etapes (En-dessous, sans slash)
        self.lbl_total = tk.Label(step_info_frame, textvariable=self.var_total_steps,
                                  bg="#252535", fg="#888888", font=("Consolas", 10), width=6)
        self.lbl_total.pack(side="bottom", fill="x", pady=0)

        # Bouton Suivant (Arrondi)
        self.btn_next = RoundedButton(nav_group, text="▶", command=self.controller.nav_next,
                                      width=30, height=30, radius=8,
                                      bg_color="#252535", hover_color="#3a3a4a", fg_color="white")
        self.btn_next.pack(side="left", padx=2)

        # Bouton Auto-Travel (Arrondi avec icône centrée)
        self.btn_auto_travel = RoundedButton(nav_group, text="✈", command=self.toggle_auto_travel_ui,
                                             width=30, height=30, radius=8,
                                             bg_color="#252535", hover_color="#3a3a4a", fg_color="#666666")
        self.btn_auto_travel.pack(side="left", padx=(10, 0))

        # Initialisation état bouton avion
        self.update_auto_travel_btn_state()

        # 3. Viewer HTML
        self.html_viewer = RichTextDisplay(self, on_link_click=self.controller.on_guide_link_clicked)
        self.html_viewer.pack(fill="both", expand=True, padx=0, pady=0)

    def toggle_auto_travel_ui(self):
        """Bascule l'état et met à jour l'apparence"""
        self.controller.toggle_auto_travel()
        self.update_auto_travel_btn_state()

    def update_auto_travel_btn_state(self):
        """Met à jour la couleur du bouton avion selon l'état du contrôleur"""
        is_enabled = self.controller.is_auto_travel_enabled
        if is_enabled:
            self.btn_auto_travel.fg_color = "#00ff00"  # Vert si actif
        else:
            self.btn_auto_travel.fg_color = "#666666"  # Gris si inactif
        self.btn_auto_travel.draw()

    def on_step_submit(self, event=None):
        """Appelé quand l'utilisateur appuie sur Entrée dans le champ d'étape"""
        try:
            val = self.var_current_step.get()
            self.controller.on_guide_link_clicked(f"STEP:{val}")

            # On redonne le focus à la fenêtre principale pour réactiver les raccourcis A/D
            self.focus_set()
        except Exception:
            pass

    # --- Mise à jour UI depuis le Controller ---
    def update_tabs(self, guides, active_idx):
        for widget in self.tabs_container.winfo_children(): widget.destroy()

        for i, guide in enumerate(guides):
            is_active = (i == active_idx)
            bg = "#1e1e2e" if is_active else "#2d2d2d"
            fg = "#ffffff" if is_active else "#888888"

            f = tk.Frame(self.tabs_container, bg=bg, padx=10, pady=5)
            f.pack(side="left", padx=(0, 2), fill="y")

            name = guide['name'][:17] + "..." if len(guide['name']) > 20 else guide['name']

            l = tk.Label(f, text=name, bg=bg, fg=fg, cursor="hand2")
            l.pack(side="left")
            l.bind("<Button-1>", lambda e, x=i: self.controller.switch_tab(x))
            f.bind("<Button-1>", lambda e, x=i: self.controller.switch_tab(x))

            c = tk.Label(f, text="✕", bg=bg, fg="#ff5555", font=("Arial", 8), cursor="hand2")
            c.pack(side="left", padx=5)
            c.bind("<Button-1>", lambda e, x=i: self.controller.close_tab(x))

    def update_content(self, guide_data, parser):
        if not guide_data:
            self.var_current_step.set("--")
            self.var_total_steps.set("--")
            self.var_position.set("")
            self.html_viewer.set_html("")
            self.btn_prev.set_state("disabled")
            self.btn_next.set_state("disabled")
            # Désactiver l'input si aucun guide
            self.entry_step.config(state="disabled", bg="#252535")
            return

        # Réactiver l'input
        self.entry_step.config(state="normal", bg="#252535")

        steps = guide_data['steps']
        idx = guide_data['current_idx']

        # Mise à jour des variables texte
        self.var_current_step.set(str(idx + 1))
        self.var_total_steps.set(f"{len(steps)}")

        self.btn_prev.set_state("normal" if idx > 0 else "disabled")
        self.btn_next.set_state("normal" if idx < len(steps) - 1 else "disabled")

        step = steps[idx]
        coords = parser.get_step_coords(step)
        self.var_position.set(f"[{coords[0]}, {coords[1]}]" if coords else "")

        self.html_viewer.set_html(parser.get_step_web_text(step))