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

#: heads whose centres lie within this many of their own widths in x are one COLUMN (a chord, or two voices at one onset)
BIND_COLUMN_DX_WIDTHS = 0.6
#: at one end, a second column whose distance is within this many staff spaces of the nearest one makes the end ambiguous
BIND_COLUMN_MARGIN_SPACES = 0.5
#: a curve whose middle third sits this far (spaces) above / below the line through its two ends is ABOVE / BELOW its notes
BIND_SIDE_MIN_SPACES = 0.1


def bind_enabled() -> bool:
    """`OMR_ARC_BIND_PAGEWIDE`, default ON (ROADMAP 2.223; Sean 2026-10-31 "Fix then land", tiles 11/12, tile 11 fixed); an explicit 0/false/no/off disables."""
    return os.environ.get(ENV_BIND, "").strip().lower() not in ("0", "false", "no", "off")


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


def bind_end(ex: float, ey: float, sgn: int, heads: Sequence[Dict[str, Any]], sp: float, side: Optional[str],
             usable: Any = None) -> Dict[str, Any]:
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


def stem_tips(heads: Sequence[Dict[str, Any]], stems: Sequence[Sequence[float]]) -> List[Dict[str, Any]]:
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
        out.append({"key": h["key"], "cx": scx, "cy": ty, "w": h["w"], "h": h["h"], "cell": h.get("cell", 0), "tip": True})
    return out


def bind_curve(detail: Dict[str, Any], heads: Sequence[Dict[str, Any]], sp: float, usable: Any = None) -> Dict[str, Any]:
    """Both ends of one `Q.SYSTEM_ARC` curve (its row's `detail`): `{"left": ..., "right": ..., "side": ...}`; see `bind_end`."""
    side = curve_side(detail.get("trace"), sp)
    xl, yl = detail.get("x_left_page"), detail.get("y_left_page")
    xr, yr = detail.get("x_right_page"), detail.get("y_right_page")
    if None in (xl, yl, xr, yr) or sp <= 0:
        return {"left": {"unbound": "no_traced_end"}, "right": {"unbound": "no_traced_end"}, "side": side}
    left = bind_end(float(xl), float(yl), -1, heads, sp, side, usable)
    right = bind_end(float(xr), float(yr), +1, heads, sp, side, usable)
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
