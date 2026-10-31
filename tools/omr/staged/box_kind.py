"""ROADMAP 2.245 -- a detector box is tested against its OWN class's printed size before it stands as that kind (flag `OMR_BOX_KIND_SIZE`,
default OFF). STAGED ADJUDICATE, PURE: imports nothing from the pipeline.

THE CAUSE (benchmarks/wrong-kind-boxes-2026-10/FINDINGS.md). Sean's tiles found four marks GATHER filed as the wrong kind. In every one
the detector boxed ONE ink under several classes, and a low-confidence twin of the wrong class (0.26-0.29 in three of the four) was taken
as a mark of its class: the claim layers (the stroke owner's claimants, the page owner's marks, the system-arc reader) take a detector
box's CLASS as its KIND and never ask whether the box itself has that kind's printed size or its ink that kind's shape. Brahms p5
`glyph/5/0/4/4/15` is a `noteheadBlackOnLine` box 5.2 x 1.5 spaces -- exactly the slur four other boxes already name -- and ADJUDICATE
kept it as a head. A head is printed at most 1.69 spaces wide (SMuFL `noteheadWhole`; `noteheadBlack` 1.18): a box that wide holds no
single head.

THE RULE (this module): a head-class box at least `HEAD_BOX_MAX_W_SP` wide cannot be one head. The number is the stroke owner's own
convention size for a head's ink (`stroke_owner.HEAD_MAX_W_SP`: "a head 1.3 wide; fused to its ledger (~2.2) it is still the head's
blob"), not a cut tuned to a count: 1.8x the widest printed head. CONVENTION ASSUMED: one head is printed at most a whole note's width.
WHAT WOULD FALSIFY IT: a real single head boxed 3 or more spaces wide (a double-whole breve with its side bars is 2.5) -- Sean's tiles
in out/print/2.245-tiles. NOT CONFIRMED by Sean.

Consumer (flag ON): `adjudicate_notehead_is_not_a_notehead` refuses the box `wider_than_a_head`, LAST among its refusals (it speaks
only where every other rule would keep the box). Nothing is invented (rule 8). NOT read by the stroke owner: measured, a size veto there
lost real Litolff eighths -- a wide box over MERGED heads is the only claimant big enough to hold the fused head blob -- and where the
wide box stands on non-head ink (a slur, a beam) the per-stroke `shape_fit` already refuses it. Other lanes read the same predicate where they take a box as a mark (the page owner,
2.240; the accidental's whole-mark test, 2.242) -- see FINDINGS.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

ENV = "OMR_BOX_KIND_SIZE"
#: default OFF. Deny-list form: once the default flips to "1", only an explicit off-word disables it.
DEFAULT = "0"
OFF_WORDS = ("0", "false", "no", "off", "")

#: a head's ink is at most this wide (staff spaces): `stroke_owner.HEAD_MAX_W_SP`, the convention the owner already reads a head's
#: blob by. Read from there so the two never disagree.
from .stroke_owner import HEAD_MAX_W_SP as HEAD_BOX_MAX_W_SP  # noqa: E402

REASON_WIDE = "wider_than_a_head"


def enabled() -> bool:
    """`OMR_BOX_KIND_SIZE` (ROADMAP 2.245), default OFF."""
    return os.environ.get(ENV, DEFAULT).strip().lower() not in OFF_WORDS


def is_head_class(cls: object) -> bool:
    return str(cls or "").lower().startswith("notehead")


def head_box_misfit(cls: object, w_sp: float, h_sp: float) -> Optional[Tuple[str, float]]:
    """`(reason, margin)` when a head-class box cannot be ONE head by its own size, else None. `margin` = how far past the bound, staff
    spaces (positive = refused by this much). Not a head class, or no size: None (the rule says nothing)."""
    if not is_head_class(cls) or not w_sp or w_sp <= 0:
        return None
    if w_sp >= HEAD_BOX_MAX_W_SP:
        return REASON_WIDE, float(w_sp) - HEAD_BOX_MAX_W_SP
    return None
