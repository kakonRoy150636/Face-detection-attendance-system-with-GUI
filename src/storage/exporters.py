"""
Storage, JSON state persistence, and file exporters for attendance data.
Preserves the exact CSV, register CSV, and multi-sheet Excel logic.
"""

import csv
from datetime import datetime
import json
import os
from typing import Dict, List, Tuple, Any
import pandas as pd


def load_status_json(status_file: str, employees: List[str]) -> Tuple[Dict[str, str], Dict[str, Dict[str, str]]]:
    """Loads all_status and daily_attendance records from JSON."""
    all_status = {}
    daily_attendance = {}
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            all_status = data.get("all_status", {})
            daily_attendance = data.get("daily_attendance", {})
        except Exception:
            all_status = {}
            daily_attendance = {}

    for emp in employees:
        if emp not in all_status:
            all_status[emp] = "A"

    return all_status, daily_attendance


def save_status_json(status_file: str, all_status: Dict[str, str], daily_attendance: Dict[str, Any], employees: List[str]) -> None:
    """Saves daily attendance state to JSON."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(status_file)), exist_ok=True)
        with open(status_file, "w", encoding="utf-8") as fh:
            json.dump({
                "all_status": all_status,
                "daily_attendance": daily_attendance,
                "employees": employees,
                "last_updated": datetime.now().isoformat(),
            }, fh, indent=4)
    except Exception:
        pass


def save_csv(attendance_data: List[Dict[str, Any]], filepath: str) -> None:
    """Saves detailed log entries into attendance CSV."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["Date", "Day", "Time", "Employee", "Status", "Distance", "Confidence"])
        w.writeheader()
        w.writerows(attendance_data)


def save_register_csv(employees: List[str], all_status: Dict[str, str], register_csv: str, column_csv: str) -> None:
    """Saves matrix-style daily register and 2-column status sheets."""
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(os.path.dirname(os.path.abspath(register_csv)), exist_ok=True)

    with open(register_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Date"] + employees)
        w.writerow([today] + [all_status.get(e, "A") for e in employees])

    with open(column_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Name", "Status"])
        for e in employees:
            w.writerow([e, all_status.get(e, "A")])


def save_excel(employees: List[str], all_status: Dict[str, str], attendance_data: List[Dict[str, Any]], excel_file: str) -> None:
    """Saves multi-tab Excel workbook containing Register, Summary, and Detail."""
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(os.path.dirname(os.path.abspath(excel_file)), exist_ok=True)

    d = {"Date": [today]}
    for e in employees:
        d[e] = [all_status.get(e, "A")]
    df_r = pd.DataFrame(d)

    df_s = pd.DataFrame({
        "Name": employees,
        "Status": [all_status.get(e, "A") for e in employees]
    })
    df_d = pd.DataFrame(attendance_data)

    with pd.ExcelWriter(excel_file, engine="openpyxl") as wr:
        df_r.to_excel(wr, sheet_name="Register", index=False)
        df_s.to_excel(wr, sheet_name="Summary", index=False)
        df_d.to_excel(wr, sheet_name="Detail", index=False)
