"""ROADMAP 2.318 -- ONE BEAM COUNT, READ WHERE THE BEAM'S INK MEETS THE STEM'S INK (flag `OMR_BEAMS_AT_STEM`, default OFF).

STAGED ADJUDICATE, PURE: imports nothing from the pipeline; `adjudicators/rhythm.py::_beams_at_stem_reading` builds the inputs.

THE RULE (Sean 2026-11-18, "Let's try it" -- a TRIAL of our wording, not yet a page fact):
  A note has as many beams as there are separate bars of ink at its own stem's tip. Each bar is counted AT THAT STEM, not along the whole
  beam. A staff line, a neighbour's notehead, a slur or a hairpin is never a beam. Two beams run together into one thick bar are two, by the
  thickness at the stem. Where two fused beams cannot be told from one beam lying on a staff line, the note is marked, never guessed.

HOW (every number stands BESIDE the rule; each says whether it is a convention or measured):
  * The bar's thickness is read AT THE STEM'S OWN x from the stroke's thickness profile (12 samples, sixteenths of a space): the larger of
    the two samples either side of the stem, the two end samples never used (a stroke is cut where the stem joins it, so its end bins are
    part-empty). A stem is where a partial beam may start or stop, so either side of it belongs to it.
  * `BAR_MIN` 0.5 sp: a beam is at least this thick -- engraving convention (about half a space; beam_strokes.BEAM_MIN_THICKNESS_SP).
    Below `THIN_MAX` 0.4375 it is a staff line, hairpin or slur remnant (measured on two plates: the trough of beam_strokes.BEAM_DOUBT).
    Between the two the ink cannot say: marked, with the signed margin.
  * `TWO_MIN` 1.0 sp: beam 0.5 + gap 0.25 + beam 0.5 is 1.25 sp (convention, beam_strokes.FUSED_DOUBLE_MIN_THICKNESS_SPACES). Between
    `ONE_MAX` 0.85 and 1.0 one thick beam and two fused cannot be told: marked.
  * A bar that lies on / touches a staff line gains up to a line's thickness; where such a bar reads under `LINE_AMBIGUOUS_MAX` 1.15 it
    is one beam beside a line or two fused beams: marked (the 2.318 rule's last sentence).
  * The first bar's outer edge stands at the stem's tip: within `TIP_NEAR` 1.0 sp it is this stem's bar, beyond `TIP_FAR` 1.5 sp it is
    something else (a staff line fused to a neighbour's head, another voice's beam); between the two it cannot be told. Measured on the 24
    judged notes, two plates only: it NARROWS, it does not decide.
  * Two beams read at a stroke's END (the stem stands in its last profile bins) are marked: the profile there is one extrapolated sample.
  * A second SEPARATE bar counts only where the paper between it and the first is under `GAP_MAX` 0.5 sp (a beam gap is about 0.25).
  * A bar-shaped stroke two marks CONTEST (OMR_STROKE_OWNER `contested`) is never counted and makes the note marked. A stroke merely `owned`
    is NOT refused: the owner verdict is a box-share claim, and on the 24 judged notes the owned list holds strokes of printed beams.
Never: a staff line, a neighbour's notehead (blob), a slur, a hairpin or a long thin span is a bar; nothing falls back to another reading.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

BAR_MIN = 0.5
THIN_MAX = 0.4375
ONE_MAX = 0.85
TWO_MIN = 1.0
FUSED_MAX = 1.75
LINE_AMBIGUOUS_MAX = 1.15
TIP_NEAR = 1.0
TIP_FAR = 1.5
GAP_MAX = 0.5
OUTWARD_MAX = 0.6
INWARD_MAX = 3.8
X_SLACK = 0.35
#: a beam is at least this wide (staff spaces) to join its note to another: the nearest stem of a beamed group is more than a head's width away
#: (convention: a stem sits one head-width from the next; measured on nothing here, narrows only).
JOIN_MIN = 1.0


def thickness_at(s, x: float) -> Optional[float]:
    """Staff spaces, the stroke's thickness at page-frame cell x `x`: the larger of the two interior profile samples either side of `x`."""
    p = s.profile
    if len(p) < 4 or s.box[2] <= 0:
        return None
    n = len(p)
    f = min(max((x - s.box[0]) / s.box[2], 0.0), 1.0) * (n - 1)
    i = min(max(int(f), 1), n - 2)
    thickness_at.at_end = f < 1.0 or f > n - 2
    j = min(max(int(f) + 1, 1), n - 2)
    return max(p[i], p[j]) / 16.0


thickness_at.at_end = False


def _centre_y(s, x: float) -> Optional[float]:
    e = s.ends
    if len(e) >= 4 and abs(e[2] - e[0]) > 1:
        return e[1] + (e[3] - e[1]) * (x - e[0]) / (e[2] - e[0])
    return None


def _touches_line(yc: float, t_px: float, lines: Sequence[float], slack: float) -> bool:
    return any(yc - t_px / 2 - slack <= ly <= yc + t_px / 2 + slack for ly in lines)


def beams_at_stem(views, stem, side: str, lines: Sequence[float], space: float, owner: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    """`stem` the stem's StrokeView (vertical), `side` up/down (where the stem points), `lines` the staff lines' y in the stem's x, in the
    strokes' own frame, `space` that frame's pixels per staff space. Returns {"count": n or None, "candidates": (lo, hi), "margin": signed
    sp to the nearest cut, "reason": word, "bars": [...], "rows": [stroke row ids]}. `count` None = the note is marked (candidates say how)."""
    owner = owner or {}
    sx = stem.box[0] + stem.box[2] / 2.0
    tip = stem.box[1] if side == "up" else stem.box[1] + stem.box[3]
    sign = 1.0 if side == "up" else -1.0
    bars: List[Dict[str, Any]] = []
    doubts: List[Dict[str, Any]] = []
    for s in views:
        if s.ordinal == stem.ordinal or s.kind != "horizontal":       # a slur (curve), a notehead (blob), a stem (vertical) is never a bar
            continue
        if s.box[0] - X_SLACK * space > sx or s.box[0] + s.box[2] + X_SLACK * space < sx:
            continue
        yc = _centre_y(s, sx)
        if yc is None:
            yc = s.box[1] + s.box[3] / 2.0
        inward = (yc - tip) / space * sign
        t = thickness_at(s, sx)
        at_end = thickness_at.at_end
        if t is None:
            at_end = True
            t = s.thickness
        if not (-OUTWARD_MAX <= inward - t / 2 and inward <= INWARD_MAX):
            continue
        b = {"row": s.row_id, "kind": s.kind, "thickness": round(t, 3), "inward": round(inward, 2),
             "outer": round(inward - t / 2.0, 2), "inner": round(inward + t / 2.0, 2),
             "width": round(s.box[2] / space, 2), "at_end": at_end, "on_line": _touches_line(yc, t * space, lines, 0.1 * space), "ordinal": s.ordinal}
        (doubts if owner.get(s.ordinal) == "contested" else bars).append(b)
    rows = [stem.row_id]
    # a stroke another mark owns is ink that may be a beam: the note is marked, never counted
    near_owned = [d for d in doubts if d["outer"] <= TIP_FAR]
    if near_owned:
        rows += [d["row"] for d in near_owned]
        return {"count": None, "candidates": (0, 2), "margin": None, "reason": "bar_owned_by_another_mark", "bars": near_owned, "rows": rows}
    # thin ink (a staff line, a slur, a hairpin) is never a bar
    cand = [b for b in bars if b["thickness"] >= THIN_MAX]
    cand = [b for b in cand if b["outer"] <= TIP_FAR]
    if not cand:
        near = [b for b in bars if b["outer"] <= TIP_FAR]
        rows += [b["row"] for b in near]
        return {"count": 0, "candidates": (0, 0), "margin": round(THIN_MAX - max([b["thickness"] for b in near] or [0.0]), 3),
                "reason": "no_bar_at_the_tip", "bars": near, "rows": rows}
    cand.sort(key=lambda b: b["outer"])
    first = cand[0]
    rows.append(first["row"])
    if first["outer"] > TIP_NEAR:
        return {"count": None, "candidates": (0, 1), "margin": round(TIP_FAR - first["outer"], 3), "reason": "bar_not_clearly_at_the_tip",
                "bars": cand, "rows": rows}
    # a beam joins its note AND another note (Sean 2026-10-09): ink standing no wider than JOIN_MIN beside the stem is a stub, marked
    if first["width"] < JOIN_MIN:
        return {"count": None, "candidates": (0, 1), "margin": round(first["width"] - JOIN_MIN, 3), "reason": "bar_too_short_to_join_another_note",
                "bars": cand, "rows": rows}
    # thickness -> number of beams in the first bar
    t = first["thickness"]
    if t < BAR_MIN:
        return {"count": None, "candidates": (0, 1), "margin": round(min(t - THIN_MAX, BAR_MIN - t), 3), "reason": "bar_in_the_thickness_trough",
                "bars": cand, "rows": rows}
    if t >= FUSED_MAX:
        return {"count": None, "candidates": (2, 3), "margin": round(t - FUSED_MAX, 3), "reason": "bar_thicker_than_two_beams", "bars": cand, "rows": rows}
    if ONE_MAX <= t < TWO_MIN:
        return {"count": None, "candidates": (1, 2), "margin": round(min(t - ONE_MAX, TWO_MIN - t), 3), "reason": "one_thick_beam_or_two_fused",
                "bars": cand, "rows": rows}
    n = 1 if t < ONE_MAX else 2
    if n == 2 and first["at_end"]:
        # the stem stands in the last bins of its stroke, where the profile is one extrapolated sample: two fused beams cannot be told from
        # one beam fused to a neighbour's ink (a dynamic, a wedge) -- marked (L12 is one beam by Sean, 1.31 sp here)
        return {"count": None, "candidates": (1, 2), "margin": round(t - TWO_MIN, 3), "reason": "two_at_a_stroke_end_cannot_be_told",
                "bars": cand, "rows": rows}
    if n == 2 and first["on_line"] and t < LINE_AMBIGUOUS_MAX:
        return {"count": None, "candidates": (1, 2), "margin": round(LINE_AMBIGUOUS_MAX - t, 3), "reason": "two_fused_or_one_on_a_staff_line",
                "bars": cand, "rows": rows}
    # further, separate bars close under the first
    edge = first["inner"]
    for b in cand[1:]:
        gap = b["outer"] - edge
        if gap < -0.3:
            continue                      # the same ink read twice (overlapping strokes)
        if gap <= GAP_MAX:
            n += 2 if (b["thickness"] >= TWO_MIN) else 1
            rows.append(b["row"])
            edge = b["inner"]
        elif gap <= GAP_MAX + 0.4:
            return {"count": None, "candidates": (n, n + 1), "margin": round(GAP_MAX + 0.4 - gap, 3), "reason": "second_bar_gap_not_clear",
                    "bars": cand, "rows": rows}
    return {"count": n, "candidates": (n, n), "margin": round(min(abs(t - ONE_MAX), abs(t - BAR_MIN), abs(TWO_MIN - t)), 3), "reason": "bars_at_the_stem",
            "bars": cand, "rows": rows}
