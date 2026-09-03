"""
Unit Tests for Refactored Face Attendance Modules.
Validates configuration loading, attendance deduplication, exporters, and color math.
"""

from datetime import datetime
import os
from pathlib import Path
import unittest

from src.config import DEFAULT_CONFIG, load_config, save_config, C
from src.core.attendance_manager import AttendanceRecordManager
from src.core.recognizer import FaceMatcher
from src.storage.exporters import save_csv, save_register_csv, save_excel, save_status_json, load_status_json
from src.gui.components import blend_hex


class TestModularFaceAttendance(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path("data/test_output")
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def test_config(self):
        """Verifies configuration loader and serializer."""
        cfg = load_config("non_existent_config.json")
        self.assertEqual(cfg["tolerance"], 0.50)
        self.assertEqual(cfg["detection_model"], "hog")

        test_cfg_path = str(self.test_dir / "test_cfg.json")
        cfg["tolerance"] = 0.45
        save_config(cfg, test_cfg_path)
        loaded = load_config(test_cfg_path)
        self.assertEqual(loaded["tolerance"], 0.45)

    def test_attendance_deduplication(self):
        """Verifies session deduplication and status marking."""
        mgr = AttendanceRecordManager()
        now = datetime(2026, 9, 4, 9, 10, 0)

        # First mark
        is_new, rec = mgr.mark_attendance("Kakon Roy", 0.32, now=now)
        self.assertTrue(is_new)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["Employee"], "Kakon Roy")
        self.assertEqual(rec["Status"], "P")
        self.assertEqual(mgr.all_status["Kakon Roy"], "P")

        # Duplicate mark on the same day
        is_new_dup, rec_dup = mgr.mark_attendance("Kakon Roy", 0.30, now=now)
        self.assertFalse(is_new_dup)
        self.assertIsNone(rec_dup)

    def test_exporters(self):
        """Verifies CSV, Register, and Excel exports."""
        employees = ["Kakon Roy", "Bastob", "Murad"]
        all_status = {"Kakon Roy": "P", "Bastob": "P", "Murad": "A"}
        attendance_data = [
            {"Date": "2026-09-04", "Day": "Friday", "Time": "09:05:00", "Employee": "Kakon Roy", "Status": "P", "Distance": "0.32", "Confidence": "68.0%"},
            {"Date": "2026-09-04", "Day": "Friday", "Time": "09:12:00", "Employee": "Bastob", "Status": "P", "Distance": "0.28", "Confidence": "72.0%"},
        ]

        csv_p = str(self.test_dir / "att.csv")
        reg_p = str(self.test_dir / "reg.csv")
        col_p = str(self.test_dir / "col.csv")
        xlsx_p = str(self.test_dir / "att.xlsx")
        status_json_p = str(self.test_dir / "status.json")

        save_csv(attendance_data, csv_p)
        save_register_csv(employees, all_status, reg_p, col_p)
        save_excel(employees, all_status, attendance_data, xlsx_p)
        save_status_json(status_json_p, all_status, {}, employees)

        self.assertTrue(os.path.exists(csv_p) and os.path.getsize(csv_p) > 0)
        self.assertTrue(os.path.exists(reg_p) and os.path.getsize(reg_p) > 0)
        self.assertTrue(os.path.exists(col_p) and os.path.getsize(col_p) > 0)
        self.assertTrue(os.path.exists(xlsx_p) and os.path.getsize(xlsx_p) > 0)
        self.assertTrue(os.path.exists(status_json_p) and os.path.getsize(status_json_p) > 0)

        loaded_status, _ = load_status_json(status_json_p, employees)
        self.assertEqual(loaded_status["Kakon Roy"], "P")
        self.assertEqual(loaded_status["Murad"], "A")

    def test_blend_hex(self):
        """Verifies color blending helper."""
        c = blend_hex("#000000", "#ffffff", 0.5)
        self.assertEqual(c.lower(), "#7f7f7f")


if __name__ == "__main__":
    unittest.main()
