"""ROADMAP 2.190 -- THE ACCIDENTAL SHAPE CHECK (flag `OMR_ACCIDENTAL_SHAPE`, default ON). STAGED GATHER (the measurement, one row detail) +
ADJUDICATE (the choice among the detector's own candidates, `adjudicate_accidental_owner`). Built on 2.186 (`OMR_ONE_INK_ONE_MARK`).

THE CAUSE (benchmarks/omr-accidental-shape-2026-10/FINDINGS.md): where two accidental classes both clear the detector's floor on ONE ink, the
detector-confidence margin does not say which is right (median margin ~0.2 on both plates, wrong winners at every margin). Sean's tiles on 2.186:
every error was a NATURAL written as a sharp or a flat, or its accidental lost (a flat winner under a key that already has the flat writes nothing).

WHAT THIS IS, PLAINLY: a SECOND READER of the SAME raster the detector looked at. It is not an independent source (CLAUDE section 5: two witnesses
off one raster fall silent together); it counts as one more reading of the same ink, and it can only CHOOSE AMONG THE DETECTOR'S CANDIDATES
for that ink (rule 6: never a class the detector did not offer). Whatever it picks is written GUESSED (blue), never READ: the READ bar
`SHAPE_READ` is None until Sean sets it on tiles.

THE SHAPE, off the staff-erased raster, measured on the mark's OWN ink (relative to its own tight ink box; no staff position is used, so a tilted
staff cannot move it -- page-facts section 3 measures against the staff LOCALLY, and this reads no staff):
  * a FLAT   is ONE tall stem on the left with a closed bowl at its lower right: the stem reaches the BOTTOM of the glyph at the left, and
             nothing stands at the top right.
  * a NATURAL is two short verticals offset (left one up, right one down) joined by two slanted bars: neither the bottom left nor the top
             right of the glyph is inked (the left stem stops above the bottom, the right stem starts below the top).
  * a SHARP  is two verticals crossed by two slanted bars: BOTH the bottom left and the top right are inked.
So two windows decide: BL (bottom-left corner) and TR (top-right corner), each read as STEM STRENGTH: the best 3-column-wide vertical run of ink
in the window, as a fraction of the window's height (a stem crossing the window reads ~1, an empty corner 0, a bar or bit of noise in between). (TR absent, BL present)=flat, (absent, absent)=natural,
(present, present)=sharp, (TR present, BL absent)=nothing a printed accidental is (unclear). Each window's ink density has three zones:
clear PRESENT (>= `PRESENT_MIN`), clear ABSENT (<= `ABSENT_MAX`), and the band between, where the answer is UNCLEAR and nothing is chosen.
CUT-OFFS ARE A MEASUREMENT, NOT A CONVENTION (CLAUDE section 4): they were set by looking at crops of two plates (Litolff, Breitkopf) and Sean's 12
tiles, so they may only NARROW; the shape counts as agreeing with a candidate only when both windows are in a clear zone.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Sequence

SHAPE_ENV = "OMR_ACCIDENTAL_SHAPE"

#: Window size, as a fraction of the glyph's tight ink box: the outer 45% of the width by the outer 20% of the height (a sharp's stems stand at
#: about a quarter and three quarters of its width, so a narrower corner would miss them).
WINDOW_W = 0.45
WINDOW_H = 0.20
#: Stem strength (see above) at or above which a corner clearly holds a stem, and at or below which it clearly does not.
PRESENT_MIN = 0.60
ABSENT_MAX = 0.25
#: The smallest ink box (px) the check will read at all; below it the box is a speck and the answer is `unread`.
MIN_SIDE_PX = 6
#: The shape is never READ: Sean's to set on blind tiles.
SHAPE_READ: Optional[float] = None

#: shape name -> the detector class names it can stand for (SMuFL spelling, compared lower-case).
_CLASS_OF = {"flat": "accidentalflat", "natural": "accidentalnatural", "sharp": "accidentalsharp"}
_SHAPE_OF = {v: k for k, v in _CLASS_OF.items()}


def enabled() -> bool:
    """`OMR_ACCIDENTAL_SHAPE`, default ON (ROADMAP 2.190, Sean 2026-10-22); an explicit 0/false/no/off disables."""
    return os.environ.get(SHAPE_ENV, "").strip().lower() not in ("0", "false", "no", "off")


def shape_of_class(class_name: str) -> Optional[str]:
    """`flat|natural|sharp` for a detector class, None for every other (double sharp, double flat, key*, ...)."""
    return _SHAPE_OF.get(str(class_name or "").lower())


def _zone(density: float) -> str:
    if density >= PRESENT_MIN:
        return "present"
    if density <= ABSENT_MAX:
        return "absent"
    return "between"


def _tight(ink):
    import numpy as np
    ys, xs = np.nonzero(ink)
    if len(ys) == 0:
        return None
    return int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1


def _stem_strength(win) -> float:
    """The best vertical run: the largest column fill (ink / window height) after a 3-column moving average."""
    import numpy as np
    col = win.mean(axis=0)
    if len(col) >= 3:
        col = np.convolve(col, np.ones(3) / 3.0, mode="valid")
    return float(col.max())


def measure(img: Any, box: Sequence[float]) -> Optional[Dict[str, Any]]:
    """The two corner densities of ONE accidental box on the cell's staff-erased raster (0 = ink), or None where there is nothing to read.

    `box` is `(x, y, w, h)` in the raster's own frame. Small specks (components under 8% of the box's ink) are dropped first, so a neighbouring
    notehead's fringe or a dust mote cannot fill a corner; the corners are then read off the TIGHT ink box of what is left."""
    import numpy as np
    img = np.asarray(img)
    if img.ndim != 2:
        return None
    x, y, w, h = [float(v) for v in box]
    x0, y0 = max(0, int(round(x))), max(0, int(round(y)))
    x1, y1 = min(img.shape[1], int(round(x + w))), min(img.shape[0], int(round(y + h)))
    if x1 - x0 < MIN_SIDE_PX or y1 - y0 < MIN_SIDE_PX:
        return None
    ink = (img[y0:y1, x0:x1] == 0)
    if not ink.any():
        return None
    import cv2
    n, lab, stats, _ = cv2.connectedComponentsWithStats(ink.astype("uint8"), connectivity=8)
    total = int(ink.sum())
    keep = np.zeros_like(ink)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= 0.08 * total:
            keep |= (lab == i)
    t = _tight(keep)
    if t is None:
        return None
    ty0, ty1, tx0, tx1 = t
    th, tw = ty1 - ty0, tx1 - tx0
    if th < MIN_SIDE_PX or tw < 3:
        return None
    g = keep[ty0:ty1, tx0:tx1]
    ww, wh = max(1, int(round(tw * WINDOW_W))), max(1, int(round(th * WINDOW_H)))
    bl = _stem_strength(g[th - wh:, :ww])
    tr = _stem_strength(g[:wh, tw - ww:])
    return {"bl": round(bl, 3), "tr": round(tr, 3), "ink_w": tw, "ink_h": th, "aspect": round(tw / th, 3)}


def _dist(d: float, z: str) -> float:
    return (d - PRESENT_MIN) if z == "present" else (ABSENT_MAX - d) if z == "absent" else -min(abs(d - PRESENT_MIN), abs(d - ABSENT_MAX))


def classify(m: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """`{shape, bl_zone, tr_zone, margin}` from `measure`'s densities. `shape` is flat|natural|sharp or `unclear` (a window between the zones, or
    an arrangement no printed accidental has) or `unread` (nothing measured). `margin`: the signed distance of the NEARER window to its cut-off
    (positive = inside a clear zone, negative = in the band between)."""
    if not m:
        return {"shape": "unread", "bl_zone": None, "tr_zone": None, "margin": None}
    zb, zt = _zone(m["bl"]), _zone(m["tr"])
    margin = round(min(_dist(m["bl"], zb), _dist(m["tr"], zt)), 3)
    shape = "unclear"
    if zb != "between" and zt != "between":
        shape = {("present", "absent"): "flat", ("absent", "absent"): "natural", ("present", "present"): "sharp"}.get((zb, zt), "unclear")
    return {"shape": shape, "bl_zone": zb, "tr_zone": zt, "margin": margin}


def reads_shape(margin: Optional[float]) -> bool:
    """Does this margin clear the (unset) READ bar? With the bar unset nothing reads."""
    return SHAPE_READ is not None and margin is not None and margin >= SHAPE_READ


def choose(candidates: Sequence[str], shape: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The shape's verdict on a set of the detector's own classes for ONE ink: `{"pick": class|None, "why": ...}`.

    pick = the candidate class whose shape the measured shape names, ONLY if it is one of `candidates` and the shape is clear; else None and
    `why` says which: `unread`, `unclear`, `shape_not_offered` (a clear shape the detector did not offer: never invented), `unambiguous` (one
    candidate only -- a single class has nothing to choose among)."""
    cl = [str(c) for c in candidates]
    if len(set(c.lower() for c in cl)) < 2:
        return {"pick": None, "why": "unambiguous"}
    if not shape or shape.get("shape") in (None, "unread"):
        return {"pick": None, "why": "unread"}
    s = shape["shape"]
    if s == "unclear":
        return {"pick": None, "why": "unclear"}
    want = _CLASS_OF.get(s)
    for c in cl:
        if c.lower() == want:
            return {"pick": c, "why": "shape_names_a_candidate", "shape": s}
    return {"pick": None, "why": "shape_not_offered", "shape": s}


# ── ROADMAP 2.192 -- AN ACCIDENTAL BOX ON A REST'S INK (flag `OMR_ACCIDENTAL_ON_A_REST`, default OFF) ──────────────────────────────────────
# THE CAUSE (benchmarks/omr-phantom-accidental-2026-10/FINDINGS.md): the production detector boxes an eighth rest's bulb-and-stem as
# `accidentalDoubleSharp` (and, rarely, a real rest as another class); 2.186 merges only WITHIN a family and `adjudicate_rest_is_not_a_rest` /
# `adjudicate_accidental_is_not_an_accidental` each look only at their own family, so nothing ever compares the two boxes on one ink.
ON_REST_ENV = "OMR_ACCIDENTAL_ON_A_REST"
#: Two boxes in one cell contest ONE ink when their IoU is at least this (checked on crops: 10 of 10 double sharps at >= .5 were an eighth rest; the
#: kept-rest overlap of real accidentals sits in the same band, which is why the SHAPE, not the overlap, decides whether the accidental stays).
ON_REST_IOU = 0.5
#: Every accidental class the shape reader can compare, to the shape (family) its ink must have.
_FAMILY_OF_CLASS = {"accidentalflat": "flat", "accidentaldoubleflat": "flat", "accidentalnatural": "natural",
                    "accidentalsharp": "sharp", "accidentaldoublesharp": "sharp"}


def on_rest_enabled() -> bool:
    """`OMR_ACCIDENTAL_ON_A_REST`, default OFF; only an explicit 1/true/yes/on enables."""
    return os.environ.get(ON_REST_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def on_rest_verdict(detector_class: str, shape: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """For an accidental that CONTESTS a kept rest's ink: `{"keep": bool, "why": ...}`. It is kept only when its own ink is clearly accidental-shaped
    AND of the shape its class names (a double sharp stands for `sharp`, a double flat for `flat`). An unread / unclear / mismatched shape is
    refused (rule 8: where it cannot tell, the accidental is NOT applied -- the note keeps its key/bar alteration -- and the case is counted)."""
    want = _FAMILY_OF_CLASS.get(str(detector_class or "").lower())
    if want is None:
        return {"keep": False, "why": "class_has_no_shape"}
    if not shape or shape.get("shape") in (None, "unread"):
        return {"keep": False, "why": "unread"}
    if shape["shape"] == "unclear":
        return {"keep": False, "why": "unclear"}
    if shape["shape"] != want:
        return {"keep": False, "why": "shape_is_%s_not_%s" % (shape["shape"], want)}
    return {"keep": True, "why": "shape_matches_class"}
