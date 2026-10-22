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

from .. import margins as M
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
#: A rest has a body: the tallest ink column of the 140 standing Brahms rests
#: is at least 49% of their height. Ink with no column above this is a thin
#: stroke -- the END OF A SLUR (Sean, tile 10 of 2.99: Brahms p1 s1 staff 3
#: bar 6, 0.395), a tie's tip -- whatever its size and place.
THIN_STROKE_MAX_COLUMN_SHARE = 0.45
TOUCHED_SHARE = 0.1

# ── ROADMAP 2.106: how close each call came (bookkeeping, no decision) ──────
#
# `margin` is in each cut's OWN unit (spaces, a share of the column, a step);
# `margin_axis` names the tightest one. >= 0: the verdict reached cleared its
# cut by that much; < 0: the rule declined, short of the nearer candidate.
# `band` is None where the cut is one line with no declared abstention band.
_MIXED = "mixed (spaces, steps, column share)"
_SHAPE_BAND = {"width_spaces/eighth": EIGHTH_WIDTH_SPACES,
               "height_spaces/eighth": EIGHTH_HEIGHT_SPACES,
               "staff_step/eighth": EIGHTH_STEP,
               "width_spaces/quarter": QUARTER_WIDTH_SPACES,
               "height_spaces/quarter": QUARTER_HEIGHT_SPACES,
               "staff_step/quarter": QUARTER_STEP}


def _eighth_slacks(w, h, step, mass_y, col, prof):
    return (("width_spaces", M.slack(w, *EIGHTH_WIDTH_SPACES)),
            ("height_spaces", M.slack(h, *EIGHTH_HEIGHT_SPACES)),
            ("staff_step", M.slack(step, *EIGHTH_STEP)),
            ("mass_y", M.slack(mass_y, hi=EIGHTH_MAX_MASS_Y)),
            ("max_column_share", M.slack(col, hi=EIGHTH_MAX_COLUMN_SHARE)),
            ("left_bins", M.slack(max(prof[:2]), hi=EIGHTH_LEFT_BINS_MAX)))


def _quarter_slacks(w, h, step, prof):
    return (("width_spaces", M.slack(w, *QUARTER_WIDTH_SPACES)),
            ("height_spaces", M.slack(h, *QUARTER_HEIGHT_SPACES)),
            ("staff_step", M.slack(step, *QUARTER_STEP)),
            ("middle_peak", M.slack(max(prof[2], prof[3]),
                                    lo=QUARTER_PEAK_SHARE)),
            ("fourth_bin", M.slack(prof[4], hi=QUARTER_FOURTH_BIN_MAX)),
            ("right_bin", M.slack(prof[5], hi=QUARTER_RIGHT_BIN_MAX)))


def _margin(ruling: Ruling, axis, margin, unit, band, would=(), **extra):
    return M.attach(ruling, margin=margin, axis=axis, unit=unit, band=band,
                    would_choose=would, **extra)


def _shape_refusal(ruling: Ruling, w, h, step, mass_y, col, prof,
                   blocked_by=None) -> Ruling:
    """`shape_cannot_tell`: the margin is the NEARER candidate's tightest
    slack (negative: short of its window by that much) and `would_choose`
    names it. `blocked_by` is set where the shape may even fit but a place
    rule (a cell edge, too many pieces) stood the rule down."""
    eight = M.tightest(_eighth_slacks(w, h, step, mass_y, col, prof))
    quart = M.tightest(_quarter_slacks(w, h, step, prof))
    (axis, m), name = ((eight, "eighth")
                       if (eight[1] or -1e9) >= (quart[1] or -1e9)
                       else (quart, "quarter"))
    extra = {"blocked_by": blocked_by} if blocked_by else {}
    return _margin(ruling, axis, m, _MIXED, _SHAPE_BAND,
                   (name,) if m is not None else (), **extra)


@decision(
    quantity=Q.UNBOXED_INK_IS_A_REST,
    composed_from=(Q.UNBOXED_REST_SHAPE,),
    scope=Kind.GLYPH,
    wants=(Q.UNBOXED_REST_SHAPE,),
    subjects_from=Q.UNBOXED_REST_SHAPE,
    reasons=("rest8th_shape", "restQuarter_shape", "already_read_as_a_glyph",
             "stem_stroke_not_a_rest", "thin_stroke_not_a_rest",
             "claimed_by_another_class",
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
        return _margin(
            Ruling(value=False, reason="already_read_as_a_glyph",
                   used=used, detail=detail),
            "coverage", cover - COVERED_SHARE, "share of the cluster covered",
            {"coverage": (TOUCHED_SHARE, COVERED_SHARE)}, (False,))
    if cover >= TOUCHED_SHARE:
        nearer_read = (COVERED_SHARE - cover) <= (cover - TOUCHED_SHARE)
        return _margin(
            Ruling.abstain("claimed_by_another_class", **detail),
            "coverage", -min(cover - TOUCHED_SHARE, COVERED_SHARE - cover),
            "share of the cluster covered",
            {"coverage": (TOUCHED_SHARE, COVERED_SHARE)},
            (False,) if nearer_read else ())

    col, prof, mass_y = (d.get("max_column_share"), d.get("column_profile"),
                         d.get("mass_y"))
    if (col is None or not prof or len(prof) < 6 or mass_y is None
            or not d.get("n_pieces")):
        return Ruling.abstain("no_ink_reading", **detail)

    if col < THIN_STROKE_MAX_COLUMN_SHARE:
        return _margin(
            Ruling(value=False, reason="thin_stroke_not_a_rest",
                   used=used, detail=detail),
            "max_column_share", THIN_STROKE_MAX_COLUMN_SHARE - col,
            "share of the cluster height (tallest ink column)", None, (False,))

    # A flat / natural: a full-height stroke on the LEFT and little else. (A
    # quarter rest peaks in the middle; an eighth rest has no full slice.)
    if (prof[0] >= 0.6 and prof[1] >= STROKE_SHARE
            and max(prof[2:]) < STROKE_SHARE
            and prof[1] >= max(prof[2:])):
        return _margin(
            Ruling(value=False, reason="stem_stroke_not_a_rest",
                   used=used, detail=detail),
            *M.tightest((("left_bin_0", M.slack(prof[0], lo=0.6)),
                         ("left_bin_1", M.slack(prof[1], lo=STROKE_SHARE)),
                         ("right_bins", M.slack(max(prof[2:]), hi=STROKE_SHARE)),
                         ("left_over_right", prof[1] - max(prof[2:])))),
            "share of the cluster height (column profile)", None, (False,))

    # The header (clef, key signature, meter) is ink nobody boxed: abstain
    # inside it, and where the first cell has no header box to measure from.
    if d.get("left_of_header") or (d.get("first_cell")
                                   and not d.get("header_known")):
        return Ruling.abstain("in_the_header", **detail)
    if d.get("touches_cell_edge") or (d.get("n_pieces") or 0) > REST_MAX_PIECES:
        return _shape_refusal(
            Ruling.abstain("shape_cannot_tell", **detail), w, h, step,
            mass_y, col, prof,
            blocked_by=("touches_cell_edge" if d.get("touches_cell_edge")
                        else "too_many_pieces"))

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
        return _margin(
            Ruling(value="eighth", reason="rest8th_shape", used=used,
                   detail=detail),
            *M.tightest(_eighth_slacks(w, h, step, mass_y, col, prof)),
            _MIXED, _SHAPE_BAND, ("eighth",))
    head = d.get("right_head")
    if quarter and head and head.get("dx_spaces") is not None \
            and head["dx_spaces"] <= QUARTER_HEAD_BESIDE_SPACES \
            and abs(head.get("dy_spaces") or 0.0) <= QUARTER_HEAD_BESIDE_DY_SPACES:
        return _margin(
            Ruling.abstain("head_beside_it", **detail), "head_beside_it",
            -min(QUARTER_HEAD_BESIDE_SPACES - head["dx_spaces"],
                 QUARTER_HEAD_BESIDE_DY_SPACES
                 - abs(head.get("dy_spaces") or 0.0)),
            "staff spaces to the head on the right",
            {"dx_spaces": (0.0, QUARTER_HEAD_BESIDE_SPACES),
             "dy_spaces": (-QUARTER_HEAD_BESIDE_DY_SPACES,
                           QUARTER_HEAD_BESIDE_DY_SPACES)}, ("quarter",))
    if quarter:
        return _margin(
            Ruling(value="quarter", reason="restQuarter_shape", used=used,
                   detail=detail),
            *M.tightest(_quarter_slacks(w, h, step, prof)),
            _MIXED, _SHAPE_BAND, ("quarter",))
    return _shape_refusal(Ruling.abstain("shape_cannot_tell", **detail),
                          w, h, step, mass_y, col, prof)
