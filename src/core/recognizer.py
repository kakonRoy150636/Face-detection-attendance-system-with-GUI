"""
Face Recognition and Verification Pipeline with 3D Depth Liveness Detection.
Optimized for high FPS via Frame Skipping and Conditional Liveness.
"""

import os
import time
from typing import Dict, List, Optional, Set, Tuple, Any
import cv2
import numpy as np
from src.core.depth_liveness import DepthLivenessDetector

try:
    import face_recognition
    HAS_FACE_REC = True
except ImportError:
    HAS_FACE_REC = False


class FaceMatcher:
    def __init__(self, known_dir: str):
        self.known_dir = known_dir
        self.known_encodings: List[np.ndarray] = []
        self.known_names: List[str] = []
        self.known_paths: List[str] = []
        self.face_seen_time: Dict[str, float] = {}
        self.depth_detector = DepthLivenessDetector(depth_variance_threshold=0.035)

        # FPS অপটিমাইজেশন ভ্যারিয়েবল
        self.frame_count = 0
        self.skip_frames = 3  # প্রতি ৩ ফ্রেমে ১ বার রিকগনিশন ও ল্যাবনেস চলবে
        self.last_confirmed: List[Dict[str, Any]] = []
        self.last_detected: Set[str] = set()
        self.last_overlays: List[Dict[str, Any]] = []

    def load_known_faces(self, log_callback=None) -> int:
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
    ) -> Tuple[np.ndarray, List[Dict[str, Any]], Set[str], List[Dict[str, Any]]]:

        if current_time is None:
            current_time = time.time()

        if not HAS_FACE_REC or not self.known_encodings:
            return frame, [], set(), []

        # অপটিমাইজেশন ১: স্কিপ ফ্রেম চেক (FPS ড্রপ ঠেকানোর মূল জায়গা)
        self.frame_count += 1
        if self.frame_count % self.skip_frames != 0:
            return frame, self.last_confirmed, self.last_detected, self.last_overlays

        # দ্রুত লোকেশন ডিটেকশনের জন্য 0.25x ছোট করা
        small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        face_locs = face_recognition.face_locations(rgb)

        # অপটিমাইজেশন ২: ফ্রেমে মুখ না থাকলে MediaPipe চালানোর কোনো প্রয়োজন নেই
        if not face_locs:
            self.last_confirmed = []
            self.last_detected = set()
            self.last_overlays = []
            return frame, [], set(), []

        # ফ্রেমে মুখ পেলেই কেবল 3D Depth চেক হবে
        is_live_global, depth_score = self.depth_detector.check_liveness(frame)
        face_encs = face_recognition.face_encodings(rgb, face_locs)

        detected_names = set()
        confirmed_matches = []
        overlay_results = []

        for (t, r, b, l), enc in zip(face_locs, face_encs):
            t *= 4
            r *= 4
            b *= 4
            l *= 4

            name_show = "Unknown"
            best_dist = 1.0

            if self.known_encodings:
                dists = face_recognition.face_distance(self.known_encodings, enc)
                idx = int(np.argmin(dists))
                best_dist = float(dists[idx])

                if best_dist < tolerance:
                    det_name = self.known_names[idx]
                    detected_names.add(det_name)

                    if is_live_global:
                        if det_name not in self.face_seen_time:
                            self.face_seen_time[det_name] = current_time

                        dur = current_time - self.face_seen_time[det_name]
                        if dur >= confirm_time:
                            name_show = det_name
                            confirmed_matches.append({
                                "name": det_name,
                                "distance": best_dist,
                                "index": idx,
                                "path": self.known_paths[idx] if idx < len(self.known_paths) else None
                            })
                        else:
                            remaining = confirm_time - dur
                            name_show = f"Verifying... {remaining:.1f}s"
                    else:
                        self.face_seen_time.pop(det_name, None)
                        name_show = det_name

            overlay_results.append({
                "name": name_show,
                "box": (t, r, b, l),
                "is_live": is_live_global,
                "confidence": 1.0 - best_dist if best_dist < 1.0 else 0.0
            })

        for p in list(self.face_seen_time):
            if p not in detected_names:
                del self.face_seen_time[p]

        # ক্যাশ আপডেট
        self.last_confirmed = confirmed_matches
        self.last_detected = detected_names
        self.last_overlays = overlay_results

        return frame, confirmed_matches, detected_names, overlay_results
