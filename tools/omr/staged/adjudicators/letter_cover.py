"""A head or rest box whose ink the second look read as dynamic letters --
ROADMAP 2.107.

Sean, 2026-10-13: *"sf should be read as a dynamic - it is letters"*. GATHER
(`gather.gather_letter_look`) shows the detector the staff-line-erased ink under
a head/rest box that looks like letters, votes its letter classes over five
scales, and keeps a reading only where the string the letters spell is a
dynamic the TERMS LIBRARY holds. Where it does, it files the letters as
`dynamic*` boxes (so spelling, twins, ownership, anchor and export are the
2.68 machinery, unchanged) and files `Q.LETTER_LOOK_COVER` on every notehead or
rest box whose ink they explain: the share of the box's OWN ink inside the read
letters' boxes.

This module is the one place that row is read. It decides nothing about
letters: it says that a head or a rest which is (mostly) a read letter's ink is
not a head or a rest -- the same refusal 2.76 makes for a head on a DETECTED
letter (`on_a_dynamic_letter`, reused so a refused head stays "not a note at
all" to `rhythm._not_a_note_mark`), and its rest counterpart.

CONTROLS (CLAUDE.md rule 7), each a test: a real note beside a dynamic is not
covered (its ink is mostly outside the letters' boxes -> no row, or a share
under the bar -> spared with the signal recorded); a real eighth or sixteenth
rest beside a dynamic likewise; the refusal is only ever as strong as the
letters, and the letters exist only where the library holds the string.

The bar, `COVER_REFUSE_SHARE`, is a CONVENTION ASSUMED: the majority of a box's
own ink. WHAT WOULD FALSIFY IT: a real head or rest whose box is half letter
ink (a note touching an `f`'s hook) -- the gather files the share and the
refusal's margin, so the near misses are countable. NOT CONFIRMED by Sean until
he judges the `out/print/2.107-review` tiles.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .. import margins as M
from ..adjudicate import Ruling

COVER_REFUSE_SHARE = 0.5


def _signal(rows, detail: Dict[str, Any]):
    """`(row, share)` of this box's `Q.LETTER_LOOK_COVER` rows (the DECISION
    reads them with `ev.rows` and passes them in, so the declaration is read
    where it is declared), with the signal put on `detail`; `(None, None)`
    where GATHER filed none (the box is clear of every read letter, which is
    not a reading)."""
    if not rows:
        return None, None
    row = rows[-1]
    try:
        share = float(row.value)
    except (TypeError, ValueError):
        return None, None
    d = row.detail or {}
    detail["letter_look_signal"] = {
        "cover_share": round(share, 3), "bar": COVER_REFUSE_SHARE,
        "margin": round(share - COVER_REFUSE_SHARE, 3),
        "read_as": d.get("read_as"), "candidates": d.get("candidates"),
        "status": d.get("status"), "letters": d.get("letters")}
    return row, share


def cover_of(rows, detail: Dict[str, Any]):
    """`(row, share)` of the box's `Q.LETTER_LOOK_COVER` rows, the signal put on
    `detail`; `(None, None)` where GATHER filed none. The DECISION builds its own
    Ruling with its own literal reason word (`brakes.vocabulary_gap` reads the
    `reason=` slot's AST in the decision's module) and calls `with_margin`."""
    return _signal(rows, detail)


def refuses(share: Optional[float]) -> bool:
    return share is not None and share >= COVER_REFUSE_SHARE


def with_margin(ruling: Ruling, share: float, *, would_choose: str) -> Ruling:
    """`ruling` with the 2.106 margin: how far over the bar the share was."""
    return M.attach(
        ruling, margin=share - COVER_REFUSE_SHARE, axis="cover_share",
        unit="share of the box's own ink inside the read letters' boxes",
        band=None, would_choose=[would_choose])
