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


# ── ROADMAP 2.334: an eighth rest the detector boxed as something else ───────
#
# "A box says where to look; the ink says the kind." A mark with an eighth
# rest's shape (a bulb at the top left and a stroke down to the right, the
# windows above) standing alone in the staff is an eighth rest whatever the
# detector called it. NEVER where the ink is an accidental or a clef: a
# sharp, natural or flat carries a full-height stroke on its left (refused
# above as `stem_stroke_not_a_rest`, and outside the eighth's left-bin window),
# a real double sharp is a small x about one space tall (below the eighth's
# height window), and a clef is taller or wider than the window. Measured
# (lane 2.334, whole-movement records 20261122-night): of the clusters an
# accidental box covers by half or more, 0 of 59 Litolff and 0 of 1,045
# Brahms flat/sharp/natural-boxed inks pass the eighth window except 6 Brahms
# whose crops are eighth rests; 42 Litolff and 205 Brahms double-sharp-boxed
# inks and 14 / 3 clefF-boxed inks pass. No real double sharp is known on
# either plate, so its side rests on the SMuFL size convention.
REST_BOXED_AS_OTHER_ENV = "OMR_REST_BOXED_AS_OTHER"
#: The detector classes whose box gives way to an eighth rest's shape.
#: Accidentals lose their reading at ADJUDICATE (`accidental_is_not_an_accidental`,
#: reason `eighth_rest_shaped_ink`); a clef-class detector box is no reader at
#: all (clefs are read page-wide from ink, ROADMAP 2.324), so it stops counting
#: as an account of rest-shaped ink here.
WRONG_KIND_PREFIXES = ("accidental", "clef")
#: Share of the cluster a box must cover to be the box standing on that ink.
WRONG_KIND_BOX_SHARE = 0.5


def rest_boxed_as_other_enabled() -> bool:
    """`OMR_REST_BOXED_AS_OTHER`, default ON (ROADMAP 2.334; Sean 2026-11-23 "Land the rest switch on"); "0"/"false"/"no"/"off" turns it off."""
    import os
    return os.environ.get(REST_BOXED_AS_OTHER_ENV, "").strip().lower() not in ("0", "false", "no", "off")


def eighth_rest_shaped(d: Dict[str, Any]) -> bool:
    """Does this `Q.UNBOXED_REST_SHAPE` row (coverage aside) read as an eighth
    rest on its own shape and place? The same windows and refusals the 2.99
    decision applies, in the same order; any missing measure is False."""
    w, h, step = d.get("width_spaces"), d.get("height_spaces"), d.get("staff_step")
    col, prof, mass_y = d.get("max_column_share"), d.get("column_profile"), d.get("mass_y")
    if None in (w, h, step, col, mass_y) or not prof or len(prof) < 6 or not d.get("n_pieces"):
        return False
    if col < THIN_STROKE_MAX_COLUMN_SHARE:
        return False
    if (prof[0] >= 0.6 and prof[1] >= STROKE_SHARE and max(prof[2:]) < STROKE_SHARE
            and prof[1] >= max(prof[2:])):
        return False
    if d.get("left_of_header") or (d.get("first_cell") and not d.get("header_known")):
        return False
    if d.get("touches_cell_edge") or (d.get("n_pieces") or 0) > REST_MAX_PIECES:
        return False
    return all(v >= 0 for _k, v in _eighth_slacks(w, h, step, mass_y, col, prof))


# ── ROADMAP 2.339: a quarter rest hidden under another box ──────────────────
#
# The same rule for the quarter rest's shape (a zigzag hanging in the middle
# of the staff: the quarter windows above). NEVER a real arpeggio (a wavy line
# standing immediately left of a chord: `head_beside_it`, the 2.99 guard), a
# stem or a stem with its flag (a full-height stroke on the left: the flat's
# `stem_stroke` test; a flag box is never stepped aside), or ledger lines (a
# ledger box steps aside only where its own decision refused it). Boxes that
# step aside for a quarter: an `arpeggiato` box refused `quarter_rest_shaped_ink`,
# a clef-class box, a refused ledger box, and two rest boxes of DIFFERENT
# classes refused against each other (`rest_is_a_duplicate_box`, 2.15: the
# boxes could not tell the value; the ink can).
QUARTER_REST_BOXED_AS_OTHER_ENV = "OMR_QUARTER_REST_BOXED_AS_OTHER"


def quarter_rest_boxed_as_other_enabled() -> bool:
    """`OMR_QUARTER_REST_BOXED_AS_OTHER`, default ON (ROADMAP 2.339; Sean 2026-11-23); "0"/"false"/"no"/"off" turns it off; acts only with `OMR_REST_BOXED_AS_OTHER` on."""
    import os
    return rest_boxed_as_other_enabled() and os.environ.get(QUARTER_REST_BOXED_AS_OTHER_ENV, "").strip().lower() not in (
        "0", "false", "no", "off")


def quarter_rest_shaped(d: Dict[str, Any]) -> bool:
    """Does this `Q.UNBOXED_REST_SHAPE` row (coverage aside) read as a quarter rest on its own shape and place? The 2.99 decision's
    refusals in its order, its quarter windows, and its arpeggio guard (no head immediately right at its height)."""
    w, h, step = d.get("width_spaces"), d.get("height_spaces"), d.get("staff_step")
    col, prof, mass_y = d.get("max_column_share"), d.get("column_profile"), d.get("mass_y")
    if None in (w, h, step, col, mass_y) or not prof or len(prof) < 6 or not d.get("n_pieces"):
        return False
    if col < THIN_STROKE_MAX_COLUMN_SHARE:
        return False
    if (prof[0] >= 0.6 and prof[1] >= STROKE_SHARE and max(prof[2:]) < STROKE_SHARE
            and prof[1] >= max(prof[2:])):
        return False
    if d.get("left_of_header") or (d.get("first_cell") and not d.get("header_known")):
        return False
    if d.get("touches_cell_edge") or (d.get("n_pieces") or 0) > REST_MAX_PIECES:
        return False
    if not all(v >= 0 for _k, v in _quarter_slacks(w, h, step, prof)):
        return False
    head = d.get("right_head")
    if head and head.get("dx_spaces") is not None and head["dx_spaces"] <= QUARTER_HEAD_BESIDE_SPACES \
            and abs(head.get("dy_spaces") or 0.0) <= QUARTER_HEAD_BESIDE_DY_SPACES:
        return False
    return True


def rest_shaped(d: Dict[str, Any], quarter: bool = False) -> bool:
    """Eighth-rest shaped, or (with `quarter`) quarter-rest shaped."""
    return eighth_rest_shaped(d) or (quarter and quarter_rest_shaped(d))


def _box_share(cluster_bb, box_bb) -> float:
    ix = min(cluster_bb[2], box_bb[2]) - max(cluster_bb[0], box_bb[0])
    iy = min(cluster_bb[3], box_bb[3]) - max(cluster_bb[1], box_bb[1])
    a = (cluster_bb[2] - cluster_bb[0]) * (cluster_bb[3] - cluster_bb[1])
    return max(0.0, ix) * max(0.0, iy) / a if ix > 0 and iy > 0 and a > 0 else 0.0


_HEADER_PREFIXES = ("gclef", "fclef", "cclef", "clef", "keysig", "timesig")   # = gather.UNBOXED_REST_HEADER_PREFIXES


def header_not_from_this_ink(ev: Evidence, d: Dict[str, Any]) -> Dict[str, Any]:
    """GATHER's `left_of_header` is measured from every clef/key/meter-class BOX in the cell -- including a clef-class box standing on
    this very ink (the motif rest boxed `clefF`: the box makes the rest its own header). Re-measured from the header boxes that are NOT
    on this ink (`WRONG_KIND_BOX_SHARE`); every other measure is GATHER's as filed. Only the header fields change."""
    from ..adjudicate import Scope
    bb = d.get("bbox_page_px")
    if not bb or not d.get("left_of_header"):
        return d
    right, on_ink = 0.0, False
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS, subject=ev.subject.at(Kind.CELL)):
        if not isinstance(r.value, (list, tuple)) or not r.value:
            continue
        b = (r.detail or {}).get("bbox_page_px")
        if not b or not str(r.value[0]).lower().startswith(_HEADER_PREFIXES):
            continue
        if str(r.value[0]).lower().startswith("clef") and _box_share(bb, b) >= WRONG_KIND_BOX_SHARE:
            on_ink = True
            continue
        right = max(right, float(b[2]))
    if not on_ink:
        return d
    return {**d, "left_of_header": bool(right and bb[0] < right), "header_known": bool(right) or not d.get("first_cell")}


def eighth_rest_under_box(ev: Evidence, box_bb, shaped=eighth_rest_shaped) -> Any:
    """The rest-shaped `Q.UNBOXED_REST_SHAPE` row in this glyph's own cell
    that this box stands on (covers by `WRONG_KIND_BOX_SHARE`), or None.
    `shaped` is the shape test (2.334 eighth; 2.339 `quarter_rest_shaped`)."""
    from ..adjudicate import Scope
    cell = ev.subject.at(Kind.CELL)
    for r in ev.rows(Q.UNBOXED_REST_SHAPE, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        d = r.detail or {}
        bb = d.get("bbox_page_px")
        if bb and _box_share(bb, box_bb) >= WRONG_KIND_BOX_SHARE and shaped(header_not_from_this_ink(ev, d)):
            return r
    return None


def _cover_left(ev: Evidence, d: Dict[str, Any], quarter: bool = False):
    """ROADMAP 2.334: the cluster's cover once every wrong-kind box on it has
    given way -- an accidental box refused as `eighth_rest_shaped_ink`, a
    clef-class detector box (no clef reader), a ledger box refused as not a
    ledger. `(cover, gave_way)`; None where the boxes cannot be measured.
    ROADMAP 2.339 (`quarter`): also an arpeggiato box refused as
    `quarter_rest_shaped_ink`, and rest boxes of different classes refused
    against each other (`rest_is_a_duplicate_box` with `duplicate_disagrees_with`)."""
    from ..adjudicate import Scope
    from ..record import Outcome
    bb = d.get("bbox_page_px")
    names = set(d.get("covered_by") or ())
    if not bb or not names:
        return None
    cell = ev.subject.at(Kind.CELL)
    stand, gave = [], []
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        if r.subject == ev.subject or not isinstance(r.value, (list, tuple)) or not r.value:
            continue
        cls = str(r.value[0])
        b = (r.detail or {}).get("bbox_page_px")
        if cls not in names or not b or _box_share(bb, b) <= 0.0:
            continue
        low = cls.lower()
        if low.startswith("rest"):
            # a rest box on this ink already reads the rest (or was refused by its own family): never a second rest here --
            # except (2.339) twins of two classes refused against each other: the boxes could not tell the value, the ink can
            v = ev.verdict(Q.REST_IS_NOT_A_REST, subject=r.subject) if quarter else None
            if (v is not None and v.outcome is Outcome.DECIDED and v.value is True
                    and v.reason == "rest_is_a_duplicate_box" and (v.detail or {}).get("duplicate_disagrees_with")):
                gave.append(r.subject.to_key())
                continue
            return None
        if quarter and low.startswith("arpeggi"):
            v = ev.verdict(Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO, subject=r.subject)
            if v is not None and v.outcome is Outcome.DECIDED and v.value is True and v.reason == "quarter_rest_shaped_ink":
                gave.append(r.subject.to_key())
                continue
        if low.startswith("clef"):
            gave.append(r.subject.to_key())
            continue
        q = (Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL if low.startswith("accidental")
             else Q.LEDGER_IS_NOT_A_LEDGER if low.startswith("ledger") else None)
        if q is not None:
            v = ev.verdict(q, subject=r.subject)
            if (v is not None and v.outcome is Outcome.DECIDED and v.value is True
                    and (q != Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL or v.reason == "eighth_rest_shaped_ink")):
                gave.append(r.subject.to_key())
                continue
        stand.append(b)
    if not gave:
        return None
    import numpy as np
    x0, y0, x1, y1 = bb
    W, H = max(1, int(round(x1 - x0))), max(1, int(round(y1 - y0)))
    mask = np.zeros((H, W), dtype=bool)
    for b in stand:
        ix0, iy0 = int(max(0, b[0] - x0)), int(max(0, b[1] - y0))
        ix1, iy1 = int(min(W, b[2] - x0)), int(min(H, b[3] - y0))
        if ix1 > ix0 and iy1 > iy0:
            mask[iy0:iy1, ix0:ix1] = True
    return float(mask.sum()) / float(W * H), gave


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
    # ROADMAP 2.334 (OMR_REST_BOXED_AS_OTHER, read only while it is ON): the
    # boxes on the ink and the refusals that say a box was the wrong kind.
    wants=(Q.UNBOXED_REST_SHAPE, Q.GLYPH_BOX, Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL,
           Q.LEDGER_IS_NOT_A_LEDGER, Q.REST_IS_NOT_A_REST, Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO),
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
    if cover >= TOUCHED_SHARE and rest_boxed_as_other_enabled():
        d2 = header_not_from_this_ink(ev, d)
        eighth = eighth_rest_shaped(d2)
        # ROADMAP 2.339: the quarter shape too, behind its own switch. Written GUESSED (blue): on our plates one real
        # sharp's ink passes the quarter windows (Brahms p19, boxed as a flag), so the shape alone does not settle it.
        quarter = (not eighth) and quarter_rest_boxed_as_other_enabled() and quarter_rest_shaped(d2)
        left = _cover_left(ev, d2, quarter=quarter) if (eighth or quarter) else None
        if left is not None:
            detail = {**detail, "boxed_as_other": {"gave_way": left[1],
                                                   "coverage_was": cover,
                                                   "coverage_left": round(left[0], 3),
                                                   "header_was_this_ink": d2 is not d,
                                                   "guessed": bool(quarter)}}
            cover, d = left[0], d2
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
