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
    """`OMR_HAIRPIN_REACH`, default ON (ROADMAP 2.254, Sean 2026-11-02 "Land on as is"); 0/false/no/off disables."""
    return os.environ.get(ENV, "").strip().lower() not in ("0", "false", "no", "off")


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


# ── round 2: the hairpin read CLAIMS its own strokes, and the word reader does not read them ────────────────────────────────────────────────
# CAUSE (round 2, measured on Brahms p8 from the round-1 slices): of the 13,790 px the round-1 claim readout put in `word_dynamic ->
# stem_beam_flag`, 13,677 px stand under BOTH a detector `beam` box (scores 0.27-0.93, two to five boxes on each arm) and a cv_lines
# `beam_stroke` read: the detector and the line reader take a hairpin's thin straight arm for a beam. The CV hairpin read filed a
# `Q.WEDGE_BOX` row and claimed no ink, so once round 1 shrank the word's claim the stroke owner found no claimant before the consumers and
# the beam took the arm; and the OCR box that had read the wedge as a letter ('a dim') still counted as a word read of it.

#: the register's owner name for a hairpin read's ink claim (`unit: ink`, one row per (hairpin, staff whose cells it crosses))
OWNER = "hairpin"
#: `stroke_owner` family of the claim (tier 0, beside `arc_trace`: a page-wide mark claims its ink before the heads, plan 2026-10-28 s9)
FAMILY = "hairpin_trace"
#: a pixel lies ON an arm when it is within this many spaces of the arm's centre line (an arm is ~0.1-0.15 sp thick; a scan wanders ~1 px).
#: CONVENTION ASSUMED: a hairpin's arms are straight lines from the apex (mid-height of the narrow end) to the open end's corners of the
#: read box. WHAT WOULD FALSIFY IT: a head, stem or beam Sean values losing its stroke to the claim. NOT CONFIRMED: set on Brahms p8.
ARM_BAND_SPACES = 0.2
ARM_BAND_MIN_PX = 2.0
#: a stroke is the hairpin's when at least this share of its ink lies on the arms (the register's one cut, `arc_claim.ON_TRACE_SHARE_MIN`):
#: a stem or barline crossing an arm has a few pixels there and keeps its ink
ON_ARMS_SHARE_MIN = 0.5


def arms(kind: str, bbox) -> list:
    """The two arms of a hairpin as page-px segments `[[xa, ya, xb, yb], [...]]`, from its read box and kind: a crescendo's apex is the
    middle of the LEFT edge and it opens to the right corners; a diminuendo the mirror. The reader fits the box to the arms' ink."""
    x0, y0, x1, y1 = (float(v) for v in bbox)
    ym = (y0 + y1) / 2.0
    if str(kind) == "crescendo":
        return [[x0, ym, x1, y0], [x0, ym, x1, y1]]
    return [[x1, ym, x0, y0], [x1, ym, x0, y1]]


def dist_to_segments(px, py, segs):
    """Distance (page px) of each point to the nearest of `segs`."""
    import numpy as np
    best = np.full(np.shape(px), np.inf)
    for xa, ya, xb, yb in segs:
        dx, dy = xb - xa, yb - ya
        L2 = dx * dx + dy * dy
        t = np.clip(((px - xa) * dx + (py - ya) * dy) / L2, 0.0, 1.0) if L2 > 0 else np.zeros(np.shape(px))
        best = np.minimum(best, np.hypot(px - (xa + t * dx), py - (ya + t * dy)))
    return best


def band_px(spacing: float) -> float:
    return max(ARM_BAND_MIN_PX, ARM_BAND_SPACES * float(spacing or 0.0))


def on_arms_share(mask, x0: int, y0: int, scale: float, cell_box, up: float, segs, bbox, band: float) -> float:
    """The share of one stroke's ink (`stroke_map` mask, REDUCED px, origin `x0, y0` in the cell's reduced frame) that lies on the arms --
    inside the hairpin's box (+ `band`) and within `band` page px of an arm (the frame conversion is `arc_claim.on_trace_share`'s)."""
    import numpy as np
    ys, xs = np.nonzero(mask)
    if ys.size == 0 or scale <= 0 or up <= 0:
        return 0.0
    px = float(cell_box[0]) + ((x0 + xs + 0.5) / scale) / up
    py = float(cell_box[1]) + ((y0 + ys + 0.5) / scale) / up
    bx0, by0, bx1, by1 = (float(v) for v in bbox)
    inside = (px >= bx0 - band) & (px <= bx1 + band) & (py >= by0 - band) & (py <= by1 + band)
    if not inside.any():
        return 0.0
    on = np.zeros(px.shape, bool)
    on[inside] = dist_to_segments(px[inside], py[inside], segs) <= band
    return float(on.sum()) / float(ys.size)


def claim_strokes(res, cell_box, up: float, segs, bbox, band: float) -> list:
    """`[(stroke ordinal, share)]` for every stroke of a cell (`stroke_map.CellStrokes`) that lies `ON_ARMS_SHARE_MIN` on the arms."""
    out = []
    for i, (m, x0, y0) in enumerate(getattr(res, "masks", None) or []):
        if getattr(m, "size", 0) == 0:
            continue
        sh = on_arms_share(m, x0, y0, res.scale, cell_box, up, segs, bbox, band)
        if sh >= ON_ARMS_SHARE_MIN:
            out.append((i, round(sh, 3)))
    return out


def erase_entries(log, page: int) -> list:
    """The hairpins the CV reach reader read on `page`, as `direction_text` erase entries (`{"bbox_page_px", "segments", "band_px"}`): the
    word reader must not read a hairpin's arms as letters ('a dim', 'p espr' on Brahms p8). The flag is the caller's to read."""
    from .record import Q
    from . import record as R
    out = []
    for r in log.rows(Q.WEDGE_BOX, R.page(page), scope=R.Scope.SELF_AND_DESCENDANTS):
        d = r.detail or {}
        bb = d.get("bbox_page_px")
        if not d.get("reach") or not (isinstance(bb, (list, tuple)) and len(bb) == 4):
            continue
        out.append({"bbox_page_px": [float(v) for v in bb], "segments": arms(r.value, bb),
                    "band_px": band_px(d.get("staff_spacing_px") or 0.0)})
    return out


# ── round 3: a READ word's box is cut to its OWN ink where a hairpin runs through it ──────────────────────────────────────────────────────
# CAUSE (round 3, Brahms p8 'p espr', 'P dolce', 'pp cresc. molto'): the hairpin is engraved just ABOVE the word, over its x-height, and the
# OCR box is one rectangle from the tallest letter ('p', 'd', 'l') to the lowest, so it holds the hairpin's arms; the reach read claims those
# arms first, and the word's box still READ them (claim readout `word_dynamic -> arc_hairpin`). Round 2's cut only removed an ink component
# that passed the wedge shape tests by itself, which a hairpin cut by the box edge or touching a letter does not; and where it did fire it
# dropped every letter under the hairpin's x span ('espr' of 'p espr'). The word's own ink is its box's ink less the arm pixels.

#: a word pixel within this many spaces of a hairpin arm is the hairpin's (wider than `ARM_BAND_SPACES`: the arms' soft edge and the
#: scan's wander must not be left as a sliver of 'word' ink between them)
WORD_ARM_BAND_SPACES = 0.35
#: an ink piece left after the arms are cut this small (in sp^2) and this near an arm is the arm's debris, not a letter (a period is ~0.09)
ARM_DEBRIS_MAX_SP2 = 0.04
ARM_DEBRIS_NEAR_SPACES = 0.6


def word_ink_boxes(binary, box, entries, spacing):
    """The READ word's own ink as rectangles (page px), none holding a hairpin's arm, or None when no hairpin read (`erase_entries`) meets
    `box` (the word is left as it was). Letters are grouped left to right while their joint rectangle holds no arm pixel."""
    import cv2
    import numpy as np
    if not entries or not spacing:
        return None
    x0, y0, x1, y1 = (int(round(float(v))) for v in box)
    x0, y0 = max(0, x0), max(0, y0)
    pad = WORD_ARM_BAND_SPACES * float(spacing)
    segs = []
    for e in entries:
        bb = e.get("bbox_page_px")
        if bb and bb[0] - pad < x1 and bb[2] + pad > x0 and bb[1] - pad < y1 and bb[3] + pad > y0:
            segs.extend(e.get("segments") or ())
    if not segs:
        return None
    crop = binary[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    ink = crop == 0
    yy, xx = np.mgrid[y0:y0 + crop.shape[0], x0:x0 + crop.shape[1]]
    dist = dist_to_segments(xx + 0.5, yy + 0.5, segs)
    arm = ink & (dist <= pad)
    if not arm.any():
        return None
    rest = (ink & ~arm).astype(np.uint8) * 255
    n, lab, st, _c = cv2.connectedComponentsWithStats(rest, 8)
    sp2 = float(spacing) ** 2
    comps = []
    for k in range(1, n):
        x, y, w, h, a = (int(v) for v in st[k])
        if a < ARM_DEBRIS_MAX_SP2 * sp2 and float(dist[lab == k].min()) <= ARM_DEBRIS_NEAR_SPACES * float(spacing):
            continue
        comps.append((x, y, x + w, y + h))
    if not comps:
        return []
    arm_i = arm.astype(np.int32).cumsum(0).cumsum(1)

    def holds_arm(r):
        a, b, c, d = r
        tot = arm_i[d - 1, c - 1]
        if a > 0:
            tot -= arm_i[d - 1, a - 1]
        if b > 0:
            tot -= arm_i[b - 1, c - 1]
        if a > 0 and b > 0:
            tot += arm_i[b - 1, a - 1]
        return tot > 0

    groups = []
    for c in sorted(comps):
        if groups:
            g = groups[-1]
            m = (min(g[0], c[0]), min(g[1], c[1]), max(g[2], c[2]), max(g[3], c[3]))
            if not holds_arm(m):
                groups[-1] = m
                continue
        groups.append(c)
    return [[float(x0 + g[0]), float(y0 + g[1]), float(x0 + g[2]), float(y0 + g[3])] for g in groups]
