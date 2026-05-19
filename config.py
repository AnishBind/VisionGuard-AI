# ── Video Source ──────────────────────────────────────────────────────────────
SOURCE = 0

import sys

CAMERA_BACKEND = getattr(__import__("cv2"), "CAP_DSHOW", None) if sys.platform == "win32" else None

# ── Uploads ───────────────────────────────────────────────────────────────────
UPLOAD_DIR = "uploads"
ALLOWED_VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_UPLOAD_MB = 500
VIDEO_LOOP = True

# ── Model ─────────────────────────────────────────────────────────────────────
YOLO_MODEL = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.45
PHONE_CONFIDENCE_THRESHOLD = 0.29      # balanced threshold for tilted phones with fewer false positives
IOU_THRESHOLD = 0.5

TARGET_CLASSES = {
    0: "person",
    67: "cell phone",
}

# ── Centroid Tracker ──────────────────────────────────────────────────────────
TRACKER_MAX_DISAPPEARED = 30   # frames before dropping a tracked ID
TRACKER_MAX_DISTANCE = 80      # max pixel distance for centroid matching

# ── Pose Estimation (MediaPipe Tasks API, v0.10+) ─────────────────────────────
POSE_MODEL_COMPLEXITY = 0              # 0=lite, 1=full, 2=heavy (0 is fastest)
POSE_MODEL_DIR = "models"              # pose_landmarker_*.task files (auto-downloaded)
POSE_MIN_DETECTION_CONF = 0.5
POSE_MIN_TRACKING_CONF = 0.5
POSE_LANDMARK_VISIBILITY_THRESH = 0.5  # ignore landmarks below this confidence
POSE_MAX_PERSONS = 3                   # max persons to run pose on per frame

# ── Fall Detection (Pose-based) ───────────────────────────────────────────────
# v2: sustained "fall" from torso angle also requires hip→foot segment to be mostly
# horizontal (typical of lying on ground), not vertical (standing / crouch).
# Sudden collapse still uses head-drop (see posture_analyzer).
FALL_TORSO_ANGLE_THRESHOLD = 55    # degrees from vertical -> likely horizontal/fallen
FALL_CONFIRM_FRAMES = 3            # consecutive detection cycles to confirm fall
FALL_HEAD_DROP_THRESHOLD = 0.15    # normalised y-velocity per second for sudden collapse
FALL_HEAD_DROP_FRAMES = 3          # frames of rapid head drop to confirm

# v2 geometry: abs(dy)/length along hip→mid-foot; standing legs ≈ 1, prone ≈ low
FALL_V2_MAX_HIP_FOOT_VERTICALITY = 0.38
FALL_V2_MIN_LEG_SEGMENT_PX = 12.0  # ignore tiny segments (noise / far limbs)

# If True, torso-horizontal fall counter only advances when v2 geometry passes.
# If False, missing leg landmarks fall back to legacy torso-only counting.
FALL_V2_STRICT_LANDMARKS = True

# Legacy bbox heuristic (width > height); kept for A/B only — default off
USE_LEGACY_BBOX_FALL = True
LEGACY_BBOX_FALL_WH_RATIO = 1.25
LEGACY_BBOX_FALL_MIN_TORSO_ANGLE = 45

# ── Inactivity Detection ──────────────────────────────────────────────────────
INACTIVITY_MOVEMENT_THRESHOLD = 0.005  # normalised avg landmark displacement
INACTIVITY_DURATION_SECONDS = 600      # 10 minutes of stillness before alert
STANDING_INACTIVITY_SECONDS = 600      # 10 minutes standing continuously before alert

# ── Slouch / Sleeping Detection ───────────────────────────────────────────────
SLOUCH_TORSO_ANGLE_MIN = 30        # min torso angle for slouch
SLOUCH_HEAD_BELOW_SHOULDERS = True # require head below shoulder line
SLOUCH_DURATION_SECONDS = 10       # seconds of slouch + inactivity → sleeping alert

# ── Phone Detection ────────────────────────────────────────────────────────────
PHONE_OVERLAP_IOU_THRESHOLD = 0.01
PHONE_PERSON_MARGIN_RATIO = 0.10       # associate phones slightly outside person bbox

# ── Alert Cooldown ────────────────────────────────────────────────────────────
ALERT_COOLDOWN_SECONDS = 5.0

# ── Restricted Zone ───────────────────────────────────────────────────────────
RESTRICTED_ZONES = []

# ── Output ────────────────────────────────────────────────────────────────────
SCREENSHOT_DIR = "screenshots"
LOG_DIR = "logs"
LOG_FILE = "logs/event_log.txt"
SCREENSHOT_ON_ALERT = True
MAX_ALERT_HISTORY = 50

# ── Flask Server ──────────────────────────────────────────────────────────────
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = False
OPEN_BROWSER_ON_START = True

# ── Video Stream (lower = faster FPS) ─────────────────────────────────────────
TARGET_FPS = 30
STREAM_JPEG_QUALITY = 80
STREAM_WIDTH = 640
STREAM_HEIGHT = 360

# ── Real-time performance ─────────────────────────────────────────────────────
DETECT_EVERY_N = 2
YOLO_IMGSZ = 416
CAP_BUFFER_SIZE = 1
USE_GPU = True

# ── Display Colors (BGR) ──────────────────────────────────────────────────────
COLOR_PERSON = (0, 255, 0)
COLOR_PHONE = (0, 165, 255)
COLOR_FALL = (0, 0, 255)
COLOR_ZONE = (0, 0, 200)
COLOR_ALERT_TEXT = (0, 0, 255)
COLOR_FPS = (255, 255, 255)
COLOR_SKELETON = (255, 200, 0)
COLOR_LANDMARK = (0, 255, 255)
COLOR_INACTIVITY = (255, 165, 0)
COLOR_SLOUCH = (180, 0, 180)

# ── Sound ─────────────────────────────────────────────────────────────────────
ENABLE_ALERT_SOUND = True
