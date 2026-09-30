"""ROADMAP 2.39 -- the STANDARD notehead box, promoted to one shared place.

Sean, 2026-09-29, quoted: *"All regular noteheads are the same size so the
box should be predictable."* Measured on both count pages: a regular head's
box is a median ~= 1.4 x 1.1 staff spaces; the DETECTOR's own box extent is
NOT trustworthy -- a Brahms (Breitkopf, SHATTERING) black-in-space measured
0.28 sp wide (a sliver) and a Litolff (MERGING) box grows with merged ink
(CLAUDE.md Sec.10). So every consumer that asks "where is this head's ink"
keeps the detector's CENTRE and gives the head the extent its own staff's
spacing implies; the detector box survives as its own witness, read by
nobody here.

ROADMAP 2.37 built this LOCAL to `gather._observe_ledger_owner_density`
(`LEDGER_OWNER_HEAD_WIDTH_SPACES`/`_HEIGHT_SPACES`, `_standard_head_box`);
this module is the GENERAL version 2.39 asked for, importable by both
GATHER (`gather.py`) and ADJUDICATE (`adjudicators/*.py`) with no cycle --
it imports nothing from either. The old names in `gather.py` are kept as
aliases only (nothing here reads them back).

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: Sean's own
quoted figure, not a per-page median (a whole-page pre-pass over every
notehead is a bigger change than this round's budget) -- falsified by a
plate whose real noteheads are reliably smaller or larger than this.

⚠️ ONLY REGULAR NOTEHEADS (`noteheadBlack*`, `noteheadHalf*`, never the
`*Small` grace/cue suffix) GET THIS BOX -- `is_regular_notehead` is the one
gate every consumer must ask before calling `standard_head_box`. A whole
note (Bravura ~1.688 x 1.0 sp, wider than a regular head) and a grace/cue
head (smaller) are BOTH LEFT ON THE DETECTOR'S OWN BOX -- ROADMAP 2.39 item
5 -- because this round measured only the regular-head population; a
distinct whole-note constant is future work, not assumed here.
"""

from __future__ import annotations

from typing import Optional, Tuple

#: See this module's own docstring for the measurement and its scope.
STANDARD_HEAD_WIDTH_SPACES = 1.4
STANDARD_HEAD_HEIGHT_SPACES = 1.1

#: The `*Small` suffix is DSv2/SMuFL's own spelling for a grace/cue-size
#: head (`noteheadBlackSmall`, `noteheadHalfSmall`) -- a real notehead, but
#: not the regular-size population this box was measured against.
_SMALL_SUFFIX = "Small"
#: Canonical prefixes for a REGULAR notehead (`class_aliases.
#: canonicalize_names` is what makes these the only spellings a consumer
#: ever sees). `noteheadWhole`/`noteheadDoubleWhole` are deliberately
#: excluded -- see the module docstring.
_REGULAR_PREFIXES = ("noteheadBlack", "noteheadHalf")


def is_regular_notehead(name: Optional[str]) -> bool:
    """True only for a canonical `noteheadBlack*`/`noteheadHalf*` class at
    REGULAR size -- never a `*Small` (grace/cue) spelling, and never
    `noteheadWhole*`/`noteheadDoubleWhole*` (a different, wider shape this
    round did not measure). `False` for anything else, including `None`."""
    if not name:
        return False
    n = str(name)
    if n.endswith(_SMALL_SUFFIX):
        return False
    return n.startswith(_REGULAR_PREFIXES)


def standard_head_box(cx: float, cy: float, spacing: float
                      ) -> Tuple[float, float, float, float]:
    """`(x0, x1, y0, y1)` -- a STANDARD notehead extent centred on `(cx,
    cy)` -- the detector box's own CENTRE, never its raw width or height --
    sized from the staff's own measured spacing (`STANDARD_HEAD_WIDTH_
    SPACES` x `STANDARD_HEAD_HEIGHT_SPACES`). Frame-agnostic: `cx`, `cy` and
    `spacing` must all be in the SAME frame (page pixels, canonical cell
    pixels, whatever the caller's own geometry uses) -- the arithmetic below
    does not care which.
    """
    hw = STANDARD_HEAD_WIDTH_SPACES * spacing / 2.0
    hh = STANDARD_HEAD_HEIGHT_SPACES * spacing / 2.0
    return cx - hw, cx + hw, cy - hh, cy + hh
