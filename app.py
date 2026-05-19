import os
import threading
import time
import webbrowser

from flask import Flask, Response, jsonify, render_template, request
from werkzeug.utils import secure_filename

import config
import vision_thread

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
            frame = vision_thread.get_latest_frame()
            if frame is None:
                time.sleep(0.02)
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
            time.sleep(0.02)

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/alerts")
def alerts():
    return jsonify({
        "alerts": vision_thread.get_alert_history(),
        "fps": round(vision_thread.get_fps(), 1),
        **vision_thread.get_status(),
    })


@app.route("/status")
def status():
    s = vision_thread.get_status()
    s["alert_count"] = len(vision_thread.get_alert_history())
    s["model"] = config.YOLO_MODEL
    s["target_fps"] = config.TARGET_FPS
    return jsonify(s)


@app.route("/api/detection/start", methods=["POST"])
def detection_start():
    vision_thread.set_detection_enabled(True)
    return jsonify({"ok": True, "detection_enabled": True})


@app.route("/api/detection/stop", methods=["POST"])
def detection_stop():
    vision_thread.set_detection_enabled(False)
    return jsonify({"ok": True, "detection_enabled": False})


@app.route("/api/source/webcam", methods=["POST"])
def source_webcam():
    idx = request.json.get("index", 0) if request.is_json else 0
    vision_thread.set_webcam(idx)
    return jsonify({"ok": True, "source": "webcam"})


@app.route("/api/upload", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400

    f = request.files["video"]
    if not f.filename:
        return jsonify({"ok": False, "error": "Empty filename"}), 400

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in config.ALLOWED_VIDEO_EXT:
        return jsonify({"ok": False, "error": f"Use: {', '.join(config.ALLOWED_VIDEO_EXT)}"}), 400

    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    safe = secure_filename(f.filename)
    path = os.path.join(config.UPLOAD_DIR, safe)
    f.save(path)

    vision_thread.set_video_file(os.path.abspath(path), safe)
    vision_thread.set_detection_enabled(True)

    return jsonify({"ok": True, "filename": safe, "path": path})


@app.route("/api/playback/pause", methods=["POST"])
def playback_pause():
    vision_thread.pause_playback()
    return jsonify({"ok": True, "paused": True})


@app.route("/api/playback/resume", methods=["POST"])
def playback_resume():
    vision_thread.resume_playback()
    return jsonify({"ok": True, "paused": False})


@app.route("/api/playback/restart", methods=["POST"])
def playback_restart():
    vision_thread.restart_video()
    return jsonify({"ok": True})


@app.route("/api/playback/seek", methods=["POST"])
def playback_seek():
    data = request.get_json(silent=True) or {}
    if "frame" in data:
        vision_thread.seek_to_frame(data["frame"])
    elif "percent" in data:
        vision_thread.seek_percent(data["percent"])
    else:
        return jsonify({"ok": False, "error": "Send frame or percent"}), 400
    return jsonify({"ok": True})


@app.route("/api/alerts/clear", methods=["POST"])
def alerts_clear():
    vision_thread.clear_alerts()
    return jsonify({"ok": True})


if __name__ == "__main__":
    os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
    os.makedirs(config.LOG_DIR, exist_ok=True)
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)

    placeholder = vision_thread._placeholder_frame("Starting VisionGuard AI...")
    if placeholder:
        with vision_thread._lock:
            vision_thread._latest_frame = placeholder

    vision_thread.start_vision_thread()

    url = f"http://127.0.0.1:{config.FLASK_PORT}"
    print()
    print("=" * 50)
    print("  VisionGuard AI is running")
    print(f"  Browser: {url}")
    print("  Double-click START_VisionGuard.bat next time")
    print("=" * 50)
    print()

    if config.OPEN_BROWSER_ON_START:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
        threaded=True,
        use_reloader=False,
    )
