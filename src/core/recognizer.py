"""
Face Recognition and Verification Pipeline with 3D Depth Liveness Detection.
Handles model loading, face locations, encodings, distance metrics, liveness checks, and confirmation windows.
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
    """Manages facial encodings, 3D liveness detection, and frame-by-frame identification."""

    def __init__(self, known_dir: str):
        self.known_dir = known_dir
        self.known_encodings: List[np.ndarray] = []
        self.known_names: List[str] = []
        self.known_paths: List[str] = []
        self.face_seen_time: Dict[str, float] = {}
        # 3D Depth Liveness Detector শুরু করা
        self.depth_detector = DepthLivenessDetector(depth_variance_threshold=0.035)

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
    ) -> Tuple[np.ndarray, List[Dict[str, Any]], Set[str], List[Dict[str, Any]]]:
        """
        Detects faces, verifies 3D depth liveness, and validates attendance confirmation.
        Returns:
            frame, confirmed_matches, detected_names, overlay_results
        """
        if current_time is None:
            current_time = time.time()

        if not HAS_FACE_REC or not self.known_encodings:
            return frame, [], set(), []

        # 1. 3D Depth Liveness যাচাই
        is_live_global, depth_score = self.depth_detector.check_liveness(frame)

        # 2. ফেস রিকগনিশন প্রসেসিং (দ্রুতগতির জন্য 0.25 স্কেল)
        small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        face_locs = face_recognition.face_locations(rgb)
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
            is_confirmed = False

            if self.known_encodings:
                dists = face_recognition.face_distance(self.known_encodings, enc)
                idx = int(np.argmin(dists))
                best_dist = float(dists[idx])

                if best_dist < tolerance:
                    det_name = self.known_names[idx]
                    detected_names.add(det_name)

                    # আসল মুখ (3D) হলেই কেবল কনফার্মেশন টাইমার চলবে
                    if is_live_global:
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
                    else:
                        # ফেক হলে টাইমার বাতিল হবে
                        self.face_seen_time.pop(det_name, None)
                        name_show = det_name

            # live_tab.py এর draw_liveness_overlay এর জন্য তথ্য প্রস্তুত করা
            overlay_results.append({
                "name": name_show,
                "box": (t, r, b, l),
                "is_live": is_live_global,
                "confidence": 1.0 - best_dist if best_dist < 1.0 else 0.0
            })

        # ফ্রেম থেকে হারিয়ে যাওয়া মুখগুলোর ট্র্যাকার ক্লিন করা
        for p in list(self.face_seen_time):
            if p not in detected_names:
                del self.face_seen_time[p]

        return frame, confirmed_matches, detected_names, overlay_results
