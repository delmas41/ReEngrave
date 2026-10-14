"""ROADMAP 2.114 -- the SECOND DETECTOR at GATHER, for hollow noteheads ONLY. STAGED path; LEGACY never reads any of this.

Helpers only (no `Log` writes): the flag, the class list, a wrapper that keeps nothing but hollow heads, and the pure matching of
the second detector's boxes against production's. `gather.gather_second_hollow` is the GATHER reader that files the rows;
`adjudicators/rhythm.py` (`_second_hollow_settle`, in `adjudicate_duration`) is the ADJUDICATE half.

CONVENTION ASSUMED: production's boxes are the truth about every class; a hollow-tuned fine-tune (2.110's OLD arm: 88% vs 74% hollow
recall on the 95 clean Litolff TEST cells, but it deletes beams / ledgers / ties) is a WITNESS for hollow heads alone, so nothing it
says about any other class is read, and none of its boxes is merged into or overwrites a production box.
WHAT WOULD FALSIFY IT: a filled head the second detector calls hollow that the head's own ink (Sean's interior-white rule) cannot
refute; or any non-hollow class from this model reaching the record.
NOT CONFIRMED: the 2.88 interior cut-offs on any publisher but Litolff.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ENV = "OMR_SECOND_HOLLOW_DETECTOR"

#: The 2.110 OLD arm (`omr-weights/candidates/`, gitignored, machine-local). The flag's weights; no second knob.
DEFAULT_WEIGHTS = "omr-weights/candidates/scale2110-OLD896-raw-2026-10-13.pt"

#: The ONLY classes kept from the second detector, spelled as `yolo_detector` spells them after `class_aliases` (the model's
#: 208-class vocabulary). Hollow heads of regular size: half and whole, on a line and in a space, plus the bare `noteheadWhole`
#: alias. NOT kept, on purpose: the `...Small` (cue / grace) heads, double whole, every black head, and every non-head class.
HOLLOW_CLASSES = frozenset({
    "noteheadHalfOnLine", "noteheadHalfInSpace",
    "noteheadWholeOnLine", "noteheadWholeInSpace", "noteheadWhole",
})

#: Two boxes are the same head at or above this overlap (IoU, canonical frame) -- the cut `readout.match_glyphs` and the 2.110
#: scorers use. A convention of the scorer, not a measurement of heads.
SAME_HEAD_IOU = 0.3
#: Two boxes of the SECOND detector this close are one head boxed twice (Half and Whole classes are not suppressed across classes).
DUPLICATE_IOU = 0.5


def enabled() -> bool:
    """DEFAULT OFF; an allow-list, as `docs/measuring.md` requires of a default-OFF flag."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def is_hollow_class(name: Any) -> bool:
    return str(name) in HOLLOW_CLASSES


def is_hollow_family(name: Any) -> bool:
    """Production's own class says hollow (a half or whole of any spelling)."""
    s = str(name)
    return s.startswith("noteheadHalf") or s.startswith("noteheadWhole")


def box(d: Any) -> Tuple[float, float, float, float]:
    return (float(d.x_canonical), float(d.y_canonical), float(d.width_canonical), float(d.height_canonical))


def iou(a: Sequence[float], b: Sequence[float]) -> float:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    ix = max(0.0, min(ax0 + aw, bx0 + bw) - max(ax0, bx0))
    iy = max(0.0, min(ay0 + ah, by0 + bh) - max(ay0, by0))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def keep_hollow(dets: Sequence[Any]) -> List[Any]:
    """Only the hollow-head boxes, one per head: a duplicate (IoU >= `DUPLICATE_IOU`) keeps the higher confidence."""
    kept: List[Any] = []
    for d in sorted((d for d in dets if is_hollow_class(d.smufl_name)), key=lambda d: -float(d.confidence)):
        if all(iou(box(d), box(k)) < DUPLICATE_IOU for k in kept):
            kept.append(d)
    return kept


class SecondHollowDetector:
    """A `YoloDetector` on the second weights whose `detect` returns ONLY hollow-head boxes. Same call shape as `YoloDetector.detect`,
    so GATHER hands it the same cell, conf and (None -> per-cell) imgsz production got."""

    def __init__(self, weights_path: Any = None, *, inner: Any = None):
        self.weights_path = str(weights_path) if weights_path else None
        self._inner = inner

    def _detector(self) -> Any:
        if self._inner is None:
            from ..yolo_detector import YoloDetector
            self._inner = YoloDetector(self.weights_path)
        return self._inner

    def detect(self, cell: Any, conf_threshold: float = 0.25, imgsz: Optional[int] = None, **kw: Any) -> List[Any]:
        return keep_hollow(self._detector().detect(cell, conf_threshold=conf_threshold, imgsz=imgsz, **kw))


def default_weights_path() -> Optional[Path]:
    """`DEFAULT_WEIGHTS` under the repo root, else under the working directory (a worktree reaches `omr-weights` through a symlink)."""
    here = Path(__file__).resolve()
    for root in (here.parents[3], Path.cwd()):
        p = root / DEFAULT_WEIGHTS
        if p.exists():
            return p
    return None


def default_detector() -> Optional[SecondHollowDetector]:
    p = default_weights_path()
    return SecondHollowDetector(p) if p is not None else None


def plan_cell(production: Sequence[Any], second: Sequence[Any]) -> Dict[str, Any]:
    """Match the (already hollow-only) second boxes against production's boxes of one cell.

    Returns `{"on_head": [(prod_index, second_det, iou)], "second_only": [second_det], "over_other": [(prod_index, second_det, iou)]}`:
      * `on_head`    -- the second box overlaps a production NOTEHEAD box (IoU >= `SAME_HEAD_IOU`); the best-overlapping head wins.
                       Agreement (production hollow too) and disagreement (production black) both land here; ADJUDICATE tells
                       them apart by production's own class.
      * `over_other` -- the second box overlaps a production box of ANOTHER class (a time-signature digit, a rest, a clef ...):
                       production SAW something there, so this is not a head it missed; not added, only reported.
      * `second_only`-- no production box of any class at IoU >= `SAME_HEAD_IOU`: a head production did not see.
    """
    out: Dict[str, Any] = {"on_head": [], "second_only": [], "over_other": []}
    pboxes = [box(p) for p in production]
    for s in second:
        sb = box(s)
        best_head = best_other = None
        for i, (p, pb) in enumerate(zip(production, pboxes)):
            v = iou(sb, pb)
            if v < SAME_HEAD_IOU:
                continue
            if str(p.smufl_name).startswith("notehead"):
                if best_head is None or v > best_head[2]:
                    best_head = (i, s, v)
            elif best_other is None or v > best_other[2]:
                best_other = (i, s, v)
        if best_head is not None:
            out["on_head"].append(best_head)
        elif best_other is not None:
            out["over_other"].append(best_other)
        else:
            out["second_only"].append(s)
    return out
