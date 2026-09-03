"""
Camera Stream Acquisition Thread.
Grabs frames from webcam or IP camera URL without blocking the Tkinter GUI.
"""

import queue
import threading
import time
from typing import Optional, Union
import cv2


class CameraWorker:
    """Background worker that continuously pulls video frames from device or RTSP/HTTP URL."""

    def __init__(self, camera_url: Union[str, int], frame_queue: queue.Queue, stop_event: threading.Event, log_callback=None):
        self.camera_url = camera_url
        self.frame_queue = frame_queue
        self.stop_event = stop_event
        self.log_callback = log_callback
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True, name="CameraWorkerThread")
        self.thread.start()

    def _run(self):
        # Convert numeric string to integer for local USB webcams
        src = self.camera_url
        if isinstance(src, str) and src.isdigit():
            src = int(src)

        if isinstance(src, int):
            cap = cv2.VideoCapture(src)
        else:
            cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)

        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if self.log_callback:
            self.log_callback(f"  Camera opened: {self.camera_url}\n")

        while not self.stop_event.is_set():
            ret, frame = cap.read()
            if ret and frame is not None:
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
                self.frame_queue.put(frame)
            else:
                time.sleep(0.04)

        cap.release()
        if self.log_callback:
            self.log_callback("  Camera released.\n")
