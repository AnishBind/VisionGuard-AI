"""
Lightweight centroid-based object tracker.

Replaces DeepSORT for simple multi-person tracking without any heavy
deep-learning dependencies.  Suitable for edge-AI / CPU-only deployments
where the scene typically contains fewer than ~10 people.

Algorithm:
    1. Compute centroids of incoming bounding boxes.
    2. Match them to existing tracked objects using greedy nearest-neighbor.
    3. Register new objects, deregister objects that have been missing for
       too many consecutive frames.
"""

import math


class CentroidTracker:
    """Assign persistent integer IDs to detected bounding boxes across frames."""

    def __init__(self, max_disappeared=30, max_distance=80):
        """
        Parameters
        ----------
        max_disappeared : int
            Number of consecutive frames an object can be missing before its
            ID is dropped.
        max_distance : float
            Maximum Euclidean distance (pixels) between a new centroid and an
            existing one for them to be considered the same object.
        """
        self._next_id = 1
        self._objects = {}        # id → (cx, cy)
        self._bboxes = {}         # id → [x1, y1, x2, y2]
        self._disappeared = {}    # id → count of consecutive missing frames
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def update(self, bboxes):
        """
        Accept a list of bounding boxes ``[[x1, y1, x2, y2], ...]`` and return
        a list of tracked-person dicts::

            [{"track_id": int, "bbox": [x1,y1,x2,y2], "centroid": (cx,cy)}, ...]

        The returned list only contains objects that are *currently visible*
        (i.e., matched to a detection in this frame).
        """
        if not bboxes:
            # Mark every existing object as disappeared
            self._mark_all_disappeared()
            return []

        new_centroids = []
        for box in bboxes:
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0
            new_centroids.append((cx, cy))

        # If we have no existing objects, register everything
        if not self._objects:
            for i, box in enumerate(bboxes):
                self._register(new_centroids[i], list(box))
            return self._visible_output()

        # ---- Greedy nearest-neighbor matching ----
        existing_ids = list(self._objects.keys())
        existing_centroids = [self._objects[oid] for oid in existing_ids]

        # Build distance matrix (existing × new)
        used_existing = set()
        used_new = set()
        matches = []  # (existing_idx, new_idx, distance)

        for ei, ec in enumerate(existing_centroids):
            for ni, nc in enumerate(new_centroids):
                d = math.hypot(ec[0] - nc[0], ec[1] - nc[1])
                matches.append((ei, ni, d))

        # Sort by distance – assign closest pairs first
        matches.sort(key=lambda m: m[2])

        matched_existing = set()
        matched_new = set()

        for ei, ni, d in matches:
            if ei in matched_existing or ni in matched_new:
                continue
            if d > self.max_distance:
                continue
            oid = existing_ids[ei]
            self._objects[oid] = new_centroids[ni]
            self._bboxes[oid] = list(bboxes[ni])
            self._disappeared[oid] = 0
            matched_existing.add(ei)
            matched_new.add(ni)

        # Handle unmatched existing objects → disappeared
        for ei in range(len(existing_ids)):
            if ei not in matched_existing:
                oid = existing_ids[ei]
                self._disappeared[oid] += 1
                if self._disappeared[oid] > self.max_disappeared:
                    self._deregister(oid)

        # Handle unmatched new detections → register
        for ni in range(len(new_centroids)):
            if ni not in matched_new:
                self._register(new_centroids[ni], list(bboxes[ni]))

        return self._visible_output()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _register(self, centroid, bbox):
        oid = self._next_id
        self._objects[oid] = centroid
        self._bboxes[oid] = bbox
        self._disappeared[oid] = 0
        self._next_id += 1

    def _deregister(self, oid):
        self._objects.pop(oid, None)
        self._bboxes.pop(oid, None)
        self._disappeared.pop(oid, None)

    def _mark_all_disappeared(self):
        for oid in list(self._objects.keys()):
            self._disappeared[oid] += 1
            if self._disappeared[oid] > self.max_disappeared:
                self._deregister(oid)

    def _visible_output(self):
        """Return only currently-visible (disappeared == 0) objects."""
        result = []
        for oid, centroid in self._objects.items():
            if self._disappeared[oid] == 0:
                result.append(
                    {
                        "track_id": oid,
                        "bbox": self._bboxes[oid],
                        "centroid": centroid,
                    }
                )
        return result
