"""
Custom styled canvas widgets for the Face Attendance GUI.
Preserves the exact rounded buttons, glassmorphic tabs, and smooth corner shapes.
"""

try:
    import tkinter as tk
except ImportError:
    tk = None

from src.config import C


def create_rounded_rect(canvas, x1, y1, x2, y2, r=20, **kwargs):
    """Draws a smooth polygon with rounded corners on a Tkinter canvas."""
    points = [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def blend_hex(c1: str, c2: str, t: float) -> str:
    """Linearly blends two hex color strings."""
    c1 = c1.lstrip("#")
    c2 = c2.lstrip("#")
    r = int(int(c1[0:2], 16) * (1 - t) + int(c2[0:2], 16) * t)
    g = int(int(c1[2:4], 16) * (1 - t) + int(c2[2:4], 16) * t)
    b = int(int(c1[4:6], 16) * (1 - t) + int(c2[4:6], 16) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


class RoundedButton:
    """Custom button with rounded corners and interactive hover animations."""

    def __init__(self, parent, text, command, bg_color, fg_color, hover_color, width=140, height=36, radius=18):
        self.parent = parent
        self.text = text
        self.command = command
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_color = hover_color
        self.width = width
        self.height = height
        self.radius = radius
        self.is_hovered = False

        self.canvas = tk.Canvas(
            parent, width=width, height=height,
            bg=C["base"], highlightthickness=0, cursor="hand2"
        )

        self.bg_rect = create_rounded_rect(
            self.canvas, 2, 2, width - 2, height - 2,
            r=radius, fill=bg_color, outline="", width=0
        )

        self.text_id = self.canvas.create_text(
            width // 2, height // 2, text=text,
            fill=fg_color, font=("Segoe UI", 10, "bold")
        )

        self.canvas.bind("<Button-1>", lambda e: self.command())
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)

    def _on_enter(self, e):
        self.is_hovered = True
        self.canvas.itemconfig(self.bg_rect, fill=self.hover_color)

    def _on_leave(self, e):
        self.is_hovered = False
        self.canvas.itemconfig(self.bg_rect, fill=self.bg_color)

    def pack(self, **kwargs):
        self.canvas.pack(**kwargs)

    def config(self, **kwargs):
        if "state" in kwargs:
            state = kwargs["state"]
            if state == "disabled":
                self.canvas.config(cursor="arrow")
                self.canvas.itemconfig(self.bg_rect, fill=C["surface1"])
                self.canvas.itemconfig(self.text_id, fill=C["overlay0"])
                self.canvas.unbind("<Button-1>")
            else:
                self.canvas.config(cursor="hand2")
                self.canvas.itemconfig(self.bg_rect, fill=self.bg_color)
                self.canvas.itemconfig(self.text_id, fill=self.fg_color)
                self.canvas.bind("<Button-1>", lambda e: self.command())


class RoundedTab:
    """Glassmorphism-style tab with rounded corners, top shine, and active state."""

    def __init__(self, parent, text, command, width=180, height=42, radius=20):
        self.parent = parent
        self.text = text
        self.command = command
        self.width = width
        self.height = height
        self.radius = radius
        self.is_selected = False
        self.is_hovered = False

        self.canvas = tk.Canvas(
            parent, width=width, height=height,
            bg=C["base"], highlightthickness=0, cursor="hand2"
        )
        self.bg_rect = None
        self.shine_rect = None
        self.border_rect = None

        self.text_id = self.canvas.create_text(
            width // 2, height // 2 - 2, text=text,
            fill=C["text"], font=("Segoe UI", 14, "bold")
        )

        self._redraw()

        self.canvas.bind("<Button-1>", lambda e: self.command())
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)

    def _draw_rounded_top_rect(self, canvas, x1, y1, x2, y2, r, fill):
        return create_rounded_rect(canvas, x1, y1, x2, y2, r=r, fill=fill, outline="")

    def _redraw(self):
        self.canvas.delete("tab_bg")

        base_fill = blend_hex(C["surface0"], C["lavender"], 0.08)
        hover_fill = blend_hex(C["surface1"], C["sky"], 0.10)
        active_fill = blend_hex(C["blue"], C["sky"], 0.35)

        if self.is_selected:
            fill = active_fill
            text_color = "#000000"
            border = blend_hex(C["sky"], "#ffffff", 0.35)
        elif self.is_hovered:
            fill = hover_fill
            text_color = C["rosewater"]
            border = blend_hex(C["surface2"], C["sky"], 0.35)
        else:
            fill = base_fill
            text_color = C["text"]
            border = blend_hex(C["surface2"], C["lavender"], 0.20)

        # Glass body
        self.bg_rect = self._draw_rounded_top_rect(
            self.canvas, 2, 2, self.width - 2, self.height - 2,
            r=self.radius, fill=fill
        )
        self.canvas.itemconfig(self.bg_rect, tags=("tab_bg",))

        # Top glossy highlight strip (glass reflection)
        self.shine_rect = self._draw_rounded_top_rect(
            self.canvas, 6, 5, self.width - 6, int(self.height * 0.45),
            r=max(8, self.radius - 8), fill=blend_hex(fill, "#ffffff", 0.22)
        )
        self.canvas.itemconfig(self.shine_rect, tags=("tab_bg",))

        # Border line
        self.border_rect = self._draw_rounded_top_rect(
            self.canvas, 2, 2, self.width - 2, self.height - 2,
            r=self.radius, fill=""
        )
        self.canvas.itemconfig(self.border_rect, outline=border, width=1.2, tags=("tab_bg",))

        self.canvas.itemconfig(self.text_id, fill=text_color)
        self.canvas.tag_raise(self.text_id)

    def _on_enter(self, e):
        if not self.is_selected:
            self.is_hovered = True
            self._redraw()

    def _on_leave(self, e):
        if not self.is_selected:
            self.is_hovered = False
            self._redraw()

    def select(self):
        self.is_selected = True
        self.is_hovered = False
        self._redraw()

    def deselect(self):
        self.is_selected = False
        self._redraw()

    def pack(self, **kwargs):
        self.canvas.pack(**kwargs)
