"""
Main Application Controller.
Coordinates the Tkinter root window, custom rounded tabs, camera background threads, and storage logic.
"""

from datetime import datetime
import os
import queue
import threading
import time
from typing import Optional
import cv2

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:
    tk = None
    ttk = None
    messagebox = None

from src.config import (
    C, DEFAULT_CONFIG, load_config, save_config,
    STATUS_FILE, CSV_FILE, REGISTER_CSV, COLUMN_CSV, EXCEL_FILE, KNOWN_FOLDER
)
from src.core.camera import CameraWorker
from src.core.recognizer import FaceMatcher
from src.core.attendance_manager import AttendanceRecordManager
from src.storage.exporters import (
    load_status_json, save_status_json, save_csv, save_register_csv, save_excel
)
from src.gui.components import RoundedTab
from src.gui.tabs.live_tab import LiveTabView
from src.gui.tabs.attendance_tab import AttendanceTabView
from src.gui.tabs.settings_tab import SettingsTabView
from src.gui.tabs.log_tab import LogTabView


class FaceAttendanceApp:
    """Master Application window and workflow coordinator."""

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

        # Core Engines
        self.matcher = FaceMatcher(known_dir=KNOWN_FOLDER)
        self.attendance_mgr = AttendanceRecordManager()
        self.camera_worker: Optional[CameraWorker] = None

        self.fps = 0.0
        self._frame_count = 0
        self._fps_start = time.time()

        self._build_styles()
        self._build_ui()

        # Initial Load
        self._load_known_faces()
        self._load_status_json()
        self._refresh_cards()

    def _build_styles(self):
        self._sz = int(self.config.get("text_size", DEFAULT_CONFIG["text_size"]))
        sz = self._sz

        s = ttk.Style()
        s.theme_use("clam")

        s.configure("TNotebook", background=C["base"], borderwidth=0, tabmargins=[2, 5, 2, 0])
        s.configure("TNotebook.Tab", background=C["surface0"], foreground=C["text"], padding=[20, 10], font=("Segoe UI", sz, "bold"), borderwidth=0, focuscolor='none')
        s.map("TNotebook.Tab", background=[("selected", C["blue"])], foreground=[("selected", "#000000")], expand=[("selected", [1, 1, 1, 0])])

        s.configure("TFrame", background=C["base"])
        s.configure("TLabel", background=C["base"], foreground=C["text"], font=("Segoe UI", sz))

        for name, bg, abg in [
            ("Accent.TButton", C["blue"],  C["sky"]),
            ("Danger.TButton", C["red"],   C["pink"]),
            ("Green.TButton",  C["green"], C["teal"]),
        ]:
            s.configure(name, background=bg, foreground="#000000", font=("Segoe UI", sz, "bold"), padding=[14, 7], borderwidth=0, relief="flat")
            s.map(name, background=[("active", abg)])

        s.configure("Normal.TButton", background=C["surface1"], foreground=C["text"], font=("Segoe UI", sz, "bold"), padding=[14, 7], borderwidth=0, relief="flat")
        s.map("Normal.TButton", background=[("active", C["surface2"])], foreground=[("active", C["rosewater"])])

        s.configure("Treeview", background=C["surface0"], foreground=C["text"], fieldbackground=C["surface0"], font=("Segoe UI", sz), rowheight=max(28, sz * 3))
        s.configure("Treeview.Heading", background=C["surface1"], foreground=C["lavender"], font=("Segoe UI", sz, "bold"))
        s.map("Treeview", background=[("selected", C["blue"])], foreground=[("selected", "#000000")])

        s.configure("TEntry", fieldbackground=C["surface0"], foreground=C["text"], insertcolor=C["text"], font=("Consolas", sz))

    def _build_ui(self):
        sz = self._sz

        # Top bar
        top = tk.Frame(self.root, bg=C["mantle"], height=54)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="  Face Attendance System", bg=C["mantle"], fg=C["lavender"], font=("Segoe UI", sz + 10, "bold")).pack(side="left", padx=18)

        self.clock_lbl = tk.Label(top, bg=C["mantle"], fg=C["text"], font=("Consolas", sz + 1))
        self.clock_lbl.pack(side="right", padx=18)
        self._tick_clock()

        self.status_dot = tk.Label(top, text="● STOPPED", bg=C["mantle"], fg=C["red"], font=("Segoe UI", sz + 1, "bold"))
        self.status_dot.pack(side="right", padx=6)

        # Custom rounded tabs navigation
        tab_nav = tk.Frame(self.root, bg=C["mantle"], height=48, highlightthickness=1, highlightbackground=C["surface1"])
        tab_nav.pack(fill="x", padx=10, pady=(6, 0))

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

        # Tab container
        self.tab_container = tk.Frame(self.root, bg=C["base"])
        self.tab_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Build tabs
        self.live_tab = LiveTabView(self.tab_container, self)
        self.att_tab = AttendanceTabView(self.tab_container, self)
        self.settings_tab = SettingsTabView(self.tab_container, self)
        self.log_tab = LogTabView(self.tab_container, self)

        self.tabs = [self.live_tab.tab, self.att_tab.tab, self.settings_tab.tab, self.log_tab.tab]
        self._switch_tab(0)

    def _switch_tab(self, index: int):
        for tab in self.tabs:
            tab.pack_forget()
        for btn in self.tab_buttons:
            btn.deselect()

        if 0 <= index < len(self.tabs):
            self.tabs[index].pack(fill="both", expand=True)
            self.tab_buttons[index].select()

    def _tick_clock(self):
        self.clock_lbl.config(text=datetime.now().strftime("%Y-%m-%d   %H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    def log(self, msg: str):
        self.log_tab.append_log(msg)

    def _load_known_faces(self):
        self.matcher.load_known_faces(log_callback=self.log)
        self.employees = self.matcher.known_names.copy()

    def _load_status_json(self):
        self.attendance_mgr.all_status, self.attendance_mgr.daily_attendance = load_status_json(
            STATUS_FILE, self.matcher.known_names
        )

    def _save_status_json(self):
        save_status_json(
            STATUS_FILE,
            self.attendance_mgr.all_status,
            self.attendance_mgr.daily_attendance,
            self.matcher.known_names
        )

    def _refresh_cards(self):
        p = sum(1 for v in self.attendance_mgr.all_status.values() if v == "P")
        a = sum(1 for v in self.attendance_mgr.all_status.values() if v == "A")
        self.live_tab.refresh_cards(
            faces_count=len(self.matcher.known_encodings),
            present_count=p,
            absent_count=a,
            fps_val=self.fps
        )

    def refresh_all(self):
        self._load_known_faces()
        self._load_status_json()
        self._refresh_cards()
        self.att_tab.refresh_attendance_tree()
        self.log("  Refreshed all data.\n")

    def start_system(self):
        if self.running:
            return
        if not os.path.isdir(KNOWN_FOLDER) or not self.matcher.known_encodings:
            messagebox.showwarning("No faces", f"Add face images to {KNOWN_FOLDER} first.")
            return

        self.running = True
        self.stop_event.clear()
        self._frame_count = 0
        self._fps_start = time.time()

        self.live_tab.start_btn.config(state="disabled")
        self.live_tab.stop_btn.config(state="normal")
        self.status_dot.config(text="● RUNNING", fg=C["green"])
        self.live_tab.stream_status_lbl.config(text="  🔴 Live  ", fg=C["rosewater"])
        self.live_tab.set_match_spinner_active(True)
        self.log("\n=== System started ===\n")

        cam_url = self.config.get("camera_url", DEFAULT_CONFIG["camera_url"])
        self.camera_worker = CameraWorker(cam_url, self.frame_queue, self.stop_event, log_callback=self.log)
        self.camera_worker.start()

        self._process_loop()

    def stop_system(self):
        if not self.running:
            return
        self.log("\n=== Stopping... ===\n")
        self.stop_event.set()
        self.running = False

        self.live_tab.start_btn.config(state="normal")
        self.live_tab.stop_btn.config(state="disabled")
        self.status_dot.config(text="● STOPPED", fg=C["red"])
        self.live_tab.stream_status_lbl.config(text="  ⏸ Idle  ", fg=C["subtext"])

        self.live_tab.reset_stream_display()
        self._save_status_json()
        self._refresh_cards()

    def _process_loop(self):
        if not self.running:
            return

        tol = float(self.config.get("tolerance", DEFAULT_CONFIG["tolerance"]))
        conf_time = float(self.config.get("confirm_time", DEFAULT_CONFIG["confirm_time"]))

        if not self.frame_queue.empty():
            frame = self.frame_queue.get()
            cur_time = time.time()
            self._frame_count += 1

            elapsed = cur_time - self._fps_start
            if elapsed >= 1.0:
                self.fps = self._frame_count / elapsed
                self._frame_count = 0
                self._fps_start = cur_time
                self.live_tab.c_fps.config(text=f"{self.fps:.1f}")

            annotated, confirmed_matches, _ = self.matcher.process_frame(
                frame, tolerance=tol, confirm_time=conf_time, current_time=cur_time
            )

            for match in confirmed_matches:
                name = match["name"]
                dist = match["distance"]
                path = match["path"]

                # 5s cooldown check
                if (name not in self.attendance_mgr.recently_matched or
                        (cur_time - self.attendance_mgr.recently_matched[name] > 5)):
                    self.attendance_mgr.recently_matched[name] = cur_time
                    is_new, record = self.attendance_mgr.mark_attendance(name, dist)
                    if is_new and record:
                        self._save_status_json()
                        self.root.after(0, self.live_tab.add_activity, f"  {record['Time']}  {name}  ({record['Confidence']})")
                        self.log(f"  {name} PRESENT  dist={dist:.3f}\n")

                    if path:
                        self.root.after(0, self.live_tab.update_match_panel, name, dist, path)

            # HUD Overlay
            h, w = annotated.shape[:2]
            overlay = annotated.copy()
            cv2.rectangle(overlay, (8, h - 90), (260, h - 8), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, annotated, 0.4, 0, annotated)

            pcount = sum(1 for v in self.attendance_mgr.all_status.values() if v == "P")
            acount = sum(1 for v in self.attendance_mgr.all_status.values() if v == "A")
            cv2.putText(annotated, f"FPS: {self.fps:.1f}", (16, h - 65), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (166, 227, 161), 2)
            cv2.putText(annotated, f"Faces: {len(self.matcher.known_names)}", (16, h - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (148, 226, 213), 2)
            cv2.putText(annotated, f"Present: {pcount}   Absent: {acount}", (16, h - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (205, 214, 244), 2)

            self.live_tab.show_stream_frame(annotated)

        if int(time.time()) % 2 == 0:
            self._refresh_cards()

        self.root.after(30, self._process_loop)

    def save_all_reports(self):
        save_csv(self.attendance_mgr.attendance_data, CSV_FILE)
        save_register_csv(self.matcher.known_names, self.attendance_mgr.all_status, REGISTER_CSV, COLUMN_CSV)
        save_excel(self.matcher.known_names, self.attendance_mgr.all_status, self.attendance_mgr.attendance_data, EXCEL_FILE)
        self._save_status_json()
        self.log("  All reports saved.\n")
        messagebox.showinfo(
            "Saved",
            f"All reports saved:\n"
            f"  {os.path.basename(CSV_FILE)}\n"
            f"  {os.path.basename(REGISTER_CSV)}\n"
            f"  {os.path.basename(EXCEL_FILE)}"
        )

    def reset_today(self):
        if self.running:
            messagebox.showwarning("Warning", "Stop the system first.")
            return
        if not messagebox.askyesno("Confirm", "Delete all today's attendance data?"):
            return

        for f in [STATUS_FILE, CSV_FILE, REGISTER_CSV, COLUMN_CSV, EXCEL_FILE]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

        self.attendance_mgr.reset_today()
        self._load_status_json()
        self._refresh_cards()
        self.att_tab.refresh_attendance_tree()
        self.log("  Today's data reset.\n")

    def _on_close(self):
        if self.running:
            if not messagebox.askyesno("Quit", "System is running. Stop and quit?"):
                return
            self.stop_system()
            self.root.after(800, self.root.destroy)
        else:
            self.root.destroy()
