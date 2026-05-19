import os
from datetime import datetime

import cv2

import config
from pose_estimator import SKELETON_CONNECTIONS, _LANDMARK_NAMES


def _clamp_box(frame, x1, y1, x2, y2):
    h, w = frame.shape[:2]
    return (
        max(0, min(w - 1, int(x1))),
        max(0, min(h - 1, int(y1))),
        max(0, min(w - 1, int(x2))),
        max(0, min(h - 1, int(y2))),
    )


def _draw_label_pill(frame, text, origin, color, scale=0.48):
    x, y = origin
    text_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    pill_w = text_size[0] + 18
    pill_h = text_size[1] + 12
    x1, y1, x2, y2 = _clamp_box(frame, x, y - pill_h, x + pill_w, y)

    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (8, 12, 20), -1)
    cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1, cv2.LINE_AA)
    cv2.circle(frame, (x1 + 8, y1 + pill_h // 2), 3, color, -1, cv2.LINE_AA)
    cv2.putText(
        frame,
        text,
        (x1 + 15, y2 - 8),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (235, 245, 255),
        1,
        cv2.LINE_AA,
    )


def draw_bounding_box(frame, bbox, label, color):
    x1, y1, x2, y2 = bbox
    x1, y1, x2, y2 = _clamp_box(frame, x1, y1, x2, y2)
    thickness = 3 if color == config.COLOR_FALL else 2

    glow = frame.copy()
    cv2.rectangle(glow, (x1, y1), (x2, y2), color, thickness + 5, cv2.LINE_AA)
    cv2.addWeighted(glow, 0.18, frame, 0.82, 0, frame)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness, cv2.LINE_AA)

    corner = max(14, min(32, (x2 - x1) // 5, (y2 - y1) // 5))
    for sx, sy in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):
        ex = sx + corner if sx == x1 else sx - corner
        ey = sy + corner if sy == y1 else sy - corner
        cv2.line(frame, (sx, sy), (ex, sy), color, thickness + 1, cv2.LINE_AA)
        cv2.line(frame, (sx, sy), (sx, ey), color, thickness + 1, cv2.LINE_AA)

    _draw_label_pill(frame, label, (x1, max(24, y1 - 4)), color)


def draw_pose_skeleton(frame, landmarks):
    """Draw pose skeleton lines and landmark dots on the frame."""
    if not landmarks:
        return

    idx_to_pt = {}
    for idx, name in _LANDMARK_NAMES.items():
        lm = landmarks.get(name)
        if lm is not None:
            idx_to_pt[idx] = (lm[0], lm[1])

    for idx_a, idx_b in SKELETON_CONNECTIONS:
        pt_a = idx_to_pt.get(idx_a)
        pt_b = idx_to_pt.get(idx_b)
        if pt_a and pt_b:
            cv2.line(frame, pt_a, pt_b, config.COLOR_SKELETON, 2, cv2.LINE_AA)

    for pt in idx_to_pt.values():
        cv2.circle(frame, pt, 4, config.COLOR_LANDMARK, -1, cv2.LINE_AA)


def draw_posture_label(frame, bbox, posture_label, posture_state):
    """Draw posture state label below the person bounding box."""
    if not posture_label:
        return

    x1, y1, x2, y2 = bbox

    if posture_state and posture_state.is_fall:
        color = config.COLOR_FALL
    elif posture_state and posture_state.is_sleeping:
        color = config.COLOR_SLOUCH
    elif posture_state and posture_state.is_inactive:
        color = config.COLOR_INACTIVITY
    elif posture_state and posture_state.is_slouching:
        color = config.COLOR_SLOUCH
    else:
        color = (200, 200, 200)

    label = posture_label
    y_pos = y2 + 18
    if y_pos > frame.shape[0] - 5:
        y_pos = y1 - 30

    if "standing" in label.lower():
        color = (255, 167, 85)

    _draw_label_pill(frame, label, (x1, y_pos + 4), color, 0.42)

    if posture_state:
        angle_text = f"{posture_state.torso_angle:.0f} deg"
        cv2.putText(
            frame, angle_text, (x1 + 4, y_pos + 16),
            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (170, 185, 205), 1,
            cv2.LINE_AA,
        )


def draw_alert_overlay(frame, active_alert_messages):
    for i, msg in enumerate(active_alert_messages[:5]):
        y = 36 + i * 34
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, y - 26), (frame.shape[1] - 10, y + 8), (8, 12, 20), -1)
        cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)
        cv2.rectangle(frame, (10, y - 26), (frame.shape[1] - 10, y + 8), config.COLOR_FALL, 1, cv2.LINE_AA)
        cv2.putText(
            frame,
            msg,
            (20, y - 3),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            config.COLOR_ALERT_TEXT,
            1,
            cv2.LINE_AA,
        )


def draw_detection_legend(frame):
    """Legend intentionally removed; dashboard filters now show overlay categories."""
    return


def draw_fps(frame, fps):
    text = f"FPS: {fps:.1f}"
    label_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    x = frame.shape[1] - label_size[0] - 22
    y = 28
    overlay = frame.copy()
    cv2.rectangle(overlay, (x - 8, y - 20), (frame.shape[1] - 10, y + 8), (8, 12, 20), -1)
    cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)
    cv2.rectangle(frame, (x - 8, y - 20), (frame.shape[1] - 10, y + 8), (72, 216, 255), 1, cv2.LINE_AA)
    cv2.putText(
        frame,
        text,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        config.COLOR_FPS,
        1,
        cv2.LINE_AA,
    )


def draw_restricted_zones(frame):
    for zx1, zy1, zx2, zy2 in config.RESTRICTED_ZONES:
        overlay = frame.copy()
        cv2.rectangle(overlay, (zx1, zy1), (zx2, zy2), config.COLOR_ZONE, -1)
        cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
        cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), config.COLOR_ZONE, 2)
        cv2.putText(
            frame,
            "RESTRICTED",
            (zx1 + 4, zy1 + 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            config.COLOR_ZONE,
            2,
        )


def save_screenshot(frame, alert_type, track_id):
    os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{config.SCREENSHOT_DIR}/{alert_type}_person{track_id}_{ts}.jpg"
    cv2.imwrite(filename, frame)


def log_event(message):
    os.makedirs(config.LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(config.LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {message}\n")


def play_sound():
    if not config.ENABLE_ALERT_SOUND:
        return

    try:
        import platform

        system = platform.system()
        if system == "Windows":
            import winsound

            winsound.Beep(1000, 200)
        elif system == "Darwin":
            os.system("afplay /System/Library/Sounds/Glass.aiff &")
        else:
            os.system("printf '\\a'")
    except Exception:
        pass


def compute_iou(box_a, box_b):
    inter_x1 = max(box_a[0], box_b[0])
    inter_y1 = max(box_a[1], box_b[1])
    inter_x2 = min(box_a[2], box_b[2])
    inter_y2 = min(box_a[3], box_b[3])
    inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter_area
    return inter_area / union if union > 0 else 0.0
