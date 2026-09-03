"""
Attendance Tracking and Deduplication Logic.
Evaluates attendance status, timestamp formatting, and daily session deduplication.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any


class AttendanceRecordManager:
    """Handles session attendance deduplication and data structure formatting."""

    def __init__(self):
        self.attendance_data: List[Dict[str, Any]] = []
        self.today_attendance: Set[str] = set()
        self.all_status: Dict[str, str] = {}
        self.daily_attendance: Dict[str, Dict[str, str]] = {}
        self.recently_matched: Dict[str, float] = {}

    def mark_attendance(
        self,
        name: str,
        distance: float,
        now: Optional[datetime] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Marks an individual as Present if not already marked today.
        Returns:
            (is_newly_marked, record_dict)
        """
        if now is None:
            now = datetime.now()

        today = now.strftime("%Y-%m-%d")
        key = f"{today}_{name}"

        if key in self.today_attendance:
            return False, None

        self.all_status[name] = "P"
        self.daily_attendance.setdefault(today, {})[name] = "P"

        record = {
            "Date": today,
            "Day": now.strftime("%A"),
            "Time": now.strftime("%H:%M:%S"),
            "Employee": name,
            "Status": "P",
            "Distance": f"{distance:.2f}",
            "Confidence": f"{(1 - distance) * 100:.1f}%",
        }

        self.attendance_data.append(record)
        self.today_attendance.add(key)
        return True, record

    def reset_today(self):
        """Clears in-memory session records for the current day."""
        self.attendance_data.clear()
        self.today_attendance.clear()
        self.recently_matched.clear()
        for k in self.all_status:
            self.all_status[k] = "A"
