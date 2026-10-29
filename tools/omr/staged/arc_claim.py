"""ROADMAP (lane-arcs-claim-1029) -- ARCS CLAIMED IN GATHER; the kind decided later from the two end heads. PATH: STAGED. PURE helpers: this module
imports numpy and nothing from the pipeline; it files no row and decides nothing by itself. Its callers are `gather.gather_arc_claim` (the claim),
`adjudicators/stroke_owner.py` (the one consumer of the claim), `adjudicators/ownership.adjudicate_arc_kind` (the kind from the ends) and
`export._anchored_slur_spans` (the slur's ends). Registered in `reach.NOT_A_STAGE`.

Sean, 2026-10-29 (DECISIONS "SIMPLIFY GATHER"): "At the gather stage an arc is the most it should determine. We can use later stages to decide if it is
a tie or a slur. If we can have the gather stage claim the ink as an arc that will be enough to make sure it isn't confusing beams or other symbols."
His tie rule (page-facts s1, the same day): "a tie only ever happens between 2 adjacent notes of the same pitch. Different pitch or spanning multiple
notes is always slur. When there are multiple arcs the tie is always closer to the staff than the slur."

THE THREE FLAGS, all default OFF (an explicit on-word turns each on):

  `OMR_ARC_CLAIM`            GATHER. Each curve `gather_system_arcs` traced (`Q.SYSTEM_ARC`, 2.166) claims the strokes of every cell it runs through as
                             ONE owner, `arc`, in the register (`Q.CLAIMED_AREA`, unit `ink`, owner `arc`) -- no kind. `stroke_owner` reads it at tier 0
                             (a stroke the traced curve runs along is the curve's, whatever box also stands on it). Needs `OMR_SYSTEM_ARCS` and
                             `OMR_STROKE_MAP` (both default ON). A later reader may MARK claimed ink, never TAKE it as a beam, a hook, a stem or a head.
  `OMR_ARC_KIND_FROM_ENDS`   ADJUDICATE (the order the old rule already stood in: after the heads are read). The kind is FORCED once the two end heads
                             are read (`kind_from_ends`), and the detector's class is a prior only: where no end pair can be read, the arc's kind
                             ABSTAINS (`arc_ends_unread`) -- the arc stays an arc (it still discounts a beam), it is not written as either kind.
  `OMR_SLUR_FROM_ANCHORS`    EXPORT. A slur whose curve `Q.SYSTEM_ARC` anchored at both ends is written on those two heads where the box-count pairing
                             (`_noteheads_under`, two notes minimum) bound fewer than two.

CONVENTION ASSUMED: Sean's tie rule above, and that a curve the tracer followed (a thin stroke, no straighter than a line, 50% of its box's columns) is
an arc. WHAT WOULD FALSIFY IT: a head, beam or stem Sean values losing its stroke to the claim (the counts by kind are in the stroke-owner verdict's
census, `arc_claim:*`); a tie or slur Sean reads as the other kind after the change. NOT CONFIRMED: every cut is the register's (`COVER_SHARE_MIN` 0.5)
or 2.166's; the band half-width is 0.12 sp (a trace row is one pixel thick); the tiles are `out/print/arcs-claim-1029/`.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

ENV_CLAIM = "OMR_ARC_CLAIM"
ENV_KIND = "OMR_ARC_KIND_FROM_ENDS"
ENV_SLUR = "OMR_SLUR_FROM_ANCHORS"

#: the register's owner name for the claim (`claims.OWNER_ARC` is the same word)
OWNER = "arc"
#: `stroke_owner` family of the claim (tier 0, beside the area owners)
FAMILY = "arc_trace"

#: a stroke is the arc's when at least this share of its ink lies on the traced curve (the register's one cut, `stroke_map.COVER_SHARE_MIN`)
ON_TRACE_SHARE_MIN = 0.5
#: the band around a trace row, staff spaces (a trace row is the stroke's own thickness, `+- 1` px of a skewed raster)
BAND_SPACES = 0.12
BAND_MIN_PX = 1.5

#: the reason an arc's kind abstains when no end pair can be read; a `Q.ARC_KIND` abstention with a reason in this set is STILL AN ARC
ENDS_UNREAD = "arc_ends_unread"
ARC_STILL_AN_ARC = (ENDS_UNREAD, "same_pitch_accidental_unread", "stack_slur_over_two_same_pitch_notes")


def _on(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def claim_enabled() -> bool:
    return _on(ENV_CLAIM)


def kind_enabled() -> bool:
    return _on(ENV_KIND)


def slur_enabled() -> bool:
    return _on(ENV_SLUR)


# ── the claim: which strokes does a traced curve run along? ────────────────────────────────────────────────────────────────────────────────
def on_trace_share(mask: Any, x0: int, y0: int, scale: float, cell_box: Sequence[float], up: float,
                   trace: Dict[int, Tuple[float, float]], sp_page: float) -> float:
    """The share of one stroke's ink (`mask`, REDUCED px, origin `x0, y0` in the reduced frame of the cell) that lies on the traced curve.

    `trace` = `{page column x: (y top, y bottom)}` in page px. A reduced pixel maps to canonical px by `/ scale` and to page px by `cell_box origin
    + canonical / up`. A pixel is ON the curve when its page column has a trace row and its page y lies within `BAND_SPACES` of that row's span."""
    import numpy as np
    ys, xs = np.nonzero(mask)
    if ys.size == 0 or not trace or scale <= 0 or up <= 0:
        return 0.0
    px = float(cell_box[0]) + ((x0 + xs + 0.5) / scale) / up
    py = float(cell_box[1]) + ((y0 + ys + 0.5) / scale) / up
    cols = np.floor(px).astype(int)
    band = max(BAND_MIN_PX, BAND_SPACES * sp_page)
    xmin = min(trace)
    xmax = max(trace)
    lo = np.full(xmax - xmin + 1, np.inf)
    hi = np.full(xmax - xmin + 1, -np.inf)
    for x, (a, b) in trace.items():
        lo[x - xmin] = a
        hi[x - xmin] = b
    inside = (cols >= xmin) & (cols <= xmax)
    idx = np.clip(cols - xmin, 0, xmax - xmin)
    on = inside & (py >= lo[idx] - band) & (py <= hi[idx] + 1.0 + band)
    return float(on.sum()) / float(ys.size)


def claim_strokes(res: Any, cell_box: Sequence[float], up: float, trace: Dict[int, Tuple[float, float]],
                  sp_page: float) -> List[Tuple[int, float]]:
    """`[(stroke ordinal, share)]` for every stroke of the cell (`stroke_map.CellStrokes`) whose ink lies at least `ON_TRACE_SHARE_MIN` on the curve."""
    out: List[Tuple[int, float]] = []
    masks = getattr(res, "masks", None) or []
    for i, (m, x0, y0) in enumerate(masks):
        if m.size == 0:
            continue
        sh = on_trace_share(m, x0, y0, res.scale, cell_box, up, trace, sp_page)
        if sh >= ON_TRACE_SHARE_MIN:
            out.append((i, round(sh, 3)))
    return out


# ── the kind: from the two end heads, by Sean's rule ───────────────────────────────────────────────────────────────────────────────────────
#: what a `Q.SYSTEM_ARC` row's value (the ends' shape) says about the kind, when the ends were anchored on two different heads
SHAPE_KIND = {
    "two_heads_one_position_adjacent": ("tie", "system_arc_two_heads_one_position_adjacent"),
    "one_position_heads_between": ("slur", "system_arc_more_than_two_notes"),
    "two_positions": ("slur", "system_arc_ends_differ"),
}


def kind_from_ends(two_note: Optional[Dict[str, Any]], stack: Optional[Dict[str, Any]],
                   system_shape: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """`(kind | None, rule, conflict)`: Sean's tie rule applied to the two end heads, the detector's class NOT an input. None = ABSTAIN (`rule` says why).

    `two_note` is `ownership._two_note_reading` (the heads the arc flanks, their steps, `between`, the accidental state); `stack` is
    `ownership._stack_reading`; `system_shape` the `Q.SYSTEM_ARC` row's value where the curve was joined and anchored on page pixels.

      more than two notes under it                    -> slur  (`between`: another onset lies between the end heads)
      the two end heads at different steps            -> slur
      the two end heads at one step, adjacent         -> tie   (accidental unchanged); an accidental printed or unread -> abstain
      the ends unreadable here, the system curve anchored both ends -> its shape says the same (tie / slur)
      stacked over the same notes                     -> the nearer one is the tie, the other the slur
      nothing readable                                -> abstain `arc_ends_unread`
    """
    tn = two_note or {}
    pos: Optional[str] = None
    rule: Optional[str] = None
    if tn.get("evaluated"):
        rel = tn.get("relation")
        if tn.get("between"):
            pos, rule = "slur", "more_than_two_notes_under"
        elif rel == "different":
            pos, rule = "slur", "two_notes_different_pitch"
        elif rel == "same":
            acc = tn.get("accidental")
            if acc == "unchanged":
                pos, rule = "tie", "two_notes_same_pitch"
            else:
                return None, "same_pitch_accidental_unread", None
    if pos is None and system_shape in SHAPE_KIND:
        pos, rule = SHAPE_KIND[system_shape]
    role = (stack or {}).get("role")
    if role is None:
        if pos is None:
            return None, ENDS_UNREAD, None
        return pos, rule, None
    want = "tie" if role == "nearer" else "slur"
    if pos is None:
        if want == "tie" and (not tn.get("evaluated") or tn.get("between")):
            return None, ENDS_UNREAD, "stacked_nearer_but_not_a_two_note_arc"
        return want, "stacked_nearer_is_tie" if want == "tie" else "stacked_farther_is_slur", None
    if pos == want:
        return pos, rule, None
    if pos == "slur":
        return "slur", rule, "stack_says_tie_notes_differ"
    return None, "stack_slur_over_two_same_pitch_notes", "stack_says_slur_two_same_pitch_notes"
