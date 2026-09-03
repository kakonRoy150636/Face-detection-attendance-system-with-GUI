<div align="center">

<br>

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&size=32&duration=2800&pause=2000&color=89B4FA&center=true&vCenter=true&width=600&lines=Face+Attendance+System;Real-Time+Recognition+%E2%80%A2+Dark+UI+%E2%80%A2+Smart+Logging" alt="Typing SVG" />

### *Instant, intelligent attendance — powered by face recognition, wrapped in a stunning dark interface.*

<br>

<img src="https://img.shields.io/badge/Python-3.8%2B-89B4FA?style=for-the-badge&logo=python&logoColor=1d1d32" alt="Python"/>
<img src="https://img.shields.io/badge/OpenCV-Real--Time-a6e3a1?style=for-the-badge&logo=opencv&logoColor=1d1d32" alt="OpenCV"/>
<img src="https://img.shields.io/badge/UI-Catppuccin%20Mocha-cba6f7?style=for-the-badge&logoColor=1d1d32" alt="Catppuccin"/>
<img src="https://img.shields.io/badge/License-MIT-f9e2af?style=for-the-badge&logoColor=1d1d32" alt="License"/>
<img src="https://img.shields.io/badge/Status-Active-f38ba8?style=for-the-badge&logoColor=1d1d32" alt="Status"/>

<br><br>

</div>

---

## 🌟 Why This Project?

Traditional attendance systems are slow, manual, and prone to proxy. This app **watches**, **recognizes**, and **logs** — all in real-time with a beautiful, production-grade desktop interface.

| | Feature | Details |
|---|---------|---------|
| 🎯 | **Real-Time Face Recognition** | Detect & identify faces from any IP camera stream or webcam in milliseconds |
| 🔐 | **Anti-False-Positive Verification** | Configurable confirmation window — a face must be seen for *N* seconds before marking attendance |
| 🎨 | **Catppuccin Mocha UI** | Custom dark theme layouts, rounded buttons, and structured panels — no default Tkinter look |
| 📊 | **Live Dashboard** | Stats cards, FPS counter, activity feed, and match panel updating in real-time |
| 📤 | **Multi-Format Reports** | Export attendance as CSV, Excel, or JSON with one click |
| ⚙️ | **Fully Configurable** | Tolerance, detection model (HOG/CNN), camera URL, jitters, UI text size — all adjustable |
| 🧵 | **Threaded Architecture** | Camera capture, face processing, and UI rendering run on separate threads for zero lag |
| 💾 | **Persistent State** | Attendance data survives app restarts via structured state tracking |

---

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                    Main Thread                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐   │
│  │ Live View │  │Attendance│  │ Settings │  │  Log   │   │
│  │   Tab    │  │   Tab    │  │   Tab    │  │  Tab   │   │
│  └─────┬────┘  └──────────┘  └──────────┘  └────────┘   │
│        │                                                │
│   UI refresh loop (30ms)                                │
│        │   frame_queue                                  │
│  ┌─────▼──────────────────────┐                         │
│  │   Processing & Rendering   │                         │
│  │  • face_locations()        │                         │
│  │  • face_distance()         │                         │
│  │  • Confirmation logic      │                         │
│  │  • HUD + bounding boxes    │                         │
│  └─────────────┬──────────────┘                         │
└────────────────┼────────────────────────────────────────┘
                 │
       ┌─────────▼──────────┐
       │  Camera Thread     │
       │  • cv2.VideoCapture│
       │  • IP cam / webcam │
       │  • Queue (maxsize=2)│
       └────────────────────┘
```

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone [https://github.com/kakonRoy150636/face-attendance-system.git](https://github.com/kakonRoy150636/face-attendance-system.git)
cd face-attendance-system
```

### 2. Create a Virtual Environment (Recommended)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

> **Note for Windows users:** `face_recognition` requires `dlib`. If `pip install dlib` fails, install Visual Studio Build Tools with C++ workload first, or use a pre-built wheel.

### 4. Add Known Faces
Place clear, front-facing photos in the `known_faces/` folder:
```text
face-attendance-system/
├── known_faces/
│   ├── john_doe.jpg
│   ├── jane_smith.png
│   └── alex_walker.jpeg
├── main.py
└── ...
```
> ⚠️ **File naming = Person name.** `john_doe.jpg` → registered as `john_doe`

### 5. Run the App
```bash
python main.py
```

### 6. Configure & Start
1. Go to **⚙️ Settings** tab → enter your camera URL (IP webcam, local webcam index, etc.)
2. Click **💾 Save Settings**
3. Return to **📹 Live View** → click **▶ Start System**

---

## ⚙️ Configuration

All settings are saved in `gui_config.json` and can be edited from the Settings tab:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `camera_url` | `0` | IP camera stream URL or webcam index (`0` for default webcam) |
| `tolerance` | `0.50` | Face matching threshold (lower = stricter, `0.0`–`1.0`) |
| `detection_model` | `hog` | Face detection model: `hog` (fast) or `cnn` (accurate, needs GPU) |
| `confirm_time` | `1.0` | Seconds a face must be visible before marking attendance |
| `num_jitters` | `2` | Number of times to re-sample the face encoding (higher = more stable) |
| `text_size` | `10` | Base font size for the entire UI (restart required) |

---

## 📂 Project Structure

```text
face-attendance-system/
│
├── main.py                        # 🚀 Application entry point (Tkinter GUI + Core Logic)
├── gui_config.json                # ⚙️ Saved configuration (auto-generated)
├── attendance_status.json         # 💾 Persistent attendance state (auto-generated)
├── attendance_today.csv           # 📊 Daily CSV report (auto-generated)
│
├── known_faces/                   # 📁 Folder for registered face images
│   ├── person_one.jpg
│   ├── person_two.png
│   └── ...
│
├── face_attendance.desktop        # 💻 Linux Desktop Launcher Shortcut
└── requirements.txt               # 📦 Python dependencies
```

---

## 📦 Requirements

Create a `requirements.txt` with the following:

```text
opencv-python>=4.8.0
face_recognition>=1.3.0
numpy>=1.24.0
Pillow>=10.0.0
pandas>=2.0.0
```

---

## 🧠 How the Recognition Works

```text
Camera Frame
     │
     ▼
┌─────────────────────┐
│  Resize to 25%      │  ← Speed optimization
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  face_locations()   │  ← Detect face bounding boxes
│  (HOG or CNN)       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  face_encodings()   │  ← Generate 128-d embeddings
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  face_distance()    │  ← Compare against known faces
│  → argmin + thresh  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Confirmation Timer │  ← Must be seen for N seconds
│  (anti false pos.)  │
└─────────┬───────────┘
          │
          ▼
   ✅ Mark Present
   📊 Update Dashboard
   📝 Log Event
```

---

## 🛡️ Anti-False-Positive System

A single frame match is **not** enough to mark attendance. The system implements:

1. **Distance Threshold** — Only faces below `tolerance` distance are considered
2. **Confirmation Window** — The *same* face must be continuously detected for `confirm_time` seconds
3. **Cooldown Period** — After a successful match, the same person can't be re-marked immediately
4. **Daily Deduplication** — Each person is marked present only once per day

---

## 🔌 Supported Cameras

| Type | Example URL |
|------|-------------|
| IP Webcam (Android) | `http://192.168.0.101:4747/video` |
| Local USB Webcam | `0` (integer index) |
| RTSP Stream | `rtsp://admin:pass@192.168.1.10:554/stream1` |

---

## 📋 Feature Checklist

- [x] Real-time face detection & recognition
- [x] IP camera / USB webcam support
- [x] Catppuccin Mocha themed dark UI
- [x] Custom structured tabs & layouts
- [x] Live FPS counter
- [x] Anti-false-positive confirmation timer
- [x] Daily attendance deduplication
- [x] CSV / Excel / JSON export
- [x] Persistent state across restarts
- [x] Configurable settings with live save
- [x] Linux `.desktop` launcher integration
- [x] Thread-safe frame queue
- [ ] Multi-camera support *(planned)*
- [ ] Database backend (SQLite) *(planned)*

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork** the repository
2. Create a **feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to the branch: `git push origin feature/amazing-feature`
5. Open a **Pull Request**

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

<br>

**Built with 🎭 Python • OpenCV • face_recognition • Tkinter**

*If this project helped you, consider giving it a ⭐!*

<img src="https://capsule-render.vercel.app/api?type=waving&color=89B4FA&height=80&section=footer" width="100%"/>

</div>
