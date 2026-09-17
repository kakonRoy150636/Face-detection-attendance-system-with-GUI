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

    def __init__(self, camera_id: int, camera_url: Union[str, int], frame_queue: queue.Queue, stop_event: threading.Event, log_callback=None):
        self.camera_id = camera_id
        self.camera_url = camera_url
        self.frame_queue = frame_queue
        self.stop_event = stop_event
        self.log_callback = log_callback
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True, name=f"CameraWorkerThread_{self.camera_id}")
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

            # Some OpenCV builds cannot open HTTP/MJPEG streams through the
            # FFmpeg backend even though the default backend can handle them.
            if not cap.isOpened():
                cap.release()
                cap = cv2.VideoCapture(src)

        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            if self.log_callback:
                self.log_callback(
                    f"  Camera {self.camera_id} failed to open: {self.camera_url}\n"
                )
            return

        if self.log_callback:
            self.log_callback(f"  Camera {self.camera_id} opened: {self.camera_url}\n")

        read_failures = 0
        while not self.stop_event.is_set():
            ret, frame = cap.read()
            if ret and frame is not None:
                read_failures = 0
                # Ensure we always have the latest frame in the queue
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                
                try:
                    self.frame_queue.put_nowait((self.camera_id, frame))
                except queue.Full:
                    pass
            else:
                read_failures += 1
                if read_failures == 1 and self.log_callback:
                    self.log_callback(
                        f"  Camera {self.camera_id} opened but returned no frames: {self.camera_url}\n"
                    )
                time.sleep(0.04)

        cap.release()
        if self.log_callback:
            self.log_callback(f"  Camera {self.camera_id} released.\n")
