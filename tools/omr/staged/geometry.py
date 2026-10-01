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

from typing import Any, Iterable, Optional, Tuple

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


#: ROADMAP 2.50. The complementary half of `_REGULAR_PREFIXES` above --
#: `noteheadHalf*` appears in BOTH (a half note is regular-SIZED but
#: HOLLOW-SHAPED; the two predicates are not mutually exclusive and no
#: consumer should assume they are). Derived from `class_aliases.
#: vocabulary()` by prefix, never a hand-typed list of every OnLine/
#: InSpace/Small spelling -- the alias module is the one place that list
#: is allowed to live, per CLAUDE.md §9's "no derived check... without
#: the vocabulary it is derived from" (the canonical names themselves,
#: not a copy of them).
_HOLLOW_PREFIXES = ("noteheadHalf", "noteheadWhole", "noteheadDoubleWhole")


def _hollow_classes() -> frozenset[str]:
    from .. import class_aliases  # local import: avoid a module-load-order
    return frozenset(n for n in class_aliases.vocabulary()
                      if n.startswith(_HOLLOW_PREFIXES))


def is_hollow_notehead(name: Optional[str]) -> bool:
    """True for any canonical hollow-shaped notehead class -- `noteheadHalf*`
    (a half note; HOLLOW but regular-SIZED, so this and `is_regular_notehead`
    both say True for it), `noteheadWhole*`, `noteheadDoubleWhole*`, at any
    size suffix (`*Small` included -- a grace/cue hollow head still has a
    white interior to measure). `False` for anything else, including `None`
    or a name outside the canonical vocabulary (a typo should read as "not
    hollow", never crash a GATHER pass)."""
    if not name:
        return False
    return str(name) in _hollow_classes()


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


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.47bc -- "the SAME ink, boxed twice" moved here, ONE constant and
# ONE function, so the two decisions that both need it agree without either
# importing the other.
#
# `notehead_precision.adjudicate_notehead_is_not_a_notehead` (ADJUDICATE, keys
# `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD`, ROADMAP 2.47c) and `structure._trailing_
# cell_is_cautionary_only` (ADJUDICATE, keys `Q.MEASURE_PARTITION`, ROADMAP
# 2.47b) both ask the identical geometric question -- is this notehead-classed
# box the SAME ink the detector also boxed as a `timeSig*` class, at IoU
# measured 0.94-0.96 on the two crop-verified Brahms p0 instances
# (`benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` SS21b,
# `benchmarks/omr-measure-partition-2026-09/FINDINGS.md` SS10c/SS11c). Before
# this round each module answered it with its own copy of the arithmetic and
# its own copy of 0.9; now both read the one answer here.
#
# `structure.py` cannot import `notehead_precision` directly: `adjudicators.
# __init__` loads `structure` before `ownership`, and `notehead_precision`
# itself imports `ownership` (`from . import ownership as _ledger`), so
# `structure -> notehead_precision -> ownership -> structure` would cycle.
# This module already carries the project's other shared-but-cycle-free
# geometry (`standard_head_box`, ROADMAP 2.39's own note on the same
# constraint) and imports nothing from either adjudicator module, so it is
# the one place both sides can reach.
# ─────────────────────────────────────────────────────────────────────────────

#: How much of the two boxes' union the intersection must cover before a box
#: is read as another box's own ink, boxed a second time under a different
#: class. Measured 0.94-0.96 on the two crop-verified instances above; 0.9
#: leaves margin below both without reaching into the range two independently
#: drawn, merely-nearby boxes could share by chance.
TIMESIG_DIGIT_DUPLICATE_IOU_MIN = 0.9


def box_iou(a: Any, b: Any) -> float:
    """IoU of two `Q.GLYPH_BOX` VALUE tuples `(class, x, y, w, h)` in the SAME
    cell's canonical frame. Pure geometry -- the class slot (`a[0]`/`b[0]`) is
    never read here; the caller decides which classes are worth comparing."""
    _, x0a, y0a, wa, ha = a
    _, x0b, y0b, wb, hb = b
    x1a, y1a = x0a + wa, y0a + ha
    x1b, y1b = x0b + wb, y0b + hb
    iw = max(0.0, min(x1a, x1b) - max(x0a, x0b))
    ih = max(0.0, min(y1a, y1b) - max(y0a, y0b))
    inter = iw * ih
    union = wa * ha + wb * hb - inter
    return inter / union if union > 0 else 0.0


def is_timesig_digit_ink(box_value: Any, timesig_box_values: Iterable[Any]
                         ) -> bool:
    """True when `box_value` is the SAME ink as one of `timesig_box_values`
    -- IoU strictly greater than `TIMESIG_DIGIT_DUPLICATE_IOU_MIN` against at
    least one of them. `box_value` is any `Q.GLYPH_BOX` value tuple; this
    does not check its class -- only that it shares a box with something the
    caller already knows is a `timeSig*`-classed row. Malformed tuples (not a
    5-tuple) answer `False` rather than raising, matching the two callers'
    own existing shape guards."""
    if not isinstance(box_value, (list, tuple)) or len(box_value) != 5:
        return False
    for ts_val in timesig_box_values:
        if not isinstance(ts_val, (list, tuple)) or len(ts_val) != 5:
            continue
        if box_iou(box_value, ts_val) > TIMESIG_DIGIT_DUPLICATE_IOU_MIN:
            return True
    return False
