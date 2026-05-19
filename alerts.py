import time
from datetime import datetime

import config
import utils


class AlertManager:
    def __init__(self):
        self.last_alert_times = {}

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def check_fall(self, track_id, posture_state, person_bbox=None):
        """
        Fall detection: pose-based (v2 in PostureAnalyzer) plus optional legacy bbox.

        When ``config.USE_LEGACY_BBOX_FALL`` is True, a wide YOLO box
        (width > height * ratio) also triggers a fall alert — useful only for
        comparison; default is off.
        """
        pose_fall = posture_state is not None and posture_state.is_fall
        if not config.USE_LEGACY_BBOX_FALL:
            return pose_fall
        bbox_fall = False
        if person_bbox is not None:
            x1, y1, x2, y2 = person_bbox
            w = float(x2 - x1)
            h = float(y2 - y1)
            posture_tilted = (
                posture_state is None
                or posture_state.torso_angle >= config.LEGACY_BBOX_FALL_MIN_TORSO_ANGLE
            )
            if h > 1.0 and posture_tilted and w > h * config.LEGACY_BBOX_FALL_WH_RATIO:
                bbox_fall = True
        return pose_fall or bbox_fall

    def check_inactivity(self, track_id, posture_state):
        """Landmark-stillness based inactivity detection."""
        if posture_state is None:
            return False
        return posture_state.is_inactive

    def check_sleeping(self, track_id, posture_state):
        """Slouch + prolonged inactivity → sleeping / unconscious."""
        if posture_state is None:
            return False
        return posture_state.is_sleeping

    def check_phone_usage(self, track_id, person_bbox, phone_detections):
        px1, py1, px2, py2 = person_bbox
        pw = px2 - px1
        ph = py2 - py1
        margin = int(max(pw, ph) * config.PHONE_PERSON_MARGIN_RATIO)
        mx1 = px1 - margin
        my1 = py1 - margin
        mx2 = px2 + margin
        my2 = py2 + margin

        for phone in phone_detections:
            phone_bbox = phone["bbox_xyxy"]
            phone_cx = (phone_bbox[0] + phone_bbox[2]) // 2
            phone_cy = (phone_bbox[1] + phone_bbox[3]) // 2

            if px1 <= phone_cx <= px2 and py1 <= phone_cy <= py2:
                return True

            if mx1 <= phone_cx <= mx2 and my1 <= phone_cy <= my2:
                return True

            if (
                utils.compute_iou(person_bbox, phone_bbox)
                > config.PHONE_OVERLAP_IOU_THRESHOLD
            ):
                return True

        return False

    def check_restricted_zone(self, track_id, bbox):
        if not config.RESTRICTED_ZONES:
            return False

        cx = (bbox[0] + bbox[2]) // 2
        cy = (bbox[1] + bbox[3]) // 2

        for zx1, zy1, zx2, zy2 in config.RESTRICTED_ZONES:
            if zx1 <= cx <= zx2 and zy1 <= cy <= zy2:
                return True

        return False

    # ------------------------------------------------------------------
    # Cooldown & firing
    # ------------------------------------------------------------------

    def _should_fire(self, track_id, alert_type):
        key = (track_id, alert_type)
        last_time = self.last_alert_times.get(key, 0)
        return time.time() - last_time > config.ALERT_COOLDOWN_SECONDS

    def fire_alert(self, track_id, alert_type, frame, utils_ref):
        if not self._should_fire(track_id, alert_type):
            return None

        self.last_alert_times[(track_id, alert_type)] = time.time()

        messages = {
            "FALL": f"\u26a0 POSSIBLE FALL DETECTED \u2014 Person #{track_id}",
            "PHONE": f"\U0001f4f5 PHONE USAGE DETECTED \u2014 Person #{track_id}",
            "ZONE": f"\U0001f6ab RESTRICTED ZONE BREACH \u2014 Person #{track_id}",
            "INACTIVITY": f"\u23f8 INACTIVITY DETECTED \u2014 Person #{track_id}",
            "STANDING_INACTIVITY": f"\u23f8 STANDING TOO LONG \u2014 Person #{track_id}",
            "SLEEPING": f"\U0001f4a4 SLEEPING / UNCONSCIOUS \u2014 Person #{track_id}",
        }
        message = messages.get(alert_type)
        if not message:
            return None

        if config.SCREENSHOT_ON_ALERT:
            utils_ref.save_screenshot(frame, alert_type, track_id)
        utils_ref.log_event(message)
        utils_ref.play_sound()

        return message

    # ------------------------------------------------------------------
    # Main per-frame entry point
    # ------------------------------------------------------------------

    def process_frame(self, tracked_persons, phone_detections, posture_states, frame, utils_ref):
        """
        Process one frame of detections and posture states.

        Parameters
        ----------
        tracked_persons : list[dict]
            ``[{"track_id": int, "bbox": [x1,y1,x2,y2]}, ...]``
        phone_detections : list[dict]
            Raw phone detections from YOLO.
        posture_states : dict[int, PostureState]
            ``{track_id: PostureState}`` from the posture analyser.
        frame : np.ndarray
            Current video frame (for screenshots).
        utils_ref : module
            Reference to the ``utils`` module.

        Returns
        -------
        list[dict]
            List of fired alert dicts.
        """
        fired_alerts = []

        for person in tracked_persons:
            track_id = person["track_id"]
            bbox = person["bbox"]
            posture = posture_states.get(track_id)

            # ---- Pose-based fall detection (+ optional legacy bbox) ----
            if self.check_fall(track_id, posture, bbox):
                msg = self.fire_alert(track_id, "FALL", frame, utils_ref)
                if msg:
                    fired_alerts.append(
                        {
                            "type": "FALL",
                            "msg": msg,
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "track_id": track_id,
                        }
                    )

            # ---- Inactivity detection ----
            if self.check_inactivity(track_id, posture):
                alert_type = (
                    "STANDING_INACTIVITY"
                    if posture and posture.is_standing_too_long
                    else "INACTIVITY"
                )
                msg = self.fire_alert(track_id, alert_type, frame, utils_ref)
                if msg:
                    fired_alerts.append(
                        {
                            "type": alert_type,
                            "msg": msg,
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "track_id": track_id,
                        }
                    )

            # ---- Sleeping / unconscious detection ----
            if self.check_sleeping(track_id, posture):
                msg = self.fire_alert(track_id, "SLEEPING", frame, utils_ref)
                if msg:
                    fired_alerts.append(
                        {
                            "type": "SLEEPING",
                            "msg": msg,
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "track_id": track_id,
                        }
                    )

            # ---- Phone usage (unchanged) ----
            if self.check_phone_usage(track_id, bbox, phone_detections):
                msg = self.fire_alert(track_id, "PHONE", frame, utils_ref)
                if msg:
                    fired_alerts.append(
                        {
                            "type": "PHONE",
                            "msg": msg,
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "track_id": track_id,
                        }
                    )

            # ---- Restricted zone (unchanged) ----
            if self.check_restricted_zone(track_id, bbox):
                msg = self.fire_alert(track_id, "ZONE", frame, utils_ref)
                if msg:
                    fired_alerts.append(
                        {
                            "type": "ZONE",
                            "msg": msg,
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "track_id": track_id,
                        }
                    )

        return fired_alerts
