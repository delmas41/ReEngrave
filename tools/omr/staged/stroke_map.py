"""ROADMAP 2.195 -- the shared ink map, STEP 1: every stroke of a cell, measured ONCE (`Q.STROKE`).

STAGED GATHER, PURE: this module imports numpy and cv2 and nothing from the pipeline. `gather.gather_stroke_map` is the only
caller; it files what is returned here as `Q.STROKE` rows and decides nothing (plan `docs/plan-2026-10-22-shared-ink-map.md`
§2.1, §5 step 1). Nothing reads the rows yet (the `Q.INK` discipline: a producer and its first consumer in one change make the
reach measurement circular), so with `OMR_STROKE_MAP` on the exported file is byte-identical to flag off.

WHAT A STROKE IS. One piece of ink in one cell, found on the staff-ERASED raster (`cell.image_no_staff`, the one the CV readers
read -- the detector keeps reading the original). Not a connected component (Litolff MERGES a head, an accidental and a beam into
one; Breitkopf SHATTERS a rest into three): run analysis separates it, in this order, each ink pixel claimed by the first kind
that fits it --

  vertical    a run-stack at least `V_MIN_SPACES` tall (stem, barline, accidental stem; a vertical opening)
  horizontal  a run-stack at least `H_MIN_SPACES` long and thin (beam, ledger rung, rest bar; a horizontal opening, then the
              piece must be long against its thickness, else it is a head's lens and goes back to the remainder)
  curve       what is left, long and thin (tie, slur, hairpin line, flag hook)
  blob        what is left, otherwise (head, rest body, accidental bowl, dot, letter)

The two openings may SHARE the pixels where a stem crosses a beam (a crossing belongs to both strokes and is reported as
contact); the remainder is cut one pixel away from them so a head beside a stem does not keep a sliver of it.

THE SAME FINDERS' POPULATIONS, NOT A NEW DETECTOR: the vertical opening is `detect_stems`' first step, the horizontal one
`detect_beams`', the components `_ink_components`'. The cell is first reduced to `TARGET_SP_PX` pixels per staff space (a canonical
cell is 90-100 px per space; the kernels cost O(kernel) per pixel), which makes every field scale-free.

THE STAFF IS MEASURED LOCALLY (CLAUDE §5: a scanned staff tilts and ~1 px decides a near-boundary pitch). One class,
`LocalStaff.lines_at(x)`, finds the five lines in windows on the RAW raster and interpolates; a stroke's two ends are given in staff
steps from the lines AT THEIR OWN x. Where it cannot place all five it says so (`staff_local` false) and uses the nominal lines.

WHAT IS NOT FILED. A piece under `MIN_AREA_SP2` staff-space-squared is counted (`n_below_floor`), not filed: each of the ~30 specks a
Breitkopf cell shatters into would cost more bytes than all other quantities together. 0.05 sits under an augmentation dot (~0.12).
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

TARGET_SP_PX = 16.0
#: A reduced pixel is ink when this much (of 255) of its source was. A tie's end / ledger rung is ~2 px thick at this scale.
COVER_THRESHOLD = 96
V_MIN_SPACES = 1.5
H_MIN_SPACES = 1.0
#: length^2 / area of a horizontal piece: beam 5-30, rung 8+, filled head's lens 1.3-1.8.
H_MIN_ASPECT = 2.5
CURVE_MIN_SPACES = 1.5
CURVE_MAX_THICK_SPACES = 0.5
CURVE_MIN_ASPECT = 2.0
MIN_AREA_SP2 = 0.05
PROFILE_SAMPLES = 12
ANCHOR_STRIDE_SPACES = 3.0
ANCHOR_HALF_WINDOW_SPACES = 1.5
LINE_SEARCH_SPACES = 0.4
LINE_MIN_INK = 0.5
#: ROADMAP 2.202b. A horizontal / curve stroke's thickness is read on the UNERASED raster (CLAUDE §7: a thickness must not be read off an erased
#: line). `tools/omr/staff_line_removal.py` erases a whole vertical run through a line row when the run it WALKS (bounded at `cap + 2` rows each side)
#: is <= its crossing cut (0.45 sp): a beam 0.6 sp thick lying on a line is walked for ~37 rows, looks like 44 <= 45, and is erased from the line to
#: 37 rows below it, leaving a 0.19 sp sliver (Litolff p16, the 2.202 tile). The ink the eraser took is `raw & ~erased`; the stroke's own pixels plus
#: the erased pixels CONTIGUOUS to them in a column are what was printed there (the eraser only ever takes line rows and the run it walked with them,
#: never a neighbour's ink). False: the 2.202 reading (erased raster only); the control test turns it off to prove the fix is what moves the number.
THICKNESS_FROM_UNERASED = True

KINDS = ("vertical", "horizontal", "curve", "blob")

# ───────────────────────────── ROADMAP 2.239: split fused ink at its joins (flag `OMR_SPLIT_JOINS`, default ON) ─────────────────────────────
#: CAUSE (2.239, Brahms p0 against Sean's labels): the vertical opening is a column test -- a column run of ink at least `V_MIN_SPACES` tall is
#: "vertical" whatever its WIDTH. Two heads a third apart on one stem make columns ~2 sp tall across the whole oval, so the pair AND the stem
#: become one `vertical` stroke (197 of the 212 black heads that own no ink); a head on a ledger rung passes the horizontal opening with the
#: rung (19); a tie or slur touching a head is one remainder piece with it. The detector's head box then covers under half of that stroke and
#: no box owns it. The split below reads only the stroke's own geometry, in the reduced frame, and cuts only where the geometry shows a join;
#: every part keeps a `joined_to` link, so nothing is lost and a later reader still sees the join. Where it cannot tell, the piece stays whole
#: and the reason is counted (`CellStrokes.split_refused`).
SPLIT_JOINS_ENV = "OMR_SPLIT_JOINS"
#: a row run of a vertical stroke no wider than this is STEM (or barline) ink; wider is something fused to it (a head's oval, a beam).
#: Litolff's widest plain stem 0.43 sp, Brahms 0.37 at p90 (`STEM_TRUE_WIDTH_MAX_SPACES` note); a black head is >= 1.0 sp wide.
STEM_THIN_SPACES = 0.5
#: a thin part shorter than this is an oval's tip or a stem's stub beside a head: it goes back to the wide part it touches
STEM_PART_MIN_SPACES = 0.5
#: a wide part smaller than this is a blip on a stem (an erase scar), not a mark fused to it: it goes back to the stem
WIDE_PART_MIN_SP2 = 0.25
#: the height cap of ONE head (`head_ink.MAX_HEIGHT_SPACES_V2`, 2.220 fix 2, Sean "1.6"; a test pins that they are equal) and its width cap
#: (`head_ink.MAX_WIDTH_SPACES`): a wide part taller than this and no wider is a STACK of heads, cut at its waist
HEAD_HEIGHT_CAP_SPACES = 1.6
HEAD_WIDTH_CAP_SPACES = 1.75
#: a stack is at least a head wide (a black head is >= 1.0 sp wide; a bracket's or thick barline's line <= 0.7) and at most four heads tall
HEAD_MIN_WIDTH_SPACES = 0.8
STACK_MAX_SPACES = 5.0
#: a stack is cut only at a row this much narrower than the narrower of its two halves' widest rows (a real neck between two ovals);
#: a stack with no such row stays whole (`stack_no_waist`)
WAIST_SHARE_MAX = 0.75
#: ... or at a row where one edge steps in by at least this from both ovals' extremes (a notch; ~2 reduced px, above the +-1 px scan edge)
STACK_NOTCH_SPACES = 0.12
#: each band of a cut stack is at least this tall: a head (~1 sp), never a rung with the top of a head (2.239 tile 9, Sean "ledger line")
STACK_BAND_MIN_SPACES = 0.8
#: the oval edges of a stack are read on the cell's ink this far beside the part (the opening drops a notched column to the remainder)
STACK_EDGE_PAD_SPACES = 0.3
#: head|arc: a disk this wide survives in a head's body (a black head is ~1 sp tall) and not in a tie or slur (<= `CURVE_MAX_THICK_SPACES`)
HEAD_BODY_SPACES = 0.55
HEAD_BODY_MIN_SP2 = 0.4
#: head|ledger: a horizontal stroke's column run this much thicker than its own line is a head on the rung
LEDGER_HEAD_EXCESS_SPACES = 0.35
LEDGER_HEAD_MIN_WIDTH_SPACES = 0.6
#: ... and the rung sticks out at least this far beyond the oval on BOTH sides (a head at a rung's end, or a beam, is left whole)
LEDGER_STUB_MIN_SPACES = 0.15
#: a column belongs to the oval while its run is this much thicker than the rung's (the oval's edge, 2.239 tiles 6 and 9)
LEDGER_EDGE_EXCESS_SPACES = 0.2
#: an oval tip the horizontal opening left to the remainder is smaller than this
LEDGER_TIP_MAX_SP2 = 0.35
#: ... and lies no further than this outside the head part's box (the oval's edge columns; a dot stands clear of the head)
HEAD_EDGE_PAD_SPACES = 0.3
#: a ledger rung is level: its thin columns' centres fit a line no steeper than this (rise over run; ~3 degrees)
LEDGER_MAX_SLOPE = 0.05

# -- 2.239 round 3 (Sean's round-2 tiles 1, 7, 12): two DIFFERENT marks that merely touch, and a clef the openings chop up --
#: CAUSE: every cut above reads a change of WIDTH inside one mark; two marks that touch (an accidental's bowl on a ledger rung, beside a
#: head) have no such change, so the piece kept both (tile 1 "part of a ledger line and a flat"). And a clef is cut into ~25 pieces by
#: the openings themselves, flag OFF as well (Brahms p5 tile 7 "tip cut of a G clef": the ball is its own remainder piece, INSIDE the
#: clef box); keep-whole only stopped the split from cutting further, it never put the openings' pieces back together.
#: touching marks: the families whose boxes are read (an accidental against a head, a ledger rung or a stem: 2.239 r3 brief)
TOUCH_ACC_FAMILY = "accidental"
TOUCH_OTHER_FAMILIES = ("head", "ledger", "stem")
#: a piece is cut along the two boxes' boundary only when each side holds at least this share of its ink in its own box ALONE
TOUCH_SIDE_MIN_SHARE = 0.15
#: ... and at least this much ink (staff spaces^2, ~5 reduced px: under it the side is a scan edge, not a mark's ink)
TOUCH_SIDE_MIN_SP2 = 0.02
#: the accidental's side STANDS ALONE as its own stroke (at least `TOUCH_SIDE_MIN_SP2`). Joining it to the accidental stroke it touches
#: (`TOUCH_JOIN_HOST`) was tried and DROPPED: it widened the natural's stem stroke and the 2.201 family reading lost 4 naturals and a flat
#: (natural -> unclear, Brahms p5 / Litolff p4 -- the control that caught it). A side standing alone below `TOUCH_ALONE_MIN_SP2` is allowed
#: (a split part is filed whatever its size); the constant is read only when joining is on.
TOUCH_ALONE_MIN_SP2 = MIN_AREA_SP2
TOUCH_JOIN_HOST = False
#: ink in both boxes or in neither goes to the side it is nearer to, through the piece's own ink; more of it than this and the boxes do not
#: tell where one mark stops: the piece stays whole (`touch_boxes_undecided`, rule 6)
TOUCH_UNDECIDED_MAX_SHARE = 0.5
#: a clef's SIZE, staff spaces (width, height): the SMuFL reference font's glyph boxes, `glyphBBoxes` in
#: tools/omr/annotate/static/bravura/bravura_metadata.json (gClef 2.684 x 7.024, fClef 2.756 x 3.588 dots included, cClef 2.796 x 4.048;
#: the clef dossier docs/symbol-dossiers/clefs.md cites the same heights, and `clef_locator` uses the G height as its discriminator).
#: The clef's ink is read from its detector box OUTWARD and bounded by this size: a piece of ink joins the clef only if it lies wholly
#: inside some clef-sized rectangle that still holds the box. Ink beyond the clef's size is not the clef's (a barline, a note).
CLEF_SIZE_SPACES = {"G": (2.684, 7.024), "F": (2.756, 3.588), "C": (2.796, 4.048)}
#: two pieces of a clef are one ink when within this many reduced px (the stroke map's own contact rule, `touches`: "within 2 px")
CLEF_CONTACT_PX = 2
#: the detector's box edge is read to within that same contact distance (2 reduced px = 0.125 sp): a clef whose box is its own size has
#: pieces poking a pixel or two out of it (Brahms p0 G clefs: box 2.7 x 7.2 sp, the SMuFL size; 3 canonical px out on the right)
CLEF_EDGE_TOL_SPACES = CLEF_CONTACT_PX / TARGET_SP_PX


def split_joins_enabled() -> bool:
    """`OMR_SPLIT_JOINS` (ROADMAP 2.239), default ON (Sean 2026-10-30 "Land then fix"); an explicit 0/false/no/off disables."""
    return os.environ.get(SPLIT_JOINS_ENV, "").strip().lower() not in ("0", "false", "no", "off")


# -- ROADMAP 2.242: ONE ACCIDENTAL, ONE PIECE (flag `OMR_ACCIDENTAL_WHOLE`, default ON) --
#: CAUSE (2.239 r3 capture: 0 of 41 accidentals whole on Sean's Brahms p0 labels): the openings (eraser, vertical / horizontal / remainder)
#: cut EVERY accidental into 4-6 strokes (stems, bars, bowl) with `OMR_SPLIT_JOINS` off as well -- the same source that cut clefs into ~25
#: pieces. An accidental is read from its detector box OUTWARD like a clef (`_merge_clefs`): the seed is every piece mostly inside the box, a
#: piece touching it joins, and no piece joins that is not wholly inside the glyph's SIZE around the box. Sizes are the SMuFL reference glyph
#: boxes (`glyphBBoxes`, tools/omr/annotate/static/bravura/bravura_metadata.json), width x height in staff spaces; nothing is tuned.
ACCIDENTAL_WHOLE_ENV = "OMR_ACCIDENTAL_WHOLE"
ACCIDENTAL_SIZE_SPACES = {
    "accidentalsharp": (0.996, 2.792), "accidentalflat": (0.904, 2.456), "accidentalnatural": (0.672, 2.704),
    "accidentaldoublesharp": (0.988, 1.008), "accidentaldoubleflat": (1.644, 2.448),
    "accidentalnaturalflat": (1.836, 3.096), "accidentalnaturalsharp": (1.924, 2.792),
}
#: a piece the detector's box edge and the 1-px scan edge put outside the glyph's box: twice the contact distance on each side (the merge
#: region itself is the glyph-sized rectangle that holds the box, widened by `CLEF_EDGE_TOL_SPACES` each way)
ACC_SIZE_TOL_SPACES = 2 * CLEF_EDGE_TOL_SPACES
#: ONE accidental's most (width, height): the largest of the sized glyphs, the natural-flat / natural-sharp ligature (1.924 x 3.096). Merged ink
#: larger than this plus the tolerance holds more than one sign (two stacked accidentals in one over-large detector box).
ACC_ONE_MAX_SPACES = (max(w for w, _h in ACCIDENTAL_SIZE_SPACES.values()), max(h for _w, h in ACCIDENTAL_SIZE_SPACES.values()))


#: 2.242 r2 (Sean's tiles 2/7/11/12, 2026-10-31: "Add shape and size"): ONE connected piece inside a detector accidental box is not evidence that
#: the piece IS an accidental -- a barline's 4 x 6 px scrap, a tremolo slash (19 x 12 px), a stem's tip (5 x 10 px) and a flat's bowl alone were all
#: "whole". CONVENTION (engraving, a prior): a sharp / natural is ~2.7-2.8 sp tall and a flat ~2.5 (SMuFL `ACCIDENTAL_SIZE_SPACES`), and the glyph's
#: ink fills most of that. A cut-off tuned on two plates only NARROWS: a piece shorter than this share of its class's glyph height, or narrower than
#: that share of its width, is NOT whole (left cut / refused, never relabelled). Breitkopf prints ~10% LARGER than the font (the first try, which
#: trimmed ink to the font size, lost 15 of 21 naturals), so only a LOWER bound is used; the upper bound stays `ACC_ONE_MAX_SPACES`.
ACC_WHOLE_MIN_H_FRAC = 0.7
ACC_WHOLE_MIN_W_FRAC = 0.5


def accidental_ink_fits(name: str, w_sp: float, h_sp: float) -> Tuple[bool, str]:
    """(fits, why): does ONE piece of ink of `w_sp` x `h_sp` (local staff spaces) have the size of the `name` accidental glyph? No size known for
    the class (a `key*` mark, a quarter-tone sign) = fits (nothing to measure it against). Lower bounds only (module note)."""
    size = accidental_size(name)
    if size is None:
        return True, "no_size_for_class"
    if h_sp < ACC_WHOLE_MIN_H_FRAC * size[1]:
        return False, "too_short:%.2f_of_%.2f_sp" % (h_sp, size[1])
    if w_sp < ACC_WHOLE_MIN_W_FRAC * size[0]:
        return False, "too_narrow:%.2f_of_%.2f_sp" % (w_sp, size[0])
    return True, "glyph_sized"


def accidental_whole_enabled() -> bool:
    """`OMR_ACCIDENTAL_WHOLE` (ROADMAP 2.242), default ON (Sean 2026-10-31 "Land on", r2 tiles 11/12); an explicit 0/false/no/off disables. Read at GATHER (the stroke map) and at ADJUDICATE (`stroke_owner.shape_fit`)."""
    return os.environ.get(ACCIDENTAL_WHOLE_ENV, "").strip().lower() not in ("0", "false", "no", "off")


def accidental_size(name: str) -> Optional[Tuple[float, float]]:
    """The glyph box (width, height) in staff spaces of an `accidental*` detector class; None = not one of the sized signs (a key signature's
    `key*` mark, a quarter-tone sign): no merge, no size cut."""
    return ACCIDENTAL_SIZE_SPACES.get(str(name or "").strip().lower())


@dataclass
class Stroke:
    kind: str
    box: Tuple[int, int, int, int]            # x, y, w, h -- canonical cell px (the Q.STEM spelling)
    area_sp2: float
    length_sp: float
    angle_deg: float                          # principal axis: 0 horizontal, 90 vertical, counter-clockwise on the page
    thickness_sp: float                       # median run across the axis, slope-corrected
    thickness_spread_sp: float                # inter-quartile range of the same
    fill: float                               # area / box area
    sagitta_sp: Optional[float]               # centre-line bow (None for a blob)
    hole_share: Optional[float]               # blob only: enclosed paper / (ink + enclosed paper)
    ends: Tuple[Tuple[int, int], Tuple[int, int]]   # extreme pixels along the axis, canonical (x, y)
    profile: List[int]                        # thickness along the axis, sixteenths of a space
    component: int = -1
    component_n_strokes: int = 1
    touches: List[Tuple[int, float]] = field(default_factory=list)   # (other stroke's ordinal in the cell, contact in spaces)
    lines_left: Optional[List[int]] = None    # the five staff-line rows at the box's left / right x, canonical px
    lines_right: Optional[List[int]] = None
    staff_space_local: Optional[float] = None  # canonical px per space at the stroke's centre
    end_steps: Optional[Tuple[float, float]] = None   # ends in steps from the TOP line (0) to the bottom (8), local lines
    #: ROADMAP 2.239 (`OMR_SPLIT_JOINS`): the strokes this one was cut from the same fused piece with, and the join -- (ordinal, "head|stem")
    joined_to: List[Tuple[int, str]] = field(default_factory=list)
    #: ROADMAP 2.242 (`OMR_ACCIDENTAL_WHOLE`): a whole accidental is ONE stroke; the pieces the openings cut it into (stems, bars, bowl) are
    #: kept here, measured the same way and NOT filed as strokes, because the 2.201 type reading (stem stagger) reads them
    parts: List["Stroke"] = field(default_factory=list)


class LocalStaff:
    """The five staff lines at any x of one cell, measured on the RAW reduced raster (reduced-frame rows)."""

    def __init__(self, raw_small: Optional[np.ndarray], nominal_small: Sequence[float], sp_small: float):
        self.sp = float(sp_small)
        self.nominal = [float(y) for y in nominal_small]
        self.local = False
        self._xs: List[float] = []
        self._rows: List[List[float]] = []
        if raw_small is None or len(self.nominal) != 5 or sp_small <= 0 or raw_small.ndim != 2:
            return
        h, w = raw_small.shape
        half = max(2, int(round(ANCHOR_HALF_WINDOW_SPACES * sp_small)))
        stride = max(2, int(round(ANCHOR_STRIDE_SPACES * sp_small)))
        search = max(1, int(round(LINE_SEARCH_SPACES * sp_small)))
        prev = list(self.nominal)
        for cx in range(half, max(half + 1, w - half + stride), stride):
            cx = min(cx, w - 1)
            a, b = max(0, cx - half), min(w, cx + half + 1)
            if b - a < 3:
                continue
            prof = raw_small[:, a:b].mean(axis=1)
            rows: List[float] = []
            ok = True
            for y in prev:
                lo, hi = max(0, int(round(y)) - search), min(h, int(round(y)) + search + 1)
                if hi - lo < 2:
                    ok = False
                    break
                seg = prof[lo:hi]
                peak = float(seg.max())
                if peak < LINE_MIN_INK:
                    ok = False
                    break
                band = np.nonzero(seg >= 0.5 * peak)[0]
                wts = seg[band]
                rows.append(float(lo + (band * wts).sum() / wts.sum()))
            if not ok or any(rows[i + 1] - rows[i] <= 0 for i in range(4)):
                continue
            self._xs.append(float(cx))
            self._rows.append(rows)
            prev = rows
        self.local = bool(self._xs)

    def lines_at(self, x: float) -> List[float]:
        if not self._xs:
            return list(self.nominal)
        xs = self._xs
        if x <= xs[0]:
            return list(self._rows[0])
        if x >= xs[-1]:
            return list(self._rows[-1])
        j = int(np.searchsorted(xs, x))
        t = (x - xs[j - 1]) / (xs[j] - xs[j - 1])
        return [self._rows[j - 1][i] * (1 - t) + self._rows[j][i] * t for i in range(5)]


def _reduce(img: np.ndarray, scale: float) -> np.ndarray:
    import cv2
    ink = (img == 0).astype(np.uint8) * 255
    if scale >= 1.0:
        return ink >= COVER_THRESHOLD
    return cv2.resize(ink, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) >= COVER_THRESHOLD


def _reduce_float(img: np.ndarray, scale: float) -> np.ndarray:
    import cv2
    ink = (img == 0).astype(np.float32)
    return ink if scale >= 1.0 else cv2.resize(ink, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def _components(mask: np.ndarray, connectivity: int = 8):
    import cv2
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=connectivity)
    return n, lab, stats


def _hole_share(m: np.ndarray) -> float:
    """Enclosed paper of a blob's mask over (ink + enclosed paper)."""
    import cv2
    h, w = m.shape
    pad = np.zeros((h + 2, w + 2), np.uint8)
    pad[1:-1, 1:-1] = m
    ff = (1 - pad).astype(np.uint8)
    cv2.floodFill(ff, np.zeros((h + 4, w + 4), np.uint8), (0, 0), 2)
    holes = int((ff == 1).sum())
    area = int(m.sum())
    return holes / float(area + holes) if area + holes else 0.0


def _centres(m: np.ndarray, idx: np.ndarray, axis: int) -> np.ndarray:
    mf = m.astype(np.float64)
    if axis == 0:
        rows = np.arange(m.shape[0], dtype=np.float64)[:, None]
        return (mf[:, idx] * rows).sum(axis=0) / mf[:, idx].sum(axis=0)
    cols = np.arange(m.shape[1], dtype=np.float64)[None, :]
    return (mf[idx, :] * cols).sum(axis=1) / mf[idx, :].sum(axis=1)


def _measure(m: np.ndarray, x0: int, y0: int) -> dict:
    ys, xs = np.nonzero(m)
    cx, cy = float(xs.mean()), float(ys.mean())
    dx, dy = xs - cx, ys - cy
    theta = 0.5 * math.atan2(2 * float((dx * dy).mean()), float((dx * dx).mean()) - float((dy * dy).mean()))
    c, s = math.cos(theta), math.sin(theta)
    t = dx * c + dy * s
    i0, i1 = int(np.argmin(t)), int(np.argmax(t))
    if abs(c) >= abs(s):
        counts, axis, factor = m.sum(axis=0), 0, abs(c)
    else:
        counts, axis, factor = m.sum(axis=1), 1, abs(s)
    idx = np.nonzero(counts)[0]
    runs = counts[idx].astype(np.float64)
    centres = _centres(m, idx, axis)
    sag = None
    if idx.size >= 3 and idx[-1] > idx[0]:
        along = idx.astype(np.float64)
        chord = centres[0] + (along - along[0]) * (centres[-1] - centres[0]) / (along[-1] - along[0])
        sag = float(np.abs(centres - chord).max())
    sel = np.linspace(0, runs.size - 1, PROFILE_SAMPLES).round().astype(int)
    return dict(area=int(xs.size), theta=theta, length=float(t[i1] - t[i0]) + 1.0,
                thick=float(np.median(runs)) * factor,
                spread=float(np.percentile(runs, 75) - np.percentile(runs, 25)) * factor, sag=sag,
                profile=[int(runs[i]) for i in sel],
                end0=(x0 + int(xs[i0]), y0 + int(ys[i0])), end1=(x0 + int(xs[i1]), y0 + int(ys[i1])))


@dataclass
class CellStrokes:
    strokes: List[Stroke]
    n_below_floor: int
    scale: float
    sp_canonical: float
    staff_local: bool
    #: ROADMAP 2.198: each stroke's mask in the REDUCED frame, parallel to `strokes` -- (mask, x0, y0). Never filed; it is what lets
    #: `strokes_in_box` say how much of a stroke's ink lies inside a detector box.
    masks: List[Tuple[np.ndarray, int, int]] = field(default_factory=list, repr=False, compare=False)
    #: ROADMAP 2.239: pieces a join split looked at and left whole, by reason (empty with the flag off)
    split_refused: Dict[str, int] = field(default_factory=dict)


#: A box COVERS a stroke when at least this share of the stroke's ink lies inside the box. Not tuned: it is the register's one cut
#: (`claims.INSIDE_SHARE_MIN`, 2.177: "a mark's own piece is wholly inside, ~1.0; a neighbour shares a sliver"), and the measured
#: distribution of the share (benchmarks/shared-ink-map-2026-10/FINDINGS.md 2.198 section) is what says it sits in a gap.
COVER_SHARE_MIN = 0.5


def strokes_in_box(res: "CellStrokes", box: Sequence[float]) -> List[Tuple[int, float]]:
    """ROADMAP 2.198: `[(stroke ordinal, share)]` for every stroke of the cell with any ink inside `box` = (x0, y0, x1, y1) in CANONICAL cell
    px (the frame of `Stroke.box` and of the detector's boxes); `share` = the stroke's ink inside the box / the stroke's ink, in [0, 1].
    Pure; ordered by ordinal. A caller applies `COVER_SHARE_MIN` (covered) and keeps the rest as partial."""
    out: List[Tuple[int, float]] = []
    if not res.masks:
        return out
    s = res.scale
    bx0, by0, bx1, by1 = (float(v) * s for v in box)
    for i, (m, x0, y0) in enumerate(res.masks):
        h, w = m.shape
        lx0, ly0 = max(0, int(round(bx0)) - x0), max(0, int(round(by0)) - y0)
        lx1, ly1 = min(w, int(round(bx1)) - x0), min(h, int(round(by1)) - y0)
        if lx1 <= lx0 or ly1 <= ly0:
            continue
        total = int(m.sum())
        if total <= 0:
            continue
        inside = int(m[ly0:ly1, lx0:lx1].sum())
        if inside:
            out.append((i, round(inside / float(total), 3)))
    return out


def _restored_thickness(m: np.ndarray, x0: int, y0: int, scale: float, erased: np.ndarray, raw: np.ndarray, sp_canonical: float,
                        factor: float) -> Optional[float]:
    """ROADMAP 2.202b: the median column run of one horizontal / curve stroke with the ink the staff-line erase took out of its columns put back, in
    REDUCED px (the unit of `_measure`'s `thick`) times the axis `factor`; None when no column of the stroke touches erased ink (the erased reading IS the
    printed one). Done at CANONICAL resolution (the 16 px/sp reduction would let a line 0.06 sp clear of a beam join it).

    `erased` / `raw` are the canonical rasters (0 = ink). Per column: a run of (the stroke's own pixels + pixels the erase removed) that contains a pixel
    of the stroke. The eraser only ever removes line rows and the run it walked with them, so the added pixels are never a neighbour's ink."""
    import cv2
    H, W = erased.shape
    inv = 1.0 / scale
    h, w = m.shape
    cx0, cy0 = int(round(x0 * inv)), int(round(y0 * inv))
    cw, ch = max(1, int(round(w * inv))), max(1, int(round(h * inv)))
    pad = int(math.ceil(0.5 * sp_canonical))
    ya, yb = max(0, cy0 - pad), min(H, cy0 + ch + pad)
    xa, xb = max(0, cx0), min(W, cx0 + cw)
    if yb <= ya or xb <= xa:
        return None
    up = cv2.resize(m.astype(np.uint8), (cw, ch), interpolation=cv2.INTER_NEAREST).astype(bool)
    S = np.zeros((yb - ya, xb - xa), bool)
    ry0, rx0 = cy0 - ya, max(0, cx0) - cx0
    sub = up[:, rx0:rx0 + (xb - xa)]
    hh = min(sub.shape[0], S.shape[0] - ry0)
    if hh <= 0:
        return None
    S[ry0:ry0 + hh, :sub.shape[1]] = sub[:hh]
    ink_e = erased[ya:yb, xa:xb] == 0
    E = (raw[ya:yb, xa:xb] == 0) & ~ink_e
    # the stroke's footprint is one reduced pixel coarse: its erased ink is the ink within one reduced pixel (`inv` canonical px) of it, up and down
    k = max(1, int(round(inv)))
    foot = cv2.dilate(S.astype(np.uint8), np.ones((2 * k + 1, 1), np.uint8)).astype(bool)
    S = foot & ink_e
    if not E.any() or not S.any():
        return None
    T = S | E
    start = T.copy()
    start[1:] &= ~T[:-1]
    seg = np.cumsum(start, axis=0) * T
    nseg = int(seg.max()) + 1
    key = seg + np.arange(T.shape[1])[None, :] * nseg
    has = np.unique(key[S])
    G = np.isin(key, has) & T
    cols = foot.any(axis=0)
    if not cols.any() or not (G & E).any():
        return None          # no column of the stroke touches ink the erase took: the erased reading IS the printed one, keep it exactly
    return float(np.median(G.sum(axis=0)[cols])) * scale * factor


def _classify(m: np.ndarray, sp: float, lines: bool = True) -> str:
    """The kind of a part cut out of a fused piece, by the same rules `map_strokes` applies to whole pieces (no new cut). `lines` False: a
    part of the remainder, which the openings already refused, can only be a curve or a blob."""
    h, w = m.shape
    a = int(m.sum())
    longest = max(w, h)
    if lines and h >= V_MIN_SPACES * sp and w <= STEM_THIN_SPACES * sp:
        return "vertical"
    if lines and w >= H_MIN_SPACES * sp and w > h and a > 0 and (longest * longest) / float(a) >= H_MIN_ASPECT:
        return "horizontal"
    thick_mean = a / float(longest) if longest else 0.0
    if longest >= CURVE_MIN_SPACES * sp and thick_mean <= CURVE_MAX_THICK_SPACES * sp and longest / max(1.0, thick_mean) >= CURVE_MIN_ASPECT:
        return "curve"
    return "blob"


def _parts(full: np.ndarray, x0: int, y0: int, labels: np.ndarray, ids: Sequence[int]) -> List[Tuple[np.ndarray, int, int]]:
    """Each label id of `labels` (same frame as `full`) as a cropped (mask, x0, y0)."""
    out = []
    for i in ids:
        ys, xs = np.nonzero(labels == i)
        if ys.size == 0:
            continue
        a, b, c, d = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
        out.append(((labels[a:b, c:d] == i) & full[a:b, c:d], x0 + c, y0 + a))
    return out


def _merge_small(lab: np.ndarray, keep: Dict[int, bool]) -> np.ndarray:
    """Give every label NOT kept to the kept label it touches most (8-neighbourhood), repeatedly; a label touching no kept one stays (it is
    then kept: no ink is ever dropped). Returns the relabelled image."""
    import cv2
    lab = lab.copy()
    k3 = np.ones((3, 3), np.uint8)
    for _ in range(50):
        moved = False
        for i in [i for i, ok in keep.items() if not ok]:
            m = (lab == i)
            if not m.any():
                continue
            ring = cv2.dilate(m.astype(np.uint8), k3).astype(bool) & ~m
            nb = lab[ring]
            nb = nb[(nb > 0) & np.isin(nb, [j for j, ok in keep.items() if ok])]
            if nb.size:
                tgt = int(np.bincount(nb).argmax())
                lab[m] = tgt
                keep[i] = True          # merged away
                moved = True
        if not moved:
            break
    return lab


def _cut_stack(m: np.ndarray, sp: float, prof: Optional[np.ndarray] = None) -> Tuple[List[np.ndarray], Optional[str]]:
    """A wide part taller than one head: cut at the waist between two ovals (head|head). Returns (row-bands as masks of `m`'s frame, why-not).
    `prof` (same rows as `m`, any columns) is the ink the edges are read on: the part's own ink plus the oval edges the vertical opening left
    to the remainder (a column broken by a notch is not in the opening), rungs left out; None = `m` itself."""
    h, w = m.shape
    prof = m if prof is None else prof
    if h <= HEAD_HEIGHT_CAP_SPACES * sp:
        return [m], None
    if w > HEAD_WIDTH_CAP_SPACES * sp:
        return [m], "stack_too_wide"
    lo, hi = int(round(STACK_BAND_MIN_SPACES * sp)), h - int(round(STACK_BAND_MIN_SPACES * sp))
    if hi <= lo:
        return [m], "stack_no_waist"
    # two convex ovals meet at a NOTCH: a row where the left or right edge steps in from both ovals' extremes (a ledger rung or a scan
    # between the heads can fill the middle, so a row's width alone misses it -- Brahms p0 q6)
    rows = np.nonzero(prof.any(axis=1))[0]
    L = np.full(h, np.nan)
    Rr = np.full(h, np.nan)
    for r in rows:
        xs = np.nonzero(prof[r])[0]
        L[r], Rr[r] = xs[0], xs[-1]
    widths = prof.sum(axis=1).astype(float)
    best = (0.0, -1)
    for r in range(lo, hi):
        if np.isnan(L[r]):
            continue
        dR = min(np.nanmax(Rr[:r]), np.nanmax(Rr[r + 1:])) - Rr[r]
        dL = L[r] - max(np.nanmin(L[:r]), np.nanmin(L[r + 1:]))
        dW = (1.0 - WAIST_SHARE_MAX) * sp if widths[r] <= WAIST_SHARE_MAX * min(widths[:r].max(), widths[r + 1:].max()) else 0.0
        depth = max(dR, dL, dW)
        if depth > best[0]:
            best = (float(depth), r)
    if best[1] < 0 or best[0] < STACK_NOTCH_SPACES * sp:
        return [m], "stack_no_waist"
    r = best[1]
    top, bot = m.copy(), m.copy()
    top[r + 1:] = False
    bot[:r + 1] = False
    out: List[np.ndarray] = []
    why = None
    for part in (top, bot):
        ys = np.nonzero(part.any(axis=1))[0]
        if ys.size == 0:
            continue
        sub, w2 = _cut_stack(part[ys[0]:ys[-1] + 1], sp, prof[ys[0]:ys[-1] + 1])
        for s_ in sub:
            full = np.zeros_like(m)
            full[ys[0]:ys[-1] + 1] = s_
            out.append(full)
        why = why or w2
    return out, why


def _split_vertical(m: np.ndarray, sp: float, refused: Dict[str, int], context: Optional[Tuple[np.ndarray, int, int]] = None
                    ) -> Optional[List[Tuple[str, np.ndarray, str]]]:
    """head|stem, stem|beam, stem|flag: a vertical piece whose rows are not all thin. The stem is its THIN rows (a row run no wider than
    `STEM_THIN_SPACES`); the rows where the run is wide are what is fused to it, cut where the stem leaves them. Returns [(kind, mask in m's
    frame, join)] with the stem first, or None (left whole)."""
    import cv2
    h, w = m.shape
    thin_px = STEM_THIN_SPACES * sp
    if w <= thin_px:
        return None                                    # all thin: a stem or a barline alone
    wide = np.zeros_like(m)
    for r in range(h):
        row = m[r]
        if not row.any():
            continue
        d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
        starts, ends = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
        for a, b in zip(starts, ends):
            if b - a > thin_px:
                wide[r, a:b] = True
    if not wide.any():
        refused["vertical_all_thin_rows"] = refused.get("vertical_all_thin_rows", 0) + 1
        return None
    thin = m & ~wide
    if not thin.any():
        return _stack_or_whole(m, sp, refused, context)
    return _split_thin_wide(m, thin, wide, sp, refused, context)


def _stack_or_whole(m: np.ndarray, sp: float, refused: Dict[str, int], context) -> Optional[List[Tuple[str, np.ndarray, str]]]:
    """A vertical piece with no stem in it. A stack of heads (the stem a pixel apart, Brahms p0 q49) is cut at its notch (head|head); any
    other solid slab (a bracket, a thick barline, a beam bundle) stays whole."""
    prof = _profile(m, 0, 0, context, sp)
    if not _looks_like_heads(m, sp, prof):
        refused["vertical_no_thin_core"] = refused.get("vertical_no_thin_core", 0) + 1
        return None
    bands, why = _cut_stack(m, sp, prof)
    if len(bands) > 1:
        return [("blob" if _classify(_crop(b)[0], sp) == "vertical" else _classify(_crop(b)[0], sp), b, "head|head") for b in bands]
    refused[why or "stack_no_waist"] = refused.get(why or "stack_no_waist", 0) + 1
    return None


def _split_thin_wide(m: np.ndarray, thin: np.ndarray, wide: np.ndarray, sp: float, refused: Dict[str, int], context
                     ) -> Optional[List[Tuple[str, np.ndarray, str]]]:
    import cv2
    # label: thin components 1..nt, wide components nt+1..
    nt, tl = cv2.connectedComponents(thin.astype(np.uint8), connectivity=8)
    nw, wl = cv2.connectedComponents(wide.astype(np.uint8), connectivity=8)
    lab = np.where(thin, tl, 0) + np.where(wide, wl + (nt - 1), 0)
    keep: Dict[int, bool] = {}
    kind_of: Dict[int, str] = {}
    for i in range(1, nt):
        ys = np.nonzero((tl == i).any(axis=1))[0]
        keep[i] = bool(ys.size) and (ys[-1] - ys[0] + 1) >= STEM_PART_MIN_SPACES * sp
        kind_of[i] = "thin"
    for j in range(1, nw):
        i = j + nt - 1
        keep[i] = int((wl == j).sum()) >= WIDE_PART_MIN_SP2 * sp * sp
        kind_of[i] = "wide"
    # small wide blips go to the stem first, then oval tips / stubs to the wide part
    lab = _merge_small(lab, {i: (keep[i] or kind_of[i] == "thin") for i in keep})
    lab = _merge_small(lab, {i: (keep[i] or kind_of[i] == "wide") for i in keep if (lab == i).any()})
    ids = [i for i in sorted(keep) if (lab == i).any()]
    if not any(kind_of[i] == "thin" for i in ids):
        return _stack_or_whole(m, sp, refused, context)        # only an oval's tips were thin: no stem in it
    if not any(kind_of[i] == "wide" for i in ids):
        refused["vertical_nothing_fused"] = refused.get("vertical_nothing_fused", 0) + 1
        return None
    out: List[Tuple[str, np.ndarray, str]] = []
    for i in sorted(ids, key=lambda i: (kind_of[i] != "thin", -int((lab == i).sum()))):
        part = lab == i
        if kind_of[i] == "thin":
            out.append(("vertical" if _extent_h(part) >= V_MIN_SPACES * sp else _classify(_crop(part)[0], sp), part, "stem"))
            continue
        pc, oy, ox = _crop(part)
        prof = _profile(pc, oy, ox, context, sp)
        bands, why = (_cut_stack(pc, sp, prof) if _looks_like_heads(pc, sp, prof) else ([pc], None))
        if why:
            refused[why] = refused.get(why, 0) + 1
        for b in bands:
            full = np.zeros_like(m)
            full[oy:oy + b.shape[0], ox:ox + b.shape[1]] = b
            k = _classify(_crop(full)[0], sp)
            out.append((k, full, "stem|" + {"blob": "head", "horizontal": "beam", "curve": "flag", "vertical": "stem"}[k]))
    return out


def _profile(pc: np.ndarray, oy: int, ox: int, context: Optional[Tuple[np.ndarray, int, int]], sp: float) -> Optional[np.ndarray]:
    """The edge-reading ink of a head stack (`_cut_stack`): `context` = (cell ink minus rungs, piece x0, piece y0) in the reduced frame; the ink
    within `STACK_EDGE_PAD_SPACES` of the part, in the part's rows, connected to it. None without a context."""
    import cv2
    if context is None:
        return None
    ink, px0, py0 = context
    pad = max(1, int(round(STACK_EDGE_PAD_SPACES * sp)))
    H, W = ink.shape
    y0, x0 = py0 + oy, px0 + ox
    y1, x1 = y0 + pc.shape[0], x0 + pc.shape[1]
    xa, xb = max(0, x0 - pad), min(W, x1 + pad)
    win = ink[y0:y1, xa:xb].copy()
    win[:, x0 - xa:x0 - xa + pc.shape[1]] |= pc
    n, lab = cv2.connectedComponents(win.astype(np.uint8), connectivity=8)
    own = np.unique(lab[:, x0 - xa:x0 - xa + pc.shape[1]][pc])
    return np.isin(lab, own[own > 0])


def _crop(m: np.ndarray) -> Tuple[np.ndarray, int, int]:
    ys, xs = np.nonzero(m)
    a, b, c, d = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
    return m[a:b, c:d], a, c


def _extent_h(m: np.ndarray) -> int:
    ys = np.nonzero(m.any(axis=1))[0]
    return int(ys[-1] - ys[0] + 1) if ys.size else 0


def _looks_like_heads(m: np.ndarray, sp: float, prof: Optional[np.ndarray] = None) -> bool:
    """Taller than one head, no wider than one, at least a head's width (a bracket's or a thick barline's line is narrower), at most a few
    heads tall. The width is read on `prof` (`_profile`) when given: the opening drops a notched oval's edge columns."""
    c, _a, _b = _crop(m)
    wd = _crop(prof)[0].shape[1] if prof is not None and prof.any() else c.shape[1]
    return (HEAD_MIN_WIDTH_SPACES * sp <= wd <= HEAD_WIDTH_CAP_SPACES * sp
            and HEAD_HEIGHT_CAP_SPACES * sp < c.shape[0] <= STACK_MAX_SPACES * sp)


def _split_horizontal(m: np.ndarray, sp: float, refused: Dict[str, int]) -> Optional[List[Tuple[str, np.ndarray, str]]]:
    """ledger|head: a horizontal piece that is a LEVEL rung with ONE head on it. The head is ONE part -- every column of the oval, all its
    rows, the rung's rows through the oval included (Sean 2026-10-30, 2.239 tile 6: "just the top of an eighth note on a ledger line"
    was the fault); the rung is cut off only where it sticks out beyond the oval, left and right, and those stubs are LEDGER strokes
    (`horizontal`), never a blob (tile 9). The rung's thickness is read on its own stubs, never on the oval's columns.
    Longest column RUN, never the column count (a hairpin's two lines stack in one column)."""
    h, w = m.shape
    runs = np.zeros(w, int)
    cent = np.zeros(w, float)
    for c in range(w):
        col = m[:, c]
        if col.any():
            d = np.diff(np.concatenate(([0], col.astype(np.int8), [0])))
            st_, en_ = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
            k = int(np.argmax(en_ - st_))
            runs[c] = int(en_[k] - st_[k])
            cent[c] = (st_[k] + en_[k] - 1) / 2.0
    cols = np.nonzero(runs > 0)[0]
    if cols.size < 3:
        return None
    # the rung's own thickness: the thinnest runs at its two ends (a stub sticks out at least `LEDGER_STUB_MIN_SPACES` each side)
    stub = max(2, int(round(LEDGER_STUB_MIN_SPACES * sp)))
    ends = np.concatenate((runs[cols[:stub]], runs[cols[-stub:]]))
    line_t = float(np.median(ends))
    thick = runs > line_t + LEDGER_HEAD_EXCESS_SPACES * sp
    if not thick.any():
        return None
    a = int(np.nonzero(thick)[0][0])
    b = int(np.nonzero(thick)[0][-1]) + 1
    if int((~thick[a:b]).sum()) > 1:                     # two heads, or a beam that thickens twice: not one head on a rung
        refused["horizontal_two_thick_stretches"] = refused.get("horizontal_two_thick_stretches", 0) + 1
        return None
    # the oval's EDGE: widen the stretch while a column is still clearly thicker than the rung (`LEDGER_EDGE_EXCESS_SPACES`; a scanned rung
    # thickens a little toward the head, Brahms p5 tile 6), so the cut follows the oval's edge and never runs through the head
    edge = line_t + LEDGER_EDGE_EXCESS_SPACES * sp
    while a > 0 and runs[a - 1] > edge:
        a -= 1
    while b < w and runs[b] > edge:
        b += 1
    if b - a < LEDGER_HEAD_MIN_WIDTH_SPACES * sp or b - a > HEAD_WIDTH_CAP_SPACES * sp:
        refused["horizontal_thick_not_a_head"] = refused.get("horizontal_thick_not_a_head", 0) + 1
        return None
    left, right = (runs[:a] > 0), (runs[b:] > 0)
    if int(left.sum()) < stub or int(right.sum()) < stub:
        refused["horizontal_no_stub_both_sides"] = refused.get("horizontal_no_stub_both_sides", 0) + 1
        return None
    # a rung is LEVEL: its stub centres (both sides) fit a line no steeper than `LEDGER_MAX_SLOPE`
    xs = np.concatenate((np.nonzero(left)[0], b + np.nonzero(right)[0])).astype(float)
    slope = float(np.polyfit(xs, cent[xs.astype(int)], 1)[0])
    if abs(slope) > LEDGER_MAX_SLOPE:
        refused["horizontal_line_not_level"] = refused.get("horizontal_line_not_level", 0) + 1
        return None
    head = np.zeros_like(m)
    head[:, a:b] = m[:, a:b]
    lstub, rstub = m.copy(), m.copy()
    lstub[:, a:] = False
    rstub[:, :b] = False
    return [("blob", head, "head"), ("horizontal", lstub, "ledger|head"), ("horizontal", rstub, "ledger|head")]


def _split_remainder(m: np.ndarray, sp: float, refused: Dict[str, int]) -> Optional[List[Tuple[str, np.ndarray, str]]]:
    """head|arc: a remainder piece holding a head's body (a disk `HEAD_BODY_SPACES` wide survives in it) and a long thin tail (a tie or slur
    leaving the head). Each body no taller than one head is a head part; the thin ink at least `CURVE_MIN_SPACES` long is the arc."""
    import cv2
    h, w = m.shape
    if max(h, w) < CURVE_MIN_SPACES * sp:
        return None
    d = max(3, int(round(HEAD_BODY_SPACES * sp)))
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))
    pad = d
    mp = np.pad(m.astype(np.uint8), pad)
    body0 = cv2.morphologyEx(mp, cv2.MORPH_OPEN, disk)[pad:-pad, pad:-pad].astype(bool)
    if not body0.any():
        return None
    body = m & cv2.dilate(body0.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    nb, bl = cv2.connectedComponents(body.astype(np.uint8), connectivity=8)
    heads = []
    for i in range(1, nb):
        part = bl == i
        c, _a, _b = _crop(part)
        if int(part.sum()) >= HEAD_BODY_MIN_SP2 * sp * sp and c.shape[0] <= HEAD_HEIGHT_CAP_SPACES * sp and c.shape[1] <= HEAD_WIDTH_CAP_SPACES * sp:
            heads.append(part)
    if not heads:
        return None
    rest = m.copy()
    for hd in heads:
        rest &= ~hd
    nr, rl = cv2.connectedComponents(rest.astype(np.uint8), connectivity=8)
    lab = np.zeros(m.shape, np.int32)
    for k, hd in enumerate(heads, 1):
        lab[hd] = k
    keep: Dict[int, bool] = {k: True for k in range(1, len(heads) + 1)}
    arcs = []
    for i in range(1, nr):
        part = rl == i
        c, _a, _b = _crop(part)
        lid = len(heads) + i
        lab[part] = lid
        ok = max(c.shape) >= CURVE_MIN_SPACES * sp
        keep[lid] = ok
        if ok:
            arcs.append(lid)
    if not arcs:
        refused["remainder_no_long_tail"] = refused.get("remainder_no_long_tail", 0) + 1
        return None
    lab = _merge_small(lab, dict(keep))
    out: List[Tuple[str, np.ndarray, str]] = []
    for lid in arcs:
        if (lab == lid).any():
            part = lab == lid
            out.append((_classify(_crop(part)[0], sp, lines=False), part, "arc"))
    for k in range(1, len(heads) + 1):
        if (lab == k).any():
            out.append(("blob", lab == k, "arc|head"))
    return out if len(out) > 1 else None


def _inside_share(m: np.ndarray, x0: int, y0: int, rects: Sequence[Tuple[float, float, float, float]]) -> float:
    """The largest share of a piece's ink inside one of `rects` (reduced frame)."""
    tot = int(m.sum())
    best = 0.0
    if not tot:
        return 0.0
    h, w = m.shape
    for (a, b, c, d) in rects:
        lx0, ly0 = max(0, int(round(a)) - x0), max(0, int(round(b)) - y0)
        lx1, ly1 = min(w, int(round(c)) - x0), min(h, int(round(d)) - y0)
        if lx1 > lx0 and ly1 > ly0:
            best = max(best, int(m[ly0:ly1, lx0:lx1].sum()) / float(tot))
    return best


def _best_inside(m: np.ndarray, x0: int, y0: int, rects: Sequence[Tuple[float, float, float, float]]) -> Tuple[float, int]:
    """(largest share of the piece's ink inside one rect, that rect's index; -1 = none)."""
    best = (0.0, -1)
    for k, r in enumerate(rects):
        s_ = _inside_share(m, x0, y0, [r])
        if s_ > best[0]:
            best = (s_, k)
    return best


def clef_family(name: str) -> Optional[str]:
    """G / F / C from a clef class name (`clefG`, `clefCAlto`, `gClef`, ...); None = not a clef or no family named."""
    n = str(name or "")
    low = n.lower()
    f = n[4:5] if low.startswith("clef") else (n[0:1] if low[1:5] == "clef" else "")
    f = f.upper()
    return f if f in CLEF_SIZE_SPACES else None


def clef_region(box: Sequence[float], family: Optional[str], sp: float) -> Tuple[float, float, float, float]:
    """Every point of every clef-sized rectangle (`CLEF_SIZE_SPACES`) that still contains `box` (x0, y0, x1, y1, any frame in which `sp`
    is the staff space), widened by the box-edge tolerance `CLEF_EDGE_TOL_SPACES`; a box already larger than the clef, or no family, is
    its own region (plus that tolerance)."""
    a, b, c, d = (float(v) for v in box[:4])
    t = CLEF_EDGE_TOL_SPACES * sp
    if family not in CLEF_SIZE_SPACES:
        return a - t, b - t, c + t, d + t
    w, h = CLEF_SIZE_SPACES[family][0] * sp, CLEF_SIZE_SPACES[family][1] * sp
    return min(a, c - w) - t, min(b, d - h) - t, max(c, a + w) + t, max(d, b + h) + t


def sized_region(box: Sequence[float], size_sp: Optional[Tuple[float, float]], sp: float) -> Tuple[float, float, float, float]:
    """`clef_region`'s rule for any sign of known size (width, height in spaces): every point of every glyph-sized rectangle that still holds
    `box`, widened by the box-edge tolerance; no size = the box itself plus that tolerance."""
    a, b, c, d = (float(v) for v in box[:4])
    t = CLEF_EDGE_TOL_SPACES * sp
    if not size_sp:
        return a - t, b - t, c + t, d + t
    w, h = size_sp[0] * sp, size_sp[1] * sp
    return min(a, c - w) - t, min(b, d - h) - t, max(c, a + w) + t, max(d, b + h) + t


def merge_accidentals(pieces: List[Tuple[str, np.ndarray, int, int]], joins: List[Tuple[int, int, str]], sp: float,
                      acc_boxes: Sequence[Tuple[Tuple[float, float, float, float], str]],
                      exclude: Sequence[Tuple[float, float, float, float]], refused: Dict[str, int]
                      ) -> Tuple[List[Tuple[str, np.ndarray, int, int]], List[Tuple[int, int, str]], Dict[int, List[Tuple[str, np.ndarray, int, int]]]]:
    """2.242: the pieces the openings cut an accidental into, put back as ONE stroke (kind `blob`: a glyph's ink, not a line) holding all of its
    ink. Read from the detector box OUTWARD, as `_merge_clefs` reads a clef: the seed is every piece mostly inside the box; a piece touching
    the growing mark (`CLEF_CONTACT_PX`) joins it; no piece joins that does not lie wholly inside the glyph's size around the box
    (`sized_region`). A piece mostly inside a box in `exclude` (a head, ledger line or stem detector box, a clef / key / meter box) is never
    the accidental's: a head, stem, ledger rung, beam or flag is never joined, and a box standing on a head's ink (a false accidental box)
    merges nothing. Run AFTER the touch cut, which already separated accidental|head and accidental|ledger contacts from the accidental's
    side. Returns (pieces, joins re-numbered, {new piece index: the pieces it was made of})."""
    import cv2
    k3 = np.ones((3, 3), np.uint8)
    used: set = set()
    groups: List[List[int]] = []
    for box, name in acc_boxes:
        size = accidental_size(name)
        if size is None:
            continue
        rx0, ry0, rx1, ry1 = sized_region(box, size, sp)
        fits = [pi for pi, (_k, m, x0, y0) in enumerate(pieces)
                if pi not in used and not (exclude and _inside_share(m, x0, y0, exclude) >= 0.5)
                and x0 >= rx0 - 0.5 and y0 >= ry0 - 0.5 and x0 + m.shape[1] <= rx1 + 0.5 and y0 + m.shape[0] <= ry1 + 0.5]
        seed = [pi for pi in fits if _inside_share(pieces[pi][1], pieces[pi][2], pieces[pi][3], [box[:4]]) >= 0.5]
        if not seed:
            continue
        X0, Y0 = int(np.floor(rx0)) - 1, int(np.floor(ry0)) - 1
        X1, Y1 = int(np.ceil(rx1)) + 2, int(np.ceil(ry1)) + 2
        canvas = np.zeros((max(1, Y1 - Y0), max(1, X1 - X0)), bool)

        def paint(pi):
            _k, m, x0, y0 = pieces[pi]
            canvas[y0 - Y0:y0 - Y0 + m.shape[0], x0 - X0:x0 - X0 + m.shape[1]] |= m
        for pi in seed:
            paint(pi)
        mine = list(seed)
        rest = [pi for pi in fits if pi not in seed]
        while rest:
            near = cv2.dilate(canvas.astype(np.uint8), k3, iterations=CLEF_CONTACT_PX).astype(bool)
            add = [pi for pi in rest if (near[pieces[pi][3] - Y0:pieces[pi][3] - Y0 + pieces[pi][1].shape[0],
                                              pieces[pi][2] - X0:pieces[pi][2] - X0 + pieces[pi][1].shape[1]] & pieces[pi][1]).any()]
            if not add:
                break
            for pi in add:
                paint(pi)
                mine.append(pi)
            rest = [pi for pi in rest if pi not in add]
        if len(mine) > 1:
            ys, xs = np.nonzero(canvas)
            gw, gh = (xs.max() - xs.min() + 1) / sp, (ys.max() - ys.min() + 1) / sp
            if gw > ACC_ONE_MAX_SPACES[0] + ACC_SIZE_TOL_SPACES or gh > ACC_ONE_MAX_SPACES[1] + ACC_SIZE_TOL_SPACES:
                # an over-large box (the detector's twin boxes reach 4.8 sp round TWO stacked accidentals) holds more ink than ONE accidental:
                # the pieces stay as the openings cut them (rule 6: where the box cannot say where one mark stops, nothing is joined)
                refused["accidental_more_than_one_glyph"] = refused.get("accidental_more_than_one_glyph", 0) + 1
                continue
            if not accidental_ink_fits(name, gw, gh)[0]:
                # 2.242 r2: the pieces together are still too small for this sign (a flat's bowl, a bar): not a whole accidental, they stay cut
                refused["accidental_not_glyph_sized"] = refused.get("accidental_not_glyph_sized", 0) + 1
                continue
            groups.append(sorted(mine))
        used.update(mine)
    if not groups:
        return pieces, joins, {}
    first = {g[0]: g for g in groups}
    taken = {i for g in groups for i in g}
    out: List[Tuple[str, np.ndarray, int, int]] = []
    where: Dict[int, int] = {}
    parts_of: Dict[int, List[Tuple[str, np.ndarray, int, int]]] = {}
    for pi, pc in enumerate(pieces):
        if pi in first:
            parts = [pieces[i] for i in first[pi]]
            X0 = min(p[2] for p in parts)
            Y0 = min(p[3] for p in parts)
            X1 = max(p[2] + p[1].shape[1] for p in parts)
            Y1 = max(p[3] + p[1].shape[0] for p in parts)
            u = np.zeros((Y1 - Y0, X1 - X0), bool)
            for _k, m, x0, y0 in parts:
                u[y0 - Y0:y0 - Y0 + m.shape[0], x0 - X0:x0 - X0 + m.shape[1]] |= m
            for i in first[pi]:
                where[i] = len(out)
            parts_of[len(out)] = parts
            out.append(("blob", u, X0, Y0))
            refused["accidental_pieces_joined"] = refused.get("accidental_pieces_joined", 0) + len(parts) - 1
        elif pi not in taken:
            where[pi] = len(out)
            out.append(pc)
    new_joins = [(where[a], where[b], j) for a, b, j in joins if where[a] != where[b]]
    return out, new_joins, parts_of


def _merge_clefs(pieces: List[Tuple[str, np.ndarray, int, int]], sp: float, ink: np.ndarray,
                 clef_boxes: Sequence[Tuple[Tuple[float, float, float, float], Optional[str]]], refused: Dict[str, int],
                 others: Sequence[Tuple[float, float, float, float]] = ()) -> List[Tuple[str, np.ndarray, int, int]]:
    """2.239 r3 (Sean's round-2 tiles 6 "most of a G clef", 7 "tip cut of a G clef"; Sean: "make sure the box is big enough to claim all
    the ink and it should be based off of shape and size"): the pieces the openings cut a clef into, put back as ONE stroke that holds all
    the clef's ink. Read from the detector box OUTWARD: the seed is every piece mostly inside the box (the keep-whole cut, 0.5); a piece
    touching the clef (`CLEF_CONTACT_PX`) joins it; and no piece joins that does not lie wholly inside the clef's size around the box
    (`clef_region`) -- a G clef's tail and curl and an F clef's dots are inside it, a barline or a stem running through is not. A piece
    mostly inside a key or meter box (`others`) is that mark's, never the clef's (the key's first flat beside a loose clef box: its type is
    read from its own strokes, 2.201)."""
    import cv2
    joined_any: Dict[int, List[int]] = {}
    used: set = set()
    k3 = np.ones((3, 3), np.uint8)
    for (box, fam) in clef_boxes:
        rx0, ry0, rx1, ry1 = clef_region(box, fam, sp)
        fits = [pi for pi, (_k, m, x0, y0) in enumerate(pieces)
                if pi not in used and not (others and _inside_share(m, x0, y0, others) >= 0.5) and x0 >= rx0 - 0.5 and y0 >= ry0 - 0.5 and x0 + m.shape[1] <= rx1 + 0.5 and y0 + m.shape[0] <= ry1 + 0.5]
        seed = [pi for pi in fits if _inside_share(pieces[pi][1], pieces[pi][2], pieces[pi][3], [box[:4]]) >= 0.5]
        if not seed:
            continue
        X0, Y0 = int(np.floor(rx0)) - 1, int(np.floor(ry0)) - 1
        X1, Y1 = int(np.ceil(rx1)) + 2, int(np.ceil(ry1)) + 2
        canvas = np.zeros((max(1, Y1 - Y0), max(1, X1 - X0)), bool)

        def paint(pi):
            _k, m, x0, y0 = pieces[pi]
            canvas[y0 - Y0:y0 - Y0 + m.shape[0], x0 - X0:x0 - X0 + m.shape[1]] |= m
        for pi in seed:
            paint(pi)
        mine = list(seed)
        rest = [pi for pi in fits if pi not in seed]
        while rest:
            near = cv2.dilate(canvas.astype(np.uint8), k3, iterations=CLEF_CONTACT_PX).astype(bool)
            add = [pi for pi in rest if (near[pieces[pi][3] - Y0:pieces[pi][3] - Y0 + pieces[pi][1].shape[0],
                                              pieces[pi][2] - X0:pieces[pi][2] - X0 + pieces[pi][1].shape[1]] & pieces[pi][1]).any()]
            if not add:
                break
            for pi in add:
                paint(pi)
                mine.append(pi)
            rest = [pi for pi in rest if pi not in add]
        used.update(mine)
        if len(mine) > 1:
            joined_any[min(mine)] = sorted(mine)
    if not joined_any:
        return pieces
    taken = {i for v in joined_any.values() for i in v}
    out: List[Tuple[str, np.ndarray, int, int]] = []
    for pi, pc in enumerate(pieces):
        if pi in joined_any:
            parts = [pieces[i] for i in joined_any[pi]]
            X0 = min(p[2] for p in parts); Y0 = min(p[3] for p in parts)
            X1 = max(p[2] + p[1].shape[1] for p in parts); Y1 = max(p[3] + p[1].shape[0] for p in parts)
            u = np.zeros((Y1 - Y0, X1 - X0), bool)
            for _k, m, x0, y0 in parts:
                u[y0 - Y0:y0 - Y0 + m.shape[0], x0 - X0:x0 - X0 + m.shape[1]] |= m
            out.append((_classify(u, sp, lines=False), u, X0, Y0))
            refused["clef_pieces_joined"] = refused.get("clef_pieces_joined", 0) + len(parts) - 1
        elif pi not in taken:
            out.append(pc)
    return out


def _cut_touching(m: np.ndarray, x0: int, y0: int, sp: float, boxes: Sequence[Tuple[str, Tuple[float, float, float, float]]],
                  refused: Dict[str, int]) -> Optional[List[Tuple[str, np.ndarray, str]]]:
    """2.239 r3 (Sean's round-2 tile 1, "part of a ledger line and a flat"): a piece lying across an ACCIDENTAL box and a head / ledger /
    stem box is two marks that touch. Each side's SEED is the piece's ink inside its own family's boxes and inside no box of the other
    side; ink in both or in neither goes to the seed it is nearer to through the piece's own ink (the boundary between the two boxes' own
    ink). Returns [(kind, mask in m's frame, join)] with the other mark first, or None (not two marks / left whole, reason counted).
    The detector boxes are the only witness of where one mark stops; the accidental family reading (2.201) reads the strokes this map
    files, so it cannot steer the cut (it would read its own output) -- it is the CONTROL after the cut."""
    import cv2
    h, w = m.shape
    tot = int(m.sum())
    if not tot:
        return None
    acc = np.zeros_like(m)
    oth = np.zeros_like(m)
    fam_px: Dict[str, int] = {}
    for fam, (a, b, c, d) in boxes:
        lx0, ly0 = max(0, int(round(a)) - x0), max(0, int(round(b)) - y0)
        lx1, ly1 = min(w, int(round(c)) - x0), min(h, int(round(d)) - y0)
        if lx1 <= lx0 or ly1 <= ly0:
            continue
        r = np.zeros_like(m)
        r[ly0:ly1, lx0:lx1] = True
        r &= m
        if fam == TOUCH_ACC_FAMILY:
            acc |= r
        else:
            oth |= r
            fam_px[fam] = fam_px.get(fam, 0) + int(r.sum())
    sa, so = acc & ~oth, oth & ~acc
    floor = TOUCH_SIDE_MIN_SP2 * sp * sp
    if (int(sa.sum()) < max(floor, TOUCH_SIDE_MIN_SHARE * tot) or int(so.sum()) < max(floor, TOUCH_SIDE_MIN_SHARE * tot)):
        return None                                       # not two marks' ink (the common case: no count)
    und = m & ~sa & ~so
    if int(und.sum()) > TOUCH_UNDECIDED_MAX_SHARE * tot:
        refused["touch_boxes_undecided"] = refused.get("touch_boxes_undecided", 0) + 1
        return None
    # grow both seeds through the piece's own ink, one ring at a time; a pixel both reach in the same ring stays with the mark it lies in
    # (overlap: neither -- it goes to the other mark, the accidental is the smaller claim); never across white
    k3 = np.ones((3, 3), np.uint8)
    A, O = sa.copy(), so.copy()
    for _ in range(h + w):
        free = m & ~A & ~O
        if not free.any():
            break
        ga = cv2.dilate(A.astype(np.uint8), k3).astype(bool) & free
        go = cv2.dilate(O.astype(np.uint8), k3).astype(bool) & free
        if not ga.any() and not go.any():
            break
        both = ga & go
        A |= ga & ~both
        O |= go | both
    if int((m & ~A & ~O).sum()):
        refused["touch_unreached"] = refused.get("touch_unreached", 0) + 1     # ink joined to neither seed: leave the piece whole
        return None
    # each side is ONE part; a crumb of one side cut off from its seed goes to the part it touches
    lab = np.zeros(m.shape, np.int32)
    keep: Dict[int, bool] = {}
    side: Dict[int, str] = {}
    nxt = 1
    for nm, mk in (("other", O), ("acc", A)):
        n, cl = cv2.connectedComponents(mk.astype(np.uint8), connectivity=8)
        sizes = [(int((cl == i).sum()), i) for i in range(1, n)]
        biggest = max(sizes)[1] if sizes else None
        for sz, i in sizes:
            lab[cl == i] = nxt
            keep[nxt] = (i == biggest)
            side[nxt] = nm
            nxt += 1
    lab = _merge_small(lab, keep)
    parts = {nm: np.isin(lab, [i for i in side if side[i] == nm]) & m for nm in ("other", "acc")}   # a crumb touching nothing stays its side's
    if any(int(p_.sum()) < floor for p_ in parts.values()):
        refused["touch_part_too_small"] = refused.get("touch_part_too_small", 0) + 1
        return None
    if int(parts["other"].sum()) < TOUCH_ALONE_MIN_SP2 * sp * sp:
        refused["touch_part_too_small"] = refused.get("touch_part_too_small", 0) + 1
        return None
    fam = max(fam_px, key=lambda f: (fam_px[f], f))
    out = []
    for nm in ("other", "acc"):
        p_ = parts[nm]
        c, _a, _b = _crop(p_)
        out.append((_classify(c, sp), p_, "accidental|" + fam))
    return out


def _cut_touching_all(out: List[Tuple[str, np.ndarray, int, int]], joins: List[Tuple[int, int, str]], sp: float,
                      touch_boxes: Sequence[Tuple[str, Tuple[float, float, float, float]]], refused: Dict[str, int]
                      ) -> Tuple[List[Tuple[str, np.ndarray, int, int]], List[Tuple[int, int, str]]]:
    """`_cut_touching` over every piece the split left (a ledger stub the ledger|head cut made included); joins re-numbered. The
    accidental's side of a cut stands alone (`TOUCH_JOIN_HOST` off: see its note); with joining on it would join the accidental stroke it
    touches, and stand alone only above the stroke floor."""
    import cv2
    if not any(f == TOUCH_ACC_FAMILY for f, _r in touch_boxes) or not any(f in TOUCH_OTHER_FAMILIES for f, _r in touch_boxes):
        return out, joins
    acc_rects = [r for f, r in touch_boxes if f == TOUCH_ACC_FAMILY]
    cuts: Dict[int, List[Tuple[str, np.ndarray, str]]] = {}
    for i, (kind, m, x0, y0) in enumerate(out):
        parts = _cut_touching(m, x0, y0, sp, touch_boxes, refused)
        if parts and int(sum(int(p_.sum()) for _k, p_, _j in parts)) != int(m.sum()):
            refused["parts_do_not_add_up"] = refused.get("parts_do_not_add_up", 0) + 1
            parts = None
        if parts:
            cuts[i] = parts
    if not cuts:
        return out, joins
    pieces = list(out)
    host: Dict[int, int] = {}                             # cut piece -> the accidental stroke its accidental side joins
    undone: set = set()
    for i, parts in cuts.items():
        _k, m, x0, y0 = out[i]
        accm = parts[1][1]
        grown = cv2.dilate(np.pad(accm, 1).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)   # frame (y0-1, x0-1)
        best = (0, -1)
        for j, (_kj, mj, xj, yj) in enumerate(out):
            if j == i or j in cuts or _inside_share(mj, xj, yj, acc_rects) < 0.5:
                continue
            gx0, gy0 = x0 - 1, y0 - 1
            ox0, oy0 = max(gx0, xj), max(gy0, yj)
            ox1, oy1 = min(gx0 + grown.shape[1], xj + mj.shape[1]), min(gy0 + grown.shape[0], yj + mj.shape[0])
            if ox1 <= ox0 or oy1 <= oy0:
                continue
            n = int((grown[oy0 - gy0:oy1 - gy0, ox0 - gx0:ox1 - gx0] & mj[oy0 - yj:oy1 - yj, ox0 - xj:ox1 - xj]).sum())
            if n > best[0]:
                best = (n, j)
        if best[1] >= 0 and TOUCH_JOIN_HOST:
            host[i] = best[1]
        elif TOUCH_JOIN_HOST and int(accm.sum()) < TOUCH_ALONE_MIN_SP2 * sp * sp:
            refused["touch_part_too_small"] = refused.get("touch_part_too_small", 0) + 1
            undone.add(i)
            continue
        refused["touch_cut"] = refused.get("touch_cut", 0) + 1
    for i, j in host.items():                             # the accidental side joins its stroke (keeps that stroke's kind)
        kj, mj, xj, yj = pieces[j]
        _k, m, x0, y0 = out[i]
        accm = cuts[i][1][1]
        X0, Y0 = min(xj, x0), min(yj, y0)
        X1, Y1 = max(xj + mj.shape[1], x0 + m.shape[1]), max(yj + mj.shape[0], y0 + m.shape[0])
        u = np.zeros((Y1 - Y0, X1 - X0), bool)
        u[yj - Y0:yj - Y0 + mj.shape[0], xj - X0:xj - X0 + mj.shape[1]] |= mj
        u[y0 - Y0:y0 - Y0 + m.shape[0], x0 - X0:x0 - X0 + m.shape[1]] |= accm
        c, oy, ox = _crop(u)
        pieces[j] = (kj, c, X0 + ox, Y0 + oy)
    new: List[Tuple[str, np.ndarray, int, int]] = []
    where: Dict[int, int] = {}
    added: List[Tuple[int, int, str]] = []
    pending: List[Tuple[int, int, str]] = []
    for i, pc in enumerate(pieces):
        kind, m, x0, y0 = pc
        if i not in cuts or i in undone:
            where[i] = len(new)
            new.append(pc)
            continue
        (ko, om, jo), (ka, am, ja) = cuts[i]
        c, oy, ox = _crop(om)
        where[i] = len(new)
        new.append((ko, c, x0 + ox, y0 + oy))             # the other mark keeps the piece's place (its joins stay with it)
        if i in host:
            pending.append((i, host[i], ja))
        else:
            c, oy, ox = _crop(am)
            new.append((ka, c, x0 + ox, y0 + oy))
            added.append((len(new) - 1, where[i], ja))
    added += [(where[j], where[i], join) for i, j, join in pending]
    return new, [(where[a], where[b], j) for a, b, j in joins] + added


def split_pieces(pieces: List[Tuple[str, np.ndarray, int, int]], sp: float, ink: Optional[np.ndarray] = None,
                 keep_whole: Sequence[Tuple[float, float, float, float]] = (),
                 clef_boxes: Sequence[Tuple[Tuple[float, float, float, float], Optional[str]]] = (),
                 touch_boxes: Sequence[Tuple[str, Tuple[float, float, float, float]]] = ()
                 ) -> Tuple[List[Tuple[str, np.ndarray, int, int]], List[Tuple[int, int, str]], Dict[str, int]]:
    """ROADMAP 2.239: every piece cut at its joins (module constants above). Returns (pieces, joins [(part, first part of the same piece,
    join name)], refused {reason: n}). A piece left whole is returned unchanged; the union of a piece's parts is exactly the piece.
    `keep_whole` (reduced frame): the clef / key / meter boxes of the cell -- a piece mostly inside one is never cut (their ink is claimed
    whole by its area; the page has no join there, Sean's 2.239 tiles 2 and 5). A head cut off a rung takes back the oval's tips the
    horizontal opening left to the remainder, so a head on a ledger line is ONE stroke."""
    out: List[Tuple[str, np.ndarray, int, int]] = []
    joins: List[Tuple[int, int, str]] = []
    refused: Dict[str, int] = {}
    rung_heads: List[int] = []
    loose: List[int] = []
    lines_out = None
    if clef_boxes and ink is not None:             # 2.239 r3: a clef the openings chopped up is ONE stroke again (tile 7)
        others = [r for r in keep_whole if not any(all(abs(float(a) - float(b)) < 1e-6 for a, b in zip(r[:4], cb[:4])) for cb, _f in clef_boxes)]
        pieces = _merge_clefs(pieces, sp, ink, clef_boxes, refused, others)
    if ink is not None:
        lines_out = ink.copy()
        for kind, m, x0, y0 in pieces:            # rungs and beams are left out of a stack's edges (a rung between two heads sticks out)
            if kind == "horizontal":
                h, w = m.shape
                lines_out[y0:y0 + h, x0:x0 + w] &= ~m
    for kind, m, x0, y0 in pieces:
        if keep_whole and _inside_share(m, x0, y0, keep_whole) >= 0.5:
            refused["inside_clef_key_meter"] = refused.get("inside_clef_key_meter", 0) + 1
            parts = None
        elif kind == "vertical":
            parts = _split_vertical(m, sp, refused, (lines_out, x0, y0) if lines_out is not None else None)
        elif kind == "horizontal":
            parts = _split_horizontal(m, sp, refused)
        else:
            parts = _split_remainder(m, sp, refused)
        if parts and int(sum(int(p_.sum()) for _k, p_, _j in parts)) != int(m.sum()):
            refused["parts_do_not_add_up"] = refused.get("parts_do_not_add_up", 0) + 1   # never lose or double ink: leave it whole
            parts = None
        if not parts:
            if kind == "blob" and int(m.sum()) < LEDGER_TIP_MAX_SP2 * sp * sp:
                loose.append(len(out))
            out.append((kind, m, x0, y0))
            continue
        first = len(out)
        for k, part, join in parts:
            if not part.any():
                continue
            c, oy, ox = _crop(part)
            if k == "blob" and (kind == "horizontal" or join in ("stem|head", "head|head")):
                rung_heads.append(len(out))
            out.append((k, c, x0 + ox, y0 + oy))
            if len(out) - 1 != first:
                joins.append((len(out) - 1, first, join))
    # the oval's own edge: a small remainder blob TOUCHING a head part cut off a stem or a rung (within the 1 px gap the cut leaves), lying
    # within the head's rows and no further out than `HEAD_EDGE_PAD_SPACES`, is the oval's tip or the edge column the vertical opening
    # dropped (a notched column is not in the opening) -- it joins the head, so a head is ONE stroke (2.239 strict readout: heads were
    # 2-4 pieces). Among several heads (a stack), the one whose rows it shares most.
    import cv2
    pad = max(1, int(round(HEAD_EDGE_PAD_SPACES * sp)))
    gone = set()
    for li in loose:
        _k2, lm, lx, ly = out[li]
        lh, lw = lm.shape
        best = None
        for hi in rung_heads:
            _k, hm, hx, hy = out[hi]
            hh, hw = hm.shape
            if lx < hx - pad or lx + lw > hx + hw + pad or ly < hy - pad or ly + lh > hy + hh + pad:
                continue
            gx0, gy0 = min(hx, lx) - 3, min(hy, ly) - 3
            A = np.zeros((max(hy + hh, ly + lh) - gy0 + 3, max(hx + hw, lx + lw) - gx0 + 3), np.uint8)
            A[hy - gy0:hy - gy0 + hh, hx - gx0:hx - gx0 + hw] = hm
            near = cv2.dilate(A, np.ones((5, 5), np.uint8)).astype(bool)[ly - gy0:ly - gy0 + lh, lx - gx0:lx - gx0 + lw]
            if not (near & lm).any():
                continue
            share = min(hy + hh, ly + lh) - max(hy, ly)
            if best is None or share > best[0]:
                best = (share, hi)
        if best is None:
            continue
        hi = best[1]
        k, hm, hx, hy = out[hi]
        if True:
            X0, Y0 = min(hx, lx), min(hy, ly)
            X1, Y1 = max(hx + hm.shape[1], lx + lw), max(hy + hm.shape[0], ly + lh)
            u = np.zeros((Y1 - Y0, X1 - X0), bool)
            u[hy - Y0:hy - Y0 + hm.shape[0], hx - X0:hx - X0 + hm.shape[1]] |= hm
            u[ly - Y0:ly - Y0 + lh, lx - X0:lx - X0 + lw] |= lm
            out[hi] = (k, u, X0, Y0)
            gone.add(li)
    if gone:
        keep = [i for i in range(len(out)) if i not in gone]
        new_of = {old: new for new, old in enumerate(keep)}
        out = [out[i] for i in keep]
        joins = [(new_of[a], new_of[b], j) for a, b, j in joins]
    if touch_boxes:                                # 2.239 r3: an accidental touching a rung, a head or a stem is two marks (tile 1)
        out, joins = _cut_touching_all(out, joins, sp, touch_boxes, refused)
    return out, joins, refused


def map_strokes(erased: np.ndarray, sp_canonical: float, nominal_lines_canonical: Sequence[float],
                raw: Optional[np.ndarray] = None, split_joins: Optional[bool] = None,
                keep_whole: Sequence[Sequence[Any]] = (), touch_boxes: Sequence[Sequence[Any]] = ()) -> Optional[CellStrokes]:
    """Every stroke of one cell. `erased` = `cell.image_no_staff` (0 = ink); `raw` = `cell.binary` (0 = ink) for the local staff.
    None for a cell that cannot be reduced. Deterministic: strokes ordered by (x, y, kind). `split_joins` None = the flag
    `OMR_SPLIT_JOINS` (ROADMAP 2.239): fused pieces are cut at their joins (`split_pieces`) and each part carries `joined_to`.
    `keep_whole` (canonical [x0, y0, x1, y1] or [x0, y0, x1, y1, "clef:G|F|C"]): clef / key / meter boxes no split cuts inside; a clef box
    also joins the pieces the openings cut its clef into, read outward from the box and bounded by the clef's size (2.239 r3). `touch_boxes` (canonical [family, x0, y0, x1, y1]): the cell's accidental,
    head, ledger and stem detector boxes; a piece across an accidental box and one of the others is cut at their boundary (2.239 r3)."""
    import cv2
    if erased is None or erased.ndim != 2 or sp_canonical <= 0:
        return None
    scale = min(1.0, TARGET_SP_PX / float(sp_canonical))
    sp = TARGET_SP_PX if scale < 1.0 else float(sp_canonical)
    inv = 1.0 / scale
    ink = _reduce(erased, scale)
    if not ink.any():
        return CellStrokes([], 0, scale, float(sp_canonical), False)
    u8 = ink.astype(np.uint8)
    kh, kw = max(3, int(round(V_MIN_SPACES * sp))), max(3, int(round(H_MIN_SPACES * sp)))
    V = cv2.morphologyEx(u8, cv2.MORPH_OPEN, np.ones((kh, 1), np.uint8))
    H0 = cv2.morphologyEx(u8, cv2.MORPH_OPEN, np.ones((1, kw), np.uint8))
    claimed = V.astype(bool)
    _n, ink_lab, _ = _components(ink)

    pieces: List[Tuple[str, np.ndarray, int, int]] = []
    nv, vlab, vst = _components(V)
    for i in range(1, nv):
        x, y, w, h, _a = (int(v) for v in vst[i])
        pieces.append(("vertical", vlab[y:y + h, x:x + w] == i, x, y))
    nh, hlab, hst = _components(H0)
    for i in range(1, nh):
        x, y, w, h, a = (int(v) for v in hst[i])
        longest = max(w, h)
        if a > 0 and (longest * longest) / float(a) >= H_MIN_ASPECT:
            pieces.append(("horizontal", hlab[y:y + h, x:x + w] == i, x, y))
            claimed |= (hlab == i)
    rem = ink & ~cv2.dilate(claimed.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    nr, rlab, rst = _components(rem)
    floor_px = MIN_AREA_SP2 * sp * sp
    below = 0
    for i in range(1, nr):
        x, y, w, h, a = (int(v) for v in rst[i])
        if a < floor_px:
            below += 1
            continue
        longest = max(w, h)
        thick_mean = a / float(longest)
        curve = (longest >= CURVE_MIN_SPACES * sp and thick_mean <= CURVE_MAX_THICK_SPACES * sp
                 and longest / max(1.0, thick_mean) >= CURVE_MIN_ASPECT)
        pieces.append(("curve" if curve else "blob", rlab[y:y + h, x:x + w] == i, x, y))
    joins: List[Tuple[int, int, str]] = []
    refused: Dict[str, int] = {}
    acc_parts: Dict[int, List[Tuple[str, np.ndarray, int, int]]] = {}
    if split_joins if split_joins is not None else split_joins_enabled():
        kw = [tuple(float(v) * scale for v in r[:4]) for r in keep_whole]      # canonical (x0, y0, x1, y1) -> reduced
        clefs = [(tuple(float(v) * scale for v in r[:4]), (str(r[4]).split(":") + [None])[1])          # 2.239 r3: [.., "clef:G"]
                 for r in keep_whole if len(r) > 4 and str(r[4]).startswith("clef")]
        tb = [(str(r[0]), tuple(float(v) * scale for v in r[1:5])) for r in touch_boxes]                    # 2.239 r3: [family, x0..y1]
        pieces, joins, refused = split_pieces(pieces, sp, ink, kw, clefs, tb)
        if accidental_whole_enabled():                  # 2.242: an accidental the openings cut up is ONE stroke again (after the touch cut)
            accs = [(tuple(float(v) * scale for v in r[1:5]), str(r[5])) for r in touch_boxes if r[0] == TOUCH_ACC_FAMILY and len(r) > 5]
            excl = [tuple(float(v) * scale for v in r[1:5]) for r in touch_boxes if r[0] in TOUCH_OTHER_FAMILIES] + kw
            pieces, joins, acc_parts = merge_accidentals(pieces, joins, sp, accs, excl, refused)

    staff = LocalStaff(_reduce_float(raw, scale) if raw is not None else None,
                       [y * scale for y in nominal_lines_canonical], sp)
    restore = THICKNESS_FROM_UNERASED and raw is not None and raw.ndim == 2 and raw.shape == erased.shape

    built: List[Tuple[Tuple[int, int, int, int], Stroke, np.ndarray, int, int, int]] = []
    n_pieces = len(pieces)
    part_of: List[int] = []                      # 2.242: the pieces a whole accidental was made of are measured like any piece, then kept as its `parts`
    all_pieces = list(pieces)
    for parent, plist in acc_parts.items():
        for pc in plist:
            all_pieces.append(pc)
            part_of.append(parent)
    parts_by_parent: Dict[int, List[Stroke]] = {}
    for pidx, (kind, m, x0, y0) in enumerate(all_pieces):
        h, w = m.shape
        mm = _measure(m, x0, y0)
        if restore and kind in ("horizontal", "curve") and abs(math.cos(mm["theta"])) >= abs(math.sin(mm["theta"])):
            rt = _restored_thickness(m, x0, y0, scale, erased, raw, float(sp_canonical), abs(math.cos(mm["theta"])))
            if rt is not None:
                mm["thick"] = max(mm["thick"], rt)
        ang = -math.degrees(mm["theta"])
        ang = ang + 180.0 if ang <= -90.0 else (ang - 180.0 if ang > 90.0 else ang)
        mid = staff.lines_at(x0 + w / 2.0)
        steps = []
        for (ex, ey) in (mm["end0"], mm["end1"]):
            ln = staff.lines_at(ex)
            half = (ln[4] - ln[0]) / 8.0
            steps.append(round((ey - ln[0]) / half, 2) if half > 0 else 0.0)
        ys_, xs_ = np.nonzero(m)
        box = (int(round(x0 * inv)), int(round(y0 * inv)), int(round(w * inv)), int(round(h * inv)))
        e0, e1 = mm["end0"], mm["end1"]
        st = Stroke(
            kind=kind, box=box, area_sp2=round(mm["area"] / (sp * sp), 3), length_sp=round(mm["length"] / sp, 3),
            angle_deg=round(ang, 1), thickness_sp=round(mm["thick"] / sp, 3),
            thickness_spread_sp=round(mm["spread"] / sp, 3), fill=round(mm["area"] / float(w * h), 3),
            sagitta_sp=None if kind == "blob" or mm["sag"] is None else round(mm["sag"] / sp, 3),
            hole_share=round(_hole_share(m), 3) if kind == "blob" else None,
            ends=((int(round(e0[0] * inv)), int(round(e0[1] * inv))), (int(round(e1[0] * inv)), int(round(e1[1] * inv)))),
            profile=mm["profile"], component=int(ink_lab[y0 + int(ys_[0]), x0 + int(xs_[0])]),
            lines_left=[int(round(v * inv)) for v in staff.lines_at(x0)],
            lines_right=[int(round(v * inv)) for v in staff.lines_at(x0 + w)],
            staff_space_local=round((mid[4] - mid[0]) / 4.0 * inv, 2), end_steps=(steps[0], steps[1]))
        if pidx >= n_pieces:
            parts_by_parent.setdefault(part_of[pidx - n_pieces], []).append(st)
        else:
            built.append((box, st, m, x0, y0, pidx))
    for r in built:
        if r[5] in parts_by_parent:
            r[1].parts = parts_by_parent[r[5]]

    built.sort(key=lambda r: (r[0][0], r[0][1], KINDS.index(r[1].kind)))
    k3 = np.ones((3, 3), np.uint8)       # contact = within 2 px: the remainder was cut 1 px clear of the openings
    n = len(built)
    for i in range(n):
        _b, si, mi, xi, yi, _pi = built[i]
        hi_, wi_ = mi.shape
        for j in range(i + 1, n):
            _b2, sj, mj, xj, yj, _pj = built[j]
            hj, wj = mj.shape
            if xi + wi_ + 1 < xj or xj + wj + 1 < xi or yi + hi_ + 1 < yj or yj + hj + 1 < yi:
                continue
            gx0, gy0 = min(xi, xj) - 1, min(yi, yj) - 1
            gx1, gy1 = max(xi + wi_, xj + wj) + 1, max(yi + hi_, yj + hj) + 1
            A = np.zeros((gy1 - gy0, gx1 - gx0), np.uint8)
            B = np.zeros_like(A)
            A[yi - gy0:yi - gy0 + hi_, xi - gx0:xi - gx0 + wi_] = mi
            B[yj - gy0:yj - gy0 + hj, xj - gx0:xj - gx0 + wj] = mj
            ca = int((A.astype(bool) & cv2.dilate(B, k3, iterations=2).astype(bool)).sum())
            cb = int((B.astype(bool) & cv2.dilate(A, k3, iterations=2).astype(bool)).sum())
            if ca == 0 and cb == 0:
                continue
            contact = round((min(ca, cb) or max(ca, cb)) / sp, 2)
            si.touches.append((j, contact))
            sj.touches.append((i, contact))
    out = [r[1] for r in built]
    if joins:
        ordinal = {r[5]: o for o, r in enumerate(built)}
        for part, first, join in joins:
            a, b = ordinal[part], ordinal[first]
            out[a].joined_to.append((b, join))
            out[b].joined_to.append((a, join))
    per: Dict[int, int] = {}
    for s in out:
        per[s.component] = per.get(s.component, 0) + 1
    for s in out:
        s.component_n_strokes = per[s.component]
    return CellStrokes(out, below, scale, float(sp_canonical), staff.local, masks=[(r[2], r[3], r[4]) for r in built],
                       split_refused=refused)


#: ROADMAP 2.206d (flag `OMR_STEM_TIP_TRUE_EDGE`, default ON since 2026-10-27). The stem finder's box can be a thin core of a thick stem (Brahms p14: 4 px
#: of a 25 px stem); the stroke map holds the stem's whole width. Measured over the rows this far from either end of the stem (L7: head and
#: stem fuse up to 1.2 sp beside a head) and refused where the stroke is wider than `STEM_TRUE_WIDTH_MAX_SPACES` (Litolff's widest plain stem
#: 0.43 sp, Brahms 0.37 at p90; a fused or doubled stroke is not a stem's width).
STEM_TRUE_END_MARGIN_SPACES = 1.5
STEM_TRUE_WIDTH_MAX_SPACES = 0.7


def stem_true_edges(res: "CellStrokes", stem_box: Sequence[float]) -> Optional[Tuple[float, float]]:
    """ROADMAP 2.206d: `(x0, x1)` in canonical cell px of the stroke the finder's stem box lies on, measured mid-stem; `None` where no stroke
    carries the box's centre at the mid rows or the measured width is not a stem's. The finder says WHICH stroke; the stroke says how wide."""
    if res is None or isinstance(res, str) or not getattr(res, "masks", None):
        return None
    x, y, w, h = (float(v) for v in stem_box)
    sp = float(res.sp_canonical)
    s = float(res.scale)
    margin = STEM_TRUE_END_MARGIN_SPACES * sp
    ya, yb = y + margin, y + h - margin
    if yb - ya < 0.5 * sp:                      # a short stem: the middle half
        ya, yb = y + 0.25 * h, y + 0.75 * h
    cx = (x + w / 2.0) * s
    best = None
    for m, mx0, my0 in res.masks:
        mh, mw = m.shape
        r0, r1 = max(0, int(round(ya * s)) - my0), min(mh, int(round(yb * s)) - my0)
        c = int(round(cx)) - mx0
        if r1 <= r0 or not (0 <= c < mw):
            continue
        hits = int(m[r0:r1, c].sum())
        if hits and (best is None or hits > best[0]):
            best = (hits, m, mx0, r0, r1)
    if best is None:
        return None
    _, m, mx0, r0, r1 = best
    lefts, rights = [], []
    for r in range(r0, r1):
        row = m[r]
        c = int(round(cx)) - mx0
        if not row[c]:
            nz = np.flatnonzero(row)
            if nz.size == 0:
                continue
            c = int(nz[np.argmin(np.abs(nz - c))])
        a = c
        while a > 0 and row[a - 1]:
            a -= 1
        b = c
        while b < row.size - 1 and row[b + 1]:
            b += 1
        lefts.append(a); rights.append(b + 1)
    if len(lefts) < 3:
        return None
    x0, x1 = (mx0 + float(np.median(lefts))) / s, (mx0 + float(np.median(rights))) / s
    if x1 - x0 > STEM_TRUE_WIDTH_MAX_SPACES * sp:
        return None
    return x0, x1
