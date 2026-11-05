"""ROADMAP 2.268 (flag `OMR_DYAD_HEAD_RESCUE`, default ON, deny-list; Sean 12/12 tiles, landed 2026-11-04) -- the other head of a chord, from the detector's OWN sub-cut candidate.
STAGED GATHER; decides nothing.

CAUSE (2.267, `benchmarks/detector-unboxed-heads-2026-11/FINDINGS.md`): a dyad's other head was never boxed because the detector scores it
BELOW the 0.25 cut (14 of 14 cached cases had a candidate; none was "unseen", none was removed by NMS), and no rescue witness exists for a
head that is not at a stem's end (the stem-end rescue looks only at orphan stems; the boxed partner already makes the stem a non-orphan).

THE RULE (a convention, not a cut-off): a chord's heads share ONE stem, so a head-class candidate the detector drew below the cut that
(1) sits on a CV stem a BOXED head (any reader) also touches, a step or more along it from that head, (2) stands on ink that is ONE head
(the stem-end reader's own `head_ink.read_head_ink` tests: head-sized, oval, fill read) with the stem at its edge, and (3) is covered
neither by a head box (>= 0.5 of the ink) nor by another mark's confident box, is a note we did not see. Written GUESSED (blue) -- it can
never be READ. Nothing here moves another head: the box is APPENDED to the cell's detections (every glyph index unchanged).

A merged TALL candidate (2.267 cause 2t) is used only through 2.252's own split (`box_kind.split_tall_heads`, by holes): a head the
holes give where no one-head box stands; otherwise it is skipped.

The step: dy >= `ALONG_SPACES` (a third or wider: a third is a full space), or dy >= `STEP_SPACES` with dx >= `ACROSS_SPACES` (a second:
one step along, the head displaced to the other side of the stem, about a head's width). A head's width is the convention (1.3 sp,
`stem_end_heads.HEAD_WIDTH_SPACES`); a step is half a space by definition. No tuned cut.

CONVENTION ASSUMED: notes of one chord share one stem, one head per step, a second displaced across the stem (page-facts "Stems"). WHAT
WOULD FALSIFY IT: Sean's blind tiles on the rescued boxes showing a letter, a flag, a slur end or a beam piece read as a head. NOT
CONFIRMED beyond Litolff and Brahms; the 0.05 floor is the stem-end rescue's own.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

ENV = "OMR_DYAD_HEAD_RESCUE"
#: the detector is read at the stem-end rescue's own floor (one shared run, `_rescue_detect`'s floor_memo)
FLOOR = 0.05
#: the production cut: a candidate at or above it is a production box, not this rescue's
CUT = 0.25
#: a step along the stem is half a space; a third is a full space (see the module docstring)
STEP_SPACES = 0.4
ALONG_SPACES = 0.9
#: a displaced second stands about a head's width (1.3 sp) across; 0.9 leaves room for the box's own error
ACROSS_SPACES = 0.9
#: a boxed head touches a stem when its centre is within this of the stem's x (the stem-end rescue's own window)
TOUCH_ACROSS_SPACES = 0.9
#: ... and its centre is within the stem's span, this far past either end (the stem-end rescue's own window)
TOUCH_ALONG_SPACES = 1.0
#: the candidate's box covers the stem's x to within this (a stem drawn through a head's edge)
STEM_AT_EDGE_SPACES = 0.25
#: the candidate's ink is covered by a head box when this share of it lies inside the box
COVERED_SHARE = 0.5


def enabled() -> bool:
    """`OMR_DYAD_HEAD_RESCUE` (ROADMAP 2.268), default ON (deny-list): "0"/"false"/"no"/"off" turns it off."""
    return os.environ.get(ENV, "").strip().lower() not in ("0", "false", "no", "off")


def _share_inside(box: Sequence[float], other: Sequence[float]) -> float:
    w, h = float(box[2]) - float(box[0]), float(box[3]) - float(box[1])
    if w <= 0 or h <= 0:
        return 0.0
    iw = min(float(box[2]), float(other[2])) - max(float(box[0]), float(other[0]))
    ih = min(float(box[3]), float(other[3])) - max(float(box[1]), float(other[1]))
    return max(0.0, iw) * max(0.0, ih) / (w * h)


def stem_touches_head(stem: Any, head_box: Sequence[float], space: float) -> bool:
    """A boxed head's centre is beside the stem and within its span (a stem is drawn past its head's centre)."""
    from . import stem_end_heads as SEH
    x, yt, yb = SEH.stem_ends(stem)
    cx, cy = SEH._centre(head_box)
    return abs(cx - x) <= TOUCH_ACROSS_SPACES * space and yt - TOUCH_ALONG_SPACES * space <= cy <= yb + TOUCH_ALONG_SPACES * space


def box_on_stem(stem: Any, box: Sequence[float], space: float) -> bool:
    """The candidate box takes the stem at an edge or inside, and its centre stands along the stem's span."""
    from . import stem_end_heads as SEH
    x, yt, yb = SEH.stem_ends(stem)
    cy = SEH._centre(box)[1]
    pad = STEM_AT_EDGE_SPACES * space
    return box[0] - pad <= x <= box[2] + pad and yt - 0.5 * space <= cy <= yb + 0.5 * space


def a_step_from(box: Sequence[float], head_box: Sequence[float], space: float) -> bool:
    """The candidate is a step or more along the stem from the boxed head (a third+ straight along; a second displaced across)."""
    from . import stem_end_heads as SEH
    cx, cy = SEH._centre(box)
    hx, hy = SEH._centre(head_box)
    dx, dy = abs(cx - hx) / space, abs(cy - hy) / space
    return dy >= ALONG_SPACES or (dy >= STEP_SPACES and dx >= ACROSS_SPACES)


def candidates_for_cell(stems: Sequence[Any], existing: Sequence[Any], pool: Sequence[Any], grid: Tuple[float, float]
                        ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Pure: `(kept, refused)`. `existing` = the cell's detections so far (any reader), `pool` = head-class detections below the cut
    (head-sized; a tall one already split by holes into head-sized ones). Each kept dict: `det`, `stem_index`, `partner` (index in
    `existing`), `score`. One candidate per ink (highest score)."""
    from . import stem_end_heads as SEH
    _top, half = grid
    space = 2.0 * half
    heads = [(i, SEH._box(d)) for i, d in enumerate(existing) if SEH.is_head(d.smufl_name)]
    if not heads or not stems:
        return [], []
    others = [(SEH._box(d), float(d.confidence)) for d in existing
              if str(d.smufl_name).startswith(SEH._OTHER_FAMILY_PREFIXES) and not str(d.smufl_name).startswith(SEH.BLOCK_RESTS)
              and float(d.confidence) >= SEH.CLAIM_FLOOR]
    kept: List[Dict[str, Any]] = []
    refused: List[Dict[str, Any]] = []
    for d in sorted(pool, key=lambda x: -float(x.confidence)):
        b = SEH._box(d)
        conf = float(d.confidence)
        why = None
        if any(SEH.same_ink(b, hb) or _share_inside(b, hb) >= COVERED_SHARE for _i, hb in heads):
            why = "a_head_covers_it"
        elif any(SEH.same_ink(b, ob) for ob, _c in others):
            why = "another_mark_holds_it"
        elif any(SEH.same_ink(b, SEH._box(k["det"])) for k in kept):
            why = "same_ink_as_a_kept_candidate"
        if why is not None:
            if why != "a_head_covers_it":
                refused.append({"det": d, "why": why, "score": conf})
            continue
        found = None
        near_miss = "no_stem_through_a_boxed_head"
        for si, s in enumerate(stems):
            if not box_on_stem(s, b, space):
                continue
            partner = next((i for i, hb in heads if stem_touches_head(s, hb, space)), None)
            if partner is None:
                continue
            near_miss = "not_a_step_from_the_boxed_head"
            hb_all = [hb for _i, hb in heads if stem_touches_head(s, hb, space)]
            # a step from EVERY boxed head the stem touches: nearer than a step to any of them is that head's own ink, boxed again
            if all(a_step_from(b, hb, space) for hb in hb_all):
                found = (si, partner)
                break
        if found is None:
            refused.append({"det": d, "why": near_miss, "score": conf})
            continue
        kept.append({"det": d, "stem_index": found[0], "partner": found[1], "score": conf})
    return kept, refused


def is_dyad(detail: Optional[Dict[str, Any]]) -> bool:
    """A `Q.GLYPH_BOX` detail of a head this rescue filed."""
    return bool(detail) and detail.get("source") == "dyad_head_rescue"
