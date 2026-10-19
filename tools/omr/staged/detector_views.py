"""ROADMAP 2.172 -- the detector looks at each symbol family at its OWN size, steadily. STAGED GATHER.

Sean 2026-10-19: *"We take a big picture view of things that automatically gets rid of a lot of the noise for some of the smaller
things, and where it gets really crowded or hard to read. We look closer."* From 2.171 (`benchmarks/omr-detector-crop-mechanism-2026-10`):
the detector is shown a 16 px staff space whatever it is looking at; a dot / flag / rest wants a SMALLER view (Brahms x0.5 lifts 13 of 17
lost ones), a welded black head a LARGER one (Litolff x1.4 lifts 8 of 9); a symbol near the floor moves by a median 0.14-0.19 when the crop
shifts by under one network pixel; averaging the down-sample (INTER_AREA) beats the two-tap bilinear resize.

ONE flag, `OMR_DETECTOR_VIEWS` (default OFF; only an explicit on-word enables). Sub-switches exist so the parts can be priced one at a time:
`OMR_DETECTOR_VIEWS_PARTS` (comma list of `views`, `aa`, `phase`; default all three; `views` is the flag itself and is always present),
`OMR_DETECTOR_VIEWS_PHASES` (number of sub-pixel phases per view, default 3, ignored when `phase` is not listed), `OMR_DETECTOR_VIEWS_WHICH`
(`small`, `close`, default both).

  (1) PER-FAMILY VIEW. Besides the production view (untouched -- its boxes are never changed, moved or dropped), the SAME weights are run on
      views at other staff-space sizes (`VIEWS`), and from each only the boxes of the families that view is for are taken.
  (2) ANTI-ALIASED DOWN-SAMPLE for the views below production scale (`aa`).
  (3) PHASE MEDIAN. Each view is read at `PHASES` sub-pixel phases of the network grid; a box is kept only where the MEDIAN confidence over
      the phases (a phase that has no box counts as 0) clears `KEEP_FLOOR`, the production floor. The recorded score is that median.
  Merge into the production boxes, family-aware: a view box is dropped where a production box of the SAME family already stands on it, and
  where a production box of ANOTHER family stands on it with a confidence at least as high. So a view box only fills a place production left
  empty or holds a weaker, different reading -- it adds a candidate, it never overturns a confident production box. What survives is a GATHER fact
  like any other: appended to the cell's `detections` (so every later reader and every ADJUDICATE gate sees it) under its own reader name,
  `READERS.DETECTOR_VIEW`, carrying which view and which phases found it.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (CLAUDE.md rule 3; sizes are MEASUREMENTS, not conventions, rule 4.x):
  * ASSUMED: a dot, flag or rest is better read from a smaller view than a notehead (2.171, Brahms: dots/flags/rests x0.5, 13 of 17), a welded
    black head from a larger one (2.171, Litolff: x1.4, 8 of 9). FALSIFIED by Sean's blind tiles on the new boxes: if most of a view's new boxes
    are not the symbol of the family they were taken for, that size is wrong (or the family is, on that plate).
  * NOT CONFIRMED: 8 px and 22 px were chosen from two plates (Litolff, Brahms) and ONE weights file; they may only NARROW (add a candidate
    behind the existing gates) until a third publisher confirms them. No default flips on this lane.
  * NOT CONFIRMED: the "closer view per cell by local crowding" idea of Sean's principle is NOT built -- any crowding cut would be fitted on
    our two plates; the closer view runs on every cell and can only add.
"""
from __future__ import annotations

import dataclasses
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

DETECTOR_VIEWS_ENV = "OMR_DETECTOR_VIEWS"
PARTS_ENV = "OMR_DETECTOR_VIEWS_PARTS"
PHASES_ENV = "OMR_DETECTOR_VIEWS_PHASES"
WHICH_ENV = "OMR_DETECTOR_VIEWS_WHICH"

ALL_PARTS = ("views", "aa", "phase")

#: the families a view can be for (one spelling: `family_of`)
FAM_DOT, FAM_FLAG, FAM_REST, FAM_BLACKHEAD = "dot", "flag", "rest", "blackhead"

#: name -> (staff space shown in network pixels, families it is for, anti-alias it). Production shows 16.
#: small: 8 px = x0.5 (2.171 section 4: Brahms dot 0.10 -> 0.27, flag 0.25 -> 0.66, rest 0.06 -> 0.38; Litolff lost rests 0.03 -> 0.35).
#: close: 22 px = x1.4 (2.171: Litolff lost black heads 0.11 -> 0.35, 8 of 9 over the floor).
#: MEASURED ON TWO PLATES -- NOT CONFIRMED, may only NARROW (module docstring).
VIEWS: Dict[str, Tuple[float, Tuple[str, ...], bool]] = {
    "small": (8.0, (FAM_DOT, FAM_FLAG, FAM_REST), True),
    "close": (22.0, (FAM_BLACKHEAD,), False),
}

#: sub-pixel phases of the network grid, as (dx, dy) fractions of ONE network pixel; the first is the unshifted view
PHASE_FRACTIONS: Tuple[Tuple[float, float], ...] = ((0.0, 0.0), (0.34, 0.67), (0.67, 0.34), (0.5, 0.0))

#: a view box is READ at this floor so a phase that scores 0.05-0.25 still counts toward the median
READ_FLOOR = 0.05
#: the median over phases must clear the production GATHER floor (`OMR_CONF_THRESHOLD`, 0.25) -- not a new cut
KEEP_FLOOR = 0.25
#: two boxes of one family on one piece of ink: IoU at least this, or either centre inside the other box
SAME_INK_IOU = 0.3


def enabled() -> bool:
    """`OMR_DETECTOR_VIEWS`, default OFF; only an explicit on-word enables."""
    return os.environ.get(DETECTOR_VIEWS_ENV, "0").strip().lower() in ("1", "true", "yes", "on")


def parts() -> Tuple[str, ...]:
    raw = os.environ.get(PARTS_ENV, "").strip()
    if not raw:
        return ALL_PARTS
    named = tuple(p.strip() for p in raw.split(",") if p.strip())
    return tuple(p for p in ALL_PARTS if p in named or p == "views")


def n_phases() -> int:
    if "phase" not in parts():
        return 1
    try:
        n = int(os.environ.get(PHASES_ENV, "3"))
    except ValueError:
        n = 3
    return max(1, min(len(PHASE_FRACTIONS), n))


def active_views() -> List[str]:
    raw = os.environ.get(WHICH_ENV, "").strip()
    if not raw:
        return list(VIEWS)
    named = [w.strip() for w in raw.split(",") if w.strip()]
    return [v for v in VIEWS if v in named]


def family_of(smufl_name: str) -> Optional[str]:
    """The family a detector class belongs to for this lane (None = not one it deals in)."""
    if smufl_name == "augmentationDot":
        return FAM_DOT
    if smufl_name.startswith("flag"):
        return FAM_FLAG
    if smufl_name.startswith("rest"):
        return FAM_REST
    if smufl_name in ("noteheadBlackOnLine", "noteheadBlackInSpace"):
        return FAM_BLACKHEAD
    return None


def _family_of_production(smufl_name: str) -> str:
    """A production box's family for the merge: this lane's four, a head of any other kind as `head`, anything else by its class name."""
    f = family_of(smufl_name)
    if f is not None:
        return f
    if smufl_name.startswith("notehead"):
        return "head"
    return smufl_name


def box(d: Any) -> Tuple[float, float, float, float]:
    return (float(d.x_canonical), float(d.y_canonical),
            float(d.x_canonical + d.width_canonical), float(d.y_canonical + d.height_canonical))


def _iou(a: Sequence[float], b: Sequence[float]) -> float:
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def _inside(pt: Tuple[float, float], b: Sequence[float]) -> bool:
    return b[0] <= pt[0] <= b[2] and b[1] <= pt[1] <= b[3]


def same_ink(a: Sequence[float], b: Sequence[float]) -> bool:
    if _iou(a, b) >= SAME_INK_IOU:
        return True
    ca = ((a[0] + a[2]) / 2.0, (a[1] + a[3]) / 2.0)
    cb = ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)
    return _inside(ca, b) or _inside(cb, a)


def phase_median(per_phase: Sequence[Sequence[Any]], families: Sequence[str],
                 keep_floor: float = KEEP_FLOOR) -> List[Dict[str, Any]]:
    """Cluster the boxes of `families` across the phases of ONE view and keep a cluster whose MEDIAN confidence over the phases clears
    `keep_floor` (a phase with no box in the cluster counts 0). With one phase this is the plain floor. Returns dicts
    `{det, conf, class, family, phases, phase_confs}`, `det` the member whose confidence is nearest the median.

    A cluster is a set of same-family boxes on one ink (`same_ink`), at most one per phase (a phase's best box)."""
    n = len(per_phase)
    clusters: List[Dict[str, Any]] = []
    pool = []
    for pi, dets in enumerate(per_phase):
        for d in dets:
            f = family_of(d.smufl_name)
            if f in families:
                pool.append((float(d.confidence), pi, f, d))
    pool.sort(key=lambda t: -t[0])
    for conf, pi, f, d in pool:
        b = box(d)
        for cl in clusters:
            if cl["family"] != f or pi in cl["members"]:
                continue
            if same_ink(b, cl["box"]):
                cl["members"][pi] = (conf, d)
                break
        else:
            clusters.append({"family": f, "box": b, "members": {pi: (conf, d)}})
    kept: List[Dict[str, Any]] = []
    for cl in clusters:
        confs = [cl["members"][pi][0] if pi in cl["members"] else 0.0 for pi in range(n)]
        s = sorted(confs)
        med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0
        if med < keep_floor:
            continue
        pi_best = min(cl["members"], key=lambda k: abs(cl["members"][k][0] - med))
        d = cl["members"][pi_best][1]
        votes: Dict[str, float] = {}
        for _, (c, m) in cl["members"].items():
            votes[m.smufl_name] = votes.get(m.smufl_name, 0.0) + c
        winner = max(votes, key=votes.get)
        d = dataclasses.replace(d, smufl_name=winner, confidence=float(med))
        kept.append({"det": d, "conf": float(med), "class": winner, "family": cl["family"],
                     "phases": sorted(cl["members"]), "phase_confs": [round(c, 3) for c in confs]})
    return kept


def merge_into_production(candidates: Sequence[Dict[str, Any]], production: Sequence[Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Family-aware NMS of the view candidates against the cell's production boxes (and against each other, strongest first).
    Returns `(kept, refused)`; each refused carries `why`:
      `production_same_family`  a production box of the same family stands on this ink (production already has the symbol);
      `production_stronger`     a production box of ANOTHER family stands here with a confidence at least this one's;
      `view_stronger`           another view's candidate (any family) stands here with a higher confidence.
    A production box is never changed, moved or removed."""
    prod = [(box(p), _family_of_production(p.smufl_name), float(p.confidence)) for p in production]
    kept: List[Dict[str, Any]] = []
    refused: List[Dict[str, Any]] = []
    for cand in sorted(candidates, key=lambda c: -c["conf"]):
        b = box(cand["det"])
        why = None
        for pb, pf, pc in prod:
            if not same_ink(b, pb):
                continue
            if pf == cand["family"] or (pf == "head" and cand["family"] == FAM_BLACKHEAD):
                why = "production_same_family"
                break
            if pc >= cand["conf"]:
                why = "production_stronger"
                break
        if why is None:
            for k in kept:
                if same_ink(b, box(k["det"])):
                    why = "view_stronger"
                    break
        if why is None:
            kept.append(cand)
        else:
            refused.append(dict(cand, why=why))
    return kept, refused


def views_for_cell(detector: Any, cell: Any, production: Sequence[Any]) -> Optional[Dict[str, Any]]:
    """Run every active view on ONE cell and merge. `None` when the detector cannot do views or the cell has no staff lines to calibrate
    against. Otherwise `{kept: [...], refused: [...], calls: n_forward_passes}`; each kept dict has `view`, `staff_space_px`,
    `anti_alias`, `n_phases` besides the `phase_median` fields."""
    if not hasattr(detector, "detect_view"):
        return None
    ph = n_phases()
    shifts_net = PHASE_FRACTIONS[:ph]
    use_aa = "aa" in parts()
    ys = getattr(cell, "staff_line_ys_canonical", None) or []
    if len(ys) < 2:
        return None
    space = (ys[-1] - ys[0]) / (len(ys) - 1)
    candidates: List[Dict[str, Any]] = []
    calls = 0
    for name in active_views():
        size, fams, aa = VIEWS[name]
        r = size / space
        shifts = [(int(round(fx / r)), int(round(fy / r))) for fx, fy in shifts_net]
        per_phase = detector.detect_view(cell, size, shifts=shifts, anti_alias=(aa and use_aa), conf_threshold=READ_FLOOR)
        calls += 1
        if per_phase is None:
            continue
        for cl in phase_median(per_phase, fams):
            cl.update(view=name, staff_space_px=size, anti_alias=bool(aa and use_aa), n_phases=ph)
            candidates.append(cl)
    kept, refused = merge_into_production(candidates, production)
    return {"kept": kept, "refused": refused, "calls": calls}
