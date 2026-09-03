"""
Settings Tab.
Provides runtime parameter tuning for detection models, camera source, and verification timeouts.
"""

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    tk = None
    messagebox = None

from src.config import C, DEFAULT_CONFIG, save_config
from src.gui.components import RoundedButton, create_rounded_rect


class SettingsTabView:
    """Renders the settings input fields."""

    def __init__(self, parent, controller):
        self.parent = parent
        self.c = controller
        self.tab = tk.Frame(parent, bg=C["base"]) if tk else None
        self._setting_vars = {}

        if tk:
            self._build_ui()

    def _draw_settings_bg(self, canvas):
        canvas.delete("rounded_bg")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w > 10 and h > 10:
            create_rounded_rect(canvas, 0, 0, w, h, r=25, fill=C["crust"], outline=C["surface1"], width=2, tags="rounded_bg")
            canvas.tag_lower("rounded_bg")

    def _build_ui(self):
        settings_container = tk.Canvas(self.tab, bg=C["base"], highlightthickness=0)
        settings_container.pack(fill="both", expand=True, padx=20, pady=20)
        settings_container.bind("<Configure>", lambda e: self._draw_settings_bg(settings_container))

        form = tk.Frame(settings_container, bg=C["crust"])
        form.pack(padx=30, pady=20, anchor="nw")

        fields = [
            ("Camera URL", "camera_url", str),
            ("Tolerance (0-1)", "tolerance", float),
            ("Detection Model (hog/cnn)", "detection_model", str),
            ("Confirm Time (seconds)", "confirm_time", float),
            ("Num Jitters", "num_jitters", int),
            ("Text Size (8-20)", "text_size", int),
        ]

        for i, (label, key, typ) in enumerate(fields):
            tk.Label(
                form, text=label, bg=C["crust"], fg=C["text"],
                font=("Segoe UI", self.c._sz)
            ).grid(row=i, column=0, sticky="w", pady=8, padx=(0, 20))

            var = tk.StringVar(value=str(self.c.config.get(key, DEFAULT_CONFIG[key])))
            entry = tk.Entry(
                form, textvariable=var, width=52,
                bg=C["surface0"], fg=C["text"],
                insertbackground=C["text"], font=("Consolas", self.c._sz),
                borderwidth=2, relief="flat",
                highlightthickness=1, highlightbackground=C["surface1"],
                highlightcolor=C["blue"]
            )
            entry.grid(row=i, column=1, pady=8, ipady=6)
            self._setting_vars[key] = (var, typ)

        r = len(fields)
        brow = tk.Frame(form, bg=C["crust"])
        brow.grid(row=r, column=0, columnspan=2, pady=18)

        RoundedButton(brow, "💾 Save Settings", self.save_settings, C["blue"], "#000000", C["sky"], width=160, height=38, radius=19).pack(side="left", padx=8)
        RoundedButton(brow, "🔄 Reset Defaults", self.reset_settings, C["surface1"], C["text"], C["surface2"], width=160, height=38, radius=19).pack(side="left", padx=8)

        tk.Label(
            form, text="Save & restart the app to apply text size and other changes.",
            bg=C["crust"], foreground=C["yellow"], font=("Segoe UI", 9, "italic")
        ).grid(row=r + 1, column=0, columnspan=2, sticky="w", pady=4)

    def save_settings(self):
        try:
            for k, (var, typ) in self._setting_vars.items():
                self.c.config[k] = typ(var.get())
            save_config(self.c.config)
            messagebox.showinfo("Saved", "Settings saved. Restart system to apply.")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value:\n{e}")

    def reset_settings(self):
        self.c.config = DEFAULT_CONFIG.copy()
        for k, (var, _) in self._setting_vars.items():
            var.set(str(DEFAULT_CONFIG[k]))
        save_config(self.c.config)
