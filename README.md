# Face Attendance System with Modern GUI

An automated, real-time facial recognition attendance management system built with Python, OpenCV, and Tkinter. Featuring a responsive multi-threaded capture engine, custom Catppuccin Mocha glassmorphic UI, anti-jitter verification, animated match radar, and multi-format Excel/CSV reporting.

---

## Architecture Overview

```text
face-attendance-system/
├── assets/
│   ├── demo.gif                   # Auto-playing preview for README
│   └── app_icon.png               # Application branded icon
├── data/
│   ├── exports/                   # Export directory (.gitkeep)
│   └── known_faces/               # Storage directory for reference faces (.gitkeep)
├── src/
│   ├── core/
│   │   ├── camera.py              # Camera capture thread & frame buffer
│   │   ├── recognizer.py          # Face encoding, comparison, anti-jitter
│   │   └── attendance_manager.py  # Cooldown, confirmation queue, deduplication
│   ├── storage/
│   │   ├── exporters.py           # CSV, Excel (.xlsx), and JSON export logic
│   │   └── database.py            # SQLite/database handler
│   ├── gui/
│   │   ├── app.py                 # Main Tkinter application coordinator
│   │   ├── components.py          # Custom canvas buttons, rounded tabs, cards
│   │   └── tabs/                  # Individual tabs (live, attendance, settings, log)
│   │       ├── live_tab.py
│   │       ├── attendance_tab.py
│   │       ├── settings_tab.py
│   │       └── log_tab.py
│   └── config.py                  # Schema validation & JSON config loader
├── tests/
│   └── test_recognition.py        # Unit tests for core attendance logic
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
└── main.py                        # Minimal entry point
```

---

## Key Features

1. **Exact Catppuccin Mocha UI**: Dark aesthetic with custom canvas rounded buttons, glassmorphic tabs with glossy top shine, and smooth hover animations.
2. **Animated Match Radar**: Real-time rotating gear and radar spinner while scanning for faces, with automatic snapshot rendering and match confirmation hold.
3. **Threaded Video Stream**: Camera polling running on a dedicated daemon thread to guarantee zero UI stuttering or dropped frames.
4. **Attendance Management**: Daily deduplication, confidence bar display, real-time activity log, and multi-format reports (`attendance_today.csv`, `attendance_today_register.csv`, `attendance_today.xlsx`).
5. **Python 3.12 Compatible**: Includes pinned `setuptools<81` and `numpy<2.0.0` dependencies to avoid deprecated `pkg_resources` or C-API incompatibility.

---

## Installation & Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run unit tests
python -m unittest discover tests

# 4. Launch Application
python main.py
```

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
