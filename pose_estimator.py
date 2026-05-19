"""
MediaPipe Pose wrapper for VisionGuard AI (Tasks API, MediaPipe >= 0.10).

Given a full video frame and a person bounding box (from YOLO), this module:
    1. Crops the person ROI from the frame.
    2. Runs PoseLandmarker on the cropped region.
    3. Maps normalised landmark coordinates back to full-frame pixels.
    4. Returns a dict of landmark-name → (abs_x, abs_y, visibility).
"""

import os
import urllib.request

import config

# Landmark indices (MediaPipe Pose 33-point model)
_LANDMARK_NAMES = {
    0: "nose",
    11: "left_shoulder",
    12: "right_shoulder",
    13: "left_elbow",
    14: "right_elbow",
    15: "left_wrist",
    16: "right_wrist",
    23: "left_hip",
    24: "right_hip",
    25: "left_knee",
    26: "right_knee",
    27: "left_ankle",
    28: "right_ankle",
}

# Skeleton connections for drawing (index pairs)
SKELETON_CONNECTIONS = [
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
    (11, 23),
    (12, 24),
    (23, 24),
    (23, 25),
    (25, 27),
    (24, 26),
    (26, 28),
    (0, 11),
    (0, 12),
]

_POSE_MODEL_VARIANTS = {
    0: (
        "pose_landmarker_lite.task",
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task",
    ),
    1: (
        "pose_landmarker_full.task",
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_full/float16/latest/pose_landmarker_full.task",
    ),
    2: (
        "pose_landmarker_heavy.task",
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task",
    ),
}


def _resolve_pose_model_path() -> str:
    """Return local path to the pose .task model, downloading once if needed."""
    complexity = int(config.POSE_MODEL_COMPLEXITY)
    if complexity not in _POSE_MODEL_VARIANTS:
        complexity = 0
    filename, url = _POSE_MODEL_VARIANTS[complexity]
    model_dir = os.path.join(os.path.dirname(__file__), config.POSE_MODEL_DIR)
    os.makedirs(model_dir, exist_ok=True)
    path = os.path.join(model_dir, filename)
    if not os.path.isfile(path):
        print(f"Downloading pose model ({filename})...")
        urllib.request.urlretrieve(url, path)
        print(f"Saved pose model to {path}")
    return path


class PoseEstimator:
    """Extract human body landmarks from a person-cropped region."""

    def __init__(self):
        from mediapipe.tasks.python.core import base_options as base_options_lib
        from mediapipe.tasks.python.vision import pose_landmarker
        from mediapipe.tasks.python.vision.core import vision_task_running_mode

        model_path = _resolve_pose_model_path()
        options = pose_landmarker.PoseLandmarkerOptions(
            base_options=base_options_lib.BaseOptions(model_asset_path=model_path),
            running_mode=vision_task_running_mode.VisionTaskRunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=config.POSE_MIN_DETECTION_CONF,
            min_pose_presence_confidence=config.POSE_MIN_DETECTION_CONF,
            min_tracking_confidence=config.POSE_MIN_TRACKING_CONF,
            output_segmentation_masks=False,
        )
        self._landmarker = pose_landmarker.PoseLandmarker.create_from_options(options)
        self._mp_image_cls = __import__(
            "mediapipe.tasks.python.vision.core.image", fromlist=["Image"]
        ).Image
        self._image_format = __import__(
            "mediapipe.tasks.python.vision.core.image", fromlist=["ImageFormat"]
        ).ImageFormat
        self._vis_thresh = config.POSE_LANDMARK_VISIBILITY_THRESH

    # ------------------------------------------------------------------

    def estimate(self, frame, person_bbox):
        """
        Run pose estimation on a person crop.

        Returns ``{landmark_name: (abs_x, abs_y, visibility)}`` or ``None``.
        """
        import cv2
        import numpy as np

        x1, y1, x2, y2 = person_bbox
        h_frame, w_frame = frame.shape[:2]

        x1 = max(0, int(x1))
        y1 = max(0, int(y1))
        x2 = min(w_frame, int(x2))
        y2 = min(h_frame, int(y2))

        crop_w = x2 - x1
        crop_h = y2 - y1
        if crop_w < 20 or crop_h < 20:
            return None

        roi = frame[y1:y2, x1:x2]
        rgb_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        if not rgb_roi.flags["C_CONTIGUOUS"]:
            rgb_roi = np.ascontiguousarray(rgb_roi)

        mp_image = self._mp_image_cls(
            image_format=self._image_format.SRGB, data=rgb_roi
        )
        result = self._landmarker.detect(mp_image)

        if not result.pose_landmarks:
            return None

        pose_lms = result.pose_landmarks[0]
        landmarks = {}
        for idx, name in _LANDMARK_NAMES.items():
            if idx >= len(pose_lms):
                continue
            lm = pose_lms[idx]
            vis = lm.visibility
            if vis is None:
                vis = lm.presence if lm.presence is not None else 0.0
            if vis < self._vis_thresh:
                continue
            abs_x = int(lm.x * crop_w + x1)
            abs_y = int(lm.y * crop_h + y1)
            landmarks[name] = (abs_x, abs_y, round(float(vis), 3))

        if len(landmarks) < 4:
            return None

        return landmarks

    # ------------------------------------------------------------------

    def estimate_batch(self, frame, person_bboxes, max_persons=3):
        results = []
        for i, bbox in enumerate(person_bboxes):
            if i >= max_persons:
                results.append(None)
                continue
            results.append(self.estimate(frame, bbox))
        return results

    # ------------------------------------------------------------------

    def close(self):
        """Release MediaPipe resources."""
        self._landmarker.close()
