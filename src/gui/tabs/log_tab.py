"""
Log Tab.
Displays the scrolling terminal output with styled controls.
"""

try:
    import tkinter as tk
    from tkinter import scrolledtext
except ImportError:
    tk = None
    scrolledtext = None

from src.config import C
from src.gui.components import RoundedButton, create_rounded_rect


class LogTabView:
    """Renders the execution log console."""

    def __init__(self, parent, controller):
        self.parent = parent
        self.c = controller
        self.tab = tk.Frame(parent, bg=C["base"]) if tk else None

        if tk:
            self._build_ui()

    def _draw_log_bg(self, canvas):
        canvas.delete("rounded_bg")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w > 10 and h > 10:
            create_rounded_rect(canvas, 0, 0, w, h, r=25, fill=C["crust"], outline=C["surface1"], width=2, tags="rounded_bg")
            canvas.tag_lower("rounded_bg")

    def _build_ui(self):
        sz = self.c._sz
        log_container = tk.Canvas(self.tab, bg=C["base"], highlightthickness=0)
        log_container.pack(fill="both", expand=True, padx=14, pady=14)
        log_container.bind("<Configure>", lambda e: self._draw_log_bg(log_container))

        self.log_text = scrolledtext.ScrolledText(
            log_container, bg=C["crust"], fg=C["teal"], font=("Consolas", sz),
            insertbackground=C["teal"], borderwidth=0, state="disabled", wrap="word"
        )
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

        brow = tk.Frame(self.tab, bg=C["base"])
        brow.pack(fill="x", padx=10, pady=(0, 10))

        RoundedButton(
            brow, "🗑️ Clear Log", self.clear_log,
            C["surface1"], C["text"], C["surface2"], width=120, height=38, radius=19
        ).pack(side="right", padx=4)

    def append_log(self, msg: str):
        if not hasattr(self, "log_text"):
            return
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, msg)
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def clear_log(self):
        if not hasattr(self, "log_text"):
            return
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")
