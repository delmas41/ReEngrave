"""ROADMAP 2.254 -- HAIRPIN REACH. PATH: STAGED (GATHER reads, ADJUDICATE refuses a one-note wedge's kind). Flag `OMR_HAIRPIN_REACH`,
default OFF. Registered in `reach.NOT_A_STAGE` (a flag module, like `hairpin_bind`).

CAUSE (benchmarks/hairpin-reach-2026-11): the CV wedge reader (`hairpin_detection.detect_hairpins`) tests a hairpin as a connected
component of its own -- straight outlines, isolated on the page. On an orchestral page a BARLINE runs through the gap between the
staves of a bracket group, and stems, ledger-lined heads and slurs of the neighbouring staves reach into the band; a hairpin crossing
or touching any of them is one component with it, and is refused 'outline' or 'isolated'. Measured on Brahms p19 (crops): the long
hairpins of bars 352-358 all fail that way; the reader filed 1 of ~20 there.

ON, the reader (`detect_hairpins(..., reach=True)`):
  1. removes every vertical stroke 1.2+ spaces long (barline, stem) and closes the 0.5 sp gap it leaves (`reach_inks`);
  2. keeps only ink along a straight near-horizontal run 1.5+ spaces long (`straight_runs`: a slur's steep ends and every head fall
     away from a hairpin's arms);
  3. accepts an outline that is straight after trimming its worst 15% of columns (`robust_outline_rms`: a long scanned hairpin, a
     dot glued at one end);
  4. and, because a beam stripped of its stems is now as isolated as a hairpin and the rejoin can glue a word's letters, requires
     the arms to CONVERGE (`converges`) and the opening to grow steadily (`extent_trend`).

And in ADJUDICATE (`ownership._wedge_page_binding`): a wedge whose two tips bind to the SAME note and no wider than an accent glyph
(`ACCENT_MAX_W_SP`) is a one-note wedge, which may be an accent or a hairpin (Sean 2026-11-02, page-facts: "Hairpins can be one note in length also but only hairpins can be longer than a
note") -- it abstains `one_note_wedge`, counted, never written as either (CLAUDE s4).

CONVENTION ASSUMED: a hairpin's arms are straight lines that meet at the apex (page-facts: arcs bow, hairpins are straight).
WHAT WOULD FALSIFY IT: a real hairpin refused by the convergence or trend test, or a beam/word filed as a hairpin, on Sean's tiles.
NOT CONFIRMED: every cut-off above was set on Brahms p19/p25; they only narrow what the reader keeps.
"""
from __future__ import annotations

import os

ENV = "OMR_HAIRPIN_REACH"


def enabled() -> bool:
    """`OMR_HAIRPIN_REACH`, default OFF (ROADMAP 2.254); 1/true/yes/on enables."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


#: ADJUDICATE abstains a one-note wedge only when it is no longer than this: an accent is a printed glyph of one size (Brahms p5: the
#: accents the reach reads are 1.6-2.1 sp), while a hairpin held under one long note is as long as the note's room (Brahms p8: 17
#: one-note wedges, 3.9-6.7 sp; Sean 2026-11-02 read the ~5.5 sp one-note wedges of Brahms p19 bars 358-361 as hairpins).
#: CONVENTION ASSUMED: an accent is never wider than 3 spaces. WHAT WOULD FALSIFY IT: a one-note wedge 3+ sp that Sean reads as an
#: accent. NOT CONFIRMED beyond the p19 crop.
ACCENT_MAX_W_SP = 3.0

#: A component this many spaces wide is past any letter (2.245's `HAIRPIN_MIN_W_SP`, the same cut the wedge reader refuses letters by).
WEDGE_IN_WORD_MIN_W_SP = 1.6


def word_area_without_wedges(binary, box, spacing):
    """A READ word's claim area, less any hairpin-shaped ink component inside its box (ROADMAP 2.254; plan 2026-10-28 s5: a clearly read
    word takes ITS OWN ink; 2.253: on Brahms p8 the OCR box of 'dim.'/'espr.' held a real hairpin, read as a letter 'a').

    A component inside the box is a wedge when it is at least `WEDGE_IN_WORD_MIN_W_SP` wide and passes the reach reader's own shape
    tests (opens, straight outline, converges, opens steadily). Returns `(areas, dropped_boxes)`: one area round the ink left of the
    wedge(s) and one round the ink right of them (ink overlapping the wedges' x span is not the word's), or `[box]` unchanged when no
    wedge is inside it or no ink would be left. Page px corners in and out."""
    import cv2
    import numpy as np
    from .. import hairpin_detection as H
    x0, y0, x1, y1 = (int(round(float(v))) for v in box)
    x0, y0 = max(0, x0), max(0, y0)
    crop = binary[y0:y1, x0:x1]
    if crop.size == 0 or not spacing:
        return [float(v) for v in box], []
    ink = (crop == 0).astype(np.uint8) * 255
    n, lab, stats, _c = cv2.connectedComponentsWithStats(ink, 8)
    keep, dropped = [], []
    for k in range(1, n):
        x, y, w, h, _a = stats[k]
        if w >= WEDGE_IN_WORD_MIN_W_SP * spacing:
            mask = ((lab[y:y + h, x:x + w] == k).astype(np.uint8)) * 255
            m = H.measure_component(mask, float(spacing))
            if m is not None and m["open_spaces"] >= H.MIN_OPEN_SPACES and H.converges(m) \
                    and H.extent_trend(mask) >= H.REACH_MIN_EXTENT_TREND \
                    and (m["outline_rms_spaces"] <= H.MAX_OUTLINE_RMS_SPACES
                         or (H.robust_outline_rms(mask, float(spacing)) or 9.0) <= H.MAX_OUTLINE_RMS_SPACES):
                dropped.append([float(x0 + x), float(y0 + y), float(x0 + x + w), float(y0 + y + h)])
                continue
        keep.append((x, y, x + w, y + h))
    if not dropped or not keep:
        return [[float(v) for v in box]], []
    # The word's ink left and right of the wedge(s): a rectangle round all of it would hold the wedge again ('p espr', 'a dim' on p8).
    wx0 = min(d[0] for d in dropped) - x0
    wx1 = max(d[2] for d in dropped) - x0
    sides = [[k for k in keep if k[2] <= wx0], [k for k in keep if k[0] >= wx1]]
    areas = [[float(x0 + min(k[0] for k in g)), float(y0 + min(k[1] for k in g)),
              float(x0 + max(k[2] for k in g)), float(y0 + max(k[3] for k in g))] for g in sides if g]
    if not areas:
        return [[float(v) for v in box]], []
    return areas, dropped
