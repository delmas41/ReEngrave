"""Eighth and quarter rests the detector never boxed -- ROADMAP 2.99.

2.96 (FINDINGS `omr-bar-sum-holdout-2026-09` §2.96) found 448 held bars that
hold rest-shaped ink no box accounts for, and Sean's tiles 7-9 confirmed that
the ink is real: three of three bars hold an eighth rest the detector never
drew -- BUT on tile 7 the first marked piece was a FLAT, not the rest. Shape
alone over-counts; the mark has to be read on its shape AND its place.

## Stage

ADJUDICATE: *what does this ONE thing mean, on what evidence?* The evidence is
the CLUSTER'S OWN, read by GATHER (`Q.UNBOXED_REST_SHAPE`): its width and
height in staff spaces, the local staff step of its centre, how much of it a
standing detector box covers (and of what class), the share of its height one
pixel column fills, and the nearest notehead to its right.

⚠️⚠️ **NO BAR IS CONSULTED, AND THAT IS THE RULE** (CLAUDE.md §2 rule 8, §10:
*"two witnesses off the same raster fall silent together"*). That the bar is
short by exactly an eighth is not a second witness that the ink is a rest: the
bar's sum is made of the same readings the mark was lost from. The registry
declares no meter, event, duration or voice quantity, so none can be read, and
a test asserts it. A short bar may at most RANK between rest candidates the
shape already allows, in INFER, labelled -- there is none, the shape admits
one candidate. If the shape cannot tell, this ABSTAINS and the bar stays held
out (2.8).

## What it decides

* `"eighth"` / `"quarter"` -- the ink has the rest's shape for that value,
  hangs on the middle of the staff, carries no vertical stroke (a flat, a
  sharp and a natural are a stem with a bowl), has no notehead just to its
  right that it could be the accidental of, lies outside the clef/key/meter
  header, and no standing box covers it.
* `False` -- the ink is already read as a standing glyph (a rest box is the
  positive control, an accidental box the negative one), or it carries a
  vertical stroke.
* abstain -- anything else: partial cover, a head beside it, in the header,
  a shape between the windows.

EVALUATE's `size_unboxed_rest` gives a decided rest its length; EXPORT writes
it as a rest.
"""
from __future__ import annotations

from typing import Any, Dict

from ..adjudicate import Evidence, Mode, Ruling, decision
from ..record import Kind, Q

#: Windows, in STAFF SPACES and bins, READ OFF the clusters the detector's OWN
#: standing boxes cover in the same records (FINDINGS 2.99, the controls
#: table): 17 standing `rest8th` (w 1.31-1.46, h 1.81-2.35, step 3.4-4.0,
#: mass_y 0.34-0.48), 81+ standing `restQuarter` (w 1.08-1.34, h 2.7-3.4,
#: step 4.4-5.0) and the flats/sharps beside them (a full-height stroke on
#: the LEFT). Wider than the measured spread, narrower than the neighbours.
EIGHTH_WIDTH_SPACES = (1.1, 1.6)
EIGHTH_HEIGHT_SPACES = (1.5, 2.5)
EIGHTH_STEP = (3.2, 4.4)
#: An eighth rest's ink sits in its UPPER half (the blob, then the tail).
EIGHTH_MAX_MASS_Y = 0.50
QUARTER_WIDTH_SPACES = (1.0, 1.45)
QUARTER_HEIGHT_SPACES = (2.65, 3.5)
QUARTER_STEP = (3.7, 5.3)
REST_MAX_PIECES = 3
#: `Q.UNBOXED_REST_SHAPE.column_profile` is the cluster's tallest ink column in
#: each of six equal-width slices, as a share of its height. A flat or a
#: natural is a stem with a bowl: the LEFT slices are (nearly) full and the
#: rest are not. A sharp is two such strokes. An eighth rest has no slice
#: above this on its left; a quarter rest peaks in the MIDDLE.
STROKE_SHARE = 0.9
EIGHTH_LEFT_BINS_MAX = 0.65     # the two left slices
EIGHTH_MAX_COLUMN_SHARE = 0.92
QUARTER_PEAK_SHARE = 0.85
#: A sharp or a natural is TWO strokes: its right slices fill again. A quarter
#: rest's right side is thin (0.09-0.63 on the 100 standing ones).
QUARTER_RIGHT_BIN_MAX = 0.65
QUARTER_FOURTH_BIN_MAX = 0.85
#: A quarter rest is followed by no notehead this close (0 of 100 standing ones
#: have one within 3 spaces), but an arpeggio line -- the same zigzag -- stands
#: against its chord. A head this near on the right makes the ink the wiggle
#: of a chord, not a rest.
QUARTER_HEAD_BESIDE_SPACES = 1.0
QUARTER_HEAD_BESIDE_DY_SPACES = 2.5
#: Covered by standing boxes by this much or more = already read; between the
#: two bounds = a claim this decision cannot see past.
COVERED_SHARE = 0.5
TOUCHED_SHARE = 0.1

@decision(
    quantity=Q.UNBOXED_INK_IS_A_REST,
    composed_from=(Q.UNBOXED_REST_SHAPE,),
    scope=Kind.GLYPH,
    wants=(Q.UNBOXED_REST_SHAPE,),
    subjects_from=Q.UNBOXED_REST_SHAPE,
    reasons=("rest8th_shape", "restQuarter_shape", "already_read_as_a_glyph",
             "stem_stroke_not_a_rest", "claimed_by_another_class",
             "in_the_header", "head_beside_it", "shape_cannot_tell",
             "no_ink_reading", "no_shape_reading"),
    mode=Mode.ADDITIVE,
)
def adjudicate_unboxed_ink_is_a_rest(ev: Evidence) -> Ruling:
    """Is this rest-sized cluster of unboxed ink an eighth or a quarter rest?

    See the module docstring: the mark's own shape and place, never the bar.
    """
    rows = ev.rows(Q.UNBOXED_REST_SHAPE)
    if not rows:
        return Ruling.abstain("no_shape_reading")
    row = rows[-1]
    d: Dict[str, Any] = row.detail or {}
    w, h = d.get("width_spaces"), d.get("height_spaces")
    step = d.get("staff_step")
    if w is None or h is None or step is None:
        return Ruling.abstain("no_shape_reading")
    detail = {k: d.get(k) for k in (
        "width_spaces", "height_spaces", "staff_step", "n_pieces", "fill",
        "max_column_share", "mass_y", "column_profile", "coverage",
        "covered_by", "right_head")}
    used = (row.id,)

    cover = d.get("coverage") or 0.0
    if cover >= COVERED_SHARE:
        return Ruling(value=False, reason="already_read_as_a_glyph",
                      used=used, detail=detail)
    if cover >= TOUCHED_SHARE:
        return Ruling.abstain("claimed_by_another_class", **detail)

    col, prof, mass_y = (d.get("max_column_share"), d.get("column_profile"),
                         d.get("mass_y"))
    if (col is None or not prof or len(prof) < 6 or mass_y is None
            or not d.get("n_pieces")):
        return Ruling.abstain("no_ink_reading", **detail)

    # A flat / natural: a full-height stroke on the LEFT and little else. (A
    # quarter rest peaks in the middle; an eighth rest has no full slice.)
    if (prof[0] >= 0.6 and prof[1] >= STROKE_SHARE
            and max(prof[2:]) < STROKE_SHARE
            and prof[1] >= max(prof[2:])):
        return Ruling(value=False, reason="stem_stroke_not_a_rest",
                      used=used, detail=detail)

    # The header (clef, key signature, meter) is ink nobody boxed: abstain
    # inside it, and where the first cell has no header box to measure from.
    if d.get("left_of_header") or (d.get("first_cell")
                                   and not d.get("header_known")):
        return Ruling.abstain("in_the_header", **detail)
    if d.get("touches_cell_edge") or (d.get("n_pieces") or 0) > REST_MAX_PIECES:
        return Ruling.abstain("shape_cannot_tell", **detail)

    eighth = (EIGHTH_WIDTH_SPACES[0] <= w <= EIGHTH_WIDTH_SPACES[1]
              and EIGHTH_HEIGHT_SPACES[0] <= h <= EIGHTH_HEIGHT_SPACES[1]
              and EIGHTH_STEP[0] <= step <= EIGHTH_STEP[1]
              and mass_y <= EIGHTH_MAX_MASS_Y
              and col <= EIGHTH_MAX_COLUMN_SHARE
              and max(prof[:2]) <= EIGHTH_LEFT_BINS_MAX)
    quarter = (QUARTER_WIDTH_SPACES[0] <= w <= QUARTER_WIDTH_SPACES[1]
               and QUARTER_HEIGHT_SPACES[0] <= h <= QUARTER_HEIGHT_SPACES[1]
               and QUARTER_STEP[0] <= step <= QUARTER_STEP[1]
               and max(prof[2], prof[3]) >= QUARTER_PEAK_SHARE
               and prof[4] <= QUARTER_FOURTH_BIN_MAX
               and prof[5] <= QUARTER_RIGHT_BIN_MAX)
    if eighth:
        return Ruling(value="eighth", reason="rest8th_shape", used=used,
                      detail=detail)
    head = d.get("right_head")
    if quarter and head and head.get("dx_spaces") is not None \
            and head["dx_spaces"] <= QUARTER_HEAD_BESIDE_SPACES \
            and abs(head.get("dy_spaces") or 0.0) <= QUARTER_HEAD_BESIDE_DY_SPACES:
        return Ruling.abstain("head_beside_it", **detail)
    if quarter:
        return Ruling(value="quarter", reason="restQuarter_shape", used=used,
                      detail=detail)
    return Ruling.abstain("shape_cannot_tell", **detail)
