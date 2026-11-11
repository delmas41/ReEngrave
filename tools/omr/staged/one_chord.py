"""ONE CHORD IS ONE EVENT -- ROADMAP 2.300 (flag `OMR_ONE_CHORD_ONE_EVENT`, default OFF). PATH: STAGED.

CONVENTION ASSUMED (page-facts: "Every note on one stem shares one written value"; CLAUDE.md §5 "Stems: up -> right, down -> left"):
the two heads of a SECOND stand on opposite sides of ONE stem, one head a half-space above the other and about one head
width to the side; the heads on one stem are one chord, one event, one written value. A whole-note second has no stem: its
two heads, a step apart and one head width to the side, at one onset, are one chord.
WHAT WOULD FALSIFY IT: two beamed notes a step apart and one head width apart, each on its OWN stem (they are two events;
the join below needs the partner's stem to stand between the two heads, and a head with a stem of its own is never joined
to its neighbour's), or two voices at one onset with stems in opposite directions (two stems, never one: never merged here).
NOT CONFIRMED by Sean beyond his 2.291 tile 7 ("two half notes a second apart", one chord) and his 11 Brahms p0 stem labels.

WHY IT EXISTS (2.300 step 1, benchmarks/one-chord-one-event-2026-11/FINDINGS.md): `voicing.group_chords_in_measure` and
`adjudicate_event` group heads by x within 0.6 of a head's width, and the two heads of a second stand ~1.0 head width apart, so
they were two events, each advancing the bar: a half-note second summed 3.0 in a 2/4 bar (tile 7). Where a head touches no
stem (its partner holds it) `adjudicate_head_stem` abstained `no_stem`, so "every note on one stem shares one value" never
reached it. This module holds the ONE geometry both fixes read (the head-to-stem join and the grouping), so the two cannot
drift; it is a rule over boxes in the cell frame and decides nothing about a value.

NOTHING IS INVENTED. The bar sum is not read. A merge needs the PAGE's evidence: a decided `Q.HEAD_STEM` shared by the two
heads (or, for whole notes, no stem at all), AND the second's geometry. Where the heads' written values disagree the export
does not merge them (left as two events, counted).
"""
from __future__ import annotations

import os
from typing import Any, List, Sequence, Tuple

ENV = "OMR_ONE_CHORD_ONE_EVENT"

#: Centre-to-centre horizontal offset of a second's heads, in head widths (a second's heads touch side by side: 1.0; boxes
#: are ~+-0.3 loose). Below the low end the x grouping (0.6) already joins them; above the high end a head is the next note.
SECOND_DX = (0.7, 1.35)
#: Centre-to-centre vertical offset, in head heights: one step is half a staff space, a head is about one space tall.
SECOND_DY = (0.3, 0.8)


def enabled() -> bool:
    """`OMR_ONE_CHORD_ONE_EVENT`, default OFF; only 1/true/yes/on enables."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


Box = Tuple[float, float, float, float]   # x, y, w, h in the cell's canonical frame


def is_second(a: Box, b: Box) -> bool:
    """Do two head boxes stand as the two heads of a second (beside each other, one step apart)?"""
    w = (a[2] + b[2]) / 2.0
    h = (a[3] + b[3]) / 2.0
    if w <= 0 or h <= 0:
        return False
    dx = abs((a[0] + a[2] / 2.0) - (b[0] + b[2] / 2.0)) / w
    dy = abs((a[1] + a[3] / 2.0) - (b[1] + b[3] / 2.0)) / h
    return SECOND_DX[0] <= dx <= SECOND_DX[1] and SECOND_DY[0] <= dy <= SECOND_DY[1]


def stem_between(stem: Box, a: Box, b: Box) -> bool:
    """The stem's centre line stands between the two heads' centres (the seam a second's heads share) and its span covers
    BOTH heads' vertical middles (a stem of a second passes both heads)."""
    sx = stem[0] + stem[2] / 2.0
    ax = a[0] + a[2] / 2.0
    bx = b[0] + b[2] / 2.0
    if not (min(ax, bx) <= sx <= max(ax, bx)):
        return False
    lo, hi = stem[1], stem[1] + stem[3]
    return all(lo <= (q[1] + q[3] / 2.0) <= hi for q in (a, b))


def partner_stems(head: Box, others: Sequence[Tuple[Any, Box]],
                  stems: Sequence[Tuple[Any, Box]], touches: Any) -> List[Tuple[Any, Any, Box]]:
    """The stem a head that touches NO stem stands on, because its neighbour in a second holds it.

    `others`: (key, box) of the cell's OTHER heads; `stems`: (key, box) of the cell's stems; `touches(stem_box, head_box)`:
    the caller's own stem-contact test. Returns every `(stem_key, partner_key, partner_box)` that fits; the caller decides
    whether they are one physical stem. Never invents: a candidate needs (1) a partner in the geometry of a second,
    (2) that partner touching a stem, (3) that stem between the two heads."""
    found = []
    for pkey, pbox in others:
        if not is_second(head, pbox):
            continue
        for skey, sbox in stems:
            if touches(sbox, pbox) and stem_between(sbox, head, pbox):
                found.append((skey, pkey, pbox))
    return found
