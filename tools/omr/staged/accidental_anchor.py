"""ROADMAP 2.199 -- THE ACCIDENTAL OWNER'S ANCHOR WITHOUT A CLASS GUESS (flag `OMR_ACCIDENTAL_ANCHOR_UNCLASSED`, default OFF). ADJUDICATE
(`adjudicate_accidental_owner`) + EXPORT (the GUESSED mark). STAGED.

THE CAUSE (benchmarks/omr-accidental-anchor-2026-10/FINDINGS.md): the owner looks for the head at the height the glyph's CLASS names
(`gather._ANCHOR_FRACTION`: a flat's bowl, 0.715 down its box, because the flat's stem rises above the line it names; a sharp / natural at its
centre). That is right once the class is right. A NATURAL the detector boxed as a flat is searched from a point ~1.4-2 positions BELOW its real
height, so its own head falls just outside the owner's 1.4-position bound and the glyph abstains `no_candidate` (2.197: 22 of 23 Brahms and 8
of 8 Litolff near-miss flats are inside the bound from the box centre). The class is a guess (2.190: the detector's argmax is wrong on naturals);
the head search was resting on it.

WHAT THIS DOES, AND WHAT IT DOES NOT: ONLY where the class's own anchor finds NO head, and ONLY where nothing independent confirms the class
(the 2.190 shape reader does not read the shape the class names), the owner searches once more from the BOX CENTRE -- the anchor of every class
that is not a flat -- with the same x window, the same 1.4 bound and the same ambiguity test. It is strictly additive: every glyph the class
anchor decides (or abstains `ambiguous_height`) is untouched, so no decided head can move (measured, FINDINGS control). The head is the geometry's
and the ALTERATION stays the detector's label, written GUESSED (blue) with the measured shape beside it: the box centre says where the head is;
it does not say what the glyph is. A shape that reads the SAME class as the label keeps the class anchor (the class is then confirmed, and a miss
means the head is missing, not the anchor). Options (a) centre for every class and (b) the union of offered classes' anchors were measured and
rejected (FINDINGS): (a) moves or abstains decided heads, (b) abstains on a quarter of them and recovers nothing.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

ENV = "OMR_ACCIDENTAL_ANCHOR_UNCLASSED"
RULE = "accidental_anchor_unclassed"

#: The two anchors must differ by at least HALF A DIATONIC STEP (1 position = a step; the owner's own `_ACC_AMBIGUOUS_MARGIN_POSITIONS`) for the
#: second search to say anything the first did not. For a sharp / natural / double sharp the font's anchor is 0.50 of the box, i.e. the centre, so
#: the two searches coincide to ~0.01 positions and a "recovery" there would be a bound artefact, not a different anchor.
MIN_SHIFT_POSITIONS = 0.5


def enabled() -> bool:
    """`OMR_ACCIDENTAL_ANCHOR_UNCLASSED`, default OFF (ROADMAP 2.199); an explicit 1/true/yes/on enables."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


#: Another accidental-family box in the cell that covers at least this share of the SMALLER box's area is the SAME INK boxed twice (2.185/2.186: the
#: merge keeps two boxes when their IoU is under its cut). Measured here: every flat the second search would "recover" onto a head that a natural twin
#: already owned made a contradiction at EVALUATE (two glyphs, two alterations on one head -> nothing written) and LOST the natural.
TWIN_COVER_MIN = 0.3


def twin_of(box, others) -> Optional[Any]:
    """The first of `others` ((key, x, y, w, h) boxes of the cell's other accidental-family glyphs) that covers >= `TWIN_COVER_MIN` of the smaller
    of the two boxes, else None. `box` is (x, y, w, h)."""
    x, y, w, h = box
    for key, ox, oy, ow, oh in others:
        iw = min(x + w, ox + ow) - max(x, ox)
        ih = min(y + h, oy + oh) - max(y, oy)
        if iw <= 0 or ih <= 0:
            continue
        if iw * ih >= TWIN_COVER_MIN * min(w * h, ow * oh):
            return key
    return None


def applies(detector_class: str, class_position: float, centre_position: Optional[float], shape: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """None when the class anchor must stand; else `{why, shift_positions}` saying why the class is not trusted: `contradicted` (the shape
    reader clearly reads another accidental), or `unverified` (unclear / unread / a class with no shape: nothing confirms it)."""
    from . import accidental_shape as _s
    if centre_position is None:
        return None
    shift = float(centre_position) - float(class_position)
    if abs(shift) < MIN_SHIFT_POSITIONS:
        return None
    named = _s.shape_of_class(detector_class)
    measured = (shape or {}).get("shape")
    if named is not None and measured == named:
        return None                                   # an independent-enough second reading confirms the class: its anchor stands
    why = "contradicted" if measured in ("flat", "natural", "sharp") else "unverified"
    return {"why": why, "shift_positions": round(shift, 3), "measured_shape": measured, "named_shape": named}
