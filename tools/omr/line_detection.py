"""Classical-CV detection of line-like elements (stems, beams).

Phase 4f. YOLO bounding boxes are structurally poor at thin lines (extreme
aspect ratios, mostly-empty boxes). The Phase 3.3 model misses **stems**
entirely (0 detections even at conf=0.05) and emits **beam** bboxes with
endpoints that systematically fall short of the actual beam strokes.

This module replaces both with classical CV (morphological filtering +
connected components), which:

  * is fast (a few ms per cell on CPU)
  * is deterministic (no model weights, no GPU)
  * naturally handles thin lines (no bbox-aspect-ratio bias)
  * picks up the actual ink, not a learned approximation of it

The output integrates with `rhythm.py` and `voicing.py` by providing a
`LineDetection` dataclass that exposes the same `x_canonical`,
`y_canonical`, `width_canonical`, `height_canonical` attributes the YOLO
`SymbolDetection` exposes — so downstream code can treat them
interchangeably.

Public API:

    detect_stems(cell)  -> list[LineDetection]
    detect_beams(cell)  -> list[LineDetection]

Both operate on the cell's canonical-coord image. The staff-removed
variant (`cell.image_no_staff`) is preferred when available — it makes
the projections much cleaner since the long horizontal staff-line ink
doesn't confuse the vertical-projection step.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Sequence

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Public data type
# ---------------------------------------------------------------------------


@dataclass
class LineDetection:
    """Quack-compatible with template_matcher.SymbolDetection — exposes the
    fields rhythm.py + voicing.py read, so a list of these can be mixed
    with YOLO SymbolDetections without special-casing.
    """
    smufl_name: str          # 'stem' / 'beam' (used by rhythm.py category checks)
    category: str            # 'stem' / 'structural'
    x_canonical: int
    y_canonical: int
    width_canonical: int
    height_canonical: int
    confidence: float = 1.0  # classical CV is deterministic; conf is arbitrary
    pitch: str | None = None

    @property
    def x_center(self) -> int:
        return self.x_canonical + self.width_canonical // 2

    @property
    def y_center(self) -> int:
        return self.y_canonical + self.height_canonical // 2


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------


def _binary_ink(image: np.ndarray, threshold: int = 180) -> np.ndarray:
    """Return a uint8 mask where ink=255, paper=0. Matches Phase 1's
    convention (255=foreground in `connectedComponentsWithStats`).

    Note: opencv ops like morphology expect "ink" to be the bright value.
    Phase 1's PageImage.binary stores 0=ink/255=paper (Sauvola), so we
    re-threshold here from the source image to get the right polarity.
    """
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    return mask


def _staff_line_spacing(cell) -> float:
    """Average staff-line spacing in canonical coords. Fallback default is
    24 px (the canonical reference spacing used in pitch_resolver.py).
    """
    lines = getattr(cell, "staff_line_ys_canonical", None) or []
    if len(lines) >= 2:
        ys = sorted(lines)
        gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
        return sum(gaps) / len(gaps)
    # A one-line percussion staff has no gaps to average, and the 24 px below
    # is not this frame's number: a canonical cell spans 400 px over four
    # spaces, so its spacing is 100. `measure_extractor._build_measure_cell`
    # writes the true canonical spacing down for exactly the cells that cannot
    # answer for themselves; absent on every five-line cell, so this is inert
    # unless `OMR_ONE_LINE_STAVES` admitted one.
    stated = getattr(cell, "staff_line_spacing_canonical", None)
    if stated:
        return float(stated)
    return 24.0


# ---------------------------------------------------------------------------
# Stem detection
# ---------------------------------------------------------------------------


# The stem-isolating opening kernel, as a fraction of `min_height_lines` (see
# detect_stems). Anything at or above 0.8 gives the same answer on the
# reference sheet at every line thickness tested; below it, noteheads start
# surviving the opening again.
STEM_KERNEL_MARGIN = 0.8


# How long a vertical run may be and still be a stem, in staff spaces.
#
# A STEM IS AS LONG AS THE MUSIC NEEDS IT TO BE. It runs from its notehead to
# its beam, so a note sitting two ledger lines above the staff and beamed to
# notes inside it carries a stem of six spaces or more — ordinary orchestral
# writing, not an outlier. The old value of 6.0 cut exactly there, and the notes
# it silently un-stemmed are the ones furthest from their beam.
#
# Measured over 8746 candidates on 13 pages of 8 editions (every page of the
# phase-1 corpus plus the three engraved benchmarks), taking every component
# that passes every OTHER filter:
#
#     2-3 spaces  3130      6-7 spaces   265      10-11 spaces  43
#     3-4         3087      7-8          290      11-12          9
#     4-5         1390      ------------------    12-13         43
#     5-6          365      8-9           25      13-14         43
#                           9-10           5      14-17         42
#
# One population decays smoothly from 2 to 8 spaces and stops; a second one
# begins around 10 and runs to the height of the cell itself (the per-page
# maxima are 13.96 on a 14-space cell and 15.98 on a 16-space one). The second
# population is furniture — a barline or bracket crossing the crop — and the
# 11x drop between the 7-8 and 8-9 buckets is the sharpest edge in the whole
# distribution. This constant sits on it.
#
# The benchmark agrees with the distribution, which is why the value is not a
# tuned one — swept end to end on the engraved orchestral set:
#
#     cap    pooled   edits    brahms duration rate
#     6.0    0.1861    1315         0.931            <- before
#     7.0    0.1601    1136         0.963
#     8.0    0.1601    1136         0.964            <- chosen
#     9.0    0.1610    1142         0.963
#    12.0    0.1610    1142         0.963
#
# 7.0 ties 8.0 here and is the worse choice: it sits INSIDE the smooth decay,
# so it would cut the 290 real stems the corpus has between 7 and 8 spaces on
# scores this benchmark does not contain. Going the other way costs 6 edits,
# and the single component that buys is worth knowing — on Brahms it spans
# canonical y 260-989 against a staff of 537-896, straight through the staff
# from above it to below. That is a barline, and it is what the cap is for.
#
# The stem ground truth (`benchmarks/omr-phase4-lines`, 48 stems engraved by
# LilyPond at four line thicknesses) is UNCHANGED at every value tried — its
# music has no long stems, so it cannot speak to this and does not pretend to.
STEM_MAX_HEIGHT_LINES = 8.0


#: `OMR_STEM_STROKE` — read a stem from a COLUMN PROFILE as well as from a
#: connected component. Default OFF, so the OFF test is an ALLOW-LIST: a typo
#: must not switch a document ONTO an unpriced GATHER change (CLAUDE.md, *A
#: flag's OFF test must follow its DEFAULT*).
STEM_STROKE_ENV = "OMR_STEM_STROKE"

#: How far two adjacent columns' run endpoints may differ and still be read as
#: one stroke, in staff spaces. A stem is a hairline the engraver drew in one
#: stroke, so its columns share both endpoints to within the plate's bleed; a
#: fused blob's neighbouring columns do not.
#:
#: ⚠️ It sits on a PLATEAU, not in an empty interval: swept 0.10 / 0.15 / 0.25
#: / 0.40 / 0.60 the heads a band covers read 293 / 287 / 287 / 286 / 284 on
#: Litolff and 397 at every value on Breitkopf, while the positive control
#: (re-finding the strokes `detect_stems` already accepts) reads 98.8 / 98.2 /
#: 98.2 / 98.2 / 97.6 and 99.0 / 98.9 / 98.7 / 98.4 / 98.4. Nothing separates;
#: the value is the middle of a flat region and is not tuned to either plate.
STEM_STROKE_AGREE_SPACES = 0.25


def stem_stroke_enabled() -> bool:
    """Is the column-profile stroke reader on? Default OFF, allow-list."""
    import os
    return os.environ.get(STEM_STROKE_ENV, "0").strip().lower() in (
        "1", "true", "yes", "on")


#: `OMR_STEM_NOTEHEAD_GATE` — a vertical stroke that MEETS A DETECTED NOTEHEAD
#: is a stem, and the pair rule may not delete it. Default OFF, so the test is
#: an ALLOW-LIST (CLAUDE.md, *A flag's OFF test must follow its DEFAULT*).
#:
#: ⚠️ THE RULE IT NARROWS IS RIGHT ABOUT ITS JOB AND WRONG ABOUT ITS PREMISE.
#: `_drop_paired_strokes` deletes both members of any pair of verticals within
#: 0.9 staff spaces because *"successive notes are set further apart than an
#: accidental's own strokes"*. Measured on Litolff Beethoven 5 pp.1-4
#: (`benchmarks/omr-stem-pair-rule-2026-09/`): of the 244 strokes it deletes,
#: 80 carry a detected notehead, and **62 of those 80 (77.5%) were paired with
#: ANOTHER stroke that also carries one** — two genuine stems eating each
#: other, not an accidental. 73 of the 793 stemless heads (9.2%) would stop
#: abstaining `no_stem` without the rule.
#:
#: ⚠️ AND REMOVING THE RULE IS REFUSED, which is why this is a GATE and not a
#: deletion: on the rule's own hand count the summed |error| goes 15 (ON) to
#: 53 (OFF), OFF worse on 7 of 10 cells and better on none.
#:
#: ⚠️ NO NEW CONSTANT, and that is the reason this shape was chosen over a
#: threshold. The geometry `detect_stems` can see does NOT separate the two
#: populations — best single feature 0.823 against a 0.723 majority baseline,
#: no empty interval anywhere — so a cut read off that table would be fitted
#: to one plate. The notehead is the only discriminator available and it needs
#: no number.
#:
#: ⚠️ IT COUPLES `Q.STEM` TO THE DETECTOR, and that is the standing objection:
#: the CV stem rung is today an INDEPENDENT reader of the ink, and this file's
#: own `gather_cv_lines` docstring says the two readers see different images on
#: purpose. Where the detector misses a notehead the gate cannot protect that
#: stroke — which fails toward the SHIPPED behaviour and never toward a new
#: one, but it also means the gate is weakest exactly on the pages where stems
#: are most often missed.
STEM_NOTEHEAD_GATE_ENV = "OMR_STEM_NOTEHEAD_GATE"


def stem_notehead_gate_enabled() -> bool:
    """Is the notehead gate on the pair rule on? Default OFF, allow-list."""
    import os
    return os.environ.get(STEM_NOTEHEAD_GATE_ENV, "0").strip().lower() in (
        "1", "true", "yes", "on")


def _column_stroke_bands(ink: np.ndarray, line_spacing: float, cell_w: int, *,
                         min_height_lines: float, max_height_lines: float,
                         max_width_lines: float,
                         agree_spaces: float = STEM_STROKE_AGREE_SPACES):
    """Find stems by COLUMN PROFILE, labelling no components at all.

    ⚠️⚠️ WHY THIS EXISTS: ON THESE PLATES THE INK IS FUSED, AND A COMPONENT
    READER HAS NOTHING STEM-SHAPED TO FIND. `rejection_census.py` names the
    first filter each missing stem's component fails, and on BOTH publishers
    the overwhelming majority is *a component EXISTS and is the wrong SHAPE*
    — WIDE+TALL+SHORT is 683 of 793 (86%) on Litolff and 1,132 of 1,529 (74%)
    on Breitkopf, against *no component at all* at only 21% and 13%. The
    largest single bucket INVERTS between the two (Litolff WIDE 29.9%,
    Breitkopf TALL 31.1%), so no constant serves both.

    STEP 1 IS `detect_stems`' OWN STEP 3, UNCHANGED. `runs()` keeps the pixels
    lying in a vertical ink run of at least `k` rows, which is exactly a
    (1, k) morphological opening: erode keeps a pixel only where all k rows of
    its column window are ink, dilate puts the run back.

    ⚠️⚠️ THE DIFFERENCE IS STEP 2, AND IT IS THE WHOLE POINT. `detect_stems`
    then runs 2D connected components at connectivity 8 and measures the BLOB,
    so a stem fused to its own notehead is measured at the NOTEHEAD's width
    and the width cap throws the stem away with the blob — the failure this
    function's own kernel comment already describes and shrank the kernel from
    1.0 to 0.8 spaces to mitigate. This never labels a component. It reads the
    profile COLUMN BY COLUMN and bands adjacent columns only where they AGREE
    about where their run starts and ends, which is a property a stem has and
    a fused blob does not. A band is CUT rather than widened when a column
    disagrees, and cut again at `max_width_lines` — both are refusals to
    merge, so this can only ever produce a NARROWER stroke than a connected
    component would, never a wider one.

    ⚠️ A band's height is the MEDIAN of its columns' run extents, not their
    union: a union hands one column that caught a beam or a neighbour its
    length to the whole band.

    ⚠️ NO EROSION AND NO RE-THRESHOLDING, deliberately. The registry entry
    *Stacked beams are set 0.75 staff spaces centre to centre* [C79 + L20]
    measures a beam stroke at 0.5 spaces thick with a 0.25-space gap — "the
    gap is NARROWER than the stroke, so an erosion tuned to open the gaps will
    eat the strokes first" — and the handoff's dead hypothesis agrees from the
    other side: horizontal pre-dilation at 2/3/5 px recovered 3, 3 and 4 heads
    of 793. A profile reads the ink it is given.

    Every filter below is `detect_stems`' own, passed in rather than restated.
    """
    min_h = int(round(line_spacing * min_height_lines))
    max_h = int(round(line_spacing * max_height_lines))
    max_w = max(3, int(round(line_spacing * max_width_lines)))
    edge_margin = max(int(round(line_spacing * 0.8)), 12)
    agree_px = max(1, int(round(line_spacing * agree_spaces)))
    if min_h <= 1:
        return []

    long_mask = cv2.morphologyEx(
        ink, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, min_h)))
    m = long_mask > 0
    if not m.any():
        return []
    # ⚠️ THE LONGEST RUN PER COLUMN, NOT ITS FIRST-TO-LAST EXTENT. A column
    # holding two long runs -- two notes stacked in it, or a stem crossing a
    # second one -- has a first-to-last extent spanning both, and taking that
    # reports one stroke where there are two. Measured on a synthetic pair of
    # 2.5-space runs 1.5 spaces apart, the extent rule reported NOTHING at all
    # (its own single-run guard rejected the column), so the cost was reach
    # rather than a wrong box -- which is the failure that is hard to notice.
    h_px, w_px = m.shape
    cur = np.zeros(w_px, dtype=np.int32)
    best = np.zeros(w_px, dtype=np.int32)
    bend = np.zeros(w_px, dtype=np.int32)
    for y in range(h_px):
        cur = np.where(m[y], cur + 1, 0)
        upd = cur > best
        best = np.where(upd, cur, best)
        bend = np.where(upd, y, bend)
    has = best > 0
    bot = bend
    top = bend - best + 1

    out: list[LineDetection] = []
    i, n = 0, len(has)
    while i < n:
        if not has[i]:
            i += 1
            continue
        # ⚠️⚠️ THE SEGMENT IS CUT BY DISAGREEMENT ALONE, AND THE WIDTH CAP IS
        # THEN APPLIED TO THE WHOLE OF IT. Cutting at the cap instead is what
        # this module's own unit test caught, twice over: a solid block 2
        # staff spaces wide and 4 tall is sliced into strips of 0.6 spaces,
        # every strip agrees with its neighbours and passes the height, width
        # and 3:1 aspect filters, so a blob came out as three stems. Refusing
        # the strips that hit the cap was not enough either -- the LAST
        # remnant strip terminates on ordinary non-ink and escaped. A stem is
        # thin AND ISOLATED (`[L14]`, "about a tenth of a staff space
        # thick"), so the property that has to hold is of the agreeing region
        # as a whole: an agreeing region wider than a stem is not a stem, and
        # no part of it is either.
        j = i + 1
        while j < n and has[j]:
            d = max(abs(int(top[j]) - int(top[j - 1])),
                    abs(int(bot[j]) - int(bot[j - 1])))
            if d > agree_px:
                break
            j += 1
        x0, w = i, j - i
        i = j
        cols = slice(x0, x0 + w)
        t = int(np.median(top[cols]))
        b = int(np.median(bot[cols]))
        h = b - t + 1
        if h < min_h or h > max_h or w > max_w:
            continue
        if x0 < edge_margin or x0 + w > cell_w - edge_margin:
            continue
        if w * h < max(4, line_spacing * 0.5):
            continue
        if h / max(1, w) < 3.0:
            continue
        out.append(LineDetection(
            smufl_name="stem", category="stem",
            x_canonical=int(x0), y_canonical=int(t),
            width_canonical=int(w), height_canonical=int(h),
            confidence=1.0,
        ))
    return out


# ---------------------------------------------------------------------------
# The vertical-run CANDIDATE population -- accepted AND refused
# ---------------------------------------------------------------------------
#
# ⚠️⚠️ WHY THIS EXISTS: `detect_stems` NAMES AND FILTERS IN ONE ACT, INSIDE
# GATHER. It finds every vertical candidate, applies six filters, and returns
# only the survivors -- so a candidate the pipeline FOUND and DISCARDED leaves
# no row at all, the population arrives at every stage already named `stem`,
# and `gather_cv_lines` reports a cell whose every candidate was refused as
# `ABSTAIN.NO_INK`, i.e. as an EMPTY PAGE. That is the exact fault
# `docs/breakthrough-2026-09-18-the-unit-of-enquiry.md` diagnoses and Sean
# identified unprompted: *"NO_INK shows me that we are discarding information
# that should be black and white."*
#
# ⚠️ IT CHANGES NOTHING `detect_stems` RETURNS. The candidates go out through
# an APPEND-ONLY out-parameter, never through the return value, because this
# file is on the path every stem arm in this repo proves faithful before it
# reports a delta (1,920 = 1,920 strokes on Litolff, 2,305 = 2,305 on
# Breitkopf). A flag-off difference here would break their instruments and
# read as their bug.
#
# ⚠️ THE REASON WORDS ARE THE CENSUS'S OWN, TO THE CHARACTER.
# `benchmarks/omr-stem-ink-2026-09/rejection_census.py` already replicates
# this chain component by component and ASSERTS per cell that its accepted set
# is identical to the real `detect_stems`, so its six categories are the
# measured vocabulary and this is the one spelling of them.
# `tools/omr/tests/test_vertical_runs.py` asserts each string appears in that
# file's source -- two copies of a vocabulary is how they drift, and the
# anti-drift check is cheaper than the drift.
RUN_TOO_SHORT = "too SHORT (h < 2.0 spaces)"
RUN_TOO_TALL = "too TALL (h > 8.0 spaces)"
RUN_TOO_WIDE = "too WIDE (w > 0.6 spaces)"
RUN_AT_CELL_EDGE = "at a CELL EDGE (0.8 spaces)"
RUN_TOO_LITTLE_AREA = "too little AREA"
RUN_ASPECT = "ASPECT < 3:1"

#: ⚠️ THE SEVENTH OUTCOME, AND IT IS NOT ONE OF THE SIX. `_drop_paired_strokes`
#: runs AFTER the range filters, over the set that already passed all of them,
#: so a candidate it drops was ACCEPTED by every dimension bound and refused by
#: a RELATION to its neighbour. The census names it separately for the same
#: reason ("a component WAS accepted (pair rule dropped it)") and pooling the
#: two would hide that this rejection is the only one a single candidate's own
#: measurements cannot explain.
RUN_PAIRED = "PAIRED with a neighbour (the accidental rule)"

#: What a candidate that survived everything is called.
RUN_ACCEPTED = "accepted"

#: Every outcome, in the order the chain produces them. ⚠️ An outcome NOT in
#: this tuple is a drift in `detect_stems`' filter chain and the test fails.
RUN_OUTCOMES = (
    RUN_ACCEPTED,
    RUN_TOO_SHORT,
    RUN_TOO_TALL,
    RUN_TOO_WIDE,
    RUN_AT_CELL_EDGE,
    RUN_TOO_LITTLE_AREA,
    RUN_ASPECT,
    RUN_PAIRED,
)

#: The six DIMENSION bounds, apart from the relational one. §9 of
#: `docs/proposal-2026-09-18-boxing-is-a-decision.md` is the argument that all
#: six are size windows on an object the engraver varies on purpose -- *"length
#: is helpful in all of them except stems"* -- so a consumer that wants to ask
#: "how much of this population is refused BY DIMENSION" needs them named as a
#: group rather than enumerated by hand at the call site.
RUN_DIMENSION_REASONS = (
    RUN_TOO_SHORT, RUN_TOO_TALL, RUN_TOO_WIDE,
    RUN_AT_CELL_EDGE, RUN_TOO_LITTLE_AREA, RUN_ASPECT,
)


@dataclass(frozen=True)
class VerticalRunCandidate:
    """One connected component of the vertical opening, with its fate.

    ⚠️ THE BOX IS `[x, y, w, h]` IN CANONICAL CELL COORDINATES -- the same
    spelling `Q.STEM.value` uses, and DELIBERATELY not corners. Three
    mutually-disagreeing box conventions exist in one record
    (`Q.GLYPH_BOX.value` is `[name, x, y, w, h]`, `Q.INK`'s canonical box is
    CORNERS, `Q.STEM.value` is `[x, y, w, h]`) and reading one as another gives
    a NEGATIVE width and a clean believable zero. ⚠️ `Q.INK`'s key is named
    here WITHOUT its leaf spelling on purpose: `wiring.py` credits a detail key
    by leaf name matched anywhere under `tools/`, so a comment that spells it
    closes that key's open gap entry. The fields are named `w`/`h` rather than `x1`/`y1`
    so the convention is unmistakable at every read site.

    `outcome` is one of `RUN_OUTCOMES`. It is a fact about WHICH FILTER FIRED,
    not a name for the ink: a refused candidate is not thereby "not a stem",
    and an accepted one is not thereby a stem. That distinction is the whole
    point of recording the population.
    """
    x: int
    y: int
    w: int
    h: int
    area: int
    outcome: str
    line_spacing: float

    @property
    def accepted(self) -> bool:
        return self.outcome == RUN_ACCEPTED

    @property
    def width_spaces(self) -> float:
        return self.w / self.line_spacing if self.line_spacing > 0 else 0.0

    @property
    def height_spaces(self) -> float:
        return self.h / self.line_spacing if self.line_spacing > 0 else 0.0


def _meets_a_notehead(stroke, heads) -> bool:
    """Does this stroke's box overlap any of `heads`?

    `heads` are `(x, y, w, h)` in CANONICAL CELL coordinates — the same frame
    and the same spelling `LineDetection` uses. ⚠️ Three mutually-disagreeing
    box conventions exist in this repo (`Q.GLYPH_BOX.value` is
    `[name, x, y, w, h]`, `Q.INK`'s canonical box is CORNERS, `Q.STEM.value`
    is `[x, y, w, h]`) and reading one as another gives a negative width and a
    clean believable zero, so the caller converts and this does not guess.
    """
    sx0 = stroke.x_canonical
    sx1 = sx0 + stroke.width_canonical
    sy0 = stroke.y_canonical
    sy1 = sy0 + stroke.height_canonical
    for hx, hy, hw, hh in heads:
        if min(sx1, hx + hw) - max(sx0, hx) > 0 \
                and min(sy1, hy + hh) - max(sy0, hy) > 0:
            return True
    return False


def _drop_paired_strokes(stems, line_spacing: float, gap: float,
                         min_overlap: float, heads=None):
    """Reject vertical strokes that come in PAIRS, which stems do not.

    A sharp and a natural are each built from two parallel verticals about half
    a staff space apart and roughly two spaces tall — which is to say, they look
    exactly like a pair of short stems, and `detect_stems` was reporting them as
    such. Measured against 14 hand-counted cells, they were most of the error:
    summed |error| 60, and on the two Mahler cells the count was 16 and 14
    against a truth of 5 and 3.

    A stem is single. Two noteheads a second apart share one stem rather than
    standing side by side, and successive notes are set further apart than an
    accidental's own strokes, so the pair is the accidental's signature.

    The gap is bounded by the notation on both sides: wider than the ~0.5-0.7
    staff spaces between a sharp's strokes, narrower than the spacing between
    consecutive notes. Both members of a pair are dropped, since neither is a
    stem.

    ⚠️⚠️ THAT LAST PREMISE IS FALSE ON A DENSE LOW-RES ORCHESTRAL PLATE, and
    `heads` is the narrowing. Measured on Litolff Beethoven 5 pp.1-4, of the
    80 deleted strokes that carry a detected notehead **62 (77.5%) were paired
    with ANOTHER stroke that also carries one** — successive notes ARE set as
    close as an accidental's own strokes there, and the rule eats both of them.
    `heads` (canonical `(x, y, w, h)` notehead boxes) turns the rule into: a
    stroke that MEETS A NOTEHEAD is a stem and is kept, and a pair is dropped
    only where NEITHER member meets one. ⚠️ `heads=None` — the default, and
    what every caller that does not opt in passes — leaves the relation exactly
    as it has always been, to the stroke.

    ⚠️⚠️ THE GATE IS ON THE SUBJECT ONLY, AND THE OTHER FORM IS WORSE — this
    was found by a unit test, not by review. A stroke on a head is never
    dropped, so it can never be condemned and the 62 are safe whichever way
    the PARTNER is treated; what the partner rule decides is a different case.
    Excluding on-head strokes as partners too (the form
    `benchmarks/omr-stem-pair-rule-2026-09`'s `probe_proposed_gate.py`
    measured) means an accidental's stroke standing beside a real stem loses
    its only partner and SURVIVES as a false stem. Keeping them as partners
    drops it, which is the shipped rule still doing its job. The three cases,
    all of them tested:

      * both on a head (two stems)                -> both kept  (the 62)
      * one on a head (a stem beside a sharp)     -> stem kept, stroke dropped
      * neither on a head (a real accidental)     -> both dropped, unchanged
    """
    if line_spacing <= 0 or len(stems) < 2:
        return list(stems)
    max_dx = line_spacing * gap
    centres = [s.x_canonical + s.width_canonical / 2.0 for s in stems]
    tops = [float(s.y_canonical) for s in stems]
    bottoms = [t + s.height_canonical for t, s in zip(tops, stems)]
    # ⚠️ `None` and `[]` MUST NOT BE THE SAME THING HERE. `None` is *no gate*
    # (the shipped relation); an empty list is *the gate is on and this cell
    # holds no detected notehead*, which under the gate condemns nothing
    # differently but is a different claim, and a `heads or []` would silently
    # convert the first into the second.
    on_head = ([False] * len(stems) if heads is None
               else [_meets_a_notehead(s, heads) for s in stems])

    kept = []
    for i, stem in enumerate(stems):
        paired = False
        if heads is not None and on_head[i]:
            kept.append(stem)
            continue
        for j in range(len(stems)):
            if i == j or abs(centres[i] - centres[j]) > max_dx:
                continue
            overlap = min(bottoms[i], bottoms[j]) - max(tops[i], tops[j])
            if overlap <= 0:
                continue
            shorter = min(bottoms[i] - tops[i], bottoms[j] - tops[j])
            if overlap / max(1.0, shorter) >= min_overlap:
                paired = True
                break
        if not paired:
            kept.append(stem)
    return kept


def detect_stems(
    cell,
    *,
    min_height_lines: float = 2.0,
    max_height_lines: float = STEM_MAX_HEIGHT_LINES,
    max_width_lines: float = 0.6,
    accidental_pair_gap_lines: float = 0.9,
    accidental_pair_overlap: float = 0.6,
    drop_accidental_pairs: bool = True,
    enable_stroke_reader: bool | None = None,
    enable_notehead_gate: bool | None = None,
    noteheads: Sequence | None = None,
    candidates_out: list | None = None,
) -> list[LineDetection]:
    """Find stem-like vertical ink runs in `cell`.

    Algorithm:
      1. Pick the cleanest source image — staff-removed if available.
      2. Threshold → binary ink mask.
      3. Vertical morphological opening with a (line_spacing × 1)
         structuring element. This isolates ink runs that are tall and
         narrow — everything else (noteheads, beams, accidentals) gets
         erased.
      4. Connected components on the result. Each component is a candidate
         stem.
      5. Filter:
           - height between min/max_height_lines × line_spacing
             (rejects too-short noise, and verticals long enough to be a
             barline or bracket rather than a stem — see
             `STEM_MAX_HEIGHT_LINES`, which is where the two populations
             separate)
           - width ≤ max_width_lines × line_spacing
           - not at the cell edges (rejects measure-boundary barlines)
           - aspect ratio ≥ 3:1 vertical (rejects square noise blobs)
      6. Drop strokes that come in PAIRS — see `_drop_paired_strokes`. A sharp
         and a natural are each two parallel verticals about half a staff space
         apart and about two spaces tall, indistinguishable from a pair of short
         stems by any of the filters above.

    Returns LineDetection objects in canonical-cell coordinates.

    `enable_stroke_reader` overrides `OMR_STEM_STROKE` for a test or an arm;
    `None` (the default) reads the flag, which is OFF, so the returned set is
    exactly what it has always been. See step 7 at the foot of this function
    and `_column_stroke_bands`.

    ⚠️ `noteheads` + `enable_notehead_gate` NARROW STEP 6, and take TWO things
    to fire: the DATA (canonical `(x, y, w, h)` boxes, which only a caller
    holding the detector's output can supply) and the FLAG
    (`OMR_STEM_NOTEHEAD_GATE`, default OFF; `enable_notehead_gate` overrides
    it for a test or an arm). Either missing and the pair rule runs exactly as
    it always has, to the stroke — which is why the legacy `transcribe` path,
    whose `detect_lines(cell)` passes no detections, is unchanged BY
    CONSTRUCTION rather than by a second decision. See
    `STEM_NOTEHEAD_GATE_ENV` for what it is worth and what it costs.

    ⚠️⚠️ `candidates_out`, WHEN GIVEN, IS APPENDED WITH EVERY COMPONENT THE
    OPENING PRODUCED -- accepted AND refused, each carrying the FIRST filter
    that refused it (`VerticalRunCandidate`, `RUN_OUTCOMES`). It is the only
    way the refused population leaves this function, and it leaves through a
    SIDE CHANNEL rather than the return value **on purpose**: the returned
    list is what every stem arm in this repo proves faithful before reporting
    a delta, and the stroke reader's own comment below says why a difference
    here would read as somebody else's bug. Passing it changes no filter, no
    order and no returned stroke; omitting it costs nothing at all. It is
    ADDITIVE in exactly the sense the stroke reader is not -- the stroke
    reader adds STROKES, this adds only a record of what was already
    happening.

    Measured against 14 hand-counted cells across four scores, the pair rule
    takes summed |error| from 60 to 24, and against the LilyPond reference
    sheet from +7/+8/+5/+2 to -1/0/+1/0 on a truth of 48. Raising the height
    floor instead was tried and is worse (36) AND fails asymmetrically: it
    scores well on Boléro while destroying keyboard music, where stems in
    beamed groups are legitimately short (one WTC cell holds 15 stems and a
    2.8-space floor finds 5).
    """
    if cell is None:
        return []
    src = (
        cell.image_no_staff
        if getattr(cell, "image_no_staff", None) is not None
        else cell.image
    )
    if src is None or src.size == 0:
        return []

    line_spacing = _staff_line_spacing(cell)
    if line_spacing <= 1.0:
        return []

    cell_w = cell.width
    edge_margin = max(int(round(line_spacing * 0.8)), 12)

    ink = _binary_ink(src)
    # Vertical structuring element: width 1, height just under the shortest
    # stem this function will accept.
    #
    # It used to be one line spacing, which is exactly a notehead's height — so
    # a notehead survived the opening, stayed joined to its own stem, and the
    # component came out as wide as the notehead. The width filter below then
    # threw the stem away along with it. That stayed hidden while staff-line
    # removal was a no-op, because an un-removed staff line broke the notehead
    # up for us; fixing removal exposed it, and Mahler 5 p.11 fell from 178
    # stems to 145. Measured against the LilyPond reference sheet (which knows
    # its own stem count), the 1.0 kernel scored 35 of 48 stems at 0.29 staff
    # spaces of line thickness and 11 of 48 at 0.39; at this height, 53 and 50.
    #
    # The principle sets the value: a component shorter than `min_height_lines`
    # is rejected a few lines below regardless, so erasing it here costs
    # nothing, and the taller the kernel the more non-stem ink it clears first.
    # So take it just under that floor — the margin absorbs a stem sitting
    # exactly at the limit and the pixel or two rasterisation moves it.
    kernel_h = max(3, int(round(line_spacing * min_height_lines * STEM_KERNEL_MARGIN)))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_h))
    opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)

    # Connected components
    num, _, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
    out: list[LineDetection] = []
    min_h = int(round(line_spacing * min_height_lines))
    max_h = int(round(line_spacing * max_height_lines))
    max_w = max(3, int(round(line_spacing * max_width_lines)))
    # ⚠️ The refused population is recorded and the CONTROL FLOW IS UNCHANGED.
    # Each `continue` below still fires exactly where it did; what is new is a
    # `_note` call in front of it, appending to `candidates_out` when one was
    # supplied and doing nothing at all when it was not. Rewriting this as a
    # chain that computes a reason and then branches on it would put the
    # recording INSIDE the decision, which is the one change that could move a
    # stroke -- so the reason is derived beside the test that already exists.
    def _note(x, y, w, h, area, outcome):
        if candidates_out is not None:
            candidates_out.append(VerticalRunCandidate(
                x=int(x), y=int(y), w=int(w), h=int(h), area=int(area),
                outcome=outcome, line_spacing=float(line_spacing)))

    for i in range(1, num):  # skip background (label 0)
        x, y, w, h, area = stats[i]
        # Range filters
        if h < min_h or h > max_h:
            _note(x, y, w, h, area,
                  RUN_TOO_SHORT if h < min_h else RUN_TOO_TALL)
            continue
        if w > max_w:
            _note(x, y, w, h, area, RUN_TOO_WIDE)
            continue
        # Edge filter — barlines live at the cell boundaries.
        if x < edge_margin or x + w > cell_w - edge_margin:
            _note(x, y, w, h, area, RUN_AT_CELL_EDGE)
            continue
        if area < max(4, line_spacing * 0.5):
            _note(x, y, w, h, area, RUN_TOO_LITTLE_AREA)
            continue
        if h / max(1, w) < 3.0:
            _note(x, y, w, h, area, RUN_ASPECT)
            continue
        _note(x, y, w, h, area, RUN_ACCEPTED)
        out.append(LineDetection(
            smufl_name="stem",
            category="stem",
            x_canonical=int(x),
            y_canonical=int(y),
            width_canonical=int(w),
            height_canonical=int(h),
            confidence=1.0,
        ))
    if drop_accidental_pairs:
        before = out
        # ⚠️ TWO CONDITIONS, AND THE DATA IS ONE OF THEM. `gate_heads` stays
        # `None` — the shipped relation, byte-identical — unless the flag is on
        # AND a caller supplied notehead boxes. A flag on with no boxes is not
        # an empty gate, it is NO gate: see `_drop_paired_strokes`, where
        # `None` and `[]` are deliberately different.
        if enable_notehead_gate is None:
            enable_notehead_gate = stem_notehead_gate_enabled()
        gate_heads = (list(noteheads) if enable_notehead_gate
                      and noteheads is not None else None)
        out = _drop_paired_strokes(
            out, line_spacing, accidental_pair_gap_lines,
            accidental_pair_overlap, heads=gate_heads,
        )
        # ⚠️ RE-STAMPED, NOT RE-DERIVED. The pair rule runs over the SET, so
        # whether a candidate is paired cannot be known at the moment that
        # candidate is measured -- and re-implementing the relation here to
        # decide who was dropped is the drift `rejection_census.py` exists to
        # refuse. `_drop_paired_strokes` returns the SURVIVORS, so the dropped
        # set is a set difference over identity, and the row that was already
        # written `accepted` is replaced by one written `RUN_PAIRED`.
        if candidates_out is not None and len(out) != len(before):
            kept_boxes = {(s.x_canonical, s.y_canonical,
                           s.width_canonical, s.height_canonical)
                          for s in out}
            for i, cand in enumerate(candidates_out):
                if cand.outcome != RUN_ACCEPTED:
                    continue
                if (cand.x, cand.y, cand.w, cand.h) in kept_boxes:
                    continue
                candidates_out[i] = replace(cand, outcome=RUN_PAIRED)
    # ── `OMR_STEM_STROKE`: the column profile, ADDED, never substituted ──
    #
    # ⚠️ FLAG-OFF IS BYTE-IDENTICAL BY CONSTRUCTION, and that is load-bearing
    # rather than tidy: this file is on the path every arm of
    # `benchmarks/omr-stem-ink-2026-09/` proves faithful before it reports a
    # delta (783/783 cells, 1,920 = 1,920 strokes). A flag-off difference here
    # would break their instruments and read as their bug. Asserted directly:
    # a re-cut with the flag off reproduces the shared records stroke for
    # stroke, 1,920 = 1,920 on Litolff and 2,305 = 2,305 on Breitkopf, every
    # cell matching (`benchmarks/omr-stem-stroke-2026-09/stroke_arm.py`).
    #
    # ⚠️ It runs AFTER the pair rule so the shipped set is untouched, which
    # also means the added bands DO NOT get that rule. That is what was
    # measured and it is therefore what ships; whether the pair rule should
    # also police them is an open question and is NOT answered here.
    if enable_stroke_reader is None:
        enable_stroke_reader = stem_stroke_enabled()
    if enable_stroke_reader:
        for band in _column_stroke_bands(
                ink, line_spacing, cell_w,
                min_height_lines=min_height_lines,
                max_height_lines=max_height_lines,
                max_width_lines=max_width_lines):
            if any(_boxes_overlap(band, s) for s in out):
                continue
            out.append(band)
    return out


def _boxes_overlap(a, b) -> bool:
    return (min(a.x_canonical + a.width_canonical,
                b.x_canonical + b.width_canonical)
            - max(a.x_canonical, b.x_canonical) > 0
            and min(a.y_canonical + a.height_canonical,
                    b.y_canonical + b.height_canonical)
            - max(a.y_canonical, b.y_canonical) > 0)


# ---------------------------------------------------------------------------
# Beam detection
# ---------------------------------------------------------------------------


def _stacked_bar_bands(labels, label: int, x: int, y: int, w: int, h: int,
                       max_samples: int = 48) -> tuple[int, list[tuple[int, int]] | None]:
    """How many beam bars are stacked here, AND where each one actually is.

    Returns `(n_bars, bands)`. `bands` is one `(top, bottom)` per bar, in the
    component's own frame (add `y` for canonical), or **None** where the mask
    cannot say — in which case the caller falls back to dividing the box evenly,
    which is what this function's count alone used to force it to do.

    THE COUNT AND THE POSITIONS COME FROM THE SAME PASS, and that is the whole
    point. The run-start mask below already knows where every bar is; reducing
    it to a count threw those positions away, and `detect_beams` then FABRICATED
    them by dividing the component's height into `n_bars` equal slices. That is
    wrong for exactly the case the count exists to handle — a SLOPED stack,
    whose box is far taller than its bars and whose bars do not divide it
    evenly.

    Measured over 2,124 components on 31 pages — the 20-row scan gate and the
    11 engraved fixtures, `benchmarks/omr-beam-bar-bands-2026-09/`: **51
    components read more than one bar, every one on a scan and every one a
    two-bar stack.** The fabricated band sits a median 0.106 staff spaces from
    the measured one at its worse edge, worst case 0.743, and 18 of the 102 bar
    placements are displaced past the 0.35-space clustering tolerance. The band
    EDGE is what `rhythm._beams_attached_to_stem` reads for its end-window test;
    the band CENTRE is what it clusters into levels.

    ⚠️ **Through the real pipeline this changes 55 durations on 9 scan pages** —
    not the handful a bounding-box-sized repair sounds like. All 55 are a single
    beam level (42 longer, 13 shorter), no pitch moves and nothing is added or
    dropped.

    **Priced on the 20-row scan gate**, both arms on one merge base differing in
    this file alone: pooled OMR-NED 0.8441 -> 0.8440, **-37 edits**, of which
    +6 is the gate's documented nondeterminism on the row CLAUDE.md names, so
    **-43 is attributable**. 10 of the 11 rows carrying no multi-bar component
    are identical to the edit. `wrong note` -21 is where it lands, not
    `wrong flag/beam` (+1) — the expected signature, since that bucket counts
    notes the aligner would not PAIR and a duration is what usually stops it.

    ⚠️ **Read that as "does not harm", not as "helps".** ~8 edits per misread
    rhythm would predict hundreds from 55 corrections; 21 is what moves. Most of
    the 55 bought nothing measurable AND THAT IS NOT EVIDENCE THEY WERE WRONG:
    `entire measure insert/delete` is 39.6% of this corpus, and a correct local
    fix inside a bar already charged whole-plus-whole is invisible by
    construction. The metric cannot separate "useless" from "right, and the bar
    was already billed".

    ⚠️ **And the trade is two-sided in one place, which is worth knowing before
    widening this.** An excursion band is the right answer for the EDGE test and
    a poor one for the CENTRE: a steeply sloped bar's centre is a y its ink
    passes through only in the middle, so two overlapping excursions draw their
    centres together and the level clustering merges them. Measured, that flips
    4 of the 51 from two levels to one and 1 from one to two — bounded, and a
    minority of the direction skew, but real. A `LineDetection` carries only `y`
    and `height`, so its centre is derived and both consumers cannot be
    satisfied at once; the principled next step is a band measured at the STEM's
    own column rather than globally, which is a design change and not this
    repair.

    ⚠️ **A single-bar component is returned with `bands=None` deliberately.** It
    has nothing to place — the box IS the bar — so the caller's fallback
    reproduces the old output exactly. That is 2,022 of the 2,073 components and
    every component on every engraved page, so the fix is inert there BY
    CONSTRUCTION rather than by measurement.

    A band is the bar's whole vertical EXCURSION — min top and max bottom over
    every column that reads the stack cleanly — not a single column's reading,
    because a sloped bar is at its band's top where the group ends high and at
    its bottom where it ends low. `rhythm._beams_attached_to_stem` documents that it measures reach
    to the band and not to the centre for precisely this reason; this supplies
    the band it assumes it is being given.

    Only columns showing exactly `n_bars` runs contribute. A column crossing a
    stem or a notehead shows more, and one clipping the end of a sloped stack
    shows fewer; in neither is it known which run is which bar, so neither may
    place one.
    """
    roi = labels[y:y + h, x:x + w] == label
    if roi.size == 0:
        return 1, None
    step = max(1, roi.shape[1] // max_samples)
    cols = roi[:, ::step]
    # A run starts where ink appears under paper — count those per column.
    above = np.vstack([np.zeros((1, cols.shape[1]), dtype=bool), cols[:-1]])
    starts = cols & ~above
    per_column = starts.sum(axis=0)
    counts = per_column[per_column > 0]
    if counts.size == 0:
        return 1, None
    n_bars = max(1, int(np.median(counts)))
    if n_bars == 1:
        # Nothing to place, and nothing that could differ from the box.
        return 1, None

    # ⚠️ The BANDS are gathered over EVERY column, not over the strided sample
    # the count used. Two separate reasons, and neither is a tuning choice:
    #
    #   * the count must not move. Widening its sample could shift the median,
    #     and that median is the part of this function with an independent hand
    #     count behind it (51 of 51 real components agreed);
    #   * a band is an EXCURSION, so it is decided by the extreme columns, and a
    #     stride of `w // 48` steps straight over them. On the fixture in
    #     `test_line_detection_beam_bands.py` the strided sample stops 7 columns
    #     short of the end and loses the last 1 px of rise — small here, but it
    #     is a systematic under-reach that grows with the slope, and there is no
    #     reason to accept it when the count is already settled.
    all_starts = roi & ~np.vstack([np.zeros((1, roi.shape[1]), dtype=bool), roi[:-1]])
    all_ends = roi & ~np.vstack([roi[1:], np.zeros((1, roi.shape[1]), dtype=bool)])
    runs_per_column = all_starts.sum(axis=0)

    tops = [None] * n_bars
    bottoms = [None] * n_bars
    for j in np.flatnonzero(runs_per_column == n_bars):
        start_rows = np.flatnonzero(all_starts[:, j])
        end_rows = np.flatnonzero(all_ends[:, j])
        if start_rows.size != n_bars or end_rows.size != n_bars:
            continue
        for k in range(n_bars):
            t, b = int(start_rows[k]), int(end_rows[k])
            tops[k] = t if tops[k] is None else min(tops[k], t)
            bottoms[k] = b if bottoms[k] is None else max(bottoms[k], b)

    if any(t is None for t in tops):
        # No column read the stack cleanly — the caller keeps the old division
        # rather than placing a bar on evidence that is not there.
        return n_bars, None
    return n_bars, [(tops[k], bottoms[k]) for k in range(n_bars)]


def _stacked_bar_count(labels, label: int, x: int, y: int, w: int, h: int,
                       max_samples: int = 48) -> int:
    """How many beam bars are stacked here, counted as vertical ink runs.

    Not from the bounding box's height, which was the old approach and is wrong
    for the commonest case: a SLOPED beam. A beam over a rising figure has a
    box far taller than the beam is thick — measured on the reference sheet,
    sloped beams fill only 43-46% of their box against 95% for a level one — so
    dividing the box height by a beam's thickness reported a single sloped bar
    as two, three or eight.

    A column through the component crosses each bar exactly once, whatever the
    slope, so counting runs in a column counts bars. The median over sampled
    columns keeps a stem or a notehead crossing the beam from swaying it.

    THE COLUMN MUST BE THIS COMPONENT'S OWN INK, which is why the labels go in
    rather than the opened image. A sloped beam's bounding box is far taller
    than the bar, so it reaches over its neighbours: measured on Brahms's Violin
    2, the primary beam's box (canonical y 1082-1203, 36% filled) covers the
    lower part of the SECONDARY beam beside it, and 26 of its 51 sampled columns
    then showed two runs where the component has one bar. The median came out 2,
    the box was cut into two bands, and a dotted eighth was read as a dotted
    sixteenth. `_attached_stem_count` below already reads the label mask for the
    same reason.

    The count now comes from `_stacked_bar_bands`, which runs this same pass and
    keeps the positions as well. Counting logic is unchanged and lives in one
    place; this wrapper is the count-only view of it.
    """
    return _stacked_bar_bands(labels, label, x, y, w, h, max_samples)[0]


def _attached_stem_count(labels, label: int, stems, x: int, y: int, w: int, h: int,
                         line_spacing: float, tolerance: float, end_reach: float) -> int:
    """How many stems END at this component — which is what makes it a beam.

    A beam exists to join stems, and it joins them at their ENDS. Nothing else
    that draws a long horizontal line in a score does that: a slur or tie runs
    between noteheads, a ledger line sits at a notehead's middle with at most
    one stem beside it, and staff-line residue has no stem at all. Measured on
    Mahler 5 p.11, those three were essentially the entire beam count — one
    cell of half notes under slurs was reporting 27 beams.

    The comparison is made against the component's ink IN THE STEM'S OWN COLUMN
    rather than against its bounding box. A sloped beam's box reaches far above
    and below the bar itself, so box edges put the far stem out of range and a
    sloped double beam lost its lower bar.
    """
    found = 0
    x_lo = x - line_spacing * 0.4
    x_hi = x + w + line_spacing * 0.4
    for s in stems:
        sx = s.x_canonical + s.width_canonical / 2.0
        if not (x_lo <= sx <= x_hi):
            continue
        # Clamp only for the lookup: a beam may stop a hair short of the stem
        # that hangs from its end.
        sx = min(max(int(round(sx)), x), x + w - 1)
        column = labels[y:y + h, sx] == label
        if not column.any():
            continue
        rows = np.flatnonzero(column)
        local_top = y + int(rows[0])
        local_bottom = y + int(rows[-1])
        top = float(s.y_canonical)
        bottom = top + s.height_canonical
        # The stem must meet the beam: end at it, or run through it. A
        # SECONDARY beam is run through rather than ended at — with a double
        # beam the stems stop at the outer bar and cross the inner one — so
        # requiring an end here would find the primary bar of every group and
        # discard the secondary.
        meets = (top - tolerance) <= local_bottom and (bottom + tolerance) >= local_top
        if not meets:
            continue
        # ...but the stem's END still has to be in the neighbourhood, which is
        # what keeps a long horizontal residue INSIDE the staff from being
        # adopted by every stem that happens to cross it. A secondary beam sits
        # less than a bar-pitch from the primary, so the reach only has to
        # cover a stack of them.
        nearest_end = min(abs(top - local_top), abs(top - local_bottom),
                          abs(bottom - local_top), abs(bottom - local_bottom))
        if nearest_end <= end_reach:
            found += 1
    return found


def detect_beams(
    cell,
    *,
    stems: list[LineDetection] | None = None,
    min_width_lines: float = 1.5,
    min_height_lines: float = 0.10,
    max_height_lines: float = 2.5,
    min_height_absolute: int = 2,
    stem_attach_tolerance_lines: float = 1.0,
    stem_end_reach_lines: float = 2.5,
    stem_anchor_min_height_lines: float = 2.8,
    min_attached_stems: int = 2,
) -> list[LineDetection]:
    """Find beams in `cell`.

      1. Pick the cleanest source — staff-removed if available.
      2. Horizontal morphological opening → candidate horizontal runs.
      3. Connected components, filtered on width, height and aspect.
      4. Keep only components that at least `min_attached_stems` stems END at.
      5. Count the stacked bars in each by vertical ink runs, not box height.

    Steps 4 and 5 are what this function got wrong for a long time, and the
    LilyPond reference sheet (`benchmarks/omr-phase4-lines/`) is what made it
    visible: against a known 14 beam bars it reported 51, and against a known
    12 on one staff it reported 41.

    Without step 4 the count is dominated by things that are horizontal but are
    not beams — slurs, ties, ledger lines, staff-line residue. Requiring two
    stem ends removes all four classes at once without a rule per class:
    measured on the reference sheet, error against ground truth falls from 157
    to 3 summed over four staff-line thicknesses, and it holds under
    degradation down to a 150 DPI render.

    `max_height_lines` is 2.5 rather than 1.0 because both a stack of bars and
    a sloped bar are legitimately taller than one beam. At 1.0 an entire
    measure of sixteenths — two bars per group — was rejected outright and
    scored 0 against a known 8.
    """
    if cell is None:
        return []
    src = (
        cell.image_no_staff
        if getattr(cell, "image_no_staff", None) is not None
        else cell.image
    )
    if src is None or src.size == 0:
        return []

    line_spacing = _staff_line_spacing(cell)
    if line_spacing <= 1.0:
        return []

    if stems is None:
        stems = detect_stems(cell)

    ink = _binary_ink(src)
    kernel_w = max(3, int(round(line_spacing * 1.5)))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, 1))
    opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)

    num, labels, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
    out: list[LineDetection] = []
    min_w = int(round(line_spacing * min_width_lines))
    # Absolute pixel floor on beam height is critical at orchestral cell
    # resolution where `line_spacing × 0.10` collapses to 2-3 px.
    min_h = max(min_height_absolute, int(round(line_spacing * min_height_lines)))
    max_h = max(3, int(round(line_spacing * max_height_lines)))
    tolerance = line_spacing * stem_attach_tolerance_lines
    end_reach = line_spacing * stem_end_reach_lines

    # Only FULL-LENGTH stems may anchor a beam. `detect_stems` accepts anything
    # from 2 staff spaces up, and at that floor it also picks up the vertical
    # strokes of sharps and naturals, which are about that tall. Those false
    # stems were lending their two-stem quorum to whatever horizontal ink lay
    # near them — on a hand-labeled Mahler cell holding no beams at all, five
    # ledger lines were reported as beams because the accidentals beside them
    # counted. A beam hangs off a real stem: conventionally 3.5 staff spaces,
    # shortened in beamed groups but not to an accidental's height.
    #
    # This filters only the ANCHOR set. `detect_stems`' own output is untouched,
    # because raising its floor would drop about 30% of the stems on real pages
    # and there is no stem ground truth to say whether those are false.
    anchors = [
        s for s in stems
        if s.height_canonical >= line_spacing * stem_anchor_min_height_lines
    ]

    for i in range(1, num):
        x, y, w, h, area = stats[i]
        if w < min_w:
            continue
        if h < min_h or h > max_h:
            continue
        if area < max(6, line_spacing):
            continue
        if w / max(1, h) < 2.0:
            continue
        attached = _attached_stem_count(
            labels, i, anchors, x, y, w, h, line_spacing, tolerance, end_reach
        )
        if attached < min_attached_stems:
            continue

        # Where the bars ARE, not where an even division would put them. A
        # stack's bars do not divide its box evenly — the box is sized by the
        # slope, the bars by the engraving — and downstream those coordinates
        # become durations: `rhythm._beams_attached_to_stem` reads the band
        # edges for its end-window test and the band centres for its level
        # clustering. `bands is None` means the mask could not say, and the
        # even division below is then exactly what shipped before.
        n_bars, bands = _stacked_bar_bands(labels, i, x, y, w, h)
        if bands is None:
            sub_h = max(1, h // n_bars)
            placed = [(int(y + k * (h / n_bars)), int(sub_h))
                      for k in range(n_bars)]
        else:
            placed = [(int(y + top), max(1, int(bottom - top + 1)))
                      for top, bottom in bands]
        for bar_y, bar_h in placed:
            out.append(LineDetection(
                smufl_name="beam",
                category="structural",
                x_canonical=int(x),
                y_canonical=bar_y,
                width_canonical=int(w),
                height_canonical=bar_h,
                confidence=1.0,
            ))
    return out


# ---------------------------------------------------------------------------
# Convenience: detect both at once
# ---------------------------------------------------------------------------


def detect_lines(cell, *, candidates_out: list | None = None,
                 noteheads: Sequence | None = None
                 ) -> dict[str, list[LineDetection]]:
    """Return {'stems': [...], 'beams': [...]}.

    Stems are found first and handed to the beam pass, which needs them to tell
    a beam from a slur, a tie or a ledger line — and computing them once here
    keeps that from costing a second detection.

    `candidates_out` is forwarded to `detect_stems` unchanged; see there. It
    is NOT forwarded to `detect_beams`, which has its own filter chain and
    whose refused population is a separate, unmeasured question.

    `noteheads` is forwarded the same way — the notehead gate on the pair
    rule, off unless `OMR_STEM_NOTEHEAD_GATE` is on AND boxes are supplied.
    ⚠️ It reaches `detect_beams` only THROUGH the stems, because that pass
    takes the stem set as its input: so the gate can change which beams are
    read, and any beam delta on a gated arm is this and not a beam change.
    """
    stems = detect_stems(cell, candidates_out=candidates_out,
                         noteheads=noteheads)
    return {
        "stems": stems,
        "beams": detect_beams(cell, stems=stems),
    }
