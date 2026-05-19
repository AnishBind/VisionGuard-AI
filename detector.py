import config


class ObjectDetector:
    def __init__(self):
        import torch
        from ultralytics import YOLO

        if config.USE_GPU and torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"

        self.model = YOLO(config.YOLO_MODEL)
        # Warm-up so first live frame is not delayed
        import numpy as np

        dummy = np.zeros((config.STREAM_HEIGHT, config.STREAM_WIDTH, 3), dtype=np.uint8)
        self.model.predict(
            dummy,
            imgsz=config.YOLO_IMGSZ,
            device=self.device,
            verbose=False,
        )

    def detect(self, frame):
        min_conf = min(config.CONFIDENCE_THRESHOLD, config.PHONE_CONFIDENCE_THRESHOLD)
        results = self.model.predict(
            frame,
            conf=min_conf,
            iou=config.IOU_THRESHOLD,
            imgsz=config.YOLO_IMGSZ,
            device=self.device,
            verbose=False,
        )
        boxes = results[0].boxes
        detections = []

        if boxes is None:
            return detections

        for box in boxes:
            class_id = int(box.cls[0])
            if class_id not in config.TARGET_CLASSES:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0])
            label = config.TARGET_CLASSES[class_id]
            if label == "cell phone":
                if confidence < config.PHONE_CONFIDENCE_THRESHOLD:
                    continue
            elif confidence < config.CONFIDENCE_THRESHOLD:
                continue

            w = x2 - x1
            h = y2 - y1

            detections.append(
                {
                    "bbox_xyxy": [x1, y1, x2, y2],
                    "bbox_xywh": [x1, y1, w, h],
                    "label": label,
                    "conf": confidence,
                    "class_id": class_id,
                }
            )

        return detections

    def split_by_class(self, detections):
        persons = [d for d in detections if d["label"] == "person"]
        phones = [d for d in detections if d["label"] == "cell phone"]
        return persons, phones
