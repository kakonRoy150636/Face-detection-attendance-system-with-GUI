"""
Face Attendance System - Application Entry Point.
Initializes the Tkinter window and launches the FaceAttendanceApp coordinator.
"""

import sys

try:
    import tkinter as tk
except ImportError:
    print("[Error] Tkinter is not installed on this Python environment.")
    print("On Ubuntu/Debian, install with: sudo apt install python3-tk")
    sys.exit(1)

from src.gui.app import FaceAttendanceApp


def main():
    root = tk.Tk()
    app = FaceAttendanceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
