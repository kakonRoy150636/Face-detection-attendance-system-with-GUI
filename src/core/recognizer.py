"""
Face Recognition and Verification Pipeline.
Handles model loading, face locations, encodings, distance metrics, and confirmation windows.
"""

import os
import time
from typing import Dict, List, Optional, Set, Tuple, Any
import cv2
import numpy as np

try:
    import face_recognition
    HAS_FACE_REC = True
except ImportError:
    HAS_FACE_REC = False


class FaceMatcher:
    """Manages facial encodings and frame-by-frame identification."""

    def __init__(self, known_dir: str):
        self.known_dir = known_dir
        self.known_encodings: List[np.ndarray] = []
        self.known_names: List[str] = []
        self.known_paths: List[str] = []
        self.face_seen_time: Dict[str, float] = {}

    def load_known_faces(self, log_callback=None) -> int:
        """Loads reference face images and computes 128-d encodings."""
        self.known_encodings.clear()
        self.known_names.clear()
        self.known_paths.clear()

        if not os.path.isdir(self.known_dir):
            return 0

        if not HAS_FACE_REC:
            if log_callback:
                log_callback("  Warning: face_recognition not installed.\n")
            return 0

        valid_exts = (".jpg", ".png", ".jpeg")
        for f in sorted(os.listdir(self.known_dir)):
            if f.lower().endswith(valid_exts):
                path = os.path.join(self.known_dir, f)
                try:
                    img = face_recognition.load_image_file(path)
                    encs = face_recognition.face_encodings(img)
                    if encs:
                        name = os.path.splitext(f)[0]
                        self.known_encodings.append(encs[0])
                        self.known_names.append(name)
                        self.known_paths.append(path)
                        if log_callback:
                            log_callback(f"  Loaded: {name}\n")
                    else:
                        if log_callback:
                            log_callback(f"  Warning - No face: {f}\n")
                except Exception as e:
                    if log_callback:
                        log_callback(f"  Error loading {f}: {e}\n")

        if log_callback:
            log_callback(f"  Total faces loaded: {len(self.known_encodings)}\n")

        return len(self.known_encodings)

    def process_frame(
        self,
        frame: np.ndarray,
        tolerance: float = 0.50,
        confirm_time: float = 1.0,
        current_time: Optional[float] = None
    ) -> Tuple[np.ndarray, List[Dict[str, Any]], Set[str]]:
        """
        Detects and annotates faces on the given frame.
        Returns:
            annotated_frame, list_of_confirmed_matches, set_of_detected_names
        """
        if current_time is None:
            current_time = time.time()

        if not HAS_FACE_REC or not self.known_encodings:
            return frame, [], set()

        small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        face_locs = face_recognition.face_locations(rgb)
        face_encs = face_recognition.face_encodings(rgb, face_locs)

        detected_names = set()
        confirmed_matches = []

        for (t, r, b, l), enc in zip(face_locs, face_encs):
            t *= 4
            r *= 4
            b *= 4
            l *= 4
            name_show = "Unknown"
            best_dist = 1.0
            is_confirmed = False

            if self.known_encodings:
                dists = face_recognition.face_distance(self.known_encodings, enc)
                idx = int(np.argmin(dists))
                best_dist = float(dists[idx])

                if best_dist < tolerance:
                    det_name = self.known_names[idx]
                    detected_names.add(det_name)

                    if det_name not in self.face_seen_time:
                        self.face_seen_time[det_name] = current_time

                    dur = current_time - self.face_seen_time[det_name]

                    if dur >= confirm_time:
                        name_show = det_name
                        is_confirmed = True
                        confirmed_matches.append({
                            "name": det_name,
                            "distance": best_dist,
                            "index": idx,
                            "path": self.known_paths[idx] if idx < len(self.known_paths) else None
                        })
                    else:
                        remaining = confirm_time - dur
                        name_show = f"Verifying... {remaining:.1f}s"

            # Colors
            if name_show == "Unknown":
                color = (0, 0, 255)
            elif "Verifying" in name_show:
                color = (0, 200, 255)
            else:
                color = (0, 255, 0)

            # Box
            cv2.rectangle(frame, (l, t), (r, b), color, 2)

            # Label box
            label_w = len(name_show) * 13 + 10
            cv2.rectangle(frame, (l, t - 30), (l + label_w, t), color, -1)
            cv2.putText(frame, name_show, (l + 5, t - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Confidence bar
            if best_dist < 1.0 and name_show != "Unknown":
                conf = 1.0 - best_dist
                bar_w = int(conf * (r - l))
                cv2.rectangle(frame, (l, b + 4), (l + bar_w, b + 12), color, -1)
                cv2.rectangle(frame, (l, b + 4), (r, b + 12), color, 1)

        # Remove stale tracker times
        for p in list(self.face_seen_time):
            if p not in detected_names:
                del self.face_seen_time[p]

        return frame, confirmed_matches, detected_names
