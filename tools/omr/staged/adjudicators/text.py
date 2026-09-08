"""Dynamics and direction words."""

from __future__ import annotations

from ..adjudicate import Checkable, Evidence, Mode, Ruling, decision
from ..record import ABSTAIN, Kind, Q, Scope, State


@decision(
    quantity=Q.DYNAMIC,
    composed_from=(Q.DYNAMIC_LETTER, Q.GLYPH_OWNER),
    scope=Kind.CELL,
    wants=(Q.DYNAMIC_LETTER, Q.GLYPH_OWNER),
    reasons=("spelled", "unspellable", "no_letters"),
    mode=Mode.ADDITIVE,
    stub=True,
)
def adjudicate_dynamic(ev: Evidence) -> Ruling:
    """⚠️ DECLARED STUB. Join letters into a word by x-adjacency.

    ⚠️ AND THE KNOWN GAP IT SHOULD CLOSE: `export.measure_dynamics` uses NO
    VERTICAL INFORMATION AT ALL. Measured over 1246 letters on 18 pages of 9
    publishers, 73% of letters stand in their own staff's band and 24% in the
    band of the staff IMMEDIATELY ABOVE -- distance exactly 1, no exceptions.
    ⚠️ A GATE IS THE WRONG FIX: an out-of-band letter is usually the
    neighbour's ink, and 83% of re-attributed letters are the target staff's
    SOLE evidence. It belongs in ownership as another evidence tier, which is
    why `Q.GLYPH_OWNER` is declared here rather than a band threshold.
    """
    return Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)


@decision(
    quantity=Q.DIRECTION,
    composed_from=(Q.DIRECTION_WORD,),
    scope=Kind.CELL,
    wants=(Q.DIRECTION_WORD,),
    reasons=("in_lexicon", "not_in_lexicon", "no_words"),
    mode=Mode.ADDITIVE,
    stub=True,
)
def adjudicate_direction(ev: Evidence) -> Ruling:
    """⚠️ DECLARED STUB. ⚠️ THE LEXICON GATE IS LOAD-BEARING AND MUST NOT BE
    LOOSENED -- it is what stops every smudge on the page becoming a word.
    """
    return Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)
