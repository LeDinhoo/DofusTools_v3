import tkinter as tk
from interface.html_engine import RichTextDisplay
from interface.controls import RoundedButton


class GuidePanel(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, width=500, bg="#1e1e2e")
        self.controller = controller

        # Variables liées à l'affichage
        self.var_position = tk.StringVar(value="")
        self.var_step_display = tk.StringVar(value="-- / --")
        self.var_guide_name = tk.StringVar(value="Aucun guide")

        self.setup_layout()

    def setup_layout(self):
        # 1. Barre des Onglets
        self.tabs_container = tk.Frame(self, bg="#121212", height=30)
        self.tabs_container.pack(fill="x", side="top")

        # 2. Header de Navigation
        nav_bar = tk.Frame(self, bg="#252535", height=40)
        nav_bar.pack(fill="x", side="top")
        nav_bar.pack_propagate(False)

        nav_bar.grid_columnconfigure(0, weight=0, minsize=140)
        nav_bar.grid_columnconfigure(1, weight=1)
        nav_bar.grid_columnconfigure(2, weight=0)
        nav_bar.grid_rowconfigure(0, weight=1)

        # Position (Gauche)
        self.lbl_position = tk.Label(nav_bar, textvariable=self.var_position,
                                     bg="#252535", fg="#ffd700", font=("Segoe UI", 12, "bold"), cursor="hand2")
        self.lbl_position.grid(row=0, column=0, padx=15, sticky="w")
        self.lbl_position.bind("<Button-1>", self.controller.copy_position)

        # Navigation (Droite)
        nav_group = tk.Frame(nav_bar, bg="#252535")
        nav_group.grid(row=0, column=2, padx=10, sticky="e")

        self.btn_prev = RoundedButton(nav_group, text="<", command=self.controller.nav_previous,
                                      width=32, height=32, radius=12, bg_color="#252535", hover_color="#3a3a4a")
        self.btn_prev.pack(side="left", padx=5)

        tk.Label(nav_group, textvariable=self.var_step_display,
                 bg="#252535", fg="#4da6ff", font=("Consolas", 12, "bold"), width=10).pack(side="left", padx=5)

        self.btn_next = RoundedButton(nav_group, text=">", command=self.controller.nav_next,
                                      width=32, height=32, radius=12, bg_color="#252535", hover_color="#3a3a4a")
        self.btn_next.pack(side="left", padx=5)

        # 3. Viewer HTML
        self.html_viewer = RichTextDisplay(self, on_link_click=self.controller.on_guide_link_clicked)
        self.html_viewer.pack(fill="both", expand=True, padx=0, pady=0)

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
        # Mise à jour de l'affichage HTML et des compteurs
        # Note: Le contrôleur passera ici les données brutes
        if not guide_data:
            self.var_step_display.set("-- / --")
            self.var_position.set("")
            self.html_viewer.set_html("")
            self.btn_prev.set_state("disabled")
            self.btn_next.set_state("disabled")
            return

        steps = guide_data['steps']
        idx = guide_data['current_idx']

        self.var_step_display.set(f"{idx + 1} / {len(steps)}")
        self.btn_prev.set_state("normal" if idx > 0 else "disabled")
        self.btn_next.set_state("normal" if idx < len(steps) - 1 else "disabled")

        step = steps[idx]
        coords = parser.get_step_coords(step)
        self.var_position.set(f"[{coords[0]}, {coords[1]}]" if coords else "")

        self.html_viewer.set_html(parser.get_step_web_text(step))