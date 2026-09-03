import cv2
import numpy as np
import mediapipe as mp

class DepthLivenessDetector:
    def __init__(self, depth_variance_threshold=0.035):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.depth_threshold = depth_variance_threshold

        self.NOSE_TIP = 1
        self.LEFT_CHEEK = 234
        self.RIGHT_CHEEK = 454
        self.CHIN = 152

    def check_liveness(self, bgr_frame):
        """
        অপটিমাইজড: ফ্রেম 0.5x স্কেল ডাউন করে প্রসেস করা হচ্ছে
        """
        # ১. রেজোলিউশন কমিয়ে প্রসেসিং স্পিড বাড়ানো
        small_frame = cv2.resize(bgr_frame, (0, 0), fx=0.5, fy=0.5)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        results = self.face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            return False, 0.0

        landmarks = results.multi_face_landmarks[0].landmark

        z_nose = landmarks[self.NOSE_TIP].z
        z_left = landmarks[self.LEFT_CHEEK].z
        z_right = landmarks[self.RIGHT_CHEEK].z
        z_chin = landmarks[self.CHIN].z

        depth_horizontal = ((z_left - z_nose) + (z_right - z_nose)) / 2.0
        depth_vertical = z_chin - z_nose

        depth_score = (depth_horizontal + depth_vertical) / 2.0
        is_live = depth_score > self.depth_threshold
        return is_live, depth_score

    def release(self):
        self.face_mesh.close()
