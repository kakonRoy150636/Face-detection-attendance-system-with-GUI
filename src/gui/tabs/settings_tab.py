"""
Settings Tab.
Provides runtime parameter tuning for detection models, camera source(s), and verification timeouts.

Camera URLs now support MULTIPLE sources: each entry can be a device index (e.g. 0),
an RTSP URL, or an HTTP/MJPEG URL. Add/Remove entries before saving.
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
        self._cam_listbox = None
        self._cam_entry = None

        if tk:
            self._build_ui()

    def _draw_settings_bg(self, canvas):
        canvas.delete("rounded_bg")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w > 10 and h > 10:
            create_rounded_rect(canvas, 0, 0, w, h, r=25, fill=C["crust"], outline=C["surface1"], width=2, tags="rounded_bg")
            canvas.tag_lower("rounded_bg")

    # ---- Camera URL helpers ----
    def _load_camera_urls(self):
        """Populate the camera listbox from config, tolerating str-or-list loads."""
        urls = self.c.config.get("camera_urls", DEFAULT_CONFIG["camera_urls"])
        if isinstance(urls, str):
            urls = [urls]
        self._cam_listbox.delete(0, tk.END)
        for u in urls:
            self._cam_listbox.insert(tk.END, str(u))

    def _add_camera_url(self):
        val = self._cam_entry.get().strip()
        if not val:
            return
        existing = set(self._cam_listbox.get(0, tk.END))
        if val not in existing:
            self._cam_listbox.insert(tk.END, val)
        self._cam_entry.delete(0, tk.END)

    def _remove_camera_url(self):
        sel = self._cam_listbox.curselection()
        if not sel:
            return
        self._cam_listbox.delete(sel[0])

    def _bind_cam_entry(self, event):
        if event.keysym == "Return":
            self._add_camera_url()
            return "break"

    def _build_ui(self):
        settings_container = tk.Canvas(self.tab, bg=C["base"], highlightthickness=0)
        settings_container.pack(fill="both", expand=True, padx=20, pady=20)
        settings_container.bind("<Configure>", lambda e: self._draw_settings_bg(settings_container))

        form = tk.Frame(settings_container, bg=C["crust"])
        form.pack(padx=30, pady=20, anchor="nw")

        sz = self.c._sz
        row = 0

        # ---- Camera URLs (multi-source) ----
        tk.Label(
            form, text="Camera URLs", bg=C["crust"], fg=C["text"],
            font=("Segoe UI", sz)
        ).grid(row=row, column=0, sticky="nw", pady=8, padx=(0, 20))

        cam_frame = tk.Frame(form, bg=C["crust"])
        cam_frame.grid(row=row, column=1, sticky="nsew", pady=8)

        self._cam_listbox = tk.Listbox(
            cam_frame, height=4,
            bg=C["surface0"], fg=C["text"], selectbackground=C["blue"],
            selectforeground="#000000", highlightthickness=1,
            highlightbackground=C["surface1"], highlightcolor=C["blue"],
            font=("Consolas", sz), borderwidth=0, activestyle="none"
        )
        self._cam_listbox.pack(fill="x", side="top")

        cam_actions = tk.Frame(cam_frame, bg=C["crust"])
        cam_actions.pack(fill="x", side="top", pady=(6, 0))

        self._cam_entry = tk.Entry(
            cam_actions, bg=C["surface0"], fg=C["text"],
            insertbackground=C["text"], font=("Consolas", sz),
            borderwidth=2, relief="flat",
            highlightthickness=1, highlightbackground=C["surface1"],
            highlightcolor=C["blue"]
        )
        self._cam_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self._cam_entry.bind("<KeyRelease>", self._bind_cam_entry)

        add_btn = RoundedButton(cam_actions, "+ Add", self._add_camera_url, C["green"], "#000000", C["teal"], width=64, height=30, radius=15)
        add_btn.pack(side="left", padx=(6, 0))
        rm_btn = RoundedButton(cam_actions, "✕ Remove", self._remove_camera_url, C["red"], "#000000", C["pink"], width=80, height=30, radius=15)
        rm_btn.pack(side="left", padx=(6, 0))

        tk.Label(
            form,
            text="One source per line: device index (0), RTSP / MJPEG URL.\n"
                 "Press Enter or '+ Add' to insert each source.",
            bg=C["crust"], fg=C["subtext"], font=("Segoe UI", max(8, sz - 2)),
            justify="left"
        ).grid(row=row + 1, column=1, sticky="w", pady=(0, 8), padx=(0, 20))

        self._load_camera_urls()
        row += 2

        # ---- Other single-value fields ----
        fields = [
            ("Tolerance (0-1)", "tolerance", float),
            ("Detection Model (hog/cnn)", "detection_model", str),
            ("Confirm Time (seconds)", "confirm_time", float),
            ("Num Jitters", "num_jitters", int),
            ("Text Size (8-20)", "text_size", int),
        ]

        for i, (label, key, typ) in enumerate(fields):
            tk.Label(
                form, text=label, bg=C["crust"], fg=C["text"],
                font=("Segoe UI", sz)
            ).grid(row=row + i, column=0, sticky="w", pady=8, padx=(0, 20))

            var = tk.StringVar(value=str(self.c.config.get(key, DEFAULT_CONFIG[key])))
            entry = tk.Entry(
                form, textvariable=var, width=52,
                bg=C["surface0"], fg=C["text"],
                insertbackground=C["text"], font=("Consolas", sz),
                borderwidth=2, relief="flat",
                highlightthickness=1, highlightbackground=C["surface1"],
                highlightcolor=C["blue"]
            )
            entry.grid(row=row + i, column=1, pady=8, ipady=6)
            self._setting_vars[key] = (var, typ)

        r = row + len(fields)
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
            urls = list(self._cam_listbox.get(0, tk.END))
            urls = [u.strip() for u in urls if u.strip()]
            self.c.config["camera_urls"] = urls if urls else ["0"]
            for k, (var, typ) in self._setting_vars.items():
                self.c.config[k] = typ(var.get())
            save_config(self.c.config)
            messagebox.showinfo("Saved", "Settings saved. Restart system to apply.")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value:\n{e}")

    def reset_settings(self):
        self.c.config = DEFAULT_CONFIG.copy()
        self._load_camera_urls()
        for k, (var, _) in self._setting_vars.items():
            var.set(str(DEFAULT_CONFIG[k]))
        save_config(self.c.config)