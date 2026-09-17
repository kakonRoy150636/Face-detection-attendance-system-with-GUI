"""
Configuration settings, file paths, and color theme definitions.
Preserves the exact Catppuccin Mocha palette and default parameters from the original GUI.
"""

import json
import os
from pathlib import Path

# Paths configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
KNOWN_FOLDER = str(DATA_DIR / "known_faces")
CONFIG_FILE = str(BASE_DIR / "gui_config.json")
STATUS_FILE = str(DATA_DIR / "attendance_status.json")
CSV_FILE = str(DATA_DIR / "attendance_today.csv")
REGISTER_CSV = str(DATA_DIR / "attendance_today_register.csv")
COLUMN_CSV = str(DATA_DIR / "attendance_today_column.csv")
EXCEL_FILE = str(DATA_DIR / "attendance_today.xlsx")

# Default Parameters
DEFAULT_CONFIG = {
    "camera_urls": ["0"],
    "tolerance": 0.50,
    "detection_model": "hog",
    "confirm_time": 1.0,
    "num_jitters": 2,
    "text_size": 10,
}

# Catppuccin Mocha color palette
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


def load_config(config_path: str = CONFIG_FILE) -> dict:
    """Loads configuration from JSON file or returns defaults."""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            if "camera_urls" not in config and "camera_url" in config:
                config["camera_urls"] = config["camera_url"]
            if isinstance(config.get("camera_urls"), str):
                config["camera_urls"] = [config["camera_urls"]]
            return {**DEFAULT_CONFIG, **config}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict, config_path: str = CONFIG_FILE) -> None:
    """Saves configuration dict to JSON file."""
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)
