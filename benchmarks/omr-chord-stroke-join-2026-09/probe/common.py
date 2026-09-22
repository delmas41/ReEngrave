"""Shared reading for the chord/stroke-join lane.

⚠️ THE PREDICATES ARE THE SHIPPED ONES, IMPORTED, NEVER RESTATED. Every
overlap test here is `rhythm._boxes_overlap` and every head box is unpacked by
`rhythm._xywh_head`, so a probe cannot measure a population the decision does
not see. The sibling lane
(`benchmarks/omr-stem-attribution-2026-09/probe/reach.py`) had to restate the
predicate because it wanted a record-only probe; this lane does not need that
independence and pays for it in the other coin -- its numbers are the
decision's by construction.

⚠️ THE STREAMER IS IMPORTED TOO. The Breitkopf record is 443 MB.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "benchmarks"))

from omr_ledger_extrapolation_shim import stream_array  # noqa: E402
from tools.omr.staged.adjudicators.rhythm import (  # noqa: E402
    _boxes_overlap, _stems_on, _xywh_head,
)

__all__ = ["stream_array", "_boxes_overlap", "_stems_on", "_xywh_head",
           "cell_of", "collect", "x_overlap", "y_overlap"]


def cell_of(subject: str) -> str:
    """`glyph/p/s/st/c/g` -> `cell/p/s/st/c`. '' where there is none."""
    parts = subject.split("/")
    if parts[0] == "glyph" and len(parts) >= 6:
        return "cell/" + "/".join(parts[1:5])
    if parts[0] == "cell":
        return subject
    return ""


def x_overlap(a, b) -> bool:
    """The x half of the SHIPPED overlap predicate, and nothing else.

    ⚠️ It is the shipped predicate with the y coordinates neutralised, not a
    second inequality: `_boxes_overlap` is inclusive at a touching edge and a
    hand-written `<` would silently disagree with it there. One pair of the
    sibling lane's corpus turns on exactly that boundary.
    """
    return _boxes_overlap((a[0], 0.0, a[2], 1.0), (b[0], 0.0, b[2], 1.0))


def y_overlap(a, b) -> bool:
    """The y half of the SHIPPED overlap predicate. Same reasoning."""
    return _boxes_overlap((0.0, a[1], 1.0, a[3]), (0.0, b[1], 1.0, b[3]))


class _Row:
    """The shape `_stems_on` wants: anything with a `.value` of (x, y, w, h).

    ⚠️ `page` IS A SECOND SPELLING OF THE SAME BOX AND THE TWO ARE NAMED
    APART. `value` is CANONICAL-CELL `(x, y, w, h)`; `page` is
    `detail.bbox_page_px`, PAGE pixels as CORNERS `[x0, y0, x1, y1]`. Mixing
    them is the fault CLAUDE.md records five times, most recently inside the
    sibling lane's own crop tool, so both travel and neither is derived from
    the other here.
    """

    __slots__ = ("value", "id", "subject", "page")

    def __init__(self, value, rid, subject="", page=None):
        self.value = value
        self.id = rid
        self.subject = subject
        self.page = page


def collect(record, want_beams=False):
    """cell -> stem rows, cell -> head rows, (optionally) cell -> beam rows.

    Heads carry their subject key and their box in the SAME canonical cell
    frame the stems do. ⚠️ `Q.GLYPH_BOX` is `(smufl_name, x, y, w, h)`; it is
    unpacked by the shipped `_xywh_head` so the name offset cannot be got
    wrong here in a way it is not got wrong in the decision.
    """
    stems = defaultdict(list)
    heads = defaultdict(list)
    beams = defaultdict(list)
    n_obs = 0
    for o in stream_array(record, "observations"):
        n_obs += 1
        q = o.get("quantity")
        if q == "stem":
            v = o.get("value")
            if isinstance(v, (list, tuple)) and len(v) >= 4:
                c = cell_of(o.get("subject", ""))
                if c:
                    stems[c].append(
                        _Row(tuple(float(x) for x in v[:4]), o["id"],
                             o.get("subject", "")))
        elif q == "beam_stroke" and want_beams:
            v = o.get("value")
            if isinstance(v, (list, tuple)) and len(v) >= 4:
                c = cell_of(o.get("subject", ""))
                if c:
                    beams[c].append(
                        _Row(tuple(float(x) for x in v[:4]), o["id"],
                             o.get("subject", "")))
        elif q == "glyph_box":
            if (o.get("detail") or {}).get("category") != "notehead":
                continue
            box = _xywh_head(o.get("value"))
            if box is None:
                continue
            c = cell_of(o.get("subject", ""))
            if c:
                bp = (o.get("detail") or {}).get("bbox_page_px")
                page = ([float(x) for x in bp]
                        if bp and len(bp) == 4 else None)
                heads[c].append(
                    _Row(box, o["id"], o.get("subject", ""), page))
    return stems, heads, beams, n_obs
