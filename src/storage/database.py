"""
SQLite Database Handler for Face Attendance System.
Provides persistent storage for student profiles and timestamped attendance logs.
"""

from datetime import datetime
from pathlib import Path
import sqlite3
import threading
from typing import Dict, List, Optional, Any


class DatabaseHandler:
    """Thread-safe SQLite database manager with connection pooling."""

    def __init__(self, db_path: str = "data/attendance.db"):
        self.is_memory = (db_path == ":memory:")
        self.db_path = db_path if self.is_memory else Path(db_path)
        if not self.is_memory:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            db_target = ":memory:" if self.is_memory else str(self.db_path)
            self._conn = sqlite3.connect(db_target, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def init_db(self) -> None:
        """Initializes tables and indexes."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    department TEXT DEFAULT 'General',
                    registered_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_date ON attendance(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_name ON attendance(student_name)")
            conn.commit()

    def insert_attendance(self, name: str, date: str, time: str, status: str, confidence: float) -> int:
        """Records an attendance entry."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO attendance (student_name, date, time, status, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (name, date, time, status, confidence))
            conn.commit()
            return cursor.lastrowid

    def insert_student(self, student_id: str, name: str, department: str = "General") -> bool:
        """Registers a new student profile."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO students (student_id, name, department, registered_at)
                    VALUES (?, ?, ?, ?)
                """, (student_id, name, department, datetime.now().isoformat()))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_all_records(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Retrieves attendance records ordered by recency."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, student_name, date, time, status, confidence
                FROM attendance
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_records_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """Retrieves attendance records for a specific date (YYYY-MM-DD)."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, student_name, date, time, status, confidence
                FROM attendance
                WHERE date = ?
                ORDER BY time ASC
            """, (date_str,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_today_stats(self) -> Dict[str, int]:
        """Calculates attendance summary counts for today."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        records = self.get_records_by_date(today_str)

        total = len(records)
        on_time = sum(1 for r in records if r["status"] == "On Time")
        late = sum(1 for r in records if r["status"] == "Late")

        return {
            "total": total,
            "on_time": on_time,
            "late": late,
        }

    def close(self) -> None:
        """Closes the underlying database connection."""
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None
