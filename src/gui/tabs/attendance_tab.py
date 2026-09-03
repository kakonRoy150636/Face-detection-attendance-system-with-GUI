"""
Attendance Records Tab.
Displays the tabular view of student statuses and provides CSV export capabilities.
"""

import csv
import os
import shutil

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
except ImportError:
    tk = None
    ttk = None
    messagebox = None
    filedialog = None

from src.config import C, CSV_FILE
from src.gui.components import RoundedButton, create_rounded_rect


class AttendanceTabView:
    """Renders the Attendance table view."""

    def __init__(self, parent, controller):
        self.parent = parent
        self.c = controller
        self.tab = tk.Frame(parent, bg=C["base"]) if tk else None

        if tk:
            self._build_ui()

    def _build_ui(self):
        toolbar = tk.Frame(self.tab, bg=C["base"])
        toolbar.pack(fill="x", padx=14, pady=10)

        RoundedButton(
            toolbar, "🔄 Refresh", self.refresh_attendance_tree,
            C["surface1"], C["text"], C["surface2"], width=120, height=38, radius=19
        ).pack(side="left", padx=4)

        RoundedButton(
            toolbar, "📤 Export CSV", self.export_csv,
            C["surface1"], C["text"], C["surface2"], width=140, height=38, radius=19
        ).pack(side="left", padx=4)

        tree_container = tk.Canvas(self.tab, bg=C["base"], highlightthickness=0)
        tree_container.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        tree_container.bind("<Configure>", lambda e: self._draw_tree_bg(tree_container))

        cols = ("Students", "Status", "Time", "Confidence")
        self.att_tree = ttk.Treeview(tree_container, columns=cols, show="headings", height=20)
        for c in cols:
            self.att_tree.heading(c, text=c)
            self.att_tree.column(c, anchor="center", width=170)
        self.att_tree.pack(fill="both", expand=True, padx=8, pady=8)

        self.refresh_attendance_tree()

    def _draw_tree_bg(self, canvas):
        canvas.delete("rounded_bg")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w > 10 and h > 10:
            create_rounded_rect(canvas, 0, 0, w, h, r=25, fill=C["crust"], outline=C["surface1"], width=2, tags="rounded_bg")
            canvas.tag_lower("rounded_bg")

    def refresh_attendance_tree(self):
        if not hasattr(self, "att_tree"):
            return
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
                            row.get("Confidence", "")
                        ))
                return
            except Exception:
                pass

        for emp, st in self.c.attendance_mgr.all_status.items():
            self.att_tree.insert("", "end", values=(emp, st, "-", "-"))

    def export_csv(self):
        if not os.path.exists(CSV_FILE):
            messagebox.showinfo("No Data", "Run the system first.")
            return
        dest = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if dest:
            shutil.copy2(CSV_FILE, dest)
            messagebox.showinfo("Done", f"Exported to {dest}")
