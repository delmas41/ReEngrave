"""Shared matching/truth logic for the rest-specialist-collapse experiment
(benchmarks/omr-labeling-survey-2026-09/REST_SPECIALIST_EXPERIMENT.md).

Reuses UNBOXED-AUDIT.md's per-instance matcher (probe_spec_residual_matched.py)
rather than reinventing it, because that matcher's numbers are what motivated
this whole experiment (41% naive -> 38% matched -> ~19% genuine for rests) and
a second, different matcher would make the two documents incomparable.

Exports:
    load_full_labels(cid, root_versions, names) -> [(class_name, cx, cy, w, h)]
        normalized-coordinate boxes from the FULL (unfiltered) label file for a
        cell, wherever it lives under data/user-labeled/<version>/.
    match_detections(dets, human_px, radius=0.6) -> list of MatchResult
        greedy nearest-center match, one human box used at most once (mirrors
        probe_spec_residual_matched.py exactly, radius in units of avg box
        diagonal).
    is_fp_mode_class(name) -> bool
        True for restWhole/restHBar -- the audit's documented false-positive
        mode (staff-line/slur/beam ink hallucinated as a bar rest). Any
        UNMATCHED detection of these classes is excluded from every "genuine
        addition" set in this experiment (arms B and E, and the corrected-
        truth definition used for scoring) -- never auto-added as a label,
        never counted as truth. Painting (arm C) still erases them, since a
        painted-over region does not need to be trustworthy, only ambiguous.
    genuine_addition(det, match, conf_floor=0.5) -> bool
        the criterion for "the teacher found a real rest we didn't box":
        unmatched (to ANY human class, not just the family), not an FP-mode
        class, confidence >= conf_floor. This is an AUTOMATED PROXY for what
        Sean's eyeball sample called "genuine" (UNBOXED-AUDIT.md Sec 3: 50%
        of unmatched rests were genuine, ~90-100% of restWhole/restHBar were
        not) -- it is not Sean's own adjudication of these specific instances,
        and every place that uses it says so.
"""
from __future__ import annotations

import glob
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, os.getcwd())   # so `from tools.omr...` resolves when run as a script, per probe_spec_residual_matched.py's own convention

REPO = Path.cwd()
FP_MODE_CLASSES = {"restWhole", "restHBar"}
MATCH_RADIUS = 0.6  # fraction of avg box diagonal -- probe_spec_residual_matched.py's own constant
CONF_FLOOR = 0.5    # "high confidence" for arm B / E additions and corrected-truth (see module docstring)


def load_full_labels(cid: str, root_versions: list[str], names: list[str],
                      labels_root: Path = REPO / "data" / "user-labeled"):
    """All 208-class boxes for a cell, normalized coords, searching every
    admitted version directory until one has this cell. Mirrors
    probe_spec_residual_matched.py's load_full_labels exactly."""
    for v in root_versions:
        p = labels_root / v / "labels" / f"{cid}.txt"
        if p.exists():
            out = []
            for line in p.read_text().splitlines():
                parts = line.split()
                if len(parts) != 5:
                    continue
                cls_id = int(parts[0])
                if cls_id >= len(names):
                    continue
                out.append((names[cls_id], float(parts[1]), float(parts[2]),
                            float(parts[3]), float(parts[4])))
            return out
    return []


@dataclass
class Det:
    cls: str
    conf: float
    cx: float  # pixel center x
    cy: float
    w: float
    h: float

    @property
    def bbox(self):
        return (self.cx - self.w / 2, self.cy - self.h / 2,
                self.cx + self.w / 2, self.cy + self.h / 2)


@dataclass
class MatchResult:
    det: Det
    matched_cls: str | None   # human class matched to, or None if unmatched
    dist: float | None        # normalized distance, or None if unmatched


def match_detections(dets: list[Det], human_px: list[tuple], radius: float = MATCH_RADIUS,
                      same_class: bool = False) -> list[MatchResult]:
    """human_px: list of (class_name, cx, cy, w, h) in PIXEL coords.
    Greedy nearest-center match, each human box used at most once.

    same_class=False (default): matches to the nearest human box of ANY
    class -- probe_spec_residual_matched.py's own algorithm, used where the
    question is "is this ink boxed at all, and under what class" (arm B/C's
    corpus building, the corrected-truth calculation) -- a key-signature
    confusion or an other-class match is a real, distinct outcome there, not
    noise to suppress.

    same_class=True: only matches to a human box of the SAME class -- what
    precision/recall scoring needs (eval_rest_arm.py, crop_arm_predictions.py).
    Without this, two different rest DURATIONS (restQuarter vs rest8th)
    sitting near each other would count as a match, which is wrong for a
    metric whose whole point is duration classes."""
    used = [False] * len(human_px)
    out = []
    for d in dets:
        best_i, best_dist, best_cls = -1, 1e9, None
        for i, (hcls, hx, hy, hw, hh) in enumerate(human_px):
            if used[i]:
                continue
            if same_class and hcls != d.cls:
                continue
            dist = math.hypot(d.cx - hx, d.cy - hy)
            diag = math.hypot((d.w + hw) / 2, (d.h + hh) / 2)
            norm = dist / max(diag, 1.0)
            if norm < best_dist:
                best_dist, best_i, best_cls = norm, i, hcls
        if best_i >= 0 and best_dist <= radius:
            used[best_i] = True
            out.append(MatchResult(d, best_cls, best_dist))
        else:
            out.append(MatchResult(d, None, None))
    return out


def is_fp_mode_class(name: str) -> bool:
    return name in FP_MODE_CLASSES


def genuine_addition(mr: MatchResult, conf_floor: float = CONF_FLOOR) -> bool:
    """Would this unmatched detection be added as a label in arm B / E, or
    counted as a positive in the 'corrected truth' scoring set? See module
    docstring -- this is an automated proxy, not Sean's own adjudication."""
    if mr.matched_cls is not None:
        return False
    if is_fp_mode_class(mr.det.cls):
        return False
    return mr.det.conf >= conf_floor


def run_teacher(img, ys, rest_classes: set[str], weights: str, device: str = "mps",
                 conf: float = 0.25):
    """Run the production teacher over one cell image, return Det list for the
    rest classes only. Local import so callers that only need matching/paint
    logic (no torch) stay cheap."""
    from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell

    class Ctx:
        def __init__(self, ys, image):
            self.staff_line_ys_canonical = ys
            self.image = image

    det = YoloDetector(weights, device=device)
    c = Ctx(ys, img)
    out = []
    for d in det.detect(c, conf_threshold=conf, imgsz=imgsz_for_cell(c)):
        if d.smufl_name in rest_classes:
            out.append(Det(d.smufl_name, float(d.confidence),
                            d.x_canonical + d.width_canonical / 2,
                            d.y_canonical + d.height_canonical / 2,
                            d.width_canonical, d.height_canonical))
    return out


def load_manifest_staff_lines(cid: str) -> list[float]:
    """staff_line_ys_canonical for a cell, from whichever benchmarks/**/*cells.json
    manifest has it -- same lookup probe_spec_residual_matched.py uses."""
    import glob as _glob
    import json as _json
    for m in _glob.glob("benchmarks/**/*cells.json", recursive=True):
        try:
            for e in _json.load(open(m)):
                if e.get("cell_id") == cid:
                    return e.get("staff_line_ys_canonical") or []
        except Exception:
            continue
    return []
