import cv2
import numpy as np
import mediapipe as mp

class DepthLivenessDetector:
    def __init__(self, depth_variance_threshold=0.04):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.depth_threshold = depth_variance_threshold

        # Key landmark indices in MediaPipe Face Mesh:
        # 1: Nose tip
        # 234: Left cheek / ear side
        # 454: Right cheek / ear side
        # 10: Forehead top
        # 152: Chin bottom
        self.NOSE_TIP = 1
        self.LEFT_CHEEK = 234
        self.RIGHT_CHEEK = 454
        self.CHIN = 152

    def check_liveness(self, bgr_frame):
        """
        Returns:
            is_live (bool): True if 3D face structure is verified.
            depth_score (float): Calculated 3D curvature score.
        """
        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            return False, 0.0

        landmarks = results.multi_face_landmarks[0].landmark

        # Get Z coordinates (relative depth)
        z_nose = landmarks[self.NOSE_TIP].z
        z_left = landmarks[self.LEFT_CHEEK].z
        z_right = landmarks[self.RIGHT_CHEEK].z
        z_chin = landmarks[self.CHIN].z

        # In real 3D faces, the nose tip protrudes forward (smaller/more negative Z)
        # while sides of the face curve backward (larger Z).
        depth_horizontal = ((z_left - z_nose) + (z_right - z_nose)) / 2.0
        depth_vertical = z_chin - z_nose

        # Combined 3D curvature metric
        depth_score = (depth_horizontal + depth_vertical) / 2.0

        # Flat surfaces/screens yield very low or inconsistent depth disparity
        is_live = depth_score > self.depth_threshold
        return is_live, depth_score

    def release(self):
        self.face_mesh.close()
