"""
Posture analysis engine for VisionGuard AI.

Pure math module — no OpenCV or MediaPipe imports.  Takes landmark
coordinates produced by ``PoseEstimator`` and computes:

    - **Torso angle** (from vertical) for fall detection, combined with **v2**
      hip→foot axis geometry to reject standing/crouch bends.
    - **Head-drop velocity** for sudden collapse detection.
    - **Landmark stillness** for inactivity detection.
    - **Slouch / sleeping** (head below shoulders + torso lean + inactivity).

Each tracked person has a rolling history of states so that temporal
conditions (e.g. "horizontal for N frames") can be evaluated.
"""

import math
import time
from dataclasses import dataclass, field

import config


# ── Result data class ─────────────────────────────────────────────────────────

@dataclass
class PostureState:
    """Snapshot of a person's posture analysis for a single frame."""

    torso_angle: float = 0.0          # degrees from vertical (0=upright)
    head_drop_velocity: float = 0.0   # normalised y-delta per second
    avg_movement: float = 0.0         # avg landmark displacement (pixels)
    posture_label: str = "Unknown"    # human-readable label

    is_fall: bool = False
    is_inactive: bool = False
    is_standing_too_long: bool = False
    is_slouching: bool = False
    is_sleeping: bool = False
    standing_seconds: float = 0.0


# ── Per-person history ────────────────────────────────────────────────────────

@dataclass
class _PersonHistory:
    prev_landmarks: dict = field(default_factory=dict)
    prev_nose_y: float = 0.0
    prev_time: float = 0.0

    fall_frame_count: int = 0
    head_drop_frame_count: int = 0
    still_frame_count: int = 0
    slouch_frame_count: int = 0
    standing_start_time: float = 0.0


# ── Analyzer ──────────────────────────────────────────────────────────────────

class PostureAnalyzer:
    """Stateful posture analyser that maintains per-person history."""

    def __init__(self):
        self._history: dict[int, _PersonHistory] = {}

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def analyze(self, track_id: int, landmarks: dict, frame_time: float = None, person_bbox=None) -> PostureState:
        """
        Analyse posture from landmarks for a tracked person.

        Parameters
        ----------
        track_id : int
            Persistent ID from the centroid tracker.
        landmarks : dict
            ``{name: (x, y, visibility)}`` from ``PoseEstimator``.
        frame_time : float
            ``time.time()`` timestamp of the current frame.

        Returns
        -------
        PostureState
        """
        if frame_time is None:
            frame_time = time.time()

        hist = self._history.setdefault(track_id, _PersonHistory())
        state = PostureState()

        # ---- 1. Torso angle ----
        state.torso_angle = self._compute_torso_angle(landmarks)

        # ---- 2. Head-drop velocity ----
        state.head_drop_velocity = self._compute_head_drop(
            hist, landmarks, frame_time
        )

        # ---- 3. Landmark stillness ----
        state.avg_movement = self._compute_landmark_stillness(
            hist, landmarks
        )

        # ---- 4. Fall detection (v2 torso + hip–foot geometry + confirmation) ----
        torso_alert = state.torso_angle >= config.FALL_TORSO_ANGLE_THRESHOLD
        v2_ok, v2_has_legs = self._v2_fall_geometry(landmarks)
        bbox_fall = self._bbox_fall_geometry(person_bbox, state.torso_angle)

        if bbox_fall:
            hist.fall_frame_count = max(hist.fall_frame_count, config.FALL_CONFIRM_FRAMES)
        elif torso_alert:
            if v2_ok:
                hist.fall_frame_count += 1
            elif v2_has_legs and config.FALL_V2_STRICT_LANDMARKS:
                # Legs visible but geometry says "standing-like" — do not count
                hist.fall_frame_count = max(0, hist.fall_frame_count - 2)
            elif not v2_has_legs and not config.FALL_V2_STRICT_LANDMARKS:
                # v1 fallback: insufficient landmarks, optional loose mode
                hist.fall_frame_count += 1
            else:
                # Strict mode, missing leg landmarks — do not advance sustained fall
                hist.fall_frame_count = max(0, hist.fall_frame_count - 1)
        else:
            hist.fall_frame_count = max(0, hist.fall_frame_count - 2)

        state.is_fall = hist.fall_frame_count >= config.FALL_CONFIRM_FRAMES

        # Sudden collapse: head drop (independent of v2 sustained path)
        if state.head_drop_velocity > config.FALL_HEAD_DROP_THRESHOLD:
            hist.head_drop_frame_count += 1
        else:
            hist.head_drop_frame_count = max(0, hist.head_drop_frame_count - 1)
        if hist.head_drop_frame_count >= config.FALL_HEAD_DROP_FRAMES:
            state.is_fall = True

        # ---- 5. Inactivity detection ----
        if state.avg_movement < config.INACTIVITY_MOVEMENT_THRESHOLD:
            hist.still_frame_count += 1
        else:
            hist.still_frame_count = 0

        # Convert still frames to approximate seconds using DETECT_EVERY_N
        # Each detection cycle happens every DETECT_EVERY_N frames at ~15 fps
        effective_fps = 15.0 / max(config.DETECT_EVERY_N, 1)
        still_seconds = hist.still_frame_count / max(effective_fps, 1.0)
        state.is_inactive = still_seconds >= config.INACTIVITY_DURATION_SECONDS

        # ---- 6. Slouch / sleeping detection ----
        head_below = self._is_head_below_shoulders(landmarks)
        is_leaning = config.SLOUCH_TORSO_ANGLE_MIN <= state.torso_angle < config.FALL_TORSO_ANGLE_THRESHOLD

        if head_below and is_leaning:
            hist.slouch_frame_count += 1
        else:
            hist.slouch_frame_count = max(0, hist.slouch_frame_count - 1)

        slouch_seconds = hist.slouch_frame_count / max(effective_fps, 1.0)
        state.is_slouching = slouch_seconds >= 2.0  # at least 2 seconds

        # Sleeping = slouching + inactive for a longer duration
        state.is_sleeping = (
            state.is_slouching
            and still_seconds >= config.SLOUCH_DURATION_SECONDS
        )

        # ---- 7. Long standing inactivity detection ----
        is_upright_standing = (
            state.torso_angle < 25
            and not state.is_fall
            and not state.is_slouching
            and not state.is_sleeping
        )

        if is_upright_standing:
            if hist.standing_start_time <= 0:
                hist.standing_start_time = frame_time
            state.standing_seconds = frame_time - hist.standing_start_time
        else:
            hist.standing_start_time = 0.0
            state.standing_seconds = 0.0

        state.is_standing_too_long = (
            state.standing_seconds >= config.STANDING_INACTIVITY_SECONDS
        )
        state.is_inactive = state.is_inactive or state.is_standing_too_long

        # ---- 8. Human-readable label ----
        state.posture_label = self._classify_label(state)

        # ---- Update history ----
        hist.prev_landmarks = dict(landmarks)
        nose = landmarks.get("nose")
        hist.prev_nose_y = nose[1] if nose else hist.prev_nose_y
        hist.prev_time = frame_time

        return state

    def cleanup_stale(self, active_ids: set):
        """Remove history for person IDs that are no longer tracked."""
        stale = [tid for tid in self._history if tid not in active_ids]
        for tid in stale:
            del self._history[tid]

    # ------------------------------------------------------------------
    # Computation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bbox_fall_geometry(person_bbox, torso_angle: float) -> bool:
        """Detect obvious lying bodies from a wide person bounding box."""
        if not config.USE_LEGACY_BBOX_FALL or person_bbox is None:
            return False

        x1, y1, x2, y2 = person_bbox
        width = max(0.0, float(x2 - x1))
        height = max(1.0, float(y2 - y1))
        is_wide = width > height * config.LEGACY_BBOX_FALL_WH_RATIO
        is_tilted = torso_angle >= config.LEGACY_BBOX_FALL_MIN_TORSO_ANGLE
        return is_wide and is_tilted

    @staticmethod
    def _v2_fall_geometry(landmarks: dict) -> tuple[bool, bool]:
        """
        v2 sustained-fall geometry: hip→mid-foot segment should be mostly
        horizontal in the image (lying), not vertical (standing / deep crouch).

        Returns
        -------
        (geometry_ok, has_leg_data)
            ``geometry_ok`` — True if this frame supports a lying / collapsed pose.
            ``has_leg_data`` — True if ankles or knees were usable for the segment.
        """
        lh = landmarks.get("left_hip")
        rh = landmarks.get("right_hip")
        if not lh and not rh:
            return False, False
        if lh and rh:
            mid_hx = (lh[0] + rh[0]) / 2.0
            mid_hy = (lh[1] + rh[1]) / 2.0
        else:
            h = lh or rh
            mid_hx, mid_hy = h[0], h[1]

        # Prefer ankles; else knees as foot proxy
        la = landmarks.get("left_ankle")
        ra = landmarks.get("right_ankle")
        lk = landmarks.get("left_knee")
        rk = landmarks.get("right_knee")

        foot_pts = []
        if la:
            foot_pts.append((la[0], la[1]))
        if ra:
            foot_pts.append((ra[0], ra[1]))
        if not foot_pts:
            if lk:
                foot_pts.append((lk[0], lk[1]))
            if rk:
                foot_pts.append((rk[0], rk[1]))

        if not foot_pts:
            return False, False

        mid_fx = sum(p[0] for p in foot_pts) / len(foot_pts)
        mid_fy = sum(p[1] for p in foot_pts) / len(foot_pts)

        dx = mid_fx - mid_hx
        dy = mid_fy - mid_hy
        length = math.hypot(dx, dy)
        if length < config.FALL_V2_MIN_LEG_SEGMENT_PX:
            return False, True

        # Standing: segment is mostly vertical → abs(dy)/length ≈ 1.
        # Prone / supine from typical side-ish views: mostly horizontal → low ratio.
        verticality = abs(dy) / length
        geometry_ok = verticality <= config.FALL_V2_MAX_HIP_FOOT_VERTICALITY
        return geometry_ok, True

    @staticmethod
    def _compute_torso_angle(landmarks: dict) -> float:
        """
        Compute the angle of the torso from vertical.

        Uses the vector from mid-hip to mid-shoulder.
        Returns 0° for perfectly upright, 90° for horizontal.
        """
        ls = landmarks.get("left_shoulder")
        rs = landmarks.get("right_shoulder")
        lh = landmarks.get("left_hip")
        rh = landmarks.get("right_hip")

        # Need at least one shoulder and one hip
        if not ls and not rs:
            return 0.0
        if not lh and not rh:
            return 0.0

        # Midpoints (use whichever side is available)
        if ls and rs:
            mid_sx = (ls[0] + rs[0]) / 2.0
            mid_sy = (ls[1] + rs[1]) / 2.0
        else:
            s = ls or rs
            mid_sx, mid_sy = s[0], s[1]

        if lh and rh:
            mid_hx = (lh[0] + rh[0]) / 2.0
            mid_hy = (lh[1] + rh[1]) / 2.0
        else:
            h = lh or rh
            mid_hx, mid_hy = h[0], h[1]

        # Vector from hip to shoulder
        dx = mid_sx - mid_hx
        dy = mid_sy - mid_hy  # In image coords, y increases downward

        # Angle from vertical (pointing up = negative dy in image space)
        angle = abs(math.degrees(math.atan2(dx, -dy)))
        return min(angle, 180.0)

    @staticmethod
    def _compute_head_drop(hist: _PersonHistory, landmarks: dict, frame_time: float) -> float:
        """
        Compute how fast the nose/head is dropping (normalised y-velocity).

        Positive velocity = head moving downward in image space.
        """
        nose = landmarks.get("nose")
        if not nose:
            return 0.0

        if hist.prev_time <= 0 or hist.prev_nose_y <= 0:
            return 0.0

        dt = frame_time - hist.prev_time
        if dt <= 0:
            return 0.0

        # Positive dy = head moved down (in image coords)
        dy = nose[1] - hist.prev_nose_y
        velocity = dy / dt  # pixels per second

        # Normalise by dividing by a reference frame height (~270 px)
        return velocity / 270.0

    @staticmethod
    def _compute_landmark_stillness(hist: _PersonHistory, landmarks: dict) -> float:
        """
        Compute average displacement of all visible landmarks vs previous frame.

        Returns normalised displacement (divided by reference frame size).
        """
        if not hist.prev_landmarks:
            return 999.0  # first frame — treat as "moving" to avoid false alert

        total_disp = 0.0
        count = 0

        for name, (x, y, _vis) in landmarks.items():
            prev = hist.prev_landmarks.get(name)
            if prev is None:
                continue
            px, py, _ = prev
            total_disp += math.hypot(x - px, y - py)
            count += 1

        if count == 0:
            return 999.0

        avg = total_disp / count
        # Normalise by frame height reference
        return avg / 270.0

    @staticmethod
    def _is_head_below_shoulders(landmarks: dict) -> bool:
        """Check if head (nose) is below the shoulder line in image coords."""
        nose = landmarks.get("nose")
        ls = landmarks.get("left_shoulder")
        rs = landmarks.get("right_shoulder")

        if not nose:
            return False
        if not ls and not rs:
            return False

        if ls and rs:
            mid_sy = (ls[1] + rs[1]) / 2.0
        else:
            s = ls or rs
            mid_sy = s[1]

        # In image coords y increases downward, so nose.y > shoulder.y = below
        return nose[1] > mid_sy + 5  # small margin

    @staticmethod
    def _classify_label(state: PostureState) -> str:
        """Return a human-readable posture label for display."""
        if state.is_sleeping:
            return "Sleeping"
        if state.is_fall:
            return "Falling"
        if state.is_standing_too_long:
            return "Standing too long"
        if state.is_inactive:
            return "Inactive"
        if state.is_slouching:
            return "Slouching"
        if state.torso_angle < 25:
            return "Standing"
        if state.torso_angle < 50:
            return "Leaning"
        return "Bending"
