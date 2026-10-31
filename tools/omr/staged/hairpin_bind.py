"""ROADMAP 2.223 -- PAGE-WIDE BINDING OF A HAIRPIN'S TWO TIPS to places in the bars of the staff ABOVE it. PATH: STAGED. PURE helpers: no
pipeline import, no row filed, nothing decided by itself. The one caller is `adjudicators/ownership.adjudicate_wedge_anchor` (flag ON).
Registered in `reach.NOT_A_STAGE`.

Sean 2026-10-31 (page-facts s1; DECISIONS): "hairpins are always below the staff any notes next to a hairpin below it belong to the staff
below any notes above a hairpin belong to the staff above". And 2026-10-30: arcs and hairpins "reach past cell and should be read page
wide". Sean 2026-10-29 (plan-2026-10-28-page-claim-order s9): GATHER claims a page-wide mark and records its ends; after the heads are read,
ONE page-wide pass binds each end to a note or a place in a bar, choosing only among GATHER's candidates; an end that cannot be bound
abstains and the mark stays claimed.

`OMR_HAIRPIN_BIND_PAGEWIDE` (default OFF, allow-list). OFF, `adjudicate_wedge_anchor` keeps its 2026-09-10 rule (the legacy
`_wedge_anchors_from_candidates`, heads of the hairpin's centre bar +- 1 only, the start the NEAREST head whatever its distance).

THE RULE ON, per tip (left = start, right = stop), on the staff the CV reader found the hairpin under (it searches the band BELOW each staff,
so the staff above is the owner by construction; a hairpin whose box reaches into the next staff's lines is not between two staves and
abstains):

  1. the PLACE is the tip's x in the bar whose page box holds it (a cell index restarts per system; the system is the hairpin's own);
  2. the CANDIDATES are the onset COLUMNS of that staff's usable heads (glyph owner = this staff, not refused as a notehead) that stand
     ABOVE the hairpin (a head below it is the staff below's, Sean 10-31 -- never a candidate, counted), in that bar; for the STOP also
     the first column of the next bar (a crescendo aims at the next downbeat, `_wedge_anchors`' own +1 window);
  3. AT a note: a column whose centre lies within `REACH` head widths of the tip (`export._WEDGE_STOP_REACH_NOTEHEADS`, imported, not a
     new number) binds the tip to that note; two columns both in reach and closer together than `arc_claim.BIND_COLUMN_MARGIN_SPACES`
     ABSTAIN (`two_columns_at_tip`) with both and the margin;
  4. UNDER a note: no column in reach -- the tip is a place inside the bar while a note sounds. The note sounding there is the last
     column of the tip's bar left of the tip (a hairpin drawn under a held note starts or stops under it; "one anchor is enough", Sean
     2026-09-05). Recorded `under`, so a reader can tell "on a note" from "during one";
  4a. a GATHER head box within reach of the tip that ADJUDICATE did not leave usable (refused, another staff's copy) blocks step 4:
     the tip may be at that note, so the end ABSTAINS (`head_at_tip_not_usable`) -- found on crops, Brahms p25 (2026-10-31);
  5. no column at or left of the tip in its bar (a bar of rests, an unread head, a tip before the bar's first note and out of reach)
     -> UNBOUND (`no_note_at_tip`), with the nearest candidate and its distance in spaces past the reach as the margin. Never the
     nearest head of another bar (the OFF rule's guess).

  The stop is chosen in the START's voice (MusicXML pairs a wedge inside one voice, `_wedge_anchors_from_candidates`' rule); a column with
  no head of that voice is not a candidate for the stop. Of a chord the head written is the LOWEST (the one nearest the hairpin; any head
  of the column names the same onset).

CONVENTION ASSUMED: a hairpin's tips mark where it starts and stops in time; a tip within one head width of a note is on that note, a tip
in open space is during the note sounding there. WHAT WOULD FALSIFY IT: a hairpin Sean reads as starting or stopping on a note other
than the one at (or sounding at) its tip. NOT CONFIRMED: the reach (1.0 head width) is `_WEDGE_STOP_REACH_NOTEHEADS`, a plateau "nothing
in the corpus exercises" (export.py); the column margin is 2.223's hand-set arc number.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

ENV_BIND = "OMR_HAIRPIN_BIND_PAGEWIDE"


def bind_enabled() -> bool:
    """`OMR_HAIRPIN_BIND_PAGEWIDE`, default OFF: only an explicit 1/true/yes/on enables."""
    return os.environ.get(ENV_BIND, "").strip().lower() in ("1", "true", "yes", "on")


def reach_widths() -> float:
    from ..export import _WEDGE_STOP_REACH_NOTEHEADS
    return float(_WEDGE_STOP_REACH_NOTEHEADS)


def margin_spaces() -> float:
    from .arc_claim import BIND_COLUMN_MARGIN_SPACES
    return float(BIND_COLUMN_MARGIN_SPACES)


def between_staves(box: Sequence[float], own_bottom: Optional[float], next_top: Optional[float]) -> Optional[str]:
    """None where the hairpin box lies between its staff's bottom line and the next staff's top line; else why not."""
    if own_bottom is not None and float(box[1]) < float(own_bottom):
        return "reaches_into_its_own_staff"
    if next_top is not None and float(box[3]) > float(next_top):
        return "reaches_into_the_staff_below"
    return None


def inside_a_word(box: Sequence[float], word_areas: Sequence[Sequence[float]]) -> Optional[Dict[str, Any]]:
    """The word claim (page area `[x0, y0, x1, y1]`) holding at least `claims.INSIDE_SHARE_MIN` of the hairpin box's AREA, or None.
    The page-wide pass claims words before dynamics (plan-2026-10-28 s10, Sean's order); a later reader may mark claimed ink, never
    take it. Measured 2026-10-31 on the sample: every CV 'hairpin' under 1.6 spaces wide was a letter ('c' of cresc., 'e' of
    legato, 'B' of Basso: 8 of 8 on crops)."""
    from .claims import INSIDE_SHARE_MIN
    x0, y0, x1, y1 = (float(v) for v in box)
    area = max(1e-9, (x1 - x0) * (y1 - y0))
    best = None
    for a in word_areas:
        ix = max(0.0, min(x1, float(a[2])) - max(x0, float(a[0])))
        iy = max(0.0, min(y1, float(a[3])) - max(y0, float(a[1])))
        share = ix * iy / area
        if share >= INSIDE_SHARE_MIN and (best is None or share > best["share"]):
            best = {"share": round(share, 3), "area": [float(v) for v in a]}
    return best


def bar_of(x: float, bars: Sequence[Tuple[int, float, float]]) -> Optional[int]:
    """The cell index whose page x-range `[x0, x1]` holds `x` (bars of ONE staff of ONE system)."""
    for cell, x0, x1 in bars:
        if x0 <= x <= x1:
            return int(cell)
    return None


def columns(heads: Sequence[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Heads (`{key, cx, cy, w, h, cell}`) grouped into onset columns, per bar, left to right (`arc_claim`'s column test)."""
    from .arc_claim import BIND_COLUMN_DX_WIDTHS
    cols: List[List[Dict[str, Any]]] = []
    for h in sorted(heads, key=lambda h: (h["cell"], h["cx"])):
        if cols and cols[-1][0]["cell"] == h["cell"] \
                and abs(h["cx"] - cols[-1][0]["cx"]) <= BIND_COLUMN_DX_WIDTHS * max(h["w"], cols[-1][0]["w"]):
            cols[-1].append(h)
        else:
            cols.append([h])
    return cols


def _cx(col: Sequence[Dict[str, Any]]) -> float:
    return sum(h["cx"] for h in col) / len(col)


def _lowest(col: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return max(col, key=lambda h: h["cy"])


def bind_tip(x: float, end: str, cols: Sequence[Sequence[Dict[str, Any]]], bars: Sequence[Tuple[int, float, float]],
             sp: float, voice: Optional[int] = None, voice_of: Optional[Callable[[str], int]] = None,
             unusable: Sequence[Dict[str, Any]] = ()) -> Dict[str, Any]:
    """One tip at page `x`; `end` "start" or "stop". `cols` the staff's onset columns (all bars of the system). Returns
    `{"head": key, "how": "at"|"under", "cell": c, ...}` or `{"unbound": why, "candidates": [...], "margin_spaces": m}`."""
    cell = bar_of(x, bars)
    if cell is None:
        return {"unbound": "tip_in_no_bar", "candidates": [], "margin_spaces": None}
    vo = voice_of or (lambda _k: 0)

    def in_voice(col):
        if voice is None:
            return list(col)
        return [h for h in col if vo(h["key"]) == voice]

    here = [c for c in cols if c[0]["cell"] == cell and in_voice(c)]
    pool = list(here)
    if end == "stop":
        later = sorted({c[0]["cell"] for c in cols if c[0]["cell"] > cell})
        if later:
            nxt = [c for c in cols if c[0]["cell"] == later[0] and in_voice(c)]
            if nxt:
                pool.append(min(nxt, key=_cx))
    if not pool:
        return {"unbound": "no_note_in_bar", "cell": cell, "candidates": [], "margin_spaces": None}
    w = sum(h["w"] for c in pool for h in c) / sum(len(c) for c in pool)
    reach = reach_widths() * w
    near = sorted(pool, key=lambda c: abs(_cx(c) - x))
    inreach = [c for c in near if abs(_cx(c) - x) <= reach]
    if inreach:
        if len(inreach) > 1:
            gap = (abs(_cx(inreach[1]) - x) - abs(_cx(inreach[0]) - x)) / sp
            if gap < margin_spaces():
                return {"unbound": "two_columns_at_tip", "cell": cell,
                        "candidates": [[h["key"] for h in c] for c in inreach[:2]],
                        "margin_spaces": round(gap - margin_spaces(), 3)}
        col = in_voice(inreach[0])
        pick = _lowest(col)
        return {"head": pick["key"], "how": "at", "cell": pick["cell"], "x": pick["cx"],
                "distance_spaces": round(abs(_cx(inreach[0]) - x) / sp, 3)}
    # A head box GATHER drew within reach of the tip that ADJUDICATE did not leave usable (refused, unread, another staff's copy):
    # the tip may be AT that note, so "under the note before" would be a guess -- abstain and name it.
    blocked = [h for h in unusable if h["cell"] == cell and abs(h["cx"] - x) <= reach]
    if blocked:
        return {"unbound": "head_at_tip_not_usable", "cell": cell, "candidates": [h["key"] for h in blocked],
                "margin_spaces": None}
    left = [c for c in here if _cx(c) < x]
    if left:
        col = max(left, key=_cx)
        pick = _lowest(in_voice(col))
        return {"head": pick["key"], "how": "under", "cell": pick["cell"], "x": pick["cx"],
                "distance_spaces": round((x - _cx(col)) / sp, 3)}
    first = near[0]
    return {"unbound": "no_note_at_tip", "cell": cell, "candidates": [h["key"] for h in first],
            "margin_spaces": round((abs(_cx(first) - x) - reach) / sp, 3)}


def bind_hairpin(box: Sequence[float], heads: Sequence[Dict[str, Any]], bars: Sequence[Tuple[int, float, float]], sp: float,
                 voice_of: Optional[Callable[[str], int]] = None, unusable: Sequence[Dict[str, Any]] = ()) -> Dict[str, Any]:
    """Both tips of one hairpin (page box `[x0, y0, x1, y1]`, CORNERS). `heads` the usable heads of its staff in its system.
    Returns `{"start": ..., "stop": ..., "below": [keys of heads standing below the hairpin, never candidates]}`."""
    vo = voice_of or (lambda _k: 0)
    above = [h for h in heads if h["cy"] < float(box[1])]
    below = [h["key"] for h in heads if h["cy"] >= float(box[1])]
    cols = columns(above)
    un = [h for h in unusable if h["cy"] < float(box[1])]
    start = bind_tip(float(box[0]), "start", cols, bars, sp, unusable=un)
    voice = vo(start["head"]) if start.get("head") else None
    stop = bind_tip(float(box[2]), "stop", cols, bars, sp, voice, vo, unusable=un)
    if start.get("head") and stop.get("head"):
        ks = (start["cell"], start["x"])
        kz = (stop["cell"], stop["x"])
        if kz < ks:
            stop = {"unbound": "stop_before_start", "candidates": [stop["head"]], "margin_spaces": None}
    return {"start": start, "stop": stop, "below": below}
