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


#: ROADMAP 2.271 step 3 (Sean 2026-11-05 "Anything that needs to be done to connect arc separated by systems is fine"), default OFF: EXPORT joins an arc
#: that runs off one system's edge to the piece that picks up at the next system's edge, on the same part's staff, when exactly one fits.
ENV_ACROSS_SYSTEMS = "OMR_ARC_ACROSS_SYSTEMS"


#: ROADMAP 2.271 (page-facts, Sean 2026-11-05 "Often arcs stop short. Closest note works"), default OFF: an arc end with no head in the window binds to the closest one beyond it.
ENV_CLOSEST_HEAD = "OMR_ARC_CLOSEST_HEAD"


def closest_head_enabled() -> bool:
    return _on(ENV_CLOSEST_HEAD)


#: ROADMAP 2.281 (Sean 2026-11-09 plan; FINDINGS "2.281"), default ON since 2.305 landing: a page-ink run's end whose closest head has ANOTHER curve starting at the SAME head (two arcs meeting at a note: A ends
#: on it, B begins on it) is not "half of one arc" -- both bind to that head. Without the flag `bind_end` refuses with `continues_in_another_curve`.
ENV_MEETING_AT_HEAD = "OMR_ARC_MEETING_AT_HEAD"


def meeting_at_head_enabled() -> bool:
    """`OMR_ARC_MEETING_AT_HEAD`, default ON since ROADMAP 2.305's landing (deny-list; `=0` opts out)."""
    return os.environ.get(ENV_MEETING_AT_HEAD, "1").strip().lower() not in ("0", "false", "no", "off")


def across_systems_enabled() -> bool:
    return _on(ENV_ACROSS_SYSTEMS)


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


#: ROADMAP 2.284b r2 (Sean 2026-11-10, tile 3: a `ledgerLine` box lying along an arc is "part of an arc"): a LINE-class mark box (`LINE_BOX_CLASSES`:
#: its own ink is a line, so it can be a stretch of another line) whose ink lies at least this share ON THE MARK'S OWN LINE (the arc's traced
#: curve) is a false box on that line's ink, not a mark it crosses -- it protects nothing and is no crossing. A head, dot, flat, fermata or
#: letter is never a stretch of a curve, whatever its share (measured on Litolff p2/4/6/10 with the first cut 0.5 and every class: 7 half-note
#: heads at 0.52-0.77, 4 dots, 3 fermatas, a flat and a clef at 1.0 were "on the line" -- a band of 0.12 sp round a slur holds any small mark).
#: The cut is a MEASUREMENT, n = 1 judged (tile 3, 0.90; the other 10 ledger boxes of the four pages lie at 0.54-0.83): it only NARROWS the
#: crossing rule, and the near-misses go to Sean as blind tiles (CLAUDE §4). `box_on_line` is in every crossing row, `line_boxes` in the claim.
BOX_ON_LINE_MIN = 0.85
LINE_BOX_CLASSES = ("ledgerLine",)


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
                 mark_boxes: Sequence[Tuple[str, Sequence[float]]], line_box_keys: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """The ARC's pixel claim (`claim_pixels_on` with the traced curve as the `on` test). See `claim_pixels_on`."""
    if not trace:
        return claim_pixels_on(res, cell_box, up, None, mark_boxes)
    return claim_pixels_on(res, cell_box, up, lambda px, py: _on_curve(px, py, trace, sp_page), mark_boxes, line_box_keys=line_box_keys)


def claim_pixels_on(res: Any, cell_box: Sequence[float], up: float, on_fn: Any, mark_boxes: Sequence[Tuple[str, Sequence[float]]],
                    share_min: float = ON_TRACE_SHARE_MIN, line_boxes_free: bool = True, line_box_keys: Optional[Sequence[str]] = None
                    ) -> Dict[str, Any]:
    """PURE. ROADMAP 2.284b (flag `OMR_PAGE_LEDGER_OWNS`): a page-wide line mark's claim (the arc's traced curve; the hairpin's arms,
    `hairpin_reach`) on ONE cell's strokes, pixel-honest. `on_fn(px, py)` -> bool array: the pixels (page px) that lie on the mark's own line.

    `mark_boxes` = `[(box key, (x0, y0, x1, y1) PAGE px)]`: every other mark's detector box that meets the cell, from ANY cell or staff of the
    page (a padded cell sees the neighbour cell's and the neighbour staff's ink; r4: the 3 boxes still held >= 0.5 on p2 were all held through
    a neighbour view whose own detections did not hold the box). A pixel inside one is never the arc's own (the 2.166 eraser protects them).

      * a stroke is a candidate where at least `ON_TRACE_SHARE_MIN` of its pixels lie on the traced curve AND outside every mark box;
      * a candidate holding `CROSSING_BOX_SHARE` or more of some mark box's own ink is a CROSSING: marked (its own on-curve pixels counted),
        never taken -- the stroke is left to the stroke owner's other claimants;
      * a LINE-class mark box (`line_box_keys`: the keys of the `LINE_BOX_CLASSES` boxes; none = the rule is off) whose own ink lies at least
        `BOX_ON_LINE_MIN` on the mark's own line is that line's ink (`line_boxes_free`, ROADMAP 2.284b r2; False = r6's rule, the control): it
        protects nothing, is no crossing;
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
    keyset = set(line_box_keys or ())
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
            sh = on_line_share(j) if boxes[j][0] in keyset else 0.0
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
            elif acc == "restated":
                pos, rule = "tie", "two_notes_same_pitch_restated"          # ROADMAP 2.344: the stop's printed accidental says what the start already is
            elif acc == "changed":
                pos, rule = "slur", "two_notes_pitch_changed_by_accidental"   # ROADMAP 2.344: never a tie between notes of different pitch
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


#: ROADMAP 2.344 (Sean 2026-11-24, DECISIONS "AN ARC BETWEEN THE SAME NOTES IS A TIE"; default ON, deny-list -- the flag exists so a lane report can A/B it):
#: a printed accidental on the tied-to note that says what the start note already is (a courtesy) is no reason to call the arc a slur; one that CHANGES it still is.
ENV_TIE_SAME_NOTES = "OMR_ARC_TIE_SAME_NOTES"


def tie_same_notes_enabled() -> bool:
    return os.environ.get(ENV_TIE_SAME_NOTES, "").strip().lower() not in ("0", "false", "no", "off")


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


# ── ROADMAP 2.305 r6: THE RULE, NOT A REACH WINDOW ────────────────────────────────────────────────────────────────────────────────────────
#
# Sean, 2026-11-15 (page-facts "An arc ends at the notes standing where its ink ends"): "An arc ends at the notes standing where its ink ends, on
# the staff it sits over. It often stops a little short of them; then it belongs to the closest of those notes. It never reaches past a nearer note
# to a farther one, and never to a note on another staff. Where two notes are about equally close, we don't choose."
#
# The reach numbers (`arcs_system.ANCHOR_OUT_SPACES` 1.6 ahead / `ANCHOR_IN_SPACES` 0.8 behind for a detector curve; `page_arc_bind.HEAD_BEHIND_END_SPACES`,
# `OWN_BAR_BEHIND_SPACES`, `END_REACH_SPACES` for a page-ink run) were never the rule: they guard OUR failure, a note the detector never boxed, where the arc
# would take the next note along (Sean approved, 2026-11-15: "That is the way"). With the rule ON (`rule_enabled`, which rides `OMR_PAGE_ARC_WRITE`) the
# end binds the CLOSEST usable note of its own staff, measured from the ink's end to the head's ink, in either direction and at any distance; two columns
# about equally close abstain (`two_columns_at_end`, the binder's one margin `BIND_COLUMN_MARGIN_SPACES`, beside the rule); and the failure is guarded
# directly: HEAD-SHAPED INK THAT NO READER HAS READ (`unread_head_ink`: page-ink blobs of a head's size no detector box of any class stands on) standing at
# least as near the end as that note -> "cannot tell" (`unread_ink_at_end`), the ink and the note both named, with the signed margin. Other staves' notes
# never reach the binder: the caller hands it the arc's own staff only (`ownership._page_binding`).

#: the reason word: head-shaped ink no reader has read stands at the arc's end at least as near as the closest note
UNREAD_INK_AT_END = "unread_ink_at_end"
#: the reason word: a note of a neighbouring staff stands at the arc's end at least about as near as this staff's closest note (`unread` items with
#: `other_staff`, handed in by `ownership._page_binding`): the ink does not sit over this staff's notes there -- never a binding to another staff's note
NEARER_NOTE_ON_ANOTHER_STAFF = "nearer_note_on_another_staff"
#: detector classes of LINE and CURVE marks (staff, ledger, beam, stem, tie, slur, brace): such a box is where a thin stroke runs, it reads no blob under it
#: (a beam's box spans the heads below it: Brahms p11 staff 2 bar 8, box 8/19 over the tied head 8/2). Every other class's box -- a head, a dot, a rest, an
#: accidental, a flag, a letter, a clef -- reads the ink it stands on.
LINE_MARK_CLASSES = ("staff", "ledgerline", "beam", "stem", "tie", "slur", "brace", "bracket")


def reads_ink(cls: Any) -> bool:
    """ROADMAP 2.305 r6: whether a detector box of class `cls` reads the blob it stands on (`LINE_MARK_CLASSES` do not)."""
    return str(cls or "").lower() not in LINE_MARK_CLASSES


def rule_enabled() -> bool:
    """ROADMAP 2.305 r6: the ends rule replaces the reach windows when `OMR_PAGE_ARC_WRITE` is ON (default ON since 2.305's landing; `=0` opts out)."""
    from .page_arc_bind import write_enabled
    return write_enabled()


def unread_head_ink(strokes: Sequence[Dict[str, Any]], boxes: Sequence[Sequence[float]], sp: float,
                    claimed_strokes: Optional[Any] = None, head_boxes: Optional[Sequence[Sequence[float]]] = None,
                    ledger_boxes: Optional[Sequence[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """ROADMAP 2.305 r6: the page strokes that are a notehead's INK by the page-head reader's own shape test (`page_heads`, ROADMAP 2.260e M6a: a blob of at
    least `HEAD_MIN_AREA_SP2`, at most `HEAD_MAX_W_SP` x `HEAD_MAX_H_SP` of its own staff space) that NO reader has read: no detector box of ANY class and no
    claimed area of the page ledger (`Q.CLAIMED_AREA` with a box value: a printed word, a clef, a barline, a key ...) stands on its centre, and no page-ink
    claim names it (`claimed_strokes`: the `Q.PAGE_STROKE` ordinals a `page_ink` claim holds -- a rest, a head's oval, a tremolo, an accidental). `strokes`:
    `Q.PAGE_STROKE` details (+ `id`, `kind`), every kind (a blob is a note only on a stem); `boxes`: page boxes. Returns `{id, ordinal, cx, cy, w, h,
    staff}` per such blob. GATHER's old census (`page_heads.read`, `ink_only`, retired 2.332) filed the same fact behind `OMR_PAGE_HEADS` (OFF); this reads the same filed
    rows with the same numbers, no new one, and asks the census's stem clause in its wider form: the blob TOUCHES A STEM (a vertical stroke at least
    `page_heads.STEM_MIN_LEN_SP` long) -- the census asks for a stem a BOXED head touches; an arc's unboxed note may stand on its own stem. Measured on the
    2.310 rows (Brahms p11): without the stem clause the tips of the arcs' own ink and an accidental's piece read as unread heads. NOT SEEN: a whole note
    nobody boxed (no stem) -- the guard then does not stand, and the end binds the closest note it can see."""
    from .page_heads import HEAD_MAX_H_SP, HEAD_MAX_W_SP, HEAD_MIN_AREA_SP2, STEM_MIN_LEN_SP
    out: List[Dict[str, Any]] = []
    taken = set(claimed_strokes or ())
    stems = {s.get("ordinal") for s in strokes if s.get("kind") == "vertical" and float(s.get("length_spaces") or 0.0) >= STEM_MIN_LEN_SP}
    for s in strokes:
        if s.get("kind") != "blob" or s.get("ordinal") in taken:
            continue
        if not any(t and t[0] in stems for t in (s.get("touches") or ())):
            continue
        b = s.get("bbox_page_px")
        if not b or len(b) != 4:
            continue
        x0, y0, x1, y1 = (float(v) for v in b)
        w, h = x1 - x0, y1 - y0
        spl = float(s.get("staff_space_local_px") or sp or 0.0)
        if spl <= 0 or w <= 0 or h <= 0:
            continue
        area = float(s.get("fill") or 0.0) * w * h / (spl * spl)
        if not (area >= HEAD_MIN_AREA_SP2 and w <= HEAD_MAX_W_SP * spl and h <= HEAD_MAX_H_SP * spl):
            continue
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        if any(bb[0] <= cx <= bb[2] and bb[1] <= cy <= bb[3] for bb in boxes):
            continue
        # r7 (Sean's r6 tile 12, Brahms p0 `0/0/5/4/15`: the box is drawn low on its half note and the ledger line cuts the head's top off as its own blob):
        # a blob that, joined with a read note's box beside it (sharing its x), is still no bigger than ONE head (the same shape numbers) is that note's ink
        if any(min(x1, hb[2]) > max(x0, hb[0])
               and max(y1, hb[3]) - min(y0, hb[1]) <= HEAD_MAX_H_SP * spl and max(x1, hb[2]) - min(x0, hb[0]) <= HEAD_MAX_W_SP * spl
               for hb, _st in (head_boxes or ())):
            continue
        out.append({"id": s.get("id"), "ordinal": s.get("ordinal"), "cx": cx, "cy": cy, "w": w, "h": h, "staff": list(s.get("staff") or ())})
    # r7 (Sean's r6 tile 3, Litolff p13 `13/1/0/9`: a half-note chord on ledger lines nobody boxed; its hollow heads are shattered by the ledgers, so no blob of
    # a head's size is there): page-facts "the ledger lines name the owner ... there is no far note without one" -- a ledger line is drawn only for a note,
    # so a COLUMN of ledger lines in which no read note stands is a note nobody read. Each such ledger stands for it (its own box: where to look).
    from .page_heads import RUNG_OUTSIDE_STEPS
    for lb in (ledger_boxes or ()):
        lx0, ly0, lx1, ly1 = lb["box"]
        lines = lb.get("lines")
        if lines and len(lines) == 5:
            # a ledger stands OUTSIDE the staff body (`page_heads`' own rung test): a "ledger" box on the staff's own lines is a staff line's piece (Litolff p13
            # `13/1/1/9/8`, r7's first replay: the second line of the staff boxed as a ledger, read as a note nobody read)
            hs = (float(lines[-1]) - float(lines[0])) / 8.0
            pos = (((ly0 + ly1) / 2.0) - float(lines[0])) / hs if hs > 0 else 0.0
            if not (pos <= -RUNG_OUTSIDE_STEPS or pos >= 8 + RUNG_OUTSIDE_STEPS):
                continue
        if any(lx0 <= (hb[0] + hb[2]) / 2.0 <= lx1 and list(st) == list(lb.get("staff") or ()) for hb, st in (head_boxes or ())):
            continue
        out.append({"id": lb.get("id"), "ordinal": "ledger:" + str(lb.get("key")), "cx": (lx0 + lx1) / 2.0, "cy": (ly0 + ly1) / 2.0,
                    "w": lx1 - lx0, "h": max(ly1 - ly0, 1.0), "staff": list(lb.get("staff") or ()), "ledger": True})
    return out


def _ink_xy(h: Dict[str, Any]) -> Tuple[float, float]:
    """the head's INK centre where the record holds one (2.290's page head, `ink_cx`/`ink_cy`), else its box centre (CLAUDE §4: measure the mark)"""
    return (float(h.get("ink_cx", h["cx"])), float(h.get("ink_cy", h["cy"])))


def _to_head(h: Dict[str, Any], ex: float, ey: float) -> float:
    """How far the ink's end at `(ex, ey)` stops short of the head `h`: the straight distance to the head's own extent (its box size, standing at its ink
    centre where the record holds one), 0 inside it. An arc stops short of the head's EDGE, never of its centre: measured to the centre, a cup's end just
    under a head (1.1 spaces below the centre, at the head's foot) read farther than a second head 2 spaces to the side at the end's own height (Litolff p13
    `13/1/1/11/8`, Sean's 2.305 r2 tile 1, a tie)."""
    hx, hy = _ink_xy(h)
    dx = max(0.0, abs(hx - ex) - float(h["w"]) / 2.0)
    dy = max(0.0, abs(hy - ey) - float(h["h"]) / 2.0)
    return (dx * dx + dy * dy) ** 0.5


def _bind_end_by_rule(ex: float, ey: float, sgn: int, heads: Sequence[Dict[str, Any]], sp: float, side: Optional[str], ok: Any, by_height: bool,
                      others: Optional[Sequence[Tuple[float, float]]], unread: Optional[Sequence[Dict[str, Any]]],
                      meet_back: float) -> Dict[str, Any]:
    """ROADMAP 2.305 r6 (the block above): one end by Sean's rule. `heads` are the arc's OWN staff's (the caller's); `unread` the unread head ink of that staff.
    `meet_back` is the caller's look-behind as 2.281's meeting test used it (`OMR_ARC_MEETING_AT_HEAD`, its own windows, unchanged); it never picks a note."""
    from .arcs_system import ANCHOR_IN_SPACES
    if not any(ok(h["key"]) for h in heads):
        return {"edge": True}          # (the caller tests the system's edge first: `bind_curve`, `page_arc_bind.closest_binder`, each unchanged)
    cands = []
    for h in heads:
        if ok(h["key"]):
            cands.append(dict(h, d=_to_head(h, ex, ey)))
    cands.sort(key=lambda h: h["d"])
    hh = cands[0]
    # another curve of the staff BEGINS nearer this end than the closest note stands: this curve is half of one arc (2.271's test, no number), unless both stand
    # AT that note (2.281, `OMR_ARC_MEETING_AT_HEAD`): unchanged
    offenders = [(ox, oy) for ox, oy in (others or ())
                 if abs(ox - ex) + abs(oy - ey) < min(abs(hh["cx"] - ex) + abs(hh["cy"] - ey), abs(ox - hh["cx"]) + abs(oy - hh["cy"]))
                 and (ox - ex) * sgn > -ANCHOR_IN_SPACES * sp]          # (2.271's own measure, centre to end, unchanged)
    if offenders and meeting_at_head_enabled():
        from .arcs_system import ANCHOR_DY_SPACES as _DY, ANCHOR_OUT_SPACES as _OUT

        def _at(x: float, y: float, s_: int) -> bool:
            out = (hh["cx"] - x) * s_
            return -meet_back * sp < out <= _OUT * sp and abs(hh["cy"] - y) <= _DY * sp
        if _at(ex, ey, sgn) and all(_at(ox, oy, -sgn) for ox, oy in offenders):
            offenders = []
    if offenders:
        return {"unbound": "continues_in_another_curve", "candidates": [hh["key"]], "margin_spaces": None}
    cols = sorted(_columns(cands[:12]), key=lambda c: min(h["d"] for h in c))
    d0 = min(h["d"] for h in cols[0])
    second = None          # the signed margin by which the closest note beat the next (kept on a binding: both sides of "about equally close")
    if len(cols) > 1:
        d1 = min(h["d"] for h in cols[1])
        same_note = {h["key"] for h in cols[0]} & {h["key"] for h in cols[1]}
        if (d1 - d0) < BIND_COLUMN_MARGIN_SPACES * sp and not same_note:
            return {"unbound": "two_columns_at_end", "candidates": [[h["key"] for h in c] for c in cols[:2]],
                    "margin_spaces": round((d1 - d0) / sp - BIND_COLUMN_MARGIN_SPACES, 3)}
        second = {"next": [h["key"] for h in cols[1]], "margin_spaces": round((d1 - d0) / sp - BIND_COLUMN_MARGIN_SPACES, 3)}
    # another staff's note counts only on the arc's OWN side of its end (page-facts: an arc is OVER its notes -- a cap's notes stand below it, a cup's above);
    # one on the far side cannot be this ink's note (two staves close together: Litolff p13 run 31, the cup under staff 8's tie over staff 9's notes)
    # ... and a box that is one of this staff's own heads boxed again in the other staff's cell (2.290: two boxes on one head are ONE head, `page_heads.FOLD_IOU`)
    # is this staff's note, not another's
    from .page_heads import FOLD_IOU, iou

    def _box(h: Dict[str, Any]) -> Tuple[float, float, float, float]:
        return (h["cx"] - h["w"] / 2.0, h["cy"] - h["h"] / 2.0, h["cx"] + h["w"] / 2.0, h["cy"] + h["h"] / 2.0)
    own_boxes = [_box(h) for h in heads if not h.get("tip")]
    other = [u for u in (unread or ()) if u.get("other_staff")
             and not (side == "above" and u["cy"] < ey) and not (side == "below" and u["cy"] > ey)
             and not any(iou(_box(u), ob_) >= FOLD_IOU for ob_ in own_boxes)]
    if other:
        ob = min(other, key=lambda u: _to_head(u, ex, ey))
        do = _to_head(ob, ex, ey)
        if do - d0 < BIND_COLUMN_MARGIN_SPACES * sp:
            # a note of ANOTHER staff stands at the end at least about as near as this staff's closest note: the ink does not sit over this staff's notes there
            # ("never to a note on another staff"; the caller hands in the neighbouring staves' notes for this test only, never as candidates)
            return {"unbound": NEARER_NOTE_ON_ANOTHER_STAFF, "candidates": [[h["key"] for h in cols[0]], ob.get("key")],
                    "margin_spaces": round((do - d0) / sp - BIND_COLUMN_MARGIN_SPACES, 3)}
    # r7 (Sean's r6 tile 8, Brahms p0: "there's no arc ... there is a slur above it" -- the slur over the staff BELOW was handed this staff's notes, which stand
    # wholly above its ends): page-facts, an arc is OVER its notes -- a cap's note never stands wholly above its end, a cup's never wholly below. The closest
    # note on that far side is not this ink's note: refuse, naming it (the 2.223 window's 2.5-space height limit was this guard, unstated). A stem's tip
    # stands for its head on purpose and is exempt.
    near = [h for h in cols[0] if not h.get("tip")]
    if near and side in ("above", "below") and all(
            ((_ink_xy(h)[1] + h["h"] / 2.0) < ey if side == "above" else (_ink_xy(h)[1] - h["h"] / 2.0) > ey) for h in near) \
            and len(near) == len(cols[0]):
        return {"unbound": "head_on_the_arcs_far_side", "candidates": [h["key"] for h in near],
                "margin_spaces": round(-min(abs(_ink_xy(h)[1] - ey) - h["h"] / 2.0 for h in near) / sp, 3)}
    unread = [u for u in (unread or ()) if not u.get("other_staff")]
    if unread:
        ub = min(unread, key=lambda u: _to_head(u, ex, ey))          # the unread ink measured exactly as a note is
        du = _to_head(ub, ex, ey)
        if du - d0 < BIND_COLUMN_MARGIN_SPACES * sp:
            # head-shaped ink nobody has read stands at the end at least about as near as the closest note: the note the arc ends at may be that ink -- cannot tell
            return {"unbound": UNREAD_INK_AT_END, "candidates": [[h["key"] for h in cols[0]], "page_stroke:%s" % ub.get("ordinal")],
                    "margin_spaces": round((du - d0) / sp - BIND_COLUMN_MARGIN_SPACES, 3), "unread_row": ub.get("id"),
                    "unread_xy": [round(ub["cx"], 1), round(ub["cy"], 1)]}
    col = cols[0]
    out: Dict[str, Any]
    if by_height:
        got = _chord_member_at_height(col, ey, sp, heads, ex, ok)
        if got:
            if got.get("head") is not None and all(h.get("tip") for h in col):
                got["via_stem_tip"] = True
            got["by_rule"] = True
            if second is not None and got.get("head") is not None:
                got["second"] = second
            return got
    if len(col) == 1:
        pick = col[0]
    elif side == "above":
        pick = min(col, key=lambda h: h["cy"])
    elif side == "below":
        pick = max(col, key=lambda h: h["cy"])
    else:
        return {"unbound": "chord_end_side_unread", "candidates": [h["key"] for h in col], "margin_spaces": None}
    out = {"head": pick["key"], "column": len(col), "distance_spaces": round(pick["d"] / sp, 3), "by_rule": True}
    if second is not None:
        out["second"] = second
    if pick.get("tip"):
        out["via_stem_tip"] = True
    return out


def bind_end(ex: float, ey: float, sgn: int, heads: Sequence[Dict[str, Any]], sp: float, side: Optional[str],
             usable: Any = None, by_height: bool = False, closest_ok: Optional[bool] = None,
             others: Optional[Sequence[Tuple[float, float]]] = None, closest_only: bool = False,
             behind_spaces: Optional[float] = None, by_rule: bool = False,
             unread: Optional[Sequence[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """One end of a curve at page `(ex, ey)`; `sgn` -1 for the left end, +1 for the right. `heads`: `{key, cx, cy, w, h}` of the staff in the
    system (GATHER boxes); `usable(key)` says whether ADJUDICATE left it a notehead of this staff (asked only of heads that could matter).

    Returns `{"head": key, ...}` / `{"edge": True}` / `{"unbound": why, "candidates": [...], "margin_spaces": m}` (m < 0: how far inside the
    cut the refusal came; for `no_head_at_end` how far past the window the nearest usable head lies).

    ROADMAP 2.274 step 2 (`closest_only`, `behind_spaces`; both off by default, so the detector-curve callers are unchanged): a PAGE-INK run's end is where its ink stops,
    carried on to the note by the step-1 extension (up to `page_arcs.EXT_MAX_SP`) and so it can stand PAST the note it stops at (Brahms p0: 1.4 spaces). The 2.166 window
    (a head 1.6 spaces ahead / 0.8 behind) would then pass over the note behind the end for one further on. `closest_only` skips the window and takes the closest usable head
    by distance, heads up to `behind_spaces` behind the end included; two columns about equally near still abstain."""
    from .arcs_system import ANCHOR_DY_SPACES, ANCHOR_IN_SPACES, ANCHOR_OUT_SPACES
    ok = usable or (lambda _k: True)
    if by_rule:
        # ROADMAP 2.305 r6: Sean's rule, no window (`_bind_end_by_rule`)
        return _bind_end_by_rule(ex, ey, sgn, heads, sp, side, ok, by_height, others, unread,
                                 ANCHOR_IN_SPACES if behind_spaces is None else behind_spaces)
    back = ANCHOR_IN_SPACES if behind_spaces is None else behind_spaces
    cands = []
    for h in (() if closest_only else heads):
        out_by = (h["cx"] - ex) * sgn
        if out_by > ANCHOR_OUT_SPACES * sp or out_by < -ANCHOR_IN_SPACES * sp:
            continue
        if abs(h["cy"] - ey) > ANCHOR_DY_SPACES * sp:
            continue
        if not ok(h["key"]):
            continue
        cands.append(dict(h, d=abs(h["cx"] - ex) + abs(h["cy"] - ey)))
    closest = False
    if not cands and (closest_head_enabled() if closest_ok is None else closest_ok):
        # ROADMAP 2.271 (`OMR_ARC_CLOSEST_HEAD`; page-facts, Sean 2026-11-05 "Often arcs stop short. Closest note works"): no head inside the window
        # -> the heads BEYOND the end on the curve's own side (the staff's own usable heads), the closest one binds; two about equally near
        # (the binder's own column margin, no new number) stay the `two_columns_at_end` refusal below, never a pick. No fixed distance.
        near = sorted((dict(h, d=abs(h["cx"] - ex) + abs(h["cy"] - ey)) for h in heads if (h["cx"] - ex) * sgn > -back * sp),
                      key=lambda h: h["d"])
        picked: List[Dict[str, Any]] = []
        for h in near[:8]:
            if ok(h["key"]):
                picked.append(h)
        if picked:
            # another curve of the staff BEGINS (its opposite end stands) nearer this end than the closest head does: this curve is half of one
            # arc and the other half is what reaches the note (Sean's tiles 2, 4, 5, 9, 10, 12) -- no number, the head's own distance is the bound
            # (and it stands nearer this end than the head does: a second arc that begins AT the head is a chain of two arcs, not a continuation)
            hh = picked[0]
            offenders = [(ox, oy) for ox, oy in (others or ())
                         if abs(ox - ex) + abs(oy - ey) < min(hh["d"], abs(ox - hh["cx"]) + abs(oy - hh["cy"])) and (ox - ex) * sgn > -ANCHOR_IN_SPACES * sp]
            if offenders and meeting_at_head_enabled():
                # ROADMAP 2.281 (the cause: on Brahms legato the next arc BEGINS on the very head this one ends on and its ink starts at the head's edge, so its start always stands nearer
                # than the head's centre -- the test above cannot tell "half of one arc" from "two arcs meet at a note"). A curve that stands AT the head -- this end inside the binder's own
                # head windows (`ANCHOR_OUT_SPACES` ahead, `back` behind, `ANCHOR_DY_SPACES` high: 2.166's numbers and round 2's look-behind, no new number) and every offending end inside
                # the same windows measured the other way -- does not continue this arc: both attach to the head. A head far from this end (the half of an arc: ties along a chord,
                # the arc beyond a barline) keeps the refusal.
                from .arcs_system import ANCHOR_DY_SPACES as _DY, ANCHOR_OUT_SPACES as _OUT

                def _at(x: float, y: float, s_: int) -> bool:
                    out = (hh["cx"] - x) * s_
                    return -back * sp < out <= _OUT * sp and abs(hh["cy"] - y) <= _DY * sp
                if _at(ex, ey, sgn) and all(_at(ox, oy, -sgn) for ox, oy in offenders):
                    offenders = []
            if offenders:
                return {"unbound": "continues_in_another_curve", "candidates": [picked[0]["key"]], "margin_spaces": None}
            cands, closest = picked, True
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
            if closest:
                got["via_closest"] = True
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
    if closest:
        out["via_closest"] = True
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
               by_height: bool = False, alt_ends: Optional[Dict[str, Sequence[float]]] = None,
               closest_sides: Optional[Dict[str, bool]] = None,
               other_ends: Optional[Dict[str, Sequence[Tuple[float, float]]]] = None,
               unread: Optional[Sequence[Dict[str, Any]]] = None, by_rule: Optional[bool] = None) -> Dict[str, Any]:
    """Both ends of one `Q.SYSTEM_ARC` curve (its row's `detail`): `{"left": ..., "right": ..., "side": ...}`; see `bind_end`.

    ROADMAP 2.305 r6 (`by_rule`, default `rule_enabled()`): each end is measured where the INK ends (the curve's own page stroke end, `alt_ends`, where the
    record holds one; else the traced end) and bound by Sean's rule (`_bind_end_by_rule`): no reach window, the closest note of the staff, `unread` head
    ink guarding the end. An end with no usable note ahead of it (2.223's edge test) is the system's edge, as before. A curve 2.271 found to lie inside a
    printed word or a hairpin (`closest_sides` False) is that mark's ink (claim order, CLAUDE s3): its end binds nothing (`inside_a_word_or_wedge`)."""
    side = curve_side(detail.get("trace"), sp)
    xl, yl = detail.get("x_left_page"), detail.get("y_left_page")
    xr, yr = detail.get("x_right_page"), detail.get("y_right_page")
    if None in (xl, yl, xr, yr) or sp <= 0:
        return {"left": {"unbound": "no_traced_end"}, "right": {"unbound": "no_traced_end"}, "side": side}
    cs = closest_sides or {}
    if rule_enabled() if by_rule is None else by_rule:
        from .arcs_system import ANCHOR_IN_SPACES
        ok = usable or (lambda _k: True)
        ends: Dict[str, Dict[str, Any]] = {}
        for side_, sgn_, xe, ye in (("left", -1, xl, yl), ("right", +1, xr, yr)):
            alt = (alt_ends or {}).get(side_)
            if alt is not None and (float(alt[0]) - float(xe)) * sgn_ > 0:
                # r7 (Sean's r6 tile 8, Brahms p0 `0/0/11/3/15`: the page map carves the barline out of a slur that crosses it, so the curve's page stroke ends AT
                # the barline while the traced ink runs on before the bar): the ink ends at the OUTERMOST of the traced end and the stroke end
                xe, ye = alt[0], alt[1]
            xe, ye = float(xe), float(ye)
            if cs.get(side_) is False:
                ends[side_] = {"unbound": "inside_a_word_or_wedge", "candidates": [], "margin_spaces": None}
                continue
            if not any((h["cx"] - xe) * sgn_ > -ANCHOR_IN_SPACES * sp and ok(h["key"]) for h in heads) \
                    and not any((u["cx"] - xe) * sgn_ > -ANCHOR_IN_SPACES * sp for u in (unread or ()) if not u.get("other_staff")):
                ends[side_] = {"edge": True}          # (r8: note-like ink nobody read ahead of the end is a note there, not the edge)
                continue
            got = bind_end(xe, ye, sgn_, heads, sp, side, usable, by_height, others=(other_ends or {}).get(side_), by_rule=True, unread=unread)
            got["end_xy"] = [round(xe, 1), round(ye, 1)]
            ends[side_] = got
        left, right = ends["left"], ends["right"]
        if left.get("head") is not None and left.get("head") == right.get("head"):
            left = right = {"unbound": "one_head_both_ends", "candidates": [left["head"]], "margin_spaces": None}
        return {"left": left, "right": right, "side": side, "by_rule": True}
    left = bind_end(float(xl), float(yl), -1, heads, sp, side, usable, by_height, False)
    right = bind_end(float(xr), float(yr), +1, heads, sp, side, usable, by_height, False)
    if alt_ends:
        # ROADMAP 2.260b r2 (OMR_PAGE_CLAIMS): an end that bound NO head at the traced end is tried once more at the end of the curve's own page
        # stroke; an end that bound a head (the OFF reading) is never moved
        for side_, sgn_ in (("left", -1), ("right", +1)):
            cur = left if side_ == "left" else right
            alt = alt_ends.get(side_)
            if alt is not None and cur.get("unbound") == "no_head_at_end":
                got = bind_end(float(alt[0]), float(alt[1]), sgn_, heads, sp, side, usable, by_height, False)
                if got.get("head") is not None:
                    got["via_stroke_end"] = True
                    if side_ == "left":
                        left = got
                    else:
                        right = got
    if closest_head_enabled():
        # ROADMAP 2.271: the closest head only for an end that STILL has none, measured from the end of the curve's own PAGE STROKE where that runs
        # past the traced end (the trace is the detector box + 0.5 sp; the stroke is the whole arc: Sean's tiles, "the box not capturing the full arc")
        for side_, sgn_, xe, ye in (("left", -1, xl, yl), ("right", +1, xr, yr)):
            cur = left if side_ == "left" else right
            if cur.get("unbound") != "no_head_at_end" or cs.get(side_) is False:
                continue
            alt = (alt_ends or {}).get(side_)
            if alt is not None and (float(alt[0]) - float(xe)) * sgn_ > 0:
                xe, ye = alt[0], alt[1]
            got = bind_end(float(xe), float(ye), sgn_, heads, sp, side, usable, by_height, True, (other_ends or {}).get(side_))
            if got.get("head") is not None or got.get("unbound") == "continues_in_another_curve":
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
