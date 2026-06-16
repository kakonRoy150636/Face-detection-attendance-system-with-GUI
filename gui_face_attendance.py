

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import cv2
import face_recognition
import numpy as np
import threading
import queue
import os
import sys
import json
import csv
import time
import pandas as pd
from datetime import datetime
from PIL import Image, ImageTk

# ===========================
# PATHS & DEFAULTS
# ===========================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(SCRIPT_DIR, "attendance_status.json")
CSV_FILE = os.path.join(SCRIPT_DIR, "attendance_today.csv")
REGISTER_CSV = os.path.join(SCRIPT_DIR, "attendance_today_register.csv")
COLUMN_CSV = os.path.join(SCRIPT_DIR, "attendance_today_column.csv")
EXCEL_FILE = os.path.join(SCRIPT_DIR, "attendance_today.xlsx")
KNOWN_FOLDER = os.path.join(SCRIPT_DIR, "known_faces")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "gui_config.json")

DEFAULT_CONFIG = {
    "camera_url": "http://192.168.0.101:4747/video",
    "tolerance": 0.50,
    "detection_model": "hog",
    "confirm_time": 1.0,
    "num_jitters": 2,
    "text_size": 10,
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)


# Catppuccin Mocha palette
C = {
    "base":     "#1d1d32",
    "mantle":   "#181825",
    "crust":    "#11111b",
    "surface0": "#313244",
    "surface1": "#45475a",
    "surface2": "#585b70",
    "overlay0": "#6c7086",
    "text":     "#cdd6f4",
    "subtext":  "#a6adc8",
    "blue":     "#89b4fa",
    "green":    "#a6e3a1",
    "red":      "#f38ba8",
    "yellow":   "#f9e2af",
    "peach":    "#fab387",
    "mauve":    "#cba6f7",
    "teal":     "#94e2d5",
    "lavender": "#b4befe",
    "sky":      "#89dceb",
    "pink":     "#f5c2e7",
    "rosewater": "#f5e0dc",
}

def create_rounded_rect(canvas, x1, y1, x2, y2, r=20, **kwargs):
    points = [
        x1+r, y1,
        x2-r, y1,
        x2, y1,
        x2, y1+r,
        x2, y2-r,
        x2, y2,
        x2-r, y2,
        x1+r, y2,
        x1, y2,
        x1, y2-r,
        x1, y1+r,
        x1, y1
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)

os.chdir(os.path.dirname(os.path.abspath(__file__)))
class RoundedButton:
    """Custom button with rounded corners"""
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
        
        self.canvas = tk.Canvas(parent, width=width, height=height, 
                               bg=C["base"], highlightthickness=0, cursor="hand2")
        
        # Draw button
        self.bg_rect = create_rounded_rect(self.canvas, 2, 2, width-2, height-2, 
                                          r=radius, fill=bg_color, outline="", width=0)
        
        self.text_id = self.canvas.create_text(width//2, height//2, text=text, 
                                               fill=fg_color, font=("Segoe UI", 10, "bold"))
        
        # Bind events
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
    """Glassmorphism-style tab with rounded corners."""
    def __init__(self, parent, text, command, width=180, height=42, radius=20):
        self.parent = parent
        self.text = text
        self.command = command
        self.width = width
        self.height = height
        self.radius = radius
        self.is_selected = False
        self.is_hovered = False
        
        self.canvas = tk.Canvas(parent, width=width, height=height, 
                               bg=C["base"], highlightthickness=0, cursor="hand2")
        self.bg_rect = None
        self.shine_rect = None
        self.border_rect = None

        self.text_id = self.canvas.create_text(width//2, height//2 - 2, text=text, 
                                               fill=C["text"], font=("Segoe UI", 14, "bold"))

        self._redraw()
        
        # Bind events
        self.canvas.bind("<Button-1>", lambda e: self.command())
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
    
    def _draw_rounded_top_rect(self, canvas, x1, y1, x2, y2, r, fill):
        return create_rounded_rect(canvas, x1, y1, x2, y2, r=r, fill=fill, outline="")

    def _blend(self, c1, c2, t):
        c1 = c1.lstrip("#")
        c2 = c2.lstrip("#")
        r = int(int(c1[0:2], 16) * (1 - t) + int(c2[0:2], 16) * t)
        g = int(int(c1[2:4], 16) * (1 - t) + int(c2[2:4], 16) * t)
        b = int(int(c1[4:6], 16) * (1 - t) + int(c2[4:6], 16) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _redraw(self):
        self.canvas.delete("tab_bg")

        base_fill = self._blend(C["surface0"], C["lavender"], 0.08)
        hover_fill = self._blend(C["surface1"], C["sky"], 0.10)
        active_fill = self._blend(C["blue"], C["sky"], 0.35)

        if self.is_selected:
            fill = active_fill
            text_color = "#000000"
            border = self._blend(C["sky"], "#ffffff", 0.35)
        elif self.is_hovered:
            fill = hover_fill
            text_color = C["rosewater"]
            border = self._blend(C["surface2"], C["sky"], 0.35)
        else:
            fill = base_fill
            text_color = C["text"]
            border = self._blend(C["surface2"], C["lavender"], 0.20)

        # Glass body
        self.bg_rect = self._draw_rounded_top_rect(
            self.canvas, 2, 2, self.width - 2, self.height - 2,
            r=self.radius, fill=fill
        )
        self.canvas.itemconfig(self.bg_rect, tags=("tab_bg",))

        # Top glossy highlight strip (glass reflection)
        self.shine_rect = self._draw_rounded_top_rect(
            self.canvas, 6, 5, self.width - 6, int(self.height * 0.45),
            r=max(8, self.radius - 8), fill=self._blend(fill, "#ffffff", 0.22)
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


class FaceAttendanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Attendance System")
        self.root.geometry("1340x780")
        self.root.minsize(1100, 650)
        self.root.configure(bg=C["base"])
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.config = load_config()
        self.running = False
        self.stop_event = threading.Event()
        self.frame_queue = queue.Queue(maxsize=2)

        self.known_encodings = []
        self.known_names = []
        self.known_paths = []
        self.employees = []
        self.all_status = {}
        self.daily_attendance = {}
        self.attendance_data = []
        self.today_attendance = set()
        self.total_attendance = 0
        self.face_seen_time = {}
        self.recently_matched = {}
        self.last_matched_img = None
        self.last_match_time = 0
        self.fps = 0.0
        self._frame_count = 0
        self._fps_start = time.time()
        self._match_spinner_job = None
        self._match_spinner_angle = 0
        self._match_spinner_active = False
        self._match_hold_job = None

        self._build_styles()
        self._build_ui()
        self._load_known_faces()
        self._load_status_json()
        self._refresh_cards()

    def _build_styles(self):
        self._sz = int(self.config.get("text_size", DEFAULT_CONFIG["text_size"]))
        sz = self._sz

        s = ttk.Style()
        s.theme_use("clam")

        # Rounded tab style
        s.configure("TNotebook", background=C["base"], borderwidth=0, tabmargins=[2, 5, 2, 0])
        s.configure("TNotebook.Tab", 
                   background=C["surface0"], 
                   foreground=C["text"],
                   padding=[20, 10], 
                   font=("Segoe UI", sz, "bold"),
                   borderwidth=0,
                   focuscolor='none')
        s.map("TNotebook.Tab",
               background=[("selected", C["blue"])],
               foreground=[("selected", "#000000")],
               expand=[("selected", [1, 1, 1, 0])])

        s.configure("TFrame", background=C["base"])
        s.configure("TLabel", background=C["base"], foreground=C["text"],
                     font=("Segoe UI", sz))

        # Bright-bg buttons: dark text is fine
        for name, bg, abg in [
            ("Accent.TButton", C["blue"],  C["sky"]),
            ("Danger.TButton", C["red"],   C["pink"]),
            ("Green.TButton",  C["green"], C["teal"]),
        ]:
            s.configure(name, background=bg, foreground="#000000",
                         font=("Segoe UI", sz, "bold"), padding=[14, 7],
                         borderwidth=0, relief="flat")
            s.map(name, background=[("active", abg)])

        # Dark-bg button: needs light text
        s.configure("Normal.TButton", background=C["surface1"],
                     foreground=C["text"],
                     font=("Segoe UI", sz, "bold"), padding=[14, 7],
                     borderwidth=0, relief="flat")
        s.map("Normal.TButton",
               background=[("active", C["surface2"])],
               foreground=[("active", C["rosewater"])])

        s.configure("Treeview", background=C["surface0"], foreground=C["text"],
                     fieldbackground=C["surface0"], font=("Segoe UI", sz),
                     rowheight=max(28, sz * 3))
        s.configure("Treeview.Heading", background=C["surface1"],
                     foreground=C["lavender"], font=("Segoe UI", sz, "bold"))
        s.map("Treeview",
               background=[("selected", C["blue"])],
               foreground=[("selected", "#000000")])

        s.configure("TEntry", fieldbackground=C["surface0"], foreground=C["text"],
                     insertcolor=C["text"], font=("Consolas", sz))

    def _build_ui(self):
        # Top bar
        top = tk.Frame(self.root, bg=C["mantle"], height=54)
        top.pack(fill="x")
        top.pack_propagate(False)

        sz = self._sz
        tk.Label(top, text="  Face Attendance System",
                  bg=C["mantle"], fg=C["lavender"],
                  font=("Segoe UI", sz + 10, "bold")).pack(side="left", padx=18)

        self.clock_lbl = tk.Label(top, bg=C["mantle"], fg=C["text"],
                                    font=("Consolas", sz + 1))
        self.clock_lbl.pack(side="right", padx=18)
        self._tick_clock()

        self.status_dot = tk.Label(top, text="● STOPPED", bg=C["mantle"],
                                     fg=C["red"], font=("Segoe UI", sz + 1, "bold"))
        self.status_dot.pack(side="right", padx=6)

        # Custom rounded tabs navigation
        tab_nav = tk.Frame(
            self.root,
            bg=C["mantle"],
            height=48,
            highlightthickness=1,
            highlightbackground=C["surface1"]
        )
        tab_nav.pack(fill="x", padx=10, pady=(6, 0))
        
        # Create tab buttons
        self.tab_buttons = []
        self.live_tab_btn = RoundedTab(tab_nav, "📹 Live View", lambda: self._switch_tab(0), width=180, height=42, radius=18)
        self.live_tab_btn.pack(side="left", padx=4)
        self.tab_buttons.append(self.live_tab_btn)
        
        self.att_tab_btn = RoundedTab(tab_nav, "📊 Attendance", lambda: self._switch_tab(1), width=180, height=42, radius=18)
        self.att_tab_btn.pack(side="left", padx=4)
        self.tab_buttons.append(self.att_tab_btn)
        
        self.settings_tab_btn = RoundedTab(tab_nav, "⚙️ Settings", lambda: self._switch_tab(2), width=180, height=42, radius=18)
        self.settings_tab_btn.pack(side="left", padx=4)
        self.tab_buttons.append(self.settings_tab_btn)
        
        self.log_tab_btn = RoundedTab(tab_nav, "📝 Log", lambda: self._switch_tab(3), width=150, height=42, radius=18)
        self.log_tab_btn.pack(side="left", padx=4)
        self.tab_buttons.append(self.log_tab_btn)
        
        # Container for tab content
        self.tab_container = tk.Frame(self.root, bg=C["base"])
        self.tab_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Build all tabs
        self.tabs = []
        self._build_live_tab()
        self._build_attendance_tab()
        self._build_settings_tab()
        self._build_log_tab()
        
        # Show first tab
        self._switch_tab(0)
    
    def _switch_tab(self, index):
        """Switch between tabs"""
        # Hide all tabs
        for tab in self.tabs:
            tab.pack_forget()
        
        # Deselect all tab buttons
        for btn in self.tab_buttons:
            btn.deselect()
        
        # Show selected tab
        if 0 <= index < len(self.tabs):
            self.tabs[index].pack(fill="both", expand=True)
            self.tab_buttons[index].select()

    # ===== TAB 1: LIVE VIEW =====
    def _build_live_tab(self):
        sz = self._sz
        tab = tk.Frame(self.tab_container, bg=C["base"])
        self.tabs.append(tab)

        # Cards row
        cards_row = ttk.Frame(tab)
        cards_row.pack(fill="x", padx=12, pady=(10, 6))
        cards_row.columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.c_faces = self._card(cards_row, "Known Faces", "0", 0, C["blue"])
        self.c_present = self._card(cards_row, "Present", "0", 1, C["green"])
        self.c_absent = self._card(cards_row, "Absent", "0", 2, C["red"])
        self.c_fps = self._card(cards_row, "FPS", "0", 3, C["peach"])
        self.c_date = self._card(cards_row, "Date",
                                   datetime.now().strftime("%Y-%m-%d"), 4, C["lavender"])

        # Middle: stream + match + activity
        mid = ttk.Frame(tab)
        mid.pack(fill="both", expand=True, padx=12, pady=4)
        mid.columnconfigure(0, weight=5)
        mid.columnconfigure(1, weight=2)
        mid.rowconfigure(0, weight=1)

        # Left: camera stream (with rounded corners)
        stream_box = tk.Canvas(mid, bg=C["base"], highlightthickness=0)
        stream_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        
        # Draw rounded rectangle background
        stream_box.bind("<Configure>", lambda e: self._draw_stream_box_bg(stream_box))
        
        stream_header = tk.Frame(stream_box, bg=C["surface0"])
        stream_header.pack(fill="x")
        tk.Label(stream_header, text="  LIVE CAMERA STREAM",
                  bg=C["surface0"], fg=C["sky"],
                  font=("Segoe UI", sz, "bold"),
                  anchor="w", padx=10).pack(side="left", fill="x", expand=True)
        self.stream_status_lbl = tk.Label(stream_header, text="  ⏸ Idle  ",
                                            bg=C["surface0"], fg=C["subtext"],
                                            font=("Segoe UI", sz - 1))
        self.stream_status_lbl.pack(side="right", padx=6)

        self.stream_canvas = tk.Label(
            stream_box, bg=C["crust"],
            text="\n\n\n  Press  ▶ Start System  to begin\n",
            fg=C["subtext"], font=("Segoe UI", sz + 4), justify="center")
        self.stream_canvas.pack(fill="both", expand=True)

        # Right column
        right_col = tk.Frame(mid, bg=C["base"])
        right_col.grid(row=0, column=1, sticky="nsew")
        right_col.rowconfigure(0, weight=3)
        right_col.rowconfigure(1, weight=4)
        right_col.columnconfigure(0, weight=1)

        # Match panel (with rounded corners)
        match_box = tk.Canvas(right_col, bg=C["base"], highlightthickness=0)
        match_box.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        
        # Draw rounded rectangle background
        match_box.bind("<Configure>", lambda e: self._draw_match_box_bg(match_box))
        
        tk.Label(match_box, text="  MATCHED STUDENT",
                  bg=C["surface0"], fg=C["teal"],
                  font=("Segoe UI", sz, "bold"),
                  anchor="w", padx=10).pack(fill="x")

        self.match_canvas = tk.Canvas(
            match_box, bg=C["crust"],
            highlightthickness=0,
            bd=0)
        self.match_canvas.pack(fill="both", expand=True)
        self.match_canvas.bind(
            "<Configure>",
            lambda e: self._render_match_waiting_state(
                spinning=self._match_spinner_active
            )
        )
        self._render_match_waiting_state(spinning=False)

        self.match_name_lbl = tk.Label(
            match_box, text="  — No match yet —",
            bg=C["surface0"], fg=C["text"],
            font=("Segoe UI", sz + 1, "bold"), pady=6)
        self.match_name_lbl.pack(fill="x")

        # Activity feed (with rounded corners)
        act_box = tk.Canvas(right_col, bg=C["base"], highlightthickness=0)
        act_box.grid(row=1, column=0, sticky="nsew")
        
        # Draw rounded rectangle background
        act_box.bind("<Configure>", lambda e: self._draw_activity_box_bg(act_box))
        
        tk.Label(act_box, text="  RECENT ACTIVITY",
                  bg=C["surface0"], fg=C["peach"],
                  font=("Segoe UI", sz, "bold"),
                  anchor="w", padx=10).pack(fill="x")

        self.activity_list = tk.Listbox(
            act_box, bg=C["crust"], fg=C["teal"],
            font=("Consolas", sz), borderwidth=0,
            highlightthickness=0, selectbackground=C["surface1"])
        self.activity_list.pack(fill="both", expand=True, padx=4, pady=4)

        # Bottom buttons with rounded corners
        btn_bar = tk.Frame(tab, bg=C["base"])
        btn_bar.pack(fill="x", padx=12, pady=(4, 10))

        self.start_btn = RoundedButton(btn_bar, "▶ Start System", self._start_system,
                                       C["blue"], "#000000", C["sky"], width=150, height=40, radius=20)
        self.start_btn.pack(side="left", padx=4)

        self.stop_btn = RoundedButton(btn_bar, "⏹ Stop System", self._stop_system,
                                      C["red"], "#AD3E3E", C["pink"], width=150, height=40, radius=20)
        self.stop_btn.pack(side="left", padx=4)
        self.stop_btn.config(state="disabled")

        self.save_btn = RoundedButton(btn_bar, "💾 Save Reports", self._save_all_reports,
                                      C["green"], "#000000", C["teal"], width=150, height=40, radius=20)
        self.save_btn.pack(side="left", padx=4)

        self.known_btn = RoundedButton(btn_bar, "📁 Known Faces", self._open_known_folder,
                                       C["surface1"], C["text"], C["surface2"], width=150, height=40, radius=20)
        self.known_btn.pack(side="right", padx=4)
        
        self.refresh_btn = RoundedButton(btn_bar, "🔄 Refresh", self._refresh_all,
                                         C["surface1"], C["text"], C["surface2"], width=120, height=40, radius=20)
        self.refresh_btn.pack(side="right", padx=4)
        
        self.reset_btn = RoundedButton(btn_bar, "🔁 Reset Today", self._reset_today,
                                       C["surface1"], C["text"], C["surface2"], width=140, height=40, radius=20)
        self.reset_btn.pack(side="right", padx=4)

    # ===== TAB 2: ATTENDANCE =====
    def _build_attendance_tab(self):
        sz = self._sz
        tab = tk.Frame(self.tab_container, bg=C["base"])
        self.tabs.append(tab)

        toolbar = tk.Frame(tab, bg=C["base"])
        toolbar.pack(fill="x", padx=14, pady=10)
        
        RoundedButton(toolbar, "🔄 Refresh", self._refresh_attendance_tree,
                     C["surface1"], C["text"], C["surface2"], width=120, height=38, radius=19).pack(side="left", padx=4)
        RoundedButton(toolbar, "📤 Export CSV", self._export_csv,
                     C["surface1"], C["text"], C["surface2"], width=140, height=38, radius=19).pack(side="left", padx=4)

        # Tree container with rounded corners
        tree_container = tk.Canvas(tab, bg=C["base"], highlightthickness=0)
        tree_container.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        tree_container.bind("<Configure>", lambda e: self._draw_attendance_tree_bg(tree_container))
        
        cols = ("Students", "Status", "Time", "Confidence")
        self.att_tree = ttk.Treeview(tree_container, columns=cols, show="headings", height=20)
        for c in cols:
            self.att_tree.heading(c, text=c)
            self.att_tree.column(c, anchor="center", width=170)
        self.att_tree.pack(fill="both", expand=True, padx=8, pady=8)
        self._refresh_attendance_tree()

    # ===== TAB 3: SETTINGS =====
    def _build_settings_tab(self):
        tab = tk.Frame(self.tab_container, bg=C["base"])
        self.tabs.append(tab)

        # Settings container with rounded corners
        settings_container = tk.Canvas(tab, bg=C["base"], highlightthickness=0)
        settings_container.pack(fill="both", expand=True, padx=20, pady=20)
        settings_container.bind("<Configure>", lambda e: self._draw_settings_bg(settings_container))

        form = tk.Frame(settings_container, bg=C["crust"])
        form.pack(padx=30, pady=20, anchor="nw")

        self._setting_vars = {}
        fields = [
            ("Camera URL", "camera_url", str),
            ("Tolerance (0-1)", "tolerance", float),
            ("Detection Model (hog/cnn)", "detection_model", str),
            ("Confirm Time (seconds)", "confirm_time", float),
            ("Num Jitters", "num_jitters", int),
            ("Text Size (8-20)", "text_size", int),
        ]

        for i, (label, key, typ) in enumerate(fields):
            tk.Label(form, text=label, bg=C["crust"], fg=C["text"],
                     font=("Segoe UI", self._sz)).grid(row=i, column=0, sticky="w",
                                              pady=8, padx=(0, 20))
            var = tk.StringVar(
                value=str(self.config.get(key, DEFAULT_CONFIG[key])))
            entry = tk.Entry(form, textvariable=var, width=52,
                           bg=C["surface0"], fg=C["text"],
                           insertbackground=C["text"], font=("Consolas", self._sz),
                           borderwidth=2, relief="flat",
                           highlightthickness=1, highlightbackground=C["surface1"],
                           highlightcolor=C["blue"])
            entry.grid(row=i, column=1, pady=8, ipady=6)
            self._setting_vars[key] = (var, typ)

        r = len(fields)
        brow = tk.Frame(form, bg=C["crust"])
        brow.grid(row=r, column=0, columnspan=2, pady=18)
        
        RoundedButton(brow, "💾 Save Settings", self._save_settings,
                     C["blue"], "#000000", C["sky"], width=160, height=38, radius=19).pack(side="left", padx=8)
        RoundedButton(brow, "🔄 Reset Defaults", self._reset_settings,
                     C["surface1"], C["text"], C["surface2"], width=160, height=38, radius=19).pack(side="left", padx=8)

        tk.Label(form,
                   text="Save & restart the app to apply text size and other changes.",
                   bg=C["crust"],
                   foreground=C["yellow"],
                   font=("Segoe UI", 9, "italic")).grid(
            row=r + 1, column=0, columnspan=2, sticky="w", pady=4)

    # ===== TAB 4: LOG =====
    def _build_log_tab(self):
        tab = tk.Frame(self.tab_container, bg=C["base"])
        self.tabs.append(tab)

        sz = self._sz
        
        # Log container with rounded corners
        log_container = tk.Canvas(tab, bg=C["base"], highlightthickness=0)
        log_container.pack(fill="both", expand=True, padx=14, pady=14)
        log_container.bind("<Configure>", lambda e: self._draw_log_bg(log_container))
        
        self.log_text = scrolledtext.ScrolledText(
            log_container, bg=C["crust"], fg=C["teal"], font=("Consolas", sz),
            insertbackground=C["teal"], borderwidth=0, state="disabled",
            wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

        brow = tk.Frame(tab, bg=C["base"])
        brow.pack(fill="x", padx=10, pady=(0, 10))
        
        RoundedButton(brow, "🗑️ Clear Log", self._clear_log,
                     C["surface1"], C["text"], C["surface2"], width=120, height=38, radius=19).pack(side="right", padx=4)

    # ===== CARD HELPER =====
    def _card(self, parent, title, value, col, fg):
        sz = self._sz
        f = tk.Canvas(parent, bg=C["base"], highlightthickness=0)
        f.grid(row=0, column=col, padx=5, sticky="nsew")
        
        # Draw rounded rectangle background on configure
        f.bind("<Configure>", lambda e: self._draw_card_bg(f, fg))
        
        f.columnconfigure(0, weight=1)
        tk.Label(f, text=title, bg=C["surface0"], fg=C["text"],
                  font=("Segoe UI", sz + 2, "bold")).pack(pady=(8, 0))
        lbl = tk.Label(f, text=value, bg=C["surface0"], fg=fg,
                        font=("Segoe UI", sz + 8, "bold"))
        lbl.pack(pady=(0, 8))
        return lbl

    def _tick_clock(self):
        self.clock_lbl.config(
            text=datetime.now().strftime("%Y-%m-%d   %H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    # ===== FACE DATA =====
    def _load_known_faces(self):
        self.known_encodings.clear()
        self.known_names.clear()
        self.known_paths.clear()
        if not os.path.isdir(KNOWN_FOLDER):
            return
        for f in sorted(os.listdir(KNOWN_FOLDER)):
            if f.lower().endswith((".jpg", ".png", ".jpeg")):
                path = os.path.join(KNOWN_FOLDER, f)
                try:
                    img = face_recognition.load_image_file(path)
                    encs = face_recognition.face_encodings(img)
                    if encs:
                        self.known_encodings.append(encs[0])
                        self.known_names.append(os.path.splitext(f)[0])
                        self.known_paths.append(path)
                        self._log(f"  Loaded: {os.path.splitext(f)[0]}\n")
                    else:
                        self._log(f"  Warning - No face: {f}\n")
                except Exception as e:
                    self._log(f"  Error {f}: {e}\n")
        self.employees = self.known_names.copy()
        self._log(f"  Total faces loaded: {len(self.known_encodings)}\n")

    def _load_status_json(self):
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, "r") as fh:
                    data = json.load(fh)
                self.all_status = data.get("all_status", {})
                self.daily_attendance = data.get("daily_attendance", {})
            except Exception:
                self.all_status = {}
                self.daily_attendance = {}
        for emp in self.employees:
            if emp not in self.all_status:
                self.all_status[emp] = "A"

    def _save_status_json(self):
        try:
            with open(STATUS_FILE, "w") as fh:
                json.dump({
                    "all_status": self.all_status,
                    "daily_attendance": self.daily_attendance,
                    "employees": self.employees,
                    "last_updated": datetime.now().isoformat(),
                }, fh, indent=4)
        except Exception:
            pass

    # ===== START / STOP =====
    def _start_system(self):
        if self.running:
            return
        if not os.path.isdir(KNOWN_FOLDER) or not self.known_encodings:
            messagebox.showwarning("No faces",
                                    "Add face images to known_faces/ first.")
            return

        self.running = True
        self.stop_event.clear()
        self._frame_count = 0
        self._fps_start = time.time()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_dot.config(text="● RUNNING", fg=C["green"])
        self.stream_status_lbl.config(text="  🔴 Live  ", fg=C["rosewater"])
        self._set_match_spinner_active(True)
        self._log("\n=== System started ===\n")

        threading.Thread(target=self._camera_thread, daemon=True).start()
        self._process_loop()

    def _stop_system(self):
        if not self.running:
            return
        self._log("\n=== Stopping... ===\n")
        self.stop_event.set()
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_dot.config(text="● STOPPED", fg=C["red"])
        self.stream_status_lbl.config(text="  ⏸ Idle  ", fg=C["subtext"])
        
        # Clear camera stream display
        self.stream_canvas.config(
            image='',
            text="\n\n\n  Press  ▶ Start System  to begin\n",
            fg=C["subtext"], 
            font=("Segoe UI", self._sz + 4), 
            justify="center"
        )
        if hasattr(self.stream_canvas, '_photo'):
            delattr(self.stream_canvas, '_photo')
        
        self._set_match_spinner_active(False)
        if self._match_hold_job is not None:
            self.root.after_cancel(self._match_hold_job)
            self._match_hold_job = None
        self._render_match_waiting_state(spinning=False)
        
        self.match_name_lbl.config(
            text="  — No match yet —",
            fg=C["text"]
        )
        
        self._save_status_json()
        self._refresh_cards()

    def _camera_thread(self):
        url = self.config.get("camera_url", DEFAULT_CONFIG["camera_url"])
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.root.after(0, self._log, f"  Camera: {url}\n")
        while not self.stop_event.is_set():
            ret, frame = cap.read()
            if ret:
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
                self.frame_queue.put(frame)
            else:
                time.sleep(0.05)
        cap.release()
        self.root.after(0, self._log, "  Camera released.\n")

    def _process_loop(self):
        if not self.running:
            return

        tolerance = float(
            self.config.get("tolerance", DEFAULT_CONFIG["tolerance"]))
        confirm_time = float(
            self.config.get("confirm_time", DEFAULT_CONFIG["confirm_time"]))

        if not self.frame_queue.empty():
            frame = self.frame_queue.get()
            current_time = time.time()
            self._frame_count += 1

            elapsed = current_time - self._fps_start
            if elapsed >= 1.0:
                self.fps = self._frame_count / elapsed
                self._frame_count = 0
                self._fps_start = current_time
                self.c_fps.config(text=f"{self.fps:.1f}")

            small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

            face_locs = face_recognition.face_locations(rgb)
            face_encs = face_recognition.face_encodings(rgb, face_locs)

            detected_names = set()

            for (t, r, b, l), enc in zip(face_locs, face_encs):
                t *= 4
                r *= 4
                b *= 4
                l *= 4
                name_show = "Unknown"
                best_dist = 1.0

                if self.known_encodings:
                    dists = face_recognition.face_distance(
                        self.known_encodings, enc)
                    idx = np.argmin(dists)
                    best_dist = dists[idx]

                    if best_dist < tolerance:
                        det_name = self.known_names[idx]
                        detected_names.add(det_name)

                        if det_name not in self.face_seen_time:
                            self.face_seen_time[det_name] = current_time

                        dur = current_time - self.face_seen_time[det_name]

                        if dur >= confirm_time:
                            name_show = det_name
                            if (det_name not in self.recently_matched or
                                    (current_time -
                                     self.recently_matched[det_name] > 5)):
                                self.recently_matched[det_name] = current_time
                                self.last_match_time = current_time
                                self._mark_attendance(det_name, best_dist)

                                ki = self.known_names.index(det_name)
                                mimg = cv2.imread(self.known_paths[ki])
                                if mimg is not None:
                                    self.last_matched_img = mimg
                                    self.root.after(
                                        0, self._update_match_panel,
                                        det_name, best_dist)
                        else:
                            remaining = confirm_time - dur
                            name_show = f"Verifying... {remaining:.1f}s"

                # Bounding box color
                if name_show == "Unknown":
                    color = (0, 0, 255)
                elif "Verifying" in name_show:
                    color = (0, 200, 255)
                else:
                    color = (0, 255, 0)

                cv2.rectangle(frame, (l, t), (r, b), color, 2)

                # Name label with background
                label_w = len(name_show) * 13 + 10
                cv2.rectangle(frame, (l, t - 30), (l + label_w, t),
                              color, -1)
                cv2.putText(frame, name_show, (l + 5, t - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                # Confidence bar below box
                if best_dist < 1.0 and name_show != "Unknown":
                    conf = 1 - best_dist
                    bar_w = int(conf * (r - l))
                    cv2.rectangle(frame, (l, b + 4), (l + bar_w, b + 12),
                                  color, -1)
                    cv2.rectangle(frame, (l, b + 4), (r, b + 12), color, 1)

            # Clean up unseen faces
            for p in list(self.face_seen_time):
                if p not in detected_names:
                    del self.face_seen_time[p]

            # HUD overlay
            h, w = frame.shape[:2]
            overlay = frame.copy()
            cv2.rectangle(overlay, (8, h - 90), (260, h - 8),
                          (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

            pcount = sum(1 for v in self.all_status.values() if v == "P")
            acount = sum(1 for v in self.all_status.values() if v == "A")
            cv2.putText(frame, f"FPS: {self.fps:.1f}", (16, h - 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (166, 227, 161), 2)
            cv2.putText(frame, f"Faces: {len(self.known_names)}",
                        (16, h - 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (148, 226, 213), 2)
            cv2.putText(frame,
                        f"Present: {pcount}   Absent: {acount}",
                        (16, h - 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (205, 214, 244), 2)

            self._show_frame_on_label(frame, self.stream_canvas)

        if int(time.time()) % 2 == 0:
            self._refresh_cards()

        self.root.after(30, self._process_loop)

    # ===== RENDER HELPERS =====
    def _draw_stream_box_bg(self, canvas):
        """Draw rounded rectangle background for stream box"""
        canvas.delete("rounded_bg")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w > 10 and h > 10:
            create_rounded_rect(canvas, 0, 0, w, h, r=30, 
                              fill=C["crust"], outline=C["surface1"], 
                              width=2, tags="rounded_bg")
            canvas.tag_lower("rounded_bg")
    
    def _draw_match_box_bg(self, canvas):
        """Draw rounded rectangle background for match box"""
        canvas.delete("rounded_bg")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w > 10 and h > 10:
            create_rounded_rect(canvas, 0, 0, w, h, r=25, 
                              fill=C["crust"], outline=C["surface1"], 
                              width=2, tags="rounded_bg")
            canvas.tag_lower("rounded_bg")
    
    def _draw_activity_box_bg(self, canvas):
        """Draw rounded rectangle background for activity box"""
        canvas.delete("rounded_bg")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w > 10 and h > 10:
            create_rounded_rect(canvas, 0, 0, w, h, r=25, 
                              fill=C["crust"], outline=C["surface1"], 
                              width=2, tags="rounded_bg")
            canvas.tag_lower("rounded_bg")
    
    def _draw_card_bg(self, canvas, fg):
        """Draw rounded rectangle background for card"""
        canvas.delete("rounded_bg")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w > 10 and h > 10:
            create_rounded_rect(canvas, 0, 0, w, h, r=20,
                              fill=C["surface0"], outline=C["surface1"],
                              width=1, tags="rounded_bg")
            canvas.tag_lower("rounded_bg")
    
    def _draw_attendance_tree_bg(self, canvas):
        """Draw rounded rectangle background for attendance tree"""
        canvas.delete("rounded_bg")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w > 10 and h > 10:
            create_rounded_rect(canvas, 0, 0, w, h, r=25, 
                              fill=C["crust"], outline=C["surface1"], 
                              width=2, tags="rounded_bg")
            canvas.tag_lower("rounded_bg")
    
    def _draw_settings_bg(self, canvas):
        """Draw rounded rectangle background for settings form"""
        canvas.delete("rounded_bg")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w > 10 and h > 10:
            create_rounded_rect(canvas, 0, 0, w, h, r=25, 
                              fill=C["crust"], outline=C["surface1"], 
                              width=2, tags="rounded_bg")
            canvas.tag_lower("rounded_bg")
    
    def _draw_log_bg(self, canvas):
        """Draw rounded rectangle background for log text"""
        canvas.delete("rounded_bg")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w > 10 and h > 10:
            create_rounded_rect(canvas, 0, 0, w, h, r=25, 
                              fill=C["crust"], outline=C["surface1"], 
                              width=2, tags="rounded_bg")
            canvas.tag_lower("rounded_bg")

    def _blend_hex(self, c1, c2, t):
        c1 = c1.lstrip("#")
        c2 = c2.lstrip("#")
        r = int(int(c1[0:2], 16) * (1 - t) + int(c2[0:2], 16) * t)
        g = int(int(c1[2:4], 16) * (1 - t) + int(c2[2:4], 16) * t)
        b = int(int(c1[4:6], 16) * (1 - t) + int(c2[4:6], 16) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _set_match_spinner_active(self, active):
        self._match_spinner_active = active
        if not active and self._match_spinner_job is not None:
            self.root.after_cancel(self._match_spinner_job)
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
        self._match_spinner_job = self.root.after(60, self._animate_match_spinner)

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
            canvas.create_line(
                inner_x, inner_y, outer_x, outer_y,
                fill=color, width=7, capstyle=tk.ROUND
            )

        gear_r = radius * 0.58
        canvas.create_oval(
            center_x - gear_r, center_y - gear_r,
            center_x + gear_r, center_y + gear_r,
            fill=color, outline=""
        )
        hole_r = radius * 0.23
        canvas.create_oval(
            center_x - hole_r, center_y - hole_r,
            center_x + hole_r, center_y + hole_r,
            fill=C["crust"], outline=""
        )

    def _render_match_waiting_state(self, spinning=False):
        if not hasattr(self, "match_canvas"):
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
                center_x - orbit_r,
                center_y - orbit_r,
                center_x + orbit_r,
                center_y + orbit_r,
                start=start_angle,
                extent=70,
                style="arc",
                outline=ring_color,
                width=4
            )
            self._draw_spinner_arrow(
                canvas, center_x, center_y, orbit_r,
                start_angle + 70, ring_color
            )

        self._draw_spinner_gear(
            canvas, center_x, center_y,
            max(14, orbit_r * 0.42), gear_color
        )

        canvas.create_text(
            center_x,
            center_y + orbit_r + 24,
            text="Waiting for",
            fill=C["text"],
            font=("Segoe UI", self._sz + 2, "bold")
        )
        canvas.create_text(
            center_x,
            center_y + orbit_r + 50,
            text="face match...",
            fill=C["subtext"],
            font=("Segoe UI", self._sz + 1)
        )
    
    def _show_frame_on_label(self, bgr_frame, label):
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        lw = label.winfo_width()
        lh = label.winfo_height()
        if lw > 10 and lh > 10:
            pil.thumbnail((lw, lh), Image.LANCZOS)
        photo = ImageTk.PhotoImage(pil)
        label.config(image=photo, text="")
        label._photo = photo

    def _restore_match_waiting_state(self):
        self._match_hold_job = None
        if not self.running:
            return
        self.match_name_lbl.config(
            text="  — No match yet —",
            fg=C["text"]
        )
        self._render_match_waiting_state(spinning=True)
        self._set_match_spinner_active(True)

    def _update_match_panel(self, name, dist):
        if self.last_matched_img is None:
            return
        self._set_match_spinner_active(False)
        if self._match_hold_job is not None:
            self.root.after_cancel(self._match_hold_job)
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
        self.match_name_lbl.config(
            text=f"  ✓  {name}  —  {conf:.0f}% match", fg=C["green"])
        self._match_hold_job = self.root.after(3000, self._restore_match_waiting_state)

    # ===== ATTENDANCE LOGIC =====
    def _mark_attendance(self, name, distance):
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        key = f"{today}_{name}"
        if key in self.today_attendance:
            return
        self.all_status[name] = "P"
        self.daily_attendance.setdefault(today, {})[name] = "P"
        self._save_status_json()

        record = {
            "Date": today,
            "Day": now.strftime("%A"),
            "Time": now.strftime("%H:%M:%S"),
            "Employee": name,
            "Status": "P",
            "Distance": f"{distance:.2f}",
            "Confidence": f"{(1-distance)*100:.1f}%",
        }
        self.attendance_data.append(record)
        self.today_attendance.add(key)
        self.total_attendance += 1

        self.root.after(
            0, self._add_activity,
            f"  {now.strftime('%H:%M:%S')}  {name}"
            f"  ({(1-distance)*100:.0f}%)")
        self._log(f"  {name} PRESENT  dist={distance:.3f}\n")

    def _add_activity(self, text):
        self.activity_list.insert(0, text)
        if self.activity_list.size() > 50:
            self.activity_list.delete(50, tk.END)

    # ===== REFRESH =====
    def _refresh_cards(self):
        self.c_faces.config(text=str(len(self.known_encodings)))
        p = sum(1 for v in self.all_status.values() if v == "P")
        a = sum(1 for v in self.all_status.values() if v == "A")
        self.c_present.config(text=str(p))
        self.c_absent.config(text=str(a))
        self.c_date.config(text=datetime.now().strftime("%Y-%m-%d"))

    def _refresh_all(self):
        self._load_known_faces()
        self._load_status_json()
        self._refresh_cards()
        self._refresh_attendance_tree()
        self._log("  Refreshed all data.\n")

    def _refresh_attendance_tree(self):
        for i in self.att_tree.get_children():
            self.att_tree.delete(i)
        if os.path.exists(CSV_FILE):
            try:
                with open(CSV_FILE, "r", newline="", encoding="utf-8") as fh:
                    for row in csv.DictReader(fh):
                        self.att_tree.insert("", "end", values=(
                            row.get("Employee", ""),
                            row.get("Status", ""),
                            row.get("Time", ""),
                            row.get("Confidence", "")))
                return
            except Exception:
                pass
        for emp, st in self.all_status.items():
            self.att_tree.insert("", "end", values=(emp, st, "-", "-"))

    # ===== SAVE REPORTS =====
    def _save_all_reports(self):
        self._save_csv()
        self._save_register_csv()
        self._save_excel()
        self._save_status_json()
        self._log("  All reports saved.\n")
        messagebox.showinfo(
            "Saved",
            f"All reports saved:\n"
            f"  {os.path.basename(CSV_FILE)}\n"
            f"  {os.path.basename(REGISTER_CSV)}\n"
            f"  {os.path.basename(EXCEL_FILE)}")

    def _save_csv(self):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, ["Date", "Day", "Time", "Employee",
                                     "Status", "Distance", "Confidence"])
            w.writeheader()
            w.writerows(self.attendance_data)

    def _save_register_csv(self):
        today = datetime.now().strftime("%Y-%m-%d")
        with open(REGISTER_CSV, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Date"] + self.employees)
            w.writerow([today] + [self.all_status.get(e, "A")
                                   for e in self.employees])
        with open(COLUMN_CSV, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Name", "Status"])
            for e in self.employees:
                w.writerow([e, self.all_status.get(e, "A")])

    def _save_excel(self):
        today = datetime.now().strftime("%Y-%m-%d")
        d = {"Date": [today]}
        for e in self.employees:
            d[e] = [self.all_status.get(e, "A")]
        df_r = pd.DataFrame(d)
        df_s = pd.DataFrame({
            "Name": self.employees,
            "Status": [self.all_status.get(e, "A") for e in self.employees]
        })
        df_d = pd.DataFrame(self.attendance_data)
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as wr:
            df_r.to_excel(wr, sheet_name="Register", index=False)
            df_s.to_excel(wr, sheet_name="Summary", index=False)
            df_d.to_excel(wr, sheet_name="Detail", index=False)

    # ===== SETTINGS =====
    def _save_settings(self):
        try:
            for k, (var, typ) in self._setting_vars.items():
                self.config[k] = typ(var.get())
            save_config(self.config)
            messagebox.showinfo("Saved",
                                "Settings saved. Restart system to apply.")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value:\n{e}")

    def _reset_settings(self):
        self.config = DEFAULT_CONFIG.copy()
        for k, (var, _) in self._setting_vars.items():
            var.set(str(DEFAULT_CONFIG[k]))
        save_config(self.config)

    # ===== MISC ACTIONS =====
    def _open_known_folder(self):
        os.makedirs(KNOWN_FOLDER, exist_ok=True)
        import subprocess as sp
        sp.Popen(["xdg-open", KNOWN_FOLDER])

    def _export_csv(self):
        if not os.path.exists(CSV_FILE):
            messagebox.showinfo("No Data", "Run the system first.")
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if dest:
            import shutil
            shutil.copy2(CSV_FILE, dest)
            messagebox.showinfo("Done", f"Exported to {dest}")

    def _reset_today(self):
        if self.running:
            messagebox.showwarning("Warning", "Stop the system first.")
            return
        if not messagebox.askyesno(
                "Confirm", "Delete all today's attendance data?"):
            return
        for f in [STATUS_FILE, CSV_FILE, REGISTER_CSV, COLUMN_CSV,
                  EXCEL_FILE]:
            if os.path.exists(f):
                os.remove(f)
        self.all_status.clear()
        self.attendance_data.clear()
        self.today_attendance.clear()
        self.total_attendance = 0
        self._load_status_json()
        self._refresh_cards()
        self._refresh_attendance_tree()
        self._log("  Today's data reset.\n")

    # ===== LOG =====
    def _log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, msg)
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    # ===== CLOSE =====
    def _on_close(self):
        if self.running:
            if not messagebox.askyesno(
                    "Quit", "System is running. Stop and quit?"):
                return
            self._stop_system()
            self.root.after(800, self.root.destroy)
        else:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    FaceAttendanceApp(root)
    root.mainloop()
