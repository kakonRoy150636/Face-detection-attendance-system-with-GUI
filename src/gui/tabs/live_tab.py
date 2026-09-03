"""
Live View Tab.
Contains the video feed, top stat cards, matched face panel with spinning gear, and activity feed.
"""

from datetime import datetime
import os
import subprocess
import time
from typing import Optional
import cv2
import numpy as np

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    from PIL import Image, ImageTk
except ImportError:
    tk = None
    ttk = None
    messagebox = None
    Image = None
    ImageTk = None

from src.config import C, KNOWN_FOLDER
from src.gui.components import RoundedButton, create_rounded_rect


class LiveTabView:
    """Renders and coordinates the live view tab components."""

    def __init__(self, parent, controller):
        self.parent = parent
        self.c = controller
        self.tab = tk.Frame(parent, bg=C["base"]) if tk else None

        self._match_spinner_job = None
        self._match_spinner_angle = 0
        self._match_spinner_active = False
        self._match_hold_job = None
        self.last_matched_img = None

        if tk:
            self._build_ui()

    def _card(self, parent, title, value, col, fg):
        sz = self.c._sz
        f = tk.Canvas(parent, bg=C["base"], highlightthickness=0)
        f.grid(row=0, column=col, padx=5, sticky="nsew")
        f.bind("<Configure>", lambda e: self._draw_card_bg(f))
        f.columnconfigure(0, weight=1)

        tk.Label(f, text=title, bg=C["surface0"], fg=C["text"],
                 font=("Segoe UI", sz + 2, "bold")).pack(pady=(8, 0))
        lbl = tk.Label(f, text=value, bg=C["surface0"], fg=fg,
                       font=("Segoe UI", sz + 8, "bold"))
        lbl.pack(pady=(0, 8))
        return lbl

    def _draw_card_bg(self, canvas):
        canvas.delete("rounded_bg")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w > 10 and h > 10:
            create_rounded_rect(canvas, 0, 0, w, h, r=20, fill=C["surface0"], outline=C["surface1"], width=1, tags="rounded_bg")
            canvas.tag_lower("rounded_bg")

    def _build_ui(self):
        sz = self.c._sz

        # Top metric cards
        cards_row = ttk.Frame(self.tab)
        cards_row.pack(fill="x", padx=12, pady=(10, 6))
        cards_row.columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.c_faces = self._card(cards_row, "Known Faces", "0", 0, C["blue"])
        self.c_present = self._card(cards_row, "Present", "0", 1, C["green"])
        self.c_absent = self._card(cards_row, "Absent", "0", 2, C["red"])
        self.c_fps = self._card(cards_row, "FPS", "0", 3, C["peach"])
        self.c_date = self._card(cards_row, "Date", datetime.now().strftime("%Y-%m-%d"), 4, C["lavender"])

        # Middle container
        mid = ttk.Frame(self.tab)
        mid.pack(fill="both", expand=True, padx=12, pady=4)
        mid.columnconfigure(0, weight=5)
        mid.columnconfigure(1, weight=2)
        mid.rowconfigure(0, weight=1)

        # Left: Stream box
        stream_box = tk.Canvas(mid, bg=C["base"], highlightthickness=0)
        stream_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        stream_box.bind("<Configure>", lambda e: self._draw_rounded_box(stream_box, r=30))

        stream_header = tk.Frame(stream_box, bg=C["surface0"])
        stream_header.pack(fill="x")
        tk.Label(stream_header, text="  LIVE CAMERA STREAM", bg=C["surface0"], fg=C["sky"],
                 font=("Segoe UI", sz, "bold"), anchor="w", padx=10).pack(side="left", fill="x", expand=True)
        self.stream_status_lbl = tk.Label(stream_header, text="  ⏸ Idle  ", bg=C["surface0"], fg=C["subtext"],
                                          font=("Segoe UI", sz - 1))
        self.stream_status_lbl.pack(side="right", padx=6)

        self.stream_canvas = tk.Label(
            stream_box, bg=C["crust"],
            text="\n\n\n  Press  ▶ Start System  to begin\n",
            fg=C["subtext"], font=("Segoe UI", sz + 4), justify="center"
        )
        self.stream_canvas.pack(fill="both", expand=True)

        # Right column
        right_col = tk.Frame(mid, bg=C["base"])
        right_col.grid(row=0, column=1, sticky="nsew")
        right_col.rowconfigure(0, weight=3)
        right_col.rowconfigure(1, weight=4)
        right_col.columnconfigure(0, weight=1)

        # Match panel
        match_box = tk.Canvas(right_col, bg=C["base"], highlightthickness=0)
        match_box.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        match_box.bind("<Configure>", lambda e: self._draw_rounded_box(match_box, r=25))

        tk.Label(match_box, text="  MATCHED STUDENT", bg=C["surface0"], fg=C["teal"],
                 font=("Segoe UI", sz, "bold"), anchor="w", padx=10).pack(fill="x")

        self.match_canvas = tk.Canvas(match_box, bg=C["crust"], highlightthickness=0, bd=0)
        self.match_canvas.pack(fill="both", expand=True)
        self.match_canvas.bind("<Configure>", lambda e: self._render_match_waiting_state(spinning=self._match_spinner_active))
        self._render_match_waiting_state(spinning=False)

        self.match_name_lbl = tk.Label(
            match_box, text="  — No match yet —",
            bg=C["surface0"], fg=C["text"], font=("Segoe UI", sz + 1, "bold"), pady=6
        )
        self.match_name_lbl.pack(fill="x")

        # Activity box
        act_box = tk.Canvas(right_col, bg=C["base"], highlightthickness=0)
        act_box.grid(row=1, column=0, sticky="nsew")
        act_box.bind("<Configure>", lambda e: self._draw_rounded_box(act_box, r=25))

        tk.Label(act_box, text="  RECENT ACTIVITY", bg=C["surface0"], fg=C["peach"],
                 font=("Segoe UI", sz, "bold"), anchor="w", padx=10).pack(fill="x")

        self.activity_list = tk.Listbox(
            act_box, bg=C["crust"], fg=C["teal"], font=("Consolas", sz),
            borderwidth=0, highlightthickness=0, selectbackground=C["surface1"]
        )
        self.activity_list.pack(fill="both", expand=True, padx=4, pady=4)

        # Bottom Buttons
        btn_bar = tk.Frame(self.tab, bg=C["base"])
        btn_bar.pack(fill="x", padx=12, pady=(4, 10))

        self.start_btn = RoundedButton(btn_bar, "▶ Start System", self.c.start_system, C["blue"], "#000000", C["sky"], width=150, height=40, radius=20)
        self.start_btn.pack(side="left", padx=4)

        self.stop_btn = RoundedButton(btn_bar, "⏹ Stop System", self.c.stop_system, C["red"], "#AD3E3E", C["pink"], width=150, height=40, radius=20)
        self.stop_btn.pack(side="left", padx=4)
        self.stop_btn.config(state="disabled")

        self.save_btn = RoundedButton(btn_bar, "💾 Save Reports", self.c.save_all_reports, C["green"], "#000000", C["teal"], width=150, height=40, radius=20)
        self.save_btn.pack(side="left", padx=4)

        self.known_btn = RoundedButton(btn_bar, "📁 Known Faces", self._open_known_folder, C["surface1"], C["text"], C["surface2"], width=150, height=40, radius=20)
        self.known_btn.pack(side="right", padx=4)

        self.refresh_btn = RoundedButton(btn_bar, "🔄 Refresh", self.c.refresh_all, C["surface1"], C["text"], C["surface2"], width=120, height=40, radius=20)
        self.refresh_btn.pack(side="right", padx=4)

        self.reset_btn = RoundedButton(btn_bar, "🔁 Reset Today", self.c.reset_today, C["surface1"], C["text"], C["surface2"], width=140, height=40, radius=20)
        self.reset_btn.pack(side="right", padx=4)

    def _draw_rounded_box(self, canvas, r=25):
        canvas.delete("rounded_bg")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w > 10 and h > 10:
            create_rounded_rect(canvas, 0, 0, w, h, r=r, fill=C["crust"], outline=C["surface1"], width=2, tags="rounded_bg")
            canvas.tag_lower("rounded_bg")

    def _open_known_folder(self):
        os.makedirs(KNOWN_FOLDER, exist_ok=True)
        try:
            subprocess.Popen(["xdg-open", KNOWN_FOLDER])
        except Exception:
            pass

    # Spinner Animation
    def set_match_spinner_active(self, active: bool):
        self._match_spinner_active = active
        if not active and self._match_spinner_job is not None:
            self.c.root.after_cancel(self._match_spinner_job)
            self._match_spinner_job = None
            return
        if active and self._match_spinner_job is None:
            self._animate_match_spinner()

    def _animate_match_spinner(self):
        if not self._match_spinner_active:
            self._match_spinner_job = None
            return
        self._match_spinner_angle = (self._match_spinner_angle + 10) % 360
        self._render_match_waiting_state(spinning=True)
        self._match_spinner_job = self.c.root.after(60, self._animate_match_spinner)

    def _draw_spinner_arrow(self, canvas, center_x, center_y, radius, angle_deg, color):
        angle = np.deg2rad(angle_deg)
        x1 = center_x + np.cos(angle) * radius
        y1 = center_y - np.sin(angle) * radius
        x2 = center_x + np.cos(angle) * (radius + 10)
        y2 = center_y - np.sin(angle) * (radius + 10)
        tip1 = np.deg2rad(angle_deg - 145)
        tip2 = np.deg2rad(angle_deg + 145)
        ax1 = x2 + np.cos(tip1) * 8
        ay1 = y2 - np.sin(tip1) * 8
        ax2 = x2 + np.cos(tip2) * 8
        ay2 = y2 - np.sin(tip2) * 8
        canvas.create_line(x1, y1, x2, y2, fill=color, width=3, capstyle=tk.ROUND)
        canvas.create_line(x2, y2, ax1, ay1, fill=color, width=3, capstyle=tk.ROUND)
        canvas.create_line(x2, y2, ax2, ay2, fill=color, width=3, capstyle=tk.ROUND)

    def _draw_spinner_gear(self, canvas, center_x, center_y, radius, color):
        tooth_outer = radius
        tooth_inner = radius * 0.72
        for index in range(8):
            angle = np.deg2rad(index * 45 + self._match_spinner_angle * 0.3)
            outer_x = center_x + np.cos(angle) * tooth_outer
            outer_y = center_y - np.sin(angle) * tooth_outer
            inner_x = center_x + np.cos(angle) * tooth_inner
            inner_y = center_y - np.sin(angle) * tooth_inner
            canvas.create_line(inner_x, inner_y, outer_x, outer_y, fill=color, width=7, capstyle=tk.ROUND)

        gear_r = radius * 0.58
        canvas.create_oval(center_x - gear_r, center_y - gear_r, center_x + gear_r, center_y + gear_r, fill=color, outline="")
        hole_r = radius * 0.23
        canvas.create_oval(center_x - hole_r, center_y - hole_r, center_x + hole_r, center_y + hole_r, fill=C["crust"], outline="")

    def _render_match_waiting_state(self, spinning=False):
        if not hasattr(self, "match_canvas") or self.match_canvas is None:
            return
        canvas = self.match_canvas
        canvas.delete("all")
        if hasattr(canvas, "_photo"):
            delattr(canvas, "_photo")

        width = max(canvas.winfo_width(), 10)
        height = max(canvas.winfo_height(), 10)
        center_x = width / 2
        center_y = max(58, height * 0.34)
        orbit_r = max(30, min(width, height) * 0.17)
        gear_color = C["text"] if not spinning else C["rosewater"]
        ring_color = C["surface2"] if not spinning else C["text"]

        for offset in (0, 120, 240):
            start_angle = self._match_spinner_angle + offset
            canvas.create_arc(
                center_x - orbit_r, center_y - orbit_r,
                center_x + orbit_r, center_y + orbit_r,
                start=start_angle, extent=70, style="arc",
                outline=ring_color, width=4
            )
            self._draw_spinner_arrow(canvas, center_x, center_y, orbit_r, start_angle + 70, ring_color)

        self._draw_spinner_gear(canvas, center_x, center_y, max(14, orbit_r * 0.42), gear_color)

        canvas.create_text(
            center_x, center_y + orbit_r + 24, text="Waiting for",
            fill=C["text"], font=("Segoe UI", self.c._sz + 2, "bold")
        )
        canvas.create_text(
            center_x, center_y + orbit_r + 50, text="face match...",
            fill=C["subtext"], font=("Segoe UI", self.c._sz + 1)
        )

    def show_stream_frame(self, bgr_frame):
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        lw = self.stream_canvas.winfo_width()
        lh = self.stream_canvas.winfo_height()
        if lw > 10 and lh > 10:
            pil.thumbnail((lw, lh), Image.LANCZOS)
        photo = ImageTk.PhotoImage(pil)
        self.stream_canvas.config(image=photo, text="")
        self.stream_canvas._photo = photo

    def update_match_panel(self, name: str, dist: float, img_path: Optional[str] = None):
        if img_path and os.path.exists(img_path):
            self.last_matched_img = cv2.imread(img_path)

        if self.last_matched_img is None:
            return

        self.set_match_spinner_active(False)
        if self._match_hold_job is not None:
            self.c.root.after_cancel(self._match_hold_job)
            self._match_hold_job = None

        rgb = cv2.cvtColor(self.last_matched_img, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        lw = self.match_canvas.winfo_width()
        lh = self.match_canvas.winfo_height()
        if lw > 10 and lh > 10:
            pil.thumbnail((lw, lh), Image.LANCZOS)
        photo = ImageTk.PhotoImage(pil)
        self.match_canvas.delete("all")
        self.match_canvas.create_image(lw / 2, lh / 2, image=photo)
        self.match_canvas._photo = photo

        conf = (1 - dist) * 100
        self.match_name_lbl.config(text=f"  ✓  {name}  —  {conf:.0f}% match", fg=C["green"])
        self._match_hold_job = self.c.root.after(3000, self._restore_match_waiting_state)

    def _restore_match_waiting_state(self):
        self._match_hold_job = None
        if not self.c.running:
            return
        self.match_name_lbl.config(text="  — No match yet —", fg=C["text"])
        self._render_match_waiting_state(spinning=True)
        self.set_match_spinner_active(True)

    def add_activity(self, text: str):
        self.activity_list.insert(0, text)
        if self.activity_list.size() > 50:
            self.activity_list.delete(50, tk.END)

    def refresh_cards(self, faces_count: int, present_count: int, absent_count: int, fps_val: float):
        self.c_faces.config(text=str(faces_count))
        self.c_present.config(text=str(present_count))
        self.c_absent.config(text=str(absent_count))
        self.c_fps.config(text=f"{fps_val:.1f}")
        self.c_date.config(text=datetime.now().strftime("%Y-%m-%d"))

    def reset_stream_display(self):
        self.stream_canvas.config(
            image='',
            text="\n\n\n  Press  ▶ Start System  to begin\n",
            fg=C["subtext"],
            font=("Segoe UI", self.c._sz + 4),
            justify="center"
        )
        if hasattr(self.stream_canvas, '_photo'):
            delattr(self.stream_canvas, '_photo')

        self.set_match_spinner_active(False)
        if self._match_hold_job is not None:
            self.c.root.after_cancel(self._match_hold_job)
            self._match_hold_job = None
        self._render_match_waiting_state(spinning=False)
        self.match_name_lbl.config(text="  — No match yet —", fg=C["text"])
