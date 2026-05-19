import collections
import os
import threading
import time

import cv2

import config
import utils
from alerts import AlertManager
from centroid_tracker import CentroidTracker
from detector import ObjectDetector
from pose_estimator import PoseEstimator
from posture_analyzer import PostureAnalyzer

_lock = threading.Lock()
_latest_frame = None
_alert_history = []
_fps = 0.0
_running = False

_state = {
    "source_type": "webcam",
    "source_value": config.SOURCE,
    "source_name": "Webcam",
    "detection_enabled": False,
    "paused": False,
    "reopen_capture": False,
    "seek_frame": None,
}

_playback = {
    "frame": 0,
    "total": 0,
    "filename": "",
    "fps": float(config.TARGET_FPS),
}

_ai = {
    "detector": None,
    "tracker": None,
    "pose_estimator": None,
    "posture_analyzer": None,
    "alert_manager": None,
    "ready": False,
    "loading": False,
    "error": None,
}

def get_latest_frame():
    with _lock:
        return _latest_frame


def get_alert_history():
    with _lock:
        return list(_alert_history)


def get_fps():
    with _lock:
        return _fps


def get_status():
    with _lock:
        return {
            "detection_enabled": _state["detection_enabled"],
            "detection_ready": _ai["ready"],
            "detection_loading": _ai["loading"],
            "detection_error": _ai["error"],
            "source_type": _state["source_type"],
            "source_name": _state["source_name"],
            "paused": _state["paused"],
            "playback": dict(_playback),
            "fps": round(_fps, 1),
        }


def clear_alerts():
    with _lock:
        _alert_history.clear()


def set_detection_enabled(enabled):
    with _lock:
        _state["detection_enabled"] = enabled
    if enabled and not _ai["ready"] and not _ai["loading"]:
        threading.Thread(target=_load_models_worker, daemon=True).start()


def set_webcam(index=None):
    with _lock:
        _state["source_type"] = "webcam"
        _state["source_value"] = index if index is not None else config.SOURCE
        _state["source_name"] = f"Webcam {_state['source_value']}"
        _state["reopen_capture"] = True
        _state["paused"] = False
        _playback["filename"] = ""
        _playback["frame"] = 0
        _playback["total"] = 0


def set_video_file(filepath, display_name=None):
    with _lock:
        _state["source_type"] = "file"
        _state["source_value"] = filepath
        _state["source_name"] = display_name or os.path.basename(filepath)
        _state["reopen_capture"] = True
        _state["paused"] = False
        _playback["filename"] = _state["source_name"]
        _playback["frame"] = 0
        _playback["total"] = 0


def pause_playback():
    with _lock:
        _state["paused"] = True


def resume_playback():
    with _lock:
        _state["paused"] = False


def restart_video():
    with _lock:
        _state["reopen_capture"] = True
        _state["paused"] = False
        _state["seek_frame"] = 0


def seek_to_frame(frame_num):
    with _lock:
        total = _playback["total"]
        if total > 0:
            frame_num = max(0, min(int(frame_num), total - 1))
        else:
            frame_num = max(0, int(frame_num))
        _state["seek_frame"] = frame_num
        _state["paused"] = False


def seek_percent(percent):
    with _lock:
        total = _playback["total"]
        if total <= 0:
            return
        pct = max(0.0, min(100.0, float(percent)))
        _state["seek_frame"] = int(total * pct / 100.0)
        _state["paused"] = False


def stop():
    global _running
    _running = False


def _publish_frame(jpeg_bytes, fps, fired):
    global _latest_frame, _alert_history, _fps

    with _lock:
        _latest_frame = jpeg_bytes
        _fps = fps
        if fired:
            _alert_history.extend(fired)
            if len(_alert_history) > config.MAX_ALERT_HISTORY:
                _alert_history = _alert_history[-config.MAX_ALERT_HISTORY :]


def _encode_frame(frame):
    ok, buffer = cv2.imencode(
        ".jpg",
        frame,
        [cv2.IMWRITE_JPEG_QUALITY, config.STREAM_JPEG_QUALITY],
    )
    return buffer.tobytes() if ok else None


def _placeholder_frame(text):
    import numpy as np

    frame = np.zeros((config.STREAM_HEIGHT, config.STREAM_WIDTH, 3), dtype=np.uint8)
    cv2.putText(
        frame, text, (16, config.STREAM_HEIGHT // 2),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2,
    )
    return _encode_frame(frame)


def _load_models_worker():
    if _ai["loading"] or _ai["ready"]:
        return
    _ai["loading"] = True
    _ai["error"] = None
    try:
        print("Loading YOLO + MediaPipe Pose...")
        _ai["detector"] = ObjectDetector()
        _ai["tracker"] = CentroidTracker(
            max_disappeared=config.TRACKER_MAX_DISAPPEARED,
            max_distance=config.TRACKER_MAX_DISTANCE,
        )
        _ai["pose_estimator"] = PoseEstimator()
        _ai["posture_analyzer"] = PostureAnalyzer()
        _ai["alert_manager"] = AlertManager()
        _ai["ready"] = True
        print("AI models ready (YOLO + Pose).")
    except Exception as exc:
        _ai["error"] = str(exc)
        print(f"Model load error: {exc}")
    finally:
        _ai["loading"] = False


def _open_capture_from_state():
    st = dict(_state)
    if st["source_type"] == "file":
        path = st["source_value"]
        if not os.path.isfile(path):
            print(f"Video file not found: {path}")
            return None, 0.0
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS) or float(config.TARGET_FPS)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        with _lock:
            _playback["total"] = total
            _playback["frame"] = 0
            _playback["fps"] = fps
        print(f"Opened video: {path} ({total} frames @ {fps:.1f} fps)")
        return cap, fps

    src = st["source_value"]
    backends = [config.CAMERA_BACKEND] if config.CAMERA_BACKEND is not None else [None]
    indices = [src] if isinstance(src, int) else [src]
    if isinstance(src, int):
        indices = [src] + [i for i in range(3) if i != src]

    for idx in indices:
        for backend in backends:
            cap = cv2.VideoCapture(idx, backend) if backend is not None else cv2.VideoCapture(idx)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, config.CAP_BUFFER_SIZE)
            cap.set(cv2.CAP_PROP_FPS, config.TARGET_FPS)
            if cap.isOpened() and cap.read()[0]:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                print(f"Webcam opened: {idx}")
                return cap, float(config.TARGET_FPS)
            cap.release()
    return None, 0.0


def _draw_status_banner(frame, detection_on, source_name, paused):
    if not paused:
        return

    cv2.rectangle(frame, (12, 12), (112, 42), (8, 12, 20), -1)
    cv2.rectangle(frame, (12, 12), (112, 42), (0, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(
        frame, "PAUSED", (24, 33),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1, cv2.LINE_AA,
    )


def run_vision_loop():
    global _running

    _publish_frame(_placeholder_frame("Starting..."), 0.0, [])

    cap = None
    file_fps = float(config.TARGET_FPS)
    frame_times = collections.deque(maxlen=30)
    frame_idx = 0
    last_frame_cache = None
    _running = True

    # Cache last detection results for reuse on non-detection frames
    last_tracks = []
    last_phone_dets = []
    last_posture_states = {}
    last_landmarks_map = {}

    while _running:
        with _lock:
            reopen = _state["reopen_capture"]
            paused = _state["paused"]
            detection_on = _state["detection_enabled"]
            source_name = _state["source_name"]
            source_type = _state["source_type"]
            seek_frame = _state["seek_frame"]

        if seek_frame is not None and cap is not None and source_type == "file":
            cap.set(cv2.CAP_PROP_POS_FRAMES, seek_frame)
            with _lock:
                _playback["frame"] = seek_frame
                _state["seek_frame"] = None
            last_tracks = []
            last_phone_dets = []
            last_posture_states = {}
            last_landmarks_map = {}
            frame_idx = 0

        if reopen or cap is None:
            if cap is not None:
                cap.release()
            cap, file_fps = _open_capture_from_state()
            with _lock:
                _state["reopen_capture"] = False
            last_tracks = []
            last_phone_dets = []
            last_posture_states = {}
            last_landmarks_map = {}
            frame_idx = 0
            if cap is None:
                _publish_frame(
                    _placeholder_frame("No video source — upload CCTV file or use webcam"),
                    0.0, [],
                )
                time.sleep(1)
                continue

        if paused and last_frame_cache is not None:
            frame = last_frame_cache.copy()
            _draw_status_banner(frame, detection_on, source_name, True)
            jpeg = _encode_frame(frame)
            if jpeg:
                _publish_frame(jpeg, _fps, [])
            time.sleep(0.05)
            continue

        ret, frame = cap.read()
        if not ret:
            if source_type == "file":
                if config.VIDEO_LOOP:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    with _lock:
                        _playback["frame"] = 0
                    continue
                _publish_frame(_placeholder_frame("Video ended"), 0.0, [])
                time.sleep(1)
                continue
            time.sleep(0.3)
            continue

        if source_type == "file":
            with _lock:
                _playback["frame"] = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

        frame = cv2.resize(frame, (config.STREAM_WIDTH, config.STREAM_HEIGHT))

        frame_times.append(time.time())
        fps = (len(frame_times) - 1) / (frame_times[-1] - frame_times[0]) if len(frame_times) > 1 else 0.0

        fired = []

        if detection_on:
            if _ai["error"]:
                cv2.putText(frame, f"AI error: {_ai['error'][:35]}", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            elif _ai["ready"]:
                # ── Run detection every N frames ──────────────────────
                if frame_idx % config.DETECT_EVERY_N == 0:
                    detector = _ai["detector"]
                    tracker = _ai["tracker"]
                    pose_estimator = _ai["pose_estimator"]
                    posture_analyzer = _ai["posture_analyzer"]
                    alert_manager = _ai["alert_manager"]

                    # 1. YOLO detection
                    detections = detector.detect(frame)
                    person_dets, phone_dets = detector.split_by_class(detections)

                    # 2. Centroid tracking
                    tracked = tracker.update(
                        [d["bbox_xyxy"] for d in person_dets]
                    )

                    # 3. Pose estimation (per tracked person)
                    posture_states = {}
                    landmarks_map = {}
                    current_time = time.time()

                    for i, person in enumerate(tracked):
                        if i >= config.POSE_MAX_PERSONS:
                            break
                        landmarks = pose_estimator.estimate(
                            frame, person["bbox"]
                        )
                        landmarks_map[person["track_id"]] = landmarks
                        if landmarks:
                            posture = posture_analyzer.analyze(
                                person["track_id"], landmarks, current_time, person["bbox"]
                            )
                            posture_states[person["track_id"]] = posture

                    # Cleanup stale posture history
                    active_ids = {p["track_id"] for p in tracked}
                    posture_analyzer.cleanup_stale(active_ids)

                    # 4. Alert processing
                    fired = alert_manager.process_frame(
                        tracked, phone_dets, posture_states, frame, utils
                    )

                    # Cache results
                    last_tracks = tracked
                    last_phone_dets = phone_dets
                    last_posture_states = posture_states
                    last_landmarks_map = landmarks_map

                frame_idx += 1

                # ── Draw detections (use cached results) ──────────────
                for track in last_tracks:
                    tid = track["track_id"]
                    posture = last_posture_states.get(tid)

                    is_fall = posture and posture.is_fall
                    is_sleeping = posture and posture.is_sleeping
                    is_inactive = posture and posture.is_inactive

                    if is_fall:
                        box_color = config.COLOR_FALL
                    elif is_sleeping:
                        box_color = config.COLOR_SLOUCH
                    elif is_inactive:
                        box_color = config.COLOR_INACTIVITY
                    else:
                        box_color = config.COLOR_PERSON

                    utils.draw_bounding_box(
                        frame, track["bbox"], f"Person #{tid}", box_color
                    )

                    landmarks = last_landmarks_map.get(tid)
                    if landmarks:
                        utils.draw_pose_skeleton(frame, landmarks)

                    if posture:
                        utils.draw_posture_label(
                            frame, track["bbox"],
                            posture.posture_label, posture
                        )

                for phone in last_phone_dets:
                    utils.draw_bounding_box(
                        frame, phone["bbox_xyxy"], "Phone", config.COLOR_PHONE
                    )

            elif _ai["loading"]:
                cv2.putText(frame, "Loading AI models...", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
            else:
                cv2.putText(frame, "Click START DETECTION", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

        _draw_status_banner(frame, detection_on, source_name, False)
        utils.draw_restricted_zones(frame)
        utils.draw_alert_overlay(frame, [a["msg"] for a in fired])
        if detection_on:
            utils.draw_detection_legend(frame)
        utils.draw_fps(frame, fps)

        last_frame_cache = frame.copy()
        jpeg = _encode_frame(frame)
        if jpeg:
            _publish_frame(jpeg, fps, fired)

        if source_type == "file":
            delay = 1.0 / file_fps
            if detection_on and _ai["ready"]:
                delay = max(delay * 0.5, 0.02)
            time.sleep(delay)
        elif not detection_on:
            time.sleep(0.01)

    # Cleanup
    if cap is not None:
        cap.release()
    if _ai.get("pose_estimator"):
        _ai["pose_estimator"].close()


def start_vision_thread():
    global _running
    _running = False
    time.sleep(0.2)
    t = threading.Thread(target=run_vision_loop, daemon=True)
    t.start()
    return t
