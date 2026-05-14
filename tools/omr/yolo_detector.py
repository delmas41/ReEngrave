"""YOLOv8 symbol detector — Phase 3 MVP wrapper.

Wraps an Ultralytics YOLO model so it produces `SymbolDetection` objects
compatible with the existing template-matcher scoring infrastructure.

This is an MVP — minimum viable detector. The intent is to get YOLO
producing detections in the SAME shape the template matcher produces, so
the existing `tools/omr/annotate/score.py` can directly compare them.

Weights:
    - DeepScoresV2-pretrained YOLOv8 weights are NOT publicly available
      as of Phase 3 (verified by searching huggingface.co for "deepscores"
      and "yolo music" — no music-symbol-trained YOLOv8 weights found).
    - Falling back to plain COCO-pretrained `yolov8m.pt` weights. These
      were trained on 80 generic object categories (person, car, donut,
      frisbee, etc.) and will NOT detect music symbols correctly. The
      point of using them in this MVP is to exercise the wrapper code
      end-to-end so that swapping in domain-trained weights later (when
      acquired or trained on DeepScoresV2) requires only a weights-path
      change, not a code change.

Public:
    YoloDetector(weights_path).detect(cell, conf_threshold=...) -> list[SymbolDetection]

When `category` cannot be inferred from the model's class names, the
detector emits `category="unknown"` and puts the raw YOLO class label in
`smufl_name`. The scorer treats unknown-category detections as
non-noteheads (no pitch resolution).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from .template_matcher import SymbolDetection
from .types import MeasureCell


# ---------------------------------------------------------------------------
# YOLO class name → SMuFL category mapping
# ---------------------------------------------------------------------------
#
# This is a best-effort mapping for DeepScoresV2-style class names. If a
# class name does not match anything here, the detector falls back to
# category="unknown" and puts the raw class name in `smufl_name`. The
# mapping is intentionally permissive — it tries multiple casings and
# common suffix variants.

_CATEGORY_MAP = {
    # noteheads
    "noteheadblack": "notehead",
    "noteheadhalf": "notehead",
    "noteheadwhole": "notehead",
    "noteheaddoublewhole": "notehead",
    "notehead": "notehead",
    # rests
    "restwhole": "rest",
    "resthalf": "rest",
    "restquarter": "rest",
    "rest8th": "rest",
    "rest16th": "rest",
    "rest32nd": "rest",
    "rest64th": "rest",
    "rest128th": "rest",
    "rest": "rest",
    # accidentals
    "accidentalsharp": "accidental",
    "accidentalflat": "accidental",
    "accidentalnatural": "accidental",
    "accidentaldoublesharp": "accidental",
    "accidentaldoubleflat": "accidental",
    "sharp": "accidental",
    "flat": "accidental",
    "natural": "accidental",
    # clefs
    "gclef": "clef",
    "fclef": "clef",
    "cclef": "clef",
    "clef": "clef",
    # flags
    "flag8thup": "flag",
    "flag8thdown": "flag",
    "flag16thup": "flag",
    "flag16thdown": "flag",
    "flag": "flag",
    # time-sig digits
    "timesig0": "time_sig_digit",
    "timesig1": "time_sig_digit",
    "timesig2": "time_sig_digit",
    "timesig3": "time_sig_digit",
    "timesig4": "time_sig_digit",
    "timesig5": "time_sig_digit",
    "timesig6": "time_sig_digit",
    "timesig7": "time_sig_digit",
    "timesig8": "time_sig_digit",
    "timesig9": "time_sig_digit",
    "timesigcommon": "time_sig_digit",
    "timesigcuttime": "time_sig_digit",
    # barlines
    "barline": "barline",
    "barlinesingle": "barline",
    "barlinedouble": "barline",
    "barlinefinal": "barline",
    "barlineheavy": "barline",
    # stems
    "stem": "stem",
}


def _class_name_to_category(name: str) -> str:
    """Map a YOLO class name to a SMuFL category. Falls back to 'unknown'."""
    key = "".join(ch for ch in name.lower() if ch.isalnum())
    if key in _CATEGORY_MAP:
        return _CATEGORY_MAP[key]
    # Substring fallback — DeepScoresV2 names tend to be compound
    # ("noteheadBlackOnLine") so try a contains match on the bases.
    for k, cat in _CATEGORY_MAP.items():
        if k in key:
            return cat
    return "unknown"


# ---------------------------------------------------------------------------
# Detector wrapper
# ---------------------------------------------------------------------------


class YoloDetector:
    """Ultralytics YOLO wrapped to produce SymbolDetection objects.

    Lazy-loads the model on first detect() call to keep import-time cheap.
    """

    def __init__(self, weights_path: str | Path, device: str = "auto"):
        self.weights_path = str(weights_path)
        self.device = device
        self._model = None
        self._class_names: dict[int, str] | None = None

    # --------------- model lifecycle ---------------

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        # Import here so users without ultralytics installed can still
        # import this module.
        from ultralytics import YOLO  # type: ignore
        self._model = YOLO(self.weights_path)
        names = getattr(self._model, "names", None)
        if isinstance(names, dict):
            self._class_names = {int(k): str(v) for k, v in names.items()}
        elif isinstance(names, list):
            self._class_names = {i: str(v) for i, v in enumerate(names)}
        else:
            self._class_names = {}

    # --------------- inference ---------------

    def detect(
        self,
        cell: MeasureCell,
        conf_threshold: float = 0.25,
        imgsz: int = 640,
    ) -> list[SymbolDetection]:
        """Run YOLO on `cell.image` and return SymbolDetection objects in
        canonical-image coordinates.

        Uses `cell.image` (the original, with staff lines intact) — YOLO is
        trained on full notation, not on staff-removed images.
        """
        self._ensure_loaded()
        assert self._model is not None

        img = cell.image
        if img is None:
            return []
        # YOLO expects 3-channel RGB. Cell image may be grayscale.
        if img.ndim == 2:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            # cv2 reads BGR; YOLO accepts BGR fine, but normalize for safety.
            img_rgb = img if img.shape[2] == 3 else cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)

        # MPS device hint on Apple Silicon; "auto" lets ultralytics pick.
        results = self._model.predict(
            source=img_rgb,
            conf=conf_threshold,
            imgsz=imgsz,
            device=self.device if self.device != "auto" else None,
            verbose=False,
        )
        if not results:
            return []
        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return []

        # Each box: xyxy, conf, cls
        xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes.xyxy, "cpu") else np.asarray(boxes.xyxy)
        confs = boxes.conf.cpu().numpy() if hasattr(boxes.conf, "cpu") else np.asarray(boxes.conf)
        clses = boxes.cls.cpu().numpy() if hasattr(boxes.cls, "cpu") else np.asarray(boxes.cls)

        detections: list[SymbolDetection] = []
        for (x0, y0, x1, y1), conf, cls in zip(xyxy, confs, clses):
            x = int(round(float(x0)))
            y = int(round(float(y0)))
            w = max(1, int(round(float(x1) - float(x0))))
            h = max(1, int(round(float(y1) - float(y0))))
            class_id = int(cls)
            class_name = (self._class_names or {}).get(class_id, f"cls_{class_id}")
            category = _class_name_to_category(class_name)
            # If category is unknown (e.g. COCO classes like "donut"),
            # we still emit the detection so the scorer can see it — the
            # raw class label goes in `smufl_name`.
            smufl_name = class_name if category != "unknown" else class_name
            detections.append(SymbolDetection(
                cell=cell,
                smufl_name=smufl_name,
                category=category,
                x_canonical=x,
                y_canonical=y,
                width_canonical=w,
                height_canonical=h,
                confidence=float(conf),
                pitch=None,
            ))
        return detections

    # --------------- diagnostics ---------------

    def time_detect(
        self,
        cell: MeasureCell,
        conf_threshold: float = 0.25,
        n_runs: int = 5,
    ) -> dict:
        """Run detect() N times and return timing stats. Skips the first
        run (warmup) when N >= 2."""
        runs: list[float] = []
        first: list[SymbolDetection] | None = None
        for i in range(n_runs):
            t0 = time.perf_counter()
            dets = self.detect(cell, conf_threshold=conf_threshold)
            t1 = time.perf_counter()
            if first is None:
                first = dets
            runs.append(t1 - t0)
        timed = runs[1:] if len(runs) >= 2 else runs
        return {
            "n_runs": n_runs,
            "n_detections": len(first or []),
            "all_times_s": runs,
            "median_s_excluding_warmup": float(np.median(timed)) if timed else None,
            "mean_s_excluding_warmup": float(np.mean(timed)) if timed else None,
        }
