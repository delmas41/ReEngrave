"""A head box standing on ink that another reading already owns -- ROADMAP 2.176 (flag `OMR_HEAD_ON_ANOTHER_MARK`, default OFF).

PATH: STAGED, ADJUDICATE (notehead precision). It reads rows GATHER already files (`Q.GLYPH_BOX`, `Q.GLYPH_CONF`,
`Q.CELL_BOX`, `Q.STEM`); no new producer, nothing re-measured.

## Why

2.174's random sample put "over half of Brahms's decided quarters with beam ink nearby" among non-notes. Measured on the
20261018-night record, 51% of that population (1,044 of 2,042) is ALREADY refused (`too_narrow` 937 -- barline slivers), and
refused heads are dropped at export. On the heads that stay (decided, not refused) a random look finds the rate small:
`benchmarks/omr-non-notes-2026-10/FINDINGS.md`. What does stay is ink a DIFFERENT reading owns: the detector boxed the same ink
as an accidental, a clef, a curled rest, or it is the system's leading barline. These are the connections made here:

* `on_the_staffs_leading_barline` (STAGED, geometry) -- cell 0 of a system starts at the staff's left end, where the
  system barline (and the brace beside it) is printed, and nothing is printed there but that line: a clef comes after it
  (CLAUDE.md §4: only a clef stands before the key accidentals). A head box whose left edge is within
  `LEADING_EDGE_SPACES` of that cell's left edge is the line's ink. The cut is FITTED on Brahms (23 boxes between 0.00
  and 0.44 sp, none between 0.44 and 1.0; Litolff has 1): NOT CONFIRMED on another publisher.
* `on_another_symbols_box` -- the box lies inside another class's box that the detector drew on this ink:
  - a CLEF box (`clef*`) covers at least `CLEF_COVER_MIN` of the head box: a head cannot stand inside the clef's own
    glyph box (the F clef's two dots and its head curl were boxed as heads);
  - an ACCIDENTAL box or a CURLED REST box (`restQuarter`..`rest64th`) covers at least `MARK_COVER_MIN` of the head box,
    the head box covers at least `MARK_OWN_COVER_MIN` of it (the two boxes are one mark's, not a small box in a large
    one), the other box's detector score is at least this head's (the detector's own vote between two classes on one ink),
    and NO STEM touches the head (a stemmed head is a note; rule 8: no refusal on a guess).
  Dynamics, letters, digits and slurs are not here: other gates own them and the other box does not decide them.

A refused head is REFUSED, never re-valued: it stays a `Q.GLYPH_BOX` row and export counts it under
`not_a_notehead:<reason>`.

CONVENTION ASSUMED: one ink is one mark; a box standing on a clef, an accidental or a rest that the detector scored at least
as high as this head is that mark, not a note. WHAT WOULD FALSIFY IT: a print-confirmed head, with no stem the finder saw,
inside such a box. The cut values are fitted on two plates and NOT CONFIRMED beyond them; blind tiles
`out/print/2.176-review/`.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from .. import geometry as _geom
from .. import margins as _margins
from ..adjudicate import Evidence, Ruling
from ..record import Kind, Q, Scope

ENV = "OMR_HEAD_ON_ANOTHER_MARK"
LEADING_REASON = "on_the_staffs_leading_barline"
MARK_REASON = "on_another_symbols_box"

#: A head box whose left edge is this close to the left edge of the system's first cell (staff spaces).
LEADING_EDGE_SPACES = 0.5
#: Share of the head box a clef box must cover.
CLEF_COVER_MIN = 0.9
#: A clef box counts only where it starts within this many staff spaces of its cell's left edge.
CLEF_WINDOW_SPACES = 6.0
#: Share of the head box an accidental / curled-rest box must cover, and share of THAT box the head box must cover.
MARK_COVER_MIN = 0.8
MARK_OWN_COVER_MIN = 0.25
CURLED_RESTS = ("restQuarter", "rest8th", "rest16th", "rest32nd", "rest64th", "rest128th")


def enabled() -> bool:
    """`OMR_HEAD_ON_ANOTHER_MARK`, default OFF (ROADMAP 2.176): only an explicit on-word enables."""
    return os.environ.get(ENV, "0").strip().lower() in ("1", "true", "yes", "on")


def _xywh(v) -> Optional[Tuple[float, float, float, float]]:
    if not isinstance(v, (list, tuple)) or len(v) != 5:
        return None
    try:
        return float(v[1]), float(v[2]), float(v[3]), float(v[4])
    except (TypeError, ValueError):
        return None


def _inter(a, b) -> float:
    iw = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    ih = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return iw * ih if iw > 0 and ih > 0 else 0.0


def refusal(ev: Evidence, box_row, spacing_canonical: float, cell_box_page,
            detail: Dict[str, Any]) -> Optional[Ruling]:
    """`Ruling(True, ...)` where this head box stands on another reading's ink, else None (rule 8: a missing row declines)."""
    if not enabled() or box_row is None:
        return None
    head = _xywh(box_row.value)
    if head is None or not spacing_canonical or head[2] <= 0 or head[3] <= 0:
        return None
    cell = ev.subject.at(Kind.CELL)
    if cell is None:
        return None

    # -- the leading barline: cell 0 of the system, in the page frame
    page_box = (box_row.detail or {}).get("bbox_page_px")
    if cell is not None and ev.subject.cell == 0 and page_box and len(page_box) == 4 and cell_box_page:
        sp_page = spacing_canonical * (page_box[2] - page_box[0]) / head[2]
        dl = (page_box[0] - cell_box_page[0]) / sp_page if sp_page > 0 else None
        if dl is not None and dl <= LEADING_EDGE_SPACES:
            detail["leading_barline"] = {"left_edge_spaces": round(dl, 3), "cut_spaces": LEADING_EDGE_SPACES}
            return _margins.attach(
                Ruling(value=True, reason="on_the_staffs_leading_barline", used=(box_row.id,), detail=detail),
                margin=LEADING_EDGE_SPACES - dl, axis="left_edge_spaces", unit="staff spaces", band=None,
                would_choose=(True,))

    # -- another class's box on this ink
    conf = {}
    for r in ev.rows(Q.GLYPH_CONF, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        try:
            conf[r.subject] = float(r.value)
        except (TypeError, ValueError):
            continue
    own_conf = conf.get(ev.subject)
    head_area = head[2] * head[3]
    stemmed = None

    def _stemmed() -> bool:
        nonlocal stemmed
        if stemmed is None:
            stemmed = False
            for st in ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell):
                sv = st.value
                if isinstance(sv, (list, tuple)) and len(sv) >= 4 and _geom.stem_touches_head(
                        tuple(float(x) for x in sv[:4]), head):
                    stemmed = True
                    break
        return stemmed

    best = None
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        if r.subject == ev.subject:
            continue
        name = r.value[0] if isinstance(r.value, (list, tuple)) and r.value else None
        if not isinstance(name, str):
            continue
        other = _xywh(r.value)
        if other is None or other[2] <= 0 or other[3] <= 0:
            continue
        inter = _inter(head, other)
        if inter <= 0:
            continue
        cover = inter / head_area
        own = inter / (other[2] * other[3])
        if name.startswith("clef"):
            # a clef stands at the start of a bar (the first `CLEF_WINDOW_SPACES` of its cell); a "clef" box farther in is
            # not one (Brahms `glyph/6/0/3/0/12`, a clefF box on a stemless-looking head mid-bar)
            if other[0] / spacing_canonical > CLEF_WINDOW_SPACES:
                continue
            if cover >= CLEF_COVER_MIN and (best is None or cover > best[0]):
                best = (cover, r, name, cover - CLEF_COVER_MIN, "clef_cover_of_the_head")
            continue
        if not (name.startswith("accidental") or name in CURLED_RESTS):
            continue
        if cover < MARK_COVER_MIN or own < MARK_OWN_COVER_MIN:
            continue
        o_conf = conf.get(r.subject)
        if own_conf is None or o_conf is None or o_conf < own_conf:
            continue                       # no vote, or the detector preferred the head: keep it (rule 8)
        margin = min(cover - MARK_COVER_MIN, own - MARK_OWN_COVER_MIN)
        if best is None or margin > best[3]:
            best = (cover, r, name, margin, "cover_of_the_head")
    if best is not None and _stemmed():
        return None                        # a stem stands on it: a note (rule 8: no refusal on a guess)
    if best is None:
        return None
    cover, r, name, margin, axis = best
    detail["on_another_mark"] = {"box": r.id, "class": name, "cover": round(cover, 3),
                                 "box_conf": conf.get(r.subject), "head_conf": own_conf}
    return _margins.attach(
        Ruling(value=True, reason="on_another_symbols_box", used=(box_row.id, r.id), detail=detail),
        margin=margin, axis=axis, unit="fraction of the box shared", band=None, would_choose=(True,))
