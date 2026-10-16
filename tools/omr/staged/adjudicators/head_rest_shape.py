"""A lone rest the detector boxed as a notehead -- ROADMAP 2.145 (flag `OMR_HEAD_INK_IS_A_REST`, default OFF).

PATH: STAGED, ADJUDICATE (the gate and the reading), on rows GATHER already files
(`Q.UNBOXED_REST_SHAPE` covers a cluster even where a detector box stands on it).

Sean, 2026-10-15 (`out/print/2.141-fix23-review` tile 3): Litolff 984073 p6 sys1 st2 c5, *"an eighth
rest"*, boxed `noteheadBlackOnLine` (22 x 17 px, score 0.37) and written as a note. 2.142 removes a
head only where a REST box stands on the same ink; here the detector drew no rest box, so there is no
twin and nothing refused it.

## What reads it, and on what

The ink. `Q.UNBOXED_REST_SHAPE` is filed for every rest-sized cluster of staff-erased ink, the ones a
standing box covers included (2.99 files them on purpose as controls). A cluster whose only cover is
a notehead box, with no stem anywhere near the head, is read with the 2.99 decision's own windows
(`unboxed_rest.adjudicate_unboxed_ink_is_a_rest`, called, not restated, coverage zeroed): width, height,
local staff step, upper-heavy mass, no full-height stroke on the left. The bar is never consulted
(CLAUDE.md §4: a bar sum may only confirm).

TWO SOURCES: the ink shape (the staff-erased raster) AND the stem finder's silence (`Q.STEM`, a different
reader). A rest owns no stem; every stemmed head in the controls reads rest-shaped too (a head and its
stem make a rest-sized cluster: 14 Litolff `quarter` readings), so the shape ALONE is not a witness.

## Two decisions, one reading

* `adjudicate_notehead_is_not_a_notehead` calls `head_rest_refusal` (reason `is_a_rest_shape`): the HEAD
  leaves the bar, as every other refused head does.
* `adjudicate_head_ink_is_a_rest` (here, `Q.HEAD_INK_IS_A_REST`, on the CLUSTER's subject) says which rest:
  `"eighth"` / `"quarter"`. EVALUATE's `size_head_ink_rest` gives it its length (class, never the bar);
  EXPORT writes the rest at the cluster's box. It speaks only where the head was refused `is_a_rest_shape`.
Both call `read_head_ink`, so they cannot disagree (a function of the same rows).

## Displaced rests

2.99 abstains off the middle line (a second voice). A displaced rest does occur in this corpus
(DECISIONS 2026-10-09: a whole rest hanging off the bottom line). Sean's own case sits at step 5.96
(window 3.2-4.4). An EIGHTH whose every other measure passes with the step normalised, and whose step
lies in `DISPLACED_STEP`, is read `eighth` with `displaced=True` in its detail. That window is ONE
measurement (NOT CONFIRMED); it is the thing the 2.145 tiles test.

CONVENTION ASSUMED: a head box with no stem standing on it, whose ink is the size, place and shape of an
eighth/quarter rest and carries no flat's stroke, is that rest. WHAT WOULD FALSIFY IT: a print-confirmed
stemless head (a whole note, a dot-free quarter whose stem the finder missed) on such ink. NOT CONFIRMED
with Sean beyond tile 3; blind tiles `out/print/2.145-review/`.
"""
from __future__ import annotations

import os
import types
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .. import geometry as _geom
from .. import margins as _margins
from ..adjudicate import Evidence, Mode, Ruling, decision
from ..record import Kind, Outcome, Q, Scope
from . import unboxed_rest as _u

ENV = "OMR_HEAD_INK_IS_A_REST"
REASON = "is_a_rest_shape"

#: Share of the SMALLER of {head box, ink cluster} the two share for the cluster to be the head's ink.
#: Measured: Litolff/Brahms head boxes inside their clusters (the 16 candidates) cover 0.9-1.0.
HEAD_INK_COVER_MIN = 0.5
#: A cluster the head box (or any notehead box) accounts for at least this much. Below
#: `unboxed_rest.TOUCHED_SHARE` the ink is not the head's at all.
HEAD_INK_COVERAGE_MIN = 0.3
#: Steps (half staff spaces from the bottom line) where a DISPLACED eighth rest may hang: one staff
#: space beyond the middle-line window `unboxed_rest.EIGHTH_STEP`. ONE measurement (Sean's tile 3, 5.96).
DISPLACED_STEP = (_u.EIGHTH_STEP[0] - 2.0, _u.EIGHTH_STEP[1] + 2.0)
_MIDDLE_STEP = (_u.EIGHTH_STEP[0] + _u.EIGHTH_STEP[1]) / 2.0


def enabled() -> bool:
    """`OMR_HEAD_INK_IS_A_REST`, default OFF; only an explicit on-word enables."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class HeadInk:
    value: str                      # "eighth" | "quarter"
    displaced: bool
    cluster: Any                    # the Q.UNBOXED_REST_SHAPE row
    margin: Optional[float]
    axis: Optional[str]
    ruling: Ruling                  # the 2.99 reading it rests on


def _canon_corners(v) -> Tuple[float, float, float, float]:
    return float(v[0]), float(v[1]), float(v[2]), float(v[3])


def _cover(a, b) -> float:
    """Share of the smaller of two corner boxes `(x0, y0, x1, y1)` that both cover."""
    iw = min(a[2], b[2]) - max(a[0], b[0])
    ih = min(a[3], b[3]) - max(a[1], b[1])
    small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return 0.0 if iw <= 0 or ih <= 0 or small <= 0 else iw * ih / small


def _head_corners(box_row) -> Optional[Tuple[float, float, float, float]]:
    v = box_row.value
    if not isinstance(v, (list, tuple)) or len(v) != 5 or not str(v[0]).startswith("notehead"):
        return None
    x, y, w, h = (float(t) for t in v[1:5])
    return x, y, x + w, y + h


def _read_ink(row, step: Optional[float] = None) -> Ruling:
    """The 2.99 decision over this cluster's row with NOTHING covering it (as `controls_2_99.py`)."""
    d = dict(row.detail or {})
    d["coverage"] = 0.0
    if step is not None:
        d["staff_step"] = step
    stub = types.SimpleNamespace(
        rows=lambda quantity, **kw: [types.SimpleNamespace(id=row.id, detail=d)])
    return _u.adjudicate_unboxed_ink_is_a_rest(stub)


def read_head_ink(ev: Evidence, cell, head_row) -> Optional[HeadInk]:
    """The rest this notehead box's ink reads as, or None.

    `ev` must declare `Q.UNBOXED_REST_SHAPE`, `Q.STEM`, `Q.GLYPH_BOX` and `Q.REST`. None for: a box
    that is not a notehead; no cluster of ink on it; a cover that is not the head's alone; ANY stem
    touching the head or the ink (a rest owns none: rule 8); a rest box already on it (2.142's);
    two head boxes on one ink (a chord, or a box boxed twice); a shape that is not a rest's.
    """
    head = _head_corners(head_row)
    if head is None or cell is None:
        return None
    best = None
    for r in ev.rows(Q.UNBOXED_REST_SHAPE, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        d = r.detail or {}
        box = d.get("bbox_canonical")
        if not box or len(box) != 4 or "width_spaces" not in d:
            continue
        by = [str(b) for b in (d.get("covered_by") or []) if str(b) != "ledgerLine"]
        if not by or not all(b.startswith("notehead") for b in by):
            continue
        if (d.get("coverage") or 0.0) < HEAD_INK_COVERAGE_MIN:
            continue
        c = _cover(head, _canon_corners(box))
        if c >= HEAD_INK_COVER_MIN and (best is None or c > best[0]):
            best = (c, r)
    if best is None:
        return None
    row = best[1]
    ink = _canon_corners(row.detail["bbox_canonical"])

    rest_ids = {r.subject for r in ev.rows(Q.REST, scope=Scope.SELF_AND_DESCENDANTS, subject=cell)}
    for g in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        gv = g.value
        if not isinstance(gv, (list, tuple)) or len(gv) != 5:
            continue
        corners = (float(gv[1]), float(gv[2]), float(gv[1]) + float(gv[3]), float(gv[2]) + float(gv[4]))
        if g.id == head_row.id:
            continue
        if g.subject in rest_ids and _cover(head, corners) >= HEAD_INK_COVER_MIN:
            return None                                  # a rest box stands there: 2.142's, not ours
        if str(gv[0]).startswith("notehead") and _cover(corners, ink) >= HEAD_INK_COVER_MIN:
            return None                                  # a second head on the ink: a chord / a double box

    xywh_head = (head[0], head[1], head[2] - head[0], head[3] - head[1])
    xywh_ink = (ink[0], ink[1], ink[2] - ink[0], ink[3] - ink[1])
    for st in ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell):
        sv = st.value
        if isinstance(sv, (list, tuple)) and len(sv) >= 4:
            s = tuple(float(x) for x in sv[:4])
            if _geom.stem_touches_head(s, xywh_head) or _geom.stem_touches_head(s, xywh_ink):
                return None                              # a stem stands on it: not a rest (rule 8)

    strict = _read_ink(row)
    if strict.value in ("eighth", "quarter"):
        return HeadInk(strict.value, False, row, strict.margin,
                       (strict.detail or {}).get("margin_axis"), strict)
    step = (row.detail or {}).get("staff_step")
    if step is not None and DISPLACED_STEP[0] <= step <= DISPLACED_STEP[1] \
            and not (_u.EIGHTH_STEP[0] <= step <= _u.EIGHTH_STEP[1]):
        alt = _read_ink(row, step=_MIDDLE_STEP)
        if alt.value == "eighth":
            slack = _margins.slack(step, *DISPLACED_STEP)
            m = alt.margin if alt.margin is None or slack is None else min(alt.margin, slack)
            return HeadInk("eighth", True, row, m, "staff_step", alt)
    return None


def head_rest_refusal(ev: Evidence, box_row, detail: Dict[str, Any]) -> Optional[Ruling]:
    """`Ruling(True, "is_a_rest_shape")` where a stemless head box's ink reads as a rest, else None.

    Called from `adjudicate_notehead_is_not_a_notehead`, whose `wants` carry what `read_head_ink` reads.
    """
    if not enabled() or box_row is None:
        return None
    cell = ev.subject.at(Kind.CELL)
    got = read_head_ink(ev, cell, box_row)
    if got is None:
        return None
    detail["rest_shape"] = {"value": got.value, "displaced": got.displaced, "cluster": got.cluster.subject.to_key()}
    return _margins.attach(
        Ruling(value=True, reason="is_a_rest_shape", used=(box_row.id, got.cluster.id), detail=detail),
        margin=got.margin, axis=got.axis or "rest_shape", unit="mixed (spaces, steps, column share)",
        band=None, would_choose=(True,))


@decision(
    quantity=Q.HEAD_INK_IS_A_REST,
    composed_from=(Q.UNBOXED_REST_SHAPE,),
    scope=Kind.GLYPH,
    wants=(Q.UNBOXED_REST_SHAPE, Q.GLYPH_BOX, Q.STEM, Q.REST, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD),
    subjects_from=Q.UNBOXED_REST_SHAPE,
    reasons=("rest8th_head_ink", "rest8th_head_ink_displaced", "restQuarter_head_ink",
             "no_head_refused_on_the_ink"),
    mode=Mode.ADDITIVE,
)
def adjudicate_head_ink_is_a_rest(ev: Evidence) -> Ruling:
    """Which rest is this cluster of ink, whose head box ADJUDICATE refused `is_a_rest_shape`?

    See the module docstring. Speaks only where such a head stands on this cluster; a head refused for
    any other reason, or not refused, leaves the cluster to 2.99.
    """
    if not enabled():
        return Ruling.abstain("no_head_refused_on_the_ink")
    rows = ev.rows(Q.UNBOXED_REST_SHAPE)
    cell = ev.subject.at(Kind.CELL)
    if not rows or cell is None:
        return Ruling.abstain("no_head_refused_on_the_ink")
    mine = rows[-1]
    box = (mine.detail or {}).get("bbox_canonical")
    if not box or len(box) != 4:
        return Ruling.abstain("no_head_refused_on_the_ink")
    ink = _canon_corners(box)
    for g in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        head = _head_corners(g)
        if head is None or _cover(head, ink) < HEAD_INK_COVER_MIN:
            continue
        v = ev.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, subject=g.subject)
        if (v is None or v.outcome is not Outcome.DECIDED or v.value is not True
                or v.reason != REASON):
            continue
        got = read_head_ink(ev, cell, g)
        if got is None or got.cluster.id != mine.id:
            continue
        d = {"head": g.subject.to_key(), "displaced": got.displaced,
             **{k: (mine.detail or {}).get(k) for k in (
                 "width_spaces", "height_spaces", "staff_step", "mass_y",
                 "max_column_share", "column_profile", "coverage")}}
        kw = dict(margin=got.margin, axis=got.axis or "rest_shape",
                  unit="mixed (spaces, steps, column share)", band=None, would_choose=(got.value,))
        used = (mine.id, g.id, v.id)
        if got.displaced:
            return _margins.attach(Ruling(value="eighth", reason="rest8th_head_ink_displaced",
                                          used=used, detail=d), **kw)
        if got.value == "eighth":
            return _margins.attach(Ruling(value="eighth", reason="rest8th_head_ink",
                                          used=used, detail=d), **kw)
        return _margins.attach(Ruling(value="quarter", reason="restQuarter_head_ink",
                                      used=used, detail=d), **kw)
    return Ruling.abstain("no_head_refused_on_the_ink")
