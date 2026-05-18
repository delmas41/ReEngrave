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
# Data-driven expansion (2026-05-15): the original map covered only ~50 of
# DeepScoresV2's ~147 classes, which left ~37% of detections (342/916 on
# our 30 verdict cells) flagged as `unknown`. Counting class-label
# frequencies across `benchmarks/omr-phase3/r2/detections/*.json` showed
# that almost all the "unknown" mass came from a small set of recurring
# names: `beam` (202), `staff` (38), `dynamicF` (38), `tie` (17),
# `slur` (15), `augmentationDot` (10), `dynamicP` (5), `articStaccatoAbove`
# (5), `coda` (4), `articAccentBelow` (2), `arpeggiato` (2), `dynamicZ`,
# `segno`, `ornamentTurnInverted`, `ornamentMordent`. Cross-referenced
# against `tools/omr/training/deepscores_classes.py` so that the prefix
# rules (e.g. `dynamic` → dynamic, `ornament` → ornament, `artic` →
# ornament) also catch the long tail of unseen-but-related variants.
#
# Three new top-level categories were added: `structural` (beam, staff,
# tie, slur, augmentationDot, ledger lines, brackets, repeat/coda/segno
# markers), `dynamic` (any dynamicX), and `ornament` (ornament*,
# articulation marks, grace notes, fermata, tremolo, arpeggiato,
# caesura). If a class name still does not match anything here, the
# detector falls back to `category="unknown"` and puts the raw class name
# in `smufl_name`.
#
# Ordering matters: the substring fallback in `_class_name_to_category`
# iterates `_CATEGORY_MAP` in insertion order and returns the first match.
# Long/specific keys go first so that e.g. `graceNote...StemUp` matches
# `gracenote` (→ ornament) before it can match `stem`.

_CATEGORY_MAP = {
    # ---- specific compound names first (substring fallback order matters) ----
    # ornaments / grace notes / articulations (must precede the short
    # `stem` key, since gracenote names contain "stem")
    "gracenote": "ornament",
    "ornament": "ornament",
    "arpeggiato": "ornament",
    "fermata": "ornament",
    "tremolo": "ornament",
    "caesura": "ornament",
    "artic": "ornament",
    "augmentationdot": "structural",
    # dynamics — `dynamic` substring catches dynamicP/M/F/S/Z/R, hairpins, etc.
    "dynamic": "dynamic",
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
    # accidentals (incl. key-signature variants via `keyflat`/`keysharp`/`keynatural`)
    "accidentalsharp": "accidental",
    "accidentalflat": "accidental",
    "accidentalnatural": "accidental",
    "accidentaldoublesharp": "accidental",
    "accidentaldoubleflat": "accidental",
    "keyflat": "accidental",
    "keysharp": "accidental",
    "keynatural": "accidental",
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
    "timesigcutcommon": "time_sig_digit",
    "tuplet": "structural",  # tuplet0-9 (digits painted on tuplet brackets)
    "fingering": "ornament",  # fingering0-5 (small annotation marks)
    "strings": "ornament",  # stringsUpBow, stringsDownBow (bowing direction)
    "keyboardpedal": "ornament",  # keyboardPedalPed, keyboardPedalUp
    # barlines
    "barline": "barline",
    "barlinesingle": "barline",
    "barlinedouble": "barline",
    "barlinefinal": "barline",
    "barlineheavy": "barline",
    # structural / non-symbol marks (beams, staff lines, ties, slurs,
    # navigation marks, brackets, ledger lines)
    "beam": "structural",
    "staff": "structural",
    "tie": "structural",
    "slur": "structural",
    "ledgerline": "structural",
    "brace": "structural",
    "coda": "structural",
    "segno": "structural",
    "repeatdot": "structural",
    "tupletbracket": "structural",
    "ottavabracket": "structural",
    # stems (kept as its own category for backward compatibility — see
    # gracenote ordering note above)
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
        iou_threshold: float = 0.7,
        agnostic_nms: bool = False,
    ) -> list[SymbolDetection]:
        """Run YOLO on `cell.image` and return SymbolDetection objects in
        canonical-image coordinates.

        Uses `cell.image` (the original, with staff lines intact) — YOLO is
        trained on full notation, not on staff-removed images.

        Args:
            conf_threshold: minimum detection confidence (0-1).
            imgsz: inference image size.
            iou_threshold: NMS IoU threshold. Lower = more aggressive
                suppression of overlapping boxes.
            agnostic_nms: if True, NMS suppresses across classes (one box
                per region regardless of class). Useful for music notation
                where the same region can fire multiple semantically-similar
                class predictions (e.g., `dynamicF` + `dynamicFF` on one
                `ff` mark).
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
            iou=iou_threshold,
            agnostic_nms=agnostic_nms,
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
