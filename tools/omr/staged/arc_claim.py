"""ROADMAP (lane-arcs-claim-1029) -- ARCS CLAIMED IN GATHER; the kind decided later from the two end heads. PATH: STAGED. PURE helpers: this module
imports numpy and nothing from the pipeline; it files no row and decides nothing by itself. Its callers are `gather.gather_arc_claim` (the claim),
`adjudicators/stroke_owner.py` (the one consumer of the claim), `adjudicators/ownership.adjudicate_arc_kind` (the kind from the ends) and
`export._anchored_slur_spans` (the slur's ends). Registered in `reach.NOT_A_STAGE`.

Sean, 2026-10-29 (DECISIONS "SIMPLIFY GATHER"): "At the gather stage an arc is the most it should determine. We can use later stages to decide if it is
a tie or a slur. If we can have the gather stage claim the ink as an arc that will be enough to make sure it isn't confusing beams or other symbols."
His tie rule (page-facts s1, the same day): "a tie only ever happens between 2 adjacent notes of the same pitch. Different pitch or spanning multiple
notes is always slur. When there are multiple arcs the tie is always closer to the staff than the slur."

THE THREE FLAGS. `OMR_ARC_CLAIM` is default ON (Sean 2026-10-29, "Yes"; an explicit 0/false/no/off/empty disables); the other two are
default OFF (an explicit on-word turns each on) and wait for ROADMAP 2.223:

  `OMR_ARC_CLAIM`            GATHER (default ON). Each curve `gather_system_arcs` traced (`Q.SYSTEM_ARC`, 2.166) claims the strokes of every cell it runs through as
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
    """`OMR_ARC_CLAIM`, default ON (Sean 2026-10-29); an explicit `0/false/no/off` (or empty) disables."""
    raw = os.environ.get(ENV_CLAIM)
    if raw is None:
        return True
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def kind_enabled() -> bool:
    return _on(ENV_KIND)


def slur_enabled() -> bool:
    return _on(ENV_SLUR)


# ── the claim: which strokes does a traced curve run along? ────────────────────────────────────────────────────────────────────────────────
def on_trace_share(mask: Any, x0: int, y0: int, scale: float, cell_box: Sequence[float], up: float,
                   trace: Dict[int, Tuple[float, float]], sp_page: float,
                   skip_boxes: Sequence[Sequence[float]] = ()) -> float:
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
    if skip_boxes:
        # ROADMAP 2.284 (`OMR_PAGE_LEDGER_OWNS`): the arc claims only its OWN traced pixels -- a pixel inside a head box is never the arc's
        # (`arcs_system.erase_in_cell` protects the non-arc boxes the same way), so a hollow head's rim piece the trace overruns is not the arc's
        cx = (x0 + xs + 0.5) / scale
        cy = (y0 + ys + 0.5) / scale
        for bx0, by0, bx1, by1 in skip_boxes:
            on &= ~((cx >= bx0) & (cx <= bx1) & (cy >= by0) & (cy <= by1))
    return float(on.sum()) / float(ys.size)


#: ROADMAP 2.284b (flag `OMR_PAGE_LEDGER_OWNS`): a stroke the curve runs along that ALSO holds at least this share of another mark's own ink (the
#: stroke pixels inside that mark's detector box, over all of the cell's stroke pixels inside it) is a CROSSING -- the slur passes through the
#: head, ledger, dot or letter and the cell's stroke map did not cut the two apart. The arc MARKS it (its own pixels counted, `crossings`) and
#: never TAKES it (plan 2026-10-28 §9-10: "a later reader may mark claimed ink but never take it"; the arc may not take a mark's ink either).
#: The value is `claim_final.NEAR_MIN` (0.25), the consumer's own "held at all" bar, so the arc never holds a mark box near (not tuned).
CROSSING_BOX_SHARE = 0.25


#: ROADMAP 2.284b r2 (Sean 2026-11-10, tile 3: a `ledgerLine` box lying along an arc is "part of an arc"): a mark box whose own ink lies at least
#: this share ON THE MARK'S OWN LINE (the arc's traced curve; the hairpin's arms) is a false box on that line's ink, not a mark it crosses -- it
#: protects nothing and is no crossing. A true crossing (a `p`, a flat, a head the slur passes through) has most of its ink OFF the line.
#: A cut is a measurement (CLAUDE §4): the value is the majority, and the share of every crossing and every dropped box is in the row.
BOX_ON_LINE_MIN = 0.5


def _page_xy(mask: Any, x0: int, y0: int, scale: float, cell_box: Sequence[float], up: float):
    import numpy as np
    ys, xs = np.nonzero(mask)
    px = float(cell_box[0]) + ((x0 + xs + 0.5) / scale) / up
    py = float(cell_box[1]) + ((y0 + ys + 0.5) / scale) / up
    return px, py


def _in_box(px: Any, py: Any, b: Sequence[float]) -> Any:
    return (px >= b[0]) & (px <= b[2]) & (py >= b[1]) & (py <= b[3])


def _on_curve(px: Any, py: Any, trace: Dict[int, Tuple[float, float]], sp_page: float) -> Any:
    """The pixels (page px arrays) on the traced curve: the column has a trace row and y lies within `BAND_SPACES` of its span (as `on_trace_share`)."""
    import numpy as np
    cols = np.floor(px).astype(int)
    band = max(BAND_MIN_PX, BAND_SPACES * sp_page)
    xmin, xmax = min(trace), max(trace)
    lo = np.full(xmax - xmin + 1, np.inf)
    hi = np.full(xmax - xmin + 1, -np.inf)
    for x, (a, b) in trace.items():
        lo[x - xmin] = a
        hi[x - xmin] = b
    inside = (cols >= xmin) & (cols <= xmax)
    idx = np.clip(cols - xmin, 0, xmax - xmin)
    return inside & (py >= lo[idx] - band) & (py <= hi[idx] + 1.0 + band)


def claim_pixels(res: Any, cell_box: Sequence[float], up: float, trace: Dict[int, Tuple[float, float]], sp_page: float,
                 mark_boxes: Sequence[Tuple[str, Sequence[float]]]) -> Dict[str, Any]:
    """The ARC's pixel claim (`claim_pixels_on` with the traced curve as the `on` test). See `claim_pixels_on`."""
    if not trace:
        return claim_pixels_on(res, cell_box, up, None, mark_boxes)
    return claim_pixels_on(res, cell_box, up, lambda px, py: _on_curve(px, py, trace, sp_page), mark_boxes)


def claim_pixels_on(res: Any, cell_box: Sequence[float], up: float, on_fn: Any, mark_boxes: Sequence[Tuple[str, Sequence[float]]],
                    share_min: float = ON_TRACE_SHARE_MIN, line_boxes_free: bool = True) -> Dict[str, Any]:
    """PURE. ROADMAP 2.284b (flag `OMR_PAGE_LEDGER_OWNS`): a page-wide line mark's claim (the arc's traced curve; the hairpin's arms,
    `hairpin_reach`) on ONE cell's strokes, pixel-honest. `on_fn(px, py)` -> bool array: the pixels (page px) that lie on the mark's own line.

    `mark_boxes` = `[(box key, (x0, y0, x1, y1) PAGE px)]`: every other mark's detector box that meets the cell, from ANY cell or staff of the
    page (a padded cell sees the neighbour cell's and the neighbour staff's ink; r4: the 3 boxes still held >= 0.5 on p2 were all held through
    a neighbour view whose own detections did not hold the box). A pixel inside one is never the arc's own (the 2.166 eraser protects them).

      * a stroke is a candidate where at least `ON_TRACE_SHARE_MIN` of its pixels lie on the traced curve AND outside every mark box;
      * a candidate holding `CROSSING_BOX_SHARE` or more of some mark box's own ink is a CROSSING: marked (its own on-curve pixels counted),
        never taken -- the stroke is left to the stroke owner's other claimants;
      * a mark box whose own ink lies at least `BOX_ON_LINE_MIN` on the mark's own line is that line's ink (`line_boxes_free`, ROADMAP 2.284b r2;
        False = r6's rule, the control): it protects nothing, is no crossing;
      * every other candidate is claimed whole (the register's unit is the stroke); its pixels inside a mark box, if any, are counted
        (`claimed_px_in_marks`), so the residue is visible.

    Returns `{"claimed": [(ordinal, share)], "crossings": [{"stroke", "own_px", "box", "box_share"}], "own_px": on-curve pixels of the claimed
    strokes outside every mark box, "crossing_own_px", "claimed_px", "claimed_px_in_marks"}` (pixels in the stroke map's REDUCED frame)."""
    import numpy as np
    out: Dict[str, Any] = {"claimed": [], "crossings": [], "own_px": 0, "crossing_own_px": 0, "claimed_px": 0, "claimed_px_in_marks": 0}
    masks = getattr(res, "masks", None) or []
    if on_fn is None or not masks or res.scale <= 0 or up <= 0:
        return out
    boxes = [(str(k), [float(v) for v in b]) for k, b in mark_boxes]
    cache: Dict[int, Tuple[Any, Any]] = {}

    def xy(i: int):
        if i not in cache:
            m, x0, y0 = masks[i]
            cache[i] = _page_xy(m, x0, y0, res.scale, cell_box, up)
        return cache[i]

    box_ink: Dict[int, int] = {}
    box_on: Dict[int, int] = {}
    on_cache: Dict[int, Any] = {}

    def on_of(i: int):
        if i not in on_cache:
            px, py = xy(i)
            on_cache[i] = on_fn(px, py)
        return on_cache[i]

    def ink_of(j: int) -> int:
        if j not in box_ink:
            b = boxes[j][1]
            tot = on_n = 0
            for i, (m, _x0, _y0) in enumerate(masks):
                if m.size == 0:
                    continue
                px, py = xy(i)
                if px.size and px.max() >= b[0] and px.min() <= b[2] and py.max() >= b[1] and py.min() <= b[3]:
                    ib = _in_box(px, py, b)
                    tot += int(ib.sum())
                    on_n += int((ib & on_of(i)).sum())
            box_ink[j], box_on[j] = tot, on_n
        return box_ink[j]

    line_boxes: Dict[int, float] = {}

    def on_line_share(j: int) -> float:
        ink_of(j)
        return box_on[j] / float(box_ink[j]) if box_ink[j] else 0.0

    def is_line_box(j: int) -> bool:
        """A mark box that is the mark's OWN line's ink (`BOX_ON_LINE_MIN`): recorded in `line_boxes`, never protected."""
        if j not in line_boxes:
            sh = on_line_share(j)
            line_boxes[j] = sh if sh >= BOX_ON_LINE_MIN else -1.0
        return line_boxes[j] >= 0.0

    for i, (m, _x0, _y0) in enumerate(masks):
        if m.size == 0:
            continue
        px, py = xy(i)
        if px.size == 0:
            continue
        on = on_fn(px, py)
        if float(on.sum()) < share_min * px.size:
            continue
        inside = np.zeros(px.shape, bool)
        hits: List[Tuple[int, int]] = []
        for j, (_k, b) in enumerate(boxes):
            if px.max() < b[0] or px.min() > b[2] or py.max() < b[1] or py.min() > b[3]:
                continue
            ib = _in_box(px, py, b)
            n = int(ib.sum())
            if n:
                if line_boxes_free and is_line_box(j):
                    continue
                inside |= ib
                hits.append((j, n))
        own = on & ~inside
        sh = float(own.sum()) / float(px.size)
        if sh < share_min:
            continue
        cross = None
        for j, n in hits:
            tot = ink_of(j)
            bs = n / float(tot) if tot else 0.0
            if bs >= CROSSING_BOX_SHARE and (cross is None or bs > cross[1]):
                cross = (j, bs)
        if cross is not None:
            out["crossings"].append({"stroke": i, "own_px": int(own.sum()), "box": boxes[cross[0]][0], "box_share": round(cross[1], 3),
                                     "box_on_line": round(on_line_share(cross[0]), 3)})
            out["crossing_own_px"] += int(own.sum())
            continue
        out["claimed"].append((i, round(sh, 3)))
        out["own_px"] += int(own.sum())
        out["claimed_px"] += int(px.size)
        out["claimed_px_in_marks"] += int(inside.sum())
    out["line_boxes"] = [[boxes[j][0], round(sh, 3)] for j, sh in sorted(line_boxes.items()) if sh >= 0.0]
    return out


def claim_strokes(res: Any, cell_box: Sequence[float], up: float, trace: Dict[int, Tuple[float, float]],
                  sp_page: float, head_boxes: Sequence[Sequence[float]] = ()) -> List[Tuple[int, float]]:
    """`[(stroke ordinal, share)]` for every stroke of the cell (`stroke_map.CellStrokes`) whose ink lies at least `ON_TRACE_SHARE_MIN` on the curve.
    `head_boxes` (ROADMAP 2.284, canonical cell px x0, y0, x1, y1; empty = as before): pixels inside them are never counted on the curve."""
    out: List[Tuple[int, float]] = []
    masks = getattr(res, "masks", None) or []
    for i, (m, x0, y0) in enumerate(masks):
        if m.size == 0:
            continue
        sh = on_trace_share(m, x0, y0, res.scale, cell_box, up, trace, sp_page, skip_boxes=head_boxes)
        if sh >= ON_TRACE_SHARE_MIN:
            out.append((i, round(sh, 3)))
    return out


def page_strokes_along(page_map: Any, trace: Dict[int, Tuple[float, float]], sp_page: float) -> List[Tuple[int, float]]:
    """ROADMAP 2.260b M3: `[(Q.PAGE_STROKE ordinal, share)]` for every stroke of the PAGE map (`page_strokes.PageMap`: masks in the reduced frame,
    boxes in page px) whose ink lies at least `ON_TRACE_SHARE_MIN` along the traced curve -- the claim's translation from a cell's `[cell, ordinal]`
    to the page's own ids. A page-frame call of `on_trace_share` (cell origin 0, upscale 1)."""
    out: List[Tuple[int, float]] = []
    if page_map is None or not trace:
        return out
    xs = sorted(trace)
    x_lo, x_hi = xs[0], xs[-1]
    y_lo, y_hi = min(a for a, _b in trace.values()), max(b for _a, b in trace.values())
    for i, (m, x0, y0) in enumerate(page_map.masks):
        if m.size == 0:
            continue
        bx, by, bw, bh = page_map.strokes[i].box
        if bx > x_hi or bx + bw < x_lo or by > y_hi or by + bh < y_lo:
            continue
        sh = on_trace_share(m, x0, y0, page_map.scale, (0, 0, 0, 0), 1.0, trace, sp_page)
        if sh >= ON_TRACE_SHARE_MIN:
            out.append((i, round(sh, 3)))
    return out


def page_stroke_extent(page_map: Any, ordinals: Sequence[int]) -> Optional[List[List[float]]]:
    """ROADMAP 2.260b r2: where the arc's own page stroke(s) END -- `[[x_left, y_left], [x_right, y_right]]` in page px: the leftmost / rightmost
    ink column of the union of the named strokes' masks, y = the mean row of that column's ink. No fixed distance: the stroke ends where its ink does."""
    import numpy as np
    if page_map is None or not ordinals:
        return None
    s = float(page_map.scale)
    best_l = best_r = None
    for i in ordinals:
        m, x0, y0 = page_map.masks[i]
        ys, xs = np.nonzero(m)
        if xs.size == 0:
            continue
        for sel, side in ((xs == xs.min(), "l"), (xs == xs.max(), "r")):
            x = (x0 + float(xs[sel][0]) + 0.5) / s
            y = (y0 + float(ys[sel].mean()) + 0.5) / s
            if side == "l" and (best_l is None or x < best_l[0]):
                best_l = [round(x, 1), round(y, 1)]
            if side == "r" and (best_r is None or x > best_r[0]):
                best_r = [round(x, 1), round(y, 1)]
    return None if best_l is None or best_r is None else [best_l, best_r]


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


# ── ROADMAP 2.223: PAGE-WIDE ANCHORING -- bind each claimed curve's two ends to notes, after the heads are read ──────────────────────────────
#
# Sean 2026-10-29 (DECISIONS "CLAIM EARLY, ANCHOR LATE"): GATHER claims each arc page-wide and records its ends; heads are read bar by bar;
# THEN a page-wide pass binds the ends to notes and the kind follows by the tie rule. The unit is the CURVE `gather_system_arcs` traced and
# joined across barlines (`Q.SYSTEM_ARC`), never one cell's box: every box of one printed arc gets ONE binding and so ONE kind.
#
# `OMR_ARC_BIND_PAGEWIDE` (default ON since 2026-10-31, deny-list). Its consumers: `ownership.adjudicate_arc_kind` (the kind from the bound ends),
# `ownership.adjudicate_tie_pair` (a tie's pair is the bound pair) and `export._page_bound_slur_spans` (a slur written ONCE per curve on its
# bound heads). Where the binding cannot decide, each consumer keeps its OFF behaviour and records the binding's abstention beside it.
#
# THE CANDIDATES ARE GATHER'S (rule 6, connect, never guess): the curve's two traced ends (`x_left_page` / `y_left_page`, ... -- GATHER's
# measurement) and the GATHER notehead boxes inside the SAME windows `arcs_system.anchor_ends` used to record its anchors
# (`ANCHOR_OUT_SPACES`, `ANCHOR_IN_SPACES`, `ANCHOR_DY_SPACES`, imported). What is NEW is only that ADJUDICATE's head verdicts are known: a
# box refused as a notehead or relocated to another staff is no longer a candidate, and a chord at an end is resolved by Sean's 2.75 rule
# (an arc ABOVE joins the TOP note of the column, BELOW the BOTTOM; Sean 2026-10-09). Two columns at one end that the windows cannot
# separate by `BIND_COLUMN_MARGIN_SPACES` ABSTAIN with both candidates and the signed margin.
#
# AN END WITH NO HEAD is a SYSTEM EDGE only where no usable head of the staff lies beyond it anywhere in the system (a tie running off the
# system -- also where a courtesy meter or key after the last barline made a cell of its own, which the per-cell test took for a next bar);
# otherwise it is UNBOUND (a head the reader lost) and abstains with the nearest head's distance as its margin.
#
# CONVENTION ASSUMED: Sean's tie rule (page-facts s1, 2026-10-29) and 2.75's top/bottom rule; the windows are 2.166's (set on Litolff 984073
# and Brahms 317803 only). WHAT WOULD FALSIFY IT: a written tie or slur Sean reads as joining other notes; a tie Sean reads as a slur.
# NOT CONFIRMED: `BIND_COLUMN_MARGIN_SPACES` and `BIND_COLUMN_DX_WIDTHS` are set by hand, not swept.

ENV_BIND = "OMR_ARC_BIND_PAGEWIDE"
#: ROADMAP 2.250 (default ON since 2026-11-01; an explicit 0/false/no/off disables): the binder reads the END NOTE's pitch the way the older two-note rule does (the head EXTENT's
#: step, never the box centre) and binds a chord end to the member at the arc END's height (never the outer one by curve side, never a
#: stem-tip proxy's member). CONVENTION ASSUMED (not confirmed by Sean): a tie joins two noteheads of one pitch, a chord has one tie per
#: tied note, each at its own note's staff position. WHAT WOULD FALSIFY IT: a chord tie whose end stands beside one note but ties another.
ENV_END_PITCH = "OMR_BIND_END_PITCH"

#: ROADMAP 2.258 (`OMR_ARC_ONE_CURVE`, default OFF). ONE CURVE, ONE EXTENT: the tracer follows the stroke to where the STROKE ends (not where the
#: detector's box ends + 0.5 sp), records how each pair of its boxes joined (`joins`), and the binder takes a junction of two boxes the trace
#: proved ONE STROKE (shared columns agreeing in y) or a barline's cut (the cell edge lies at the junction) as no junction at all. The Brahms p0
#: guard stands: two whole arcs meeting end to start at one note share no columns, and a note is not a cell edge.
ENV_ONE_CURVE = "OMR_ARC_ONE_CURVE"
#: two boxes whose traces AGREE (one y, `SAME_Y_SPACES`) over at least this many spaces are one stroke seen twice (a head's width is ~1.3 sp;
#: two arcs that MEET at a note agree over the touching columns only). NOT CONFIRMED beyond the measurements in benchmarks/omr-arc-binding-2026-10.
ONE_STROKE_MIN_SPACES = 1.0


#: ROADMAP 2.260b M3 (`OMR_PAGE_CLAIMS`, default ON, deny-list: "0"/"false"/"no"/"off" turns it off; Sean 2026-11-04 "Yes"): the page ledger's claims. It turns on M1 (`OMR_BARLINE_COLUMN_FACT`) and M2 (`OMR_PAGE_STROKES`),
#: builds the page stroke map BEFORE the arcs are traced and erased (so the arc is on the map whole), names the `Q.PAGE_STROKE` ids each traced curve runs
#: along (`page_strokes`, and per piece `piece_strokes`) and reads the curve as ONE curve (the 2.258 extent and junction test).
ENV_PAGE_CLAIMS = "OMR_PAGE_CLAIMS"


def page_claims_enabled() -> bool:
    # default ON, deny-list (copies key_header_ink.enabled)
    return os.environ.get(ENV_PAGE_CLAIMS, "").strip().lower() not in ("0", "false", "no", "off")


def one_curve_enabled() -> bool:
    """`OMR_ARC_ONE_CURVE` (ROADMAP 2.258, default OFF) or `OMR_PAGE_CLAIMS` (2.260b, default ON): on whenever the page claims are on."""
    return _on(ENV_ONE_CURVE) or page_claims_enabled()

#: heads whose centres lie within this many of their own widths in x are one COLUMN (a chord, or two voices at one onset)
BIND_COLUMN_DX_WIDTHS = 0.6
#: at one end, a second column whose distance is within this many staff spaces of the nearest one makes the end ambiguous
BIND_COLUMN_MARGIN_SPACES = 0.5
#: two heads of one chord COLUMN stand at least this many staff spaces apart (a third, 2 staff steps): a smaller step is a second, which an
#: engraver sets in two columns (a CONVENTION, not a fit). Two boxes of one column closer than this are ONE head drawn twice, so there is no
#: chord to choose a member of and the end binds as it did before 2.250 (`bind_end`'s side rule).
BIND_CHORD_MIN_SPACES = 1.0
#: a curve whose middle third sits this far (spaces) above / below the line through its two ends is ABOVE / BELOW its notes
BIND_SIDE_MIN_SPACES = 0.1


def bind_enabled() -> bool:
    """`OMR_ARC_BIND_PAGEWIDE`, default ON (ROADMAP 2.223; Sean 2026-10-31 "Fix then land", tiles 11/12, tile 11 fixed); an explicit 0/false/no/off disables."""
    return os.environ.get(ENV_BIND, "").strip().lower() not in ("0", "false", "no", "off")


def end_pitch_enabled() -> bool:
    """`OMR_BIND_END_PITCH` (ROADMAP 2.250; Sean 2026-11-01 "Land it"), default ON; an explicit 0/false/no/off disables."""
    return os.environ.get(ENV_END_PITCH, "").strip().lower() not in ("0", "false", "no", "off")


def curve_side(trace: Optional[Sequence[Sequence[float]]], sp: float) -> Optional[str]:
    """`above` (a cap, drawn over its notes), `below` (a cup, under them) or None (flat / no trace), from the traced rows
    `[[x, y_top, y_bottom], ...]`: the middle third's mean centre against the chord through the two ends."""
    if not trace or len(trace) < 6 or sp <= 0:
        return None
    pts = sorted((float(t[0]), (float(t[1]) + float(t[2])) / 2.0) for t in trace)
    n = len(pts)
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    mid = pts[n // 3: max(n // 3 + 1, 2 * n // 3)]
    dev = []
    for x, y in mid:
        f = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
        dev.append(y - (y0 + f * (y1 - y0)))
    m = sum(dev) / len(dev)
    if m <= -BIND_SIDE_MIN_SPACES * sp:
        return "above"
    if m >= BIND_SIDE_MIN_SPACES * sp:
        return "below"
    return None


def _columns(cands: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    cols: List[List[Dict[str, Any]]] = []
    for h in sorted(cands, key=lambda h: h["cx"]):
        if cols and abs(h["cx"] - cols[-1][0]["cx"]) <= BIND_COLUMN_DX_WIDTHS * max(h["w"], cols[-1][0]["w"]):
            cols[-1].append(h)
        else:
            cols.append([h])
    return cols


def _chord_member_at_height(col: List[Dict[str, Any]], ey: float, sp: float, heads: Sequence[Dict[str, Any]], ex: float,
                            ok: Any) -> Dict[str, Any]:
    """ROADMAP 2.250: the member of the chord column `col` standing nearest the arc END's height. A stem-tip candidate may name the
    COLUMN (the note) but never the member: the members are the column's real heads (every usable head of the staff at that x, inside the
    window or not). Two members whose distances to `ey` differ by less than `BIND_COLUMN_MARGIN_SPACES` (the m2 hand-set margin, reused,
    no new constant) abstain `chord_end_equidistant`, with both candidates and the signed margin."""
    refs = []
    for h in col:
        if h.get("tip"):
            refs.extend(t for t in heads if not t.get("tip") and t["key"] == h["key"])
        else:
            refs.append(h)
    members: Dict[str, Dict[str, Any]] = {}
    for r in refs:
        for t in heads:
            if t.get("tip") or t["key"] in members or not ok(t["key"]):
                continue
            if abs(t["cx"] - r["cx"]) <= BIND_COLUMN_DX_WIDTHS * max(t["w"], r["w"]):
                members[t["key"]] = t
    if not members:
        return {}
    def is_fused(t: Dict[str, Any]) -> bool:
        # only where the arc end stands BEYOND the box (a tie under / over the outer head of a fused dyad); an end beside the box's middle
        # is read as it always was, by the box centre -- a tall box is not always two heads (a head with its accidental or a line's ink)
        # ... and only where the column holds a SECOND box beside it (a piece or a chord-mate: the corroboration that the tall box is a
        # fused chord). A LONE tall box (a head with a ledger or stem's ink, 3 of Sean's round-1 ties) is not known to be two heads: rule 8,
        # it keeps the reading it had (box centre).
        return (bool(t.get("tall")) and len(members) > 1
                and not (t["cy"] - t["h"] / 2.0 <= ey <= t["cy"] + t["h"] / 2.0))

    def where(t: Dict[str, Any]) -> float:
        # ⚠️ A TALL box is two heads fused (the two-note rule's `half` ends): its centre is neither head's, so a tall member stands at
        # whichever head-sized END of its box is nearer the arc end (`hh` = the staff's mean head height).
        if is_fused(t):
            hh = float(t.get("hh") or t["h"])
            return min((t["cy"] - t["h"] / 2.0 + hh / 2.0, t["cy"] + t["h"] / 2.0 - hh / 2.0), key=lambda y: abs(y - ey))
        return t["cy"]

    ranked = sorted(members.values(), key=lambda t: abs(where(t) - ey))
    if len(ranked) > 1:
        gap = abs(where(ranked[1]) - ey) - abs(where(ranked[0]) - ey)
        if gap < BIND_COLUMN_MARGIN_SPACES * sp:
            if abs(where(ranked[0]) - where(ranked[1])) < BIND_CHORD_MIN_SPACES * sp:
                return {}          # one head drawn twice (members of one chord column are >= a third apart): today's rule decides
            return {"unbound": "chord_end_equidistant", "candidates": [t["key"] for t in ranked[:2]],
                    "margin_spaces": round(gap / sp - BIND_COLUMN_MARGIN_SPACES, 3)}
    pick = ranked[0]
    out = {"head": pick["key"], "column": len(ranked), "by_height": True,
           "distance_spaces": round((abs(pick["cx"] - ex) + abs(where(pick) - ey)) / sp, 3)}
    if (bool(pick.get("tall")) and len(members) == 1 and not is_fused(pick)
            and not (pick["cy"] - pick["h"] / 2.0 <= ey <= pick["cy"] + pick["h"] / 2.0)):
        # a LONE tall box with the arc end beyond it: one head, or a fused chord -- `ownership._page_binding` reads both and abstains
        # where they disagree (rule 8)
        hh = float(pick.get("hh") or pick["h"])
        out["tall_lone"] = True
        out["end_y"] = min((pick["cy"] - pick["h"] / 2.0 + hh / 2.0, pick["cy"] + pick["h"] / 2.0 - hh / 2.0), key=lambda y: abs(y - ey))
    if is_fused(pick):
        out["tall"] = True            # the member is a fused box: its step is unread (`ownership._page_binding`), never its centre's
        out["end_y"] = where(pick)    # ... and its position is the head-sized end the arc stands at, never the box centre
    return out


def bind_end(ex: float, ey: float, sgn: int, heads: Sequence[Dict[str, Any]], sp: float, side: Optional[str],
             usable: Any = None, by_height: bool = False) -> Dict[str, Any]:
    """One end of a curve at page `(ex, ey)`; `sgn` -1 for the left end, +1 for the right. `heads`: `{key, cx, cy, w, h}` of the staff in the
    system (GATHER boxes); `usable(key)` says whether ADJUDICATE left it a notehead of this staff (asked only of heads that could matter).

    Returns `{"head": key, ...}` / `{"edge": True}` / `{"unbound": why, "candidates": [...], "margin_spaces": m}` (m < 0: how far inside the
    cut the refusal came; for `no_head_at_end` how far past the window the nearest usable head lies)."""
    from .arcs_system import ANCHOR_DY_SPACES, ANCHOR_IN_SPACES, ANCHOR_OUT_SPACES
    ok = usable or (lambda _k: True)
    cands = []
    for h in heads:
        out_by = (h["cx"] - ex) * sgn
        if out_by > ANCHOR_OUT_SPACES * sp or out_by < -ANCHOR_IN_SPACES * sp:
            continue
        if abs(h["cy"] - ey) > ANCHOR_DY_SPACES * sp:
            continue
        if not ok(h["key"]):
            continue
        cands.append(dict(h, d=abs(h["cx"] - ex) + abs(h["cy"] - ey)))
    if not cands:
        beyond = sorted((h for h in heads if (h["cx"] - ex) * sgn > -ANCHOR_IN_SPACES * sp),
                        key=lambda h: abs(h["cx"] - ex))
        for h in beyond:
            if ok(h["key"]):
                return {"unbound": "no_head_at_end", "candidates": [h["key"]],
                        "margin_spaces": round((abs(h["cx"] - ex) - ANCHOR_OUT_SPACES * sp) / sp, 3)}
        return {"edge": True}
    cols = sorted(_columns(cands), key=lambda c: min(h["d"] for h in c))
    d0 = min(h["d"] for h in cols[0])
    if len(cols) > 1:
        d1 = min(h["d"] for h in cols[1])
        same_note = {h["key"] for h in cols[0]} & {h["key"] for h in cols[1]}     # a head and its own stem tip: one note
        if (d1 - d0) < BIND_COLUMN_MARGIN_SPACES * sp and not same_note:
            return {"unbound": "two_columns_at_end", "candidates": [[h["key"] for h in c] for c in cols[:2]],
                    "margin_spaces": round((d1 - d0) / sp - BIND_COLUMN_MARGIN_SPACES, 3)}
    col = cols[0]
    if by_height:
        got = _chord_member_at_height(col, ey, sp, heads, ex, ok)
        if got:
            if got.get("head") is not None and all(h.get("tip") for h in col):
                got["via_stem_tip"] = True
            return got
    if len(col) == 1:
        pick = col[0]
    elif side == "above":
        pick = min(col, key=lambda h: h["cy"])
    elif side == "below":
        pick = max(col, key=lambda h: h["cy"])
    else:
        return {"unbound": "chord_end_side_unread", "candidates": [h["key"] for h in col], "margin_spaces": None}
    out = {"head": pick["key"], "column": len(col), "distance_spaces": round(pick["d"] / sp, 3)}
    if pick.get("tip"):
        out["via_stem_tip"] = True
    return out


#: ROADMAP 2.260b r3 (rides `OMR_PAGE_CLAIMS`): a stem's free end stands for the extreme head only within one stem length of it (the engraved
#: stem is 3.5 spaces from the head, Gould; measured on Litolff p10-11 + Brahms p0/p5, 2408 tips: the modal tip stands 3-3.5 sp from its head's
#: centre, 172 at 4-4.5, 72 at 5-5.5, 89 at 6-7.5). A tip farther than this belongs to a head the detector never boxed (a ledger dyad's upper head:
#: Litolff p10 staff 4 cell 9, tip 6.9 sp from the one head boxed, tile 2; staff 5 cell 8, 5.6 sp, tile 9): the tip then names no head and the
#: end is unbound, never bound to the wrong member of the chord. NOT CONFIRMED beyond those pages; it only ever DECLINES a binding.
TIP_MAX_SPACES = 4.5


def stem_tips(heads: Sequence[Dict[str, Any]], stems: Sequence[Sequence[float]], sp: float = 0.0) -> List[Dict[str, Any]]:
    """The free END of each stem box (page `x0, y0, x1, y1`) as a candidate position for the head at that end: `{key, cx, cy, w, h,
    tip: True}`. A stem joins the heads whose boxes touch it (x within a head width of the stem, y overlapping the stem's span +- half a
    head); its free end is the end AWAY from them, and the head it stands for is the extreme head on that side (an up-stem's tip stands
    for the TOP head, a down-stem's for the BOTTOM -- the 2.75 rule, Sean 2026-10-09). A stem touching no head names nothing."""
    out: List[Dict[str, Any]] = []
    for sx0, sy0, sx1, sy1 in stems:
        scx = (sx0 + sx1) / 2.0
        on = [h for h in heads if abs(h["cx"] - scx) <= h["w"] and sy0 - h["h"] / 2.0 <= h["cy"] <= sy1 + h["h"] / 2.0]
        if not on:
            continue
        mean_y = sum(h["cy"] for h in on) / len(on)
        if mean_y > (sy0 + sy1) / 2.0:          # heads at the bottom: an UP stem, free end at the top
            h = min(on, key=lambda t: t["cy"])
            ty = sy0
        else:
            h = max(on, key=lambda t: t["cy"])
            ty = sy1
        far = sp > 0 and abs(ty - h["cy"]) > TIP_MAX_SPACES * sp
        # a tip a stem length and more from its head may stand for a head nobody boxed (`TIP_MAX_SPACES`): kept as a candidate (a TIE through it
        # is the OFF reading, 2.260b r3 measured one such tie right) but marked, and a far tip never supports "different" (see `_page_binding`)
        out.append({"key": h["key"], "cx": scx, "cy": ty, "w": h["w"], "h": h["h"], "cell": h.get("cell", 0), "tip": True, "far": far})
    return out


def bind_curve(detail: Dict[str, Any], heads: Sequence[Dict[str, Any]], sp: float, usable: Any = None,
               by_height: bool = False, alt_ends: Optional[Dict[str, Sequence[float]]] = None) -> Dict[str, Any]:
    """Both ends of one `Q.SYSTEM_ARC` curve (its row's `detail`): `{"left": ..., "right": ..., "side": ...}`; see `bind_end`."""
    side = curve_side(detail.get("trace"), sp)
    xl, yl = detail.get("x_left_page"), detail.get("y_left_page")
    xr, yr = detail.get("x_right_page"), detail.get("y_right_page")
    if None in (xl, yl, xr, yr) or sp <= 0:
        return {"left": {"unbound": "no_traced_end"}, "right": {"unbound": "no_traced_end"}, "side": side}
    left = bind_end(float(xl), float(yl), -1, heads, sp, side, usable, by_height)
    right = bind_end(float(xr), float(yr), +1, heads, sp, side, usable, by_height)
    if alt_ends:
        # ROADMAP 2.260b r2 (OMR_PAGE_CLAIMS): an end that bound NO head at the traced end is tried once more at the end of the curve's own page
        # stroke; an end that bound a head (the OFF reading) is never moved
        for side_, sgn_ in (("left", -1), ("right", +1)):
            cur = left if side_ == "left" else right
            alt = alt_ends.get(side_)
            if alt is not None and cur.get("unbound") == "no_head_at_end":
                got = bind_end(float(alt[0]), float(alt[1]), sgn_, heads, sp, side, usable, by_height)
                if got.get("head") is not None:
                    got["via_stroke_end"] = True
                    if side_ == "left":
                        left = got
                    else:
                        right = got
    if left.get("head") is not None and left.get("head") == right.get("head"):
        left = right = {"unbound": "one_head_both_ends", "candidates": [left["head"]], "margin_spaces": None}
    return {"left": left, "right": right, "side": side}


def heads_between(a: Dict[str, Any], b: Dict[str, Any], heads: Sequence[Dict[str, Any]], usable: Any = None) -> List[str]:
    """Usable heads of the staff strictly between the two bound heads in x, a head in either end's own column (its chord) excepted."""
    ok = usable or (lambda _k: True)
    lo, hi = (a, b) if a["cx"] <= b["cx"] else (b, a)
    out = []
    for h in heads:
        if h["key"] in (a["key"], b["key"]) or not (lo["cx"] < h["cx"] < hi["cx"]):
            continue
        if abs(h["cx"] - lo["cx"]) <= BIND_COLUMN_DX_WIDTHS * max(h["w"], lo["w"]) \
                or abs(h["cx"] - hi["cx"]) <= BIND_COLUMN_DX_WIDTHS * max(h["w"], hi["w"]):
            continue
        if ok(h["key"]):
            out.append(h["key"])
    return out
