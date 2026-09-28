"""*Is this really one?* — asked ONCE PER GATHERED FAMILY. ROADMAP 3.4g.

⚠️⚠️ WHY THIS FILE EXISTS, MEASURED, AND IT IS A PERSON WHO MEASURED IT.
Sean's first stage-review pass on Litolff Beethoven 5 p3 `staff/3/0/9`
(ROADMAP 3.4, 2026-09-23) marked 23 boxes as *nothing*. **Eighteen of them
reached no stage at all** — `ledgerLine` ×11, `arpeggiato` ×3,
`accidentalFlat` ×2, `accidentalNatural`, `restQuarter` — not because the
rows were lost but because `adjudicate_notehead_is_not_a_notehead` was the
whole pipeline's only "is this really one" question and it is asked of
NOTEHEADS. A reader whose reading is filed and then read by nobody is the
ABSENT/DECLINED collapse `record.py` exists to prevent, happening to the
person the project calls its cheapest evidence.

So: one decision per gathered family, each declaring `Q.HUMAN_BOX_VERDICT` and
each reading it through `notehead_precision._human_not_a_symbol` — the SAME
function, imported, never a second copy. A second parser of the human
vocabulary is how `not_a_symbol` comes to mean two things, which is the
argument `human_evidence.human_says`'s own docstring makes about `split(":")`.

⚠️⚠️ SIX OF THE SEVEN ARE HUMAN-ONLY, AND THAT IS A STATEMENT ABOUT THE
EVIDENCE, NOT A PLACEHOLDER. "Shape from the class, role from the geometry"
(DECISIONS 2026-09-23) says a geometric rule must come from a CONVENTION
somebody can state and a measurement somebody has made. Exactly one family
has both today: Sean gave the ledger line's convention in the same sitting
(*"often a staff line, a bar line or extra ink"*), and §LEDGER below measures
it on three records. For a rest, an arc, a dynamic letter, an articulation, an
accidental and an arpeggiato, nobody has stated one and nothing has been
measured, so these decisions refuse on a human witness and on nothing else.
Inventing a shape test per family to make the file look symmetrical would be
seven unmeasured defaults shipped at once.

⚠️ WHAT EACH REFUSAL REACHES IS NOT THE SAME, AND THE DIFFERENCES ARE STATED
RATHER THAN EVENED OUT. `rest` stops a `<rest>` being written, `arc` stops a
`<slur>`/`<tie>`, `articulation` stops an `<articulations>` entry, `dynamic`
stops a letter being spelled into a word, `ledger` stops a rung being counted
in ADJUDICATE's own ladder. `arpeggiato` reaches the EXPORT CENSUS AND
NOTHING ELSE, because the family reaches no file today at all
(`gather_coverage.FAMILY_TO_Q` maps it to `None`); what the decision buys is
precisely that a human's *nothing* lands on the record as a verdict he can be
shown, instead of on no stage — which is the whole of 3.4g's gate and is
worth saying plainly rather than dressing up. `accidental` was in the same
position when this file was written; since roadmap 2.7 landed (2026-09-27)
its refusal is also read by `adjudicate_accidental_owner`, so a refused
accidental owns no notehead and no `<accidental>` is written for it.

⚠️ THE DOMAIN OF THREE OF THEM IS CLASS-NARROWED, and `adjudicate.
DecisionSpec.subjects_classed` records why: `ledger`, `accidental` and
`arpeggiato` have NO quantity of their own, so their only domain is
`Q.GLYPH_BOX`, whose rows are every detection on the page.

─────────────────────────────────────────────────────────────────────────────
§LEDGER — the one family with a convention and a measurement
─────────────────────────────────────────────────────────────────────────────

Sean, 2026-09-23 (`docs/DECISIONS.md`): a LEDGER LINE stands OUTSIDE the
staff, at a whole number of spaces beyond the top or bottom line, short and
horizontal; a `ledgerLine` box lying on a staff line's y is a staff-line
fragment, a tall one is a barline or a stem, and neither is a ledger line.

Three candidate rules follow from that sentence. All three were measured on
the three records BEFORE any of them was written — `benchmarks/
omr-family-refusals-2026-09/probe/ledger_geometry.py`, 17,313 `ledgerLine`
boxes, every one of them carrying a page frame — and they came out very
differently:

  `on_a_staff_line`    SHIPS. The box's centre lands within
                       `ON_A_STAFF_LINE_TOL_SPACES` of one of the staff's own
                       five lines. Reach 1,215 of 1,878 / 4,709 of 7,617 /
                       1,409 of 7,818 — and 1,059 / 4,011 / 1,125 of those are
                       INSIDE the staff band, where the convention says a
                       ledger line cannot be at all.

  `tall_not_a_rung`    SHIPS, and its population is tiny and honest about it:
                       7 / 22 / 8 boxes of 17,313 stand taller than half a
                       staff space. ⚠️ THE ASPECT ARM SEAN'S WORDING SUGGESTS
                       — taller than wide, i.e. a barline or a stem — IS DEAD:
                       **0 of 17,313** boxes are taller than wide (max aspect
                       0.40 / 0.78 / 0.57). The detector never draws a
                       `ledgerLine` box around a whole barline; when it fires
                       on barline ink it draws a SHORT HORIZONTAL SLICE of it,
                       which no proportion test can separate from a rung. So
                       the arm is not written — a rule that cannot fire is not
                       a conservative rule, it is an unmeasured one wearing a
                       zero.

  `not_at_a_rung_step` MEASURED AND HELD BACK (`RUNG_STEP_SHIPS = False`),
                       exactly the `notehead_precision.UNLADDERED_SHIPS`
                       precedent. Over the boxes that are unambiguously
                       outside the staff (at least 1.25 spaces clear of the
                       outer line, so the nearest rung is always within half a
                       space and the number measured is scatter), the offset
                       from the nearest rung step is **very nearly UNIFORM on
                       Litolff**: p5/p50/p95 = 0.075 / 0.330 / 0.470 spaces on
                       p1-p4 and 0.073 / 0.285 / 0.470 on the whole movement,
                       on a lattice whose half-period IS 0.5. A uniform
                       distribution over the lattice carries no signal: the
                       measurement cannot tell a rung from anything else,
                       and a rule read off it would refuse 522 / 1,945 boxes
                       on evidence that is indistinguishable from noise.
                       ⚠️ Breitkopf's SAME measurement is peaked (p50 0.135,
                       p25 0.070), so the lattice is resolvable on that plate
                       and not on this one — which is a fact about the
                       registration of `Q.STAFF_LINES` against a MERGING
                       bitonal plate, not about the convention. `rhythm.py`
                       records the same cause in its own tolerance: a scanned
                       staff tilts and bows 8-17 page px, *up to a whole
                       STEP*, and a whole step is half the rung lattice.
                       The signal is computed on every ledger box and recorded
                       in `detail["rung_step_signal"]` so the finding stays on
                       the record; it sets no value.

⚠️ THE TOLERANCE IS DERIVED AND NOT CHOSEN. `ON_A_STAFF_LINE_TOL_SPACES` is
the p75 of the MEASURED gap between a `ledgerLine` box's centre and its
nearest modelled staff line, over the boxes INSIDE the staff band — the one
population where the ink can only be a staff-line fragment, so the number is
registration scatter and nothing else. That p75 is 0.245 / 0.235 / 0.162
spaces on the three records; 0.25 is the smallest round value covering all
three. See `ON_A_STAFF_LINE_TOL_SPACES` for why it cannot reach a real rung.

§LEDGER, 3.4g-2 — SEAN'S TWO CONVENTIONS (2026-09-24, on 13 crops)
─────────────────────────────────────────────────────────────────────────────
*"the ledger lines will only be on the outside of the staff and only happen
if there are actual notes in the staff"* — `[C90]` and `[C91]` in
`docs/engraving-conventions.md`. Two reasons join the three above:

  `inside_the_staff`     the box's centre lies in the band between line 1
                         and line 5. Subsumes `on_a_staff_line` for the
                         inner lines, which now reaches only a box just
                         OUTSIDE an outer line; catches the "middle of the
                         staff" boxes no line tolerance could (crops 1, 10).
  `no_head_on_the_rung`  no notehead box in the same cell x-overlaps the
                         rung within `HEAD_NEAR_TOL_SPACES` (a measured p95),
                         and none stands farther OUT than it.

and `tall_not_a_rung` now requires that no head's box INTERSECTS the rung's:
its one miss on the print (crop 9) was a real rung whose box had swallowed
the head standing on it. Crops 3 and 9 — the two real rungs the 3.4g rules
refused or would have — are KEPT; the 13 crops are pinned as fixtures in
`tests/test_staged_family_refusals.py`. Measurement and crops:
`benchmarks/omr-family-refusals-2026-09/FINDINGS.md` §3.4g-2.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..adjudicate import Evidence, Mode, Ruling, decision
from ..record import ABSTAIN, Kind, Q, Scope
from .notehead_precision import (HUMAN_OTHER_STAFF, HUMAN_REFUSAL_REASONS,
                                 _human_not_a_symbol as _human_says_no)
# ⚠️ ONE STAFF-STEP CONVENTION IN THE PIPELINE, IMPORTED NOT RESTATED. Bottom
# line 0, top line 8, one step per half space, up positive, measured in PAGE
# pixels. `rhythm.py` owns it because `adjudicate_notehead_is_a_whole_rest`
# needed it first; a second copy here is how the two would come to disagree
# about which line is zero. ⚠️ THIS FILE DOES NOT EDIT `rhythm.py` (lane
# 2.12b-cal holds its rest ruling); it reads one geometry helper.
from .rhythm import _staff_step

# ─────────────────────────────────────────────────────────────────────────────
# §LEDGER — the constants, every one of them measured. See the module
# docstring for the measurement and `benchmarks/omr-family-refusals-2026-09/`
# for the probe that made it and the crops that adjudicate it.
# ─────────────────────────────────────────────────────────────────────────────

#: A staff's five lines as STAFF STEPS in `_staff_step`'s frame.
_LINE_STEPS = (0.0, 2.0, 4.0, 6.0, 8.0)
#: The staff band, in the same frame. A ledger line cannot be inside it.
_BAND_TOP_STEP = 8.0

#: How close a `ledgerLine` box's centre must come to a staff line before it
#: is a staff-line fragment rather than a rung, in STAFF SPACES.
#:
#: ⚠️ DERIVED: the p75 of the measured centre-to-nearest-line gap over the
#: boxes INSIDE the staff band on the three records — 0.245 (beethoven5-p1-p4)
#: / 0.235 (litolff whole) / 0.162 (breitkopf whole). 0.25 is the smallest
#: round value that covers all three.
#:
#: ⚠️ IT CANNOT REACH A REAL RUNG, and that is the bound that matters. The
#: first legal rung stands ONE WHOLE SPACE beyond the outer line, so this
#: tolerance is FOUR TIMES clear of it; the largest registration error
#: `rhythm.py` measures on this plate is a whole STEP (0.5 spaces), still
#: half the distance to the first rung. The positive control the tests pin is
#: exactly that box: a rung one space below line 1 with a head on it is NOT
#: refused.
ON_A_STAFF_LINE_TOL_SPACES = 0.25

#: A `ledgerLine` box taller than this many staff spaces is not a rung.
#:
#: ⚠️ REACH 7 / 22 / 8 of 17,313, and the smallness is the point rather than
#: an embarrassment: the height distribution is p50 0.28, p95 0.37, p99 0.41
#: on all three records, so 0.5 sits well past the population's own tail and
#: catches only ink that is the wrong SHAPE for a rung. ⚠️ See the module
#: docstring for the arm that is NOT here: taller-than-wide fires 0 of 17,313.
TALL_MIN_HEIGHT_SPACES = 0.5

#: How close to a whole number of spaces beyond the outer line a rung must
#: sit, for `not_at_a_rung_step`. ⚠️ THE RULE IS HELD BACK — see
#: `RUNG_STEP_SHIPS` — and this constant exists so the signal it records is
#: reproducible, not so the rule can be turned on without re-measuring.
RUNG_STEP_TOL_SPACES = 0.25

#: ⚠️⚠️ MEASURED AND HELD BACK, 2026-09-23, on all three records. The offset
#: from the nearest rung step is very nearly UNIFORM over the lattice on
#: Litolff (p5/p50/p95 0.073 / 0.285 / 0.470 spaces on a lattice of
#: half-period 0.5), so the measurement carries no signal there at all and a
#: rule read off it would refuse 1,945 of 7,617 boxes on noise. It IS peaked
#: on Breitkopf (p50 0.135), which says the cause is the registration of
#: `Q.STAFF_LINES` against a MERGING plate rather than the convention.
#: "Print before default" (CLAUDE.md §2 rule 5) forbids shipping it on the
#: strength of the convention alone. The signal is computed on every ledger
#: box and recorded in `detail["rung_step_signal"]`; it sets no value. What
#: would have to change first: a staff-line model that follows the bow
#: (`OMR_CELL_LINE_TRACE` traces one per cell and this decision does not read
#: it), re-measured on Litolff, with the offset histogram peaked.
RUNG_STEP_SHIPS = False

#: ⚠️⚠️ SEAN'S SECOND CONVENTION, 2026-09-24 (`docs/DECISIONS.md`, ROADMAP
#: 3.4g-2, `[C91]`): *"only happen if there are actual notes in the staff"* —
#: a rung with no notehead on or near it is not a rung. How near is "near",
#: in STAFF SPACES of the cell's own frame, measured centre to centre between
#: the rung box and a notehead box that x-overlaps it in the same cell.
#:
#: ⚠️ DERIVED, NOT CHOSEN: the p95 of that distance over the rungs the 3.4g
#: rules KEEP (outside the band, off every line, rung-thick) —
#: **2.67 (beethoven5-p1-p4) / 2.67 (litolff whole) / 1.885 (breitkopf
#: whole)** spaces (`benchmarks/omr-family-refusals-2026-09/probe/
#: ledger_heads.py`, `out/ledger-heads*.json`). 2.75 is the smallest
#: quarter-space value covering all three, by the same arithmetic that made
#: `ON_A_STAFF_LINE_TOL_SPACES` 0.25.
#:
#: ⚠️ WHY A TAIL AS LONG AS TWO AND THREE-QUARTER SPACES AND NOT ONE: a note
#: three spaces beyond the staff prints three rungs and stands on the
#: outermost, so the innermost is two spaces from the only head that
#: x-overlaps it. The p95 is "how long is a ledger run on this plate", not
#: "how thick is a notehead". And past it — see `_heads_on_the_rung` — a head
#: FARTHER OUT than the rung is always its note, whatever the distance.
HEAD_NEAR_TOL_SPACES = 2.75

#: ⚠️⚠️ ROADMAP 3.4g-3 — THE SECOND WITNESS'S TWO THRESHOLDS, on
#: `Q.LEDGER_INK_UNDER` (the ink fraction in a notehead-sized window on the
#: rung, stroke removed, off the staff-erased raster; `gather.
#: ledger_ink_under`). Sean, 2026-09-27: of the four rungs 3.4g-2 refused
#: `no_head_on_the_rung`, TWO were real rungs whose head the detector never
#: boxed — so "no boxed head" is *cannot tell*, and the paper decides.
#:
#: `LEDGER_INK_KEPT_MIN` — the under-window must stand at least this far
#: ABOVE its own background (the same window one space away) for the rung to
#: be KEPT (`ink_under_the_rung`). `LEDGER_INK_REFUSED_MAX` — at or below
#: this the paper under the rung is EMPTY and Sean's `[C91]` refusal returns
#: with two witnesses. Between them the abstention stands.
#:
#: ⚠️ MEASURED, NOT CHOSEN: see `benchmarks/omr-family-refusals-2026-09/
#: FINDINGS.md` §3.4g-3 for the histograms (rungs WITH a boxed head on them
#: vs the in-band / on-a-line population, one real gather of Litolff pdf
#: index 3) and the RED run with the windows swapped.
LEDGER_INK_KEPT_MIN = 0.30
LEDGER_INK_REFUSED_MAX = 0.05


def _glyph_box_row(ev: Evidence):
    rows = ev.rows(Q.GLYPH_BOX)
    return rows[-1] if rows else None


def _cell_staff_space(ev: Evidence) -> Optional[float]:
    rows = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS)
    if not rows:
        return None
    try:
        v = float(rows[-1].value)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def _human_refusal(ev: Evidence, detail: Dict[str, Any]
                   ) -> Optional[Tuple[Any, str]]:
    """The human witness, read through the ONE function that reads it.

    ⚠️ A GENUINE SHORT-CIRCUIT AND NOT A CEREMONY. `ev.rows(Q.HUMAN_BOX_
    VERDICT)` is how this decision DECLARES that it reads the quantity — and
    `inventory --check`'s `_never_read` follows helper calls only inside the
    decision's OWN module, so a decision here that reached the vocabulary
    solely through an import from `notehead_precision` would be reported as
    declaring a quantity it never touches. The early return is also the
    honest one: no human row, no human refusal, and the common case never
    enters the parser at all.
    """
    if not ev.rows(Q.HUMAN_BOX_VERDICT):
        return None
    # ⚠️ READ HERE AND PASSED IN, for the same reason the line above is here:
    # `inventory._never_read` follows helper calls only inside the decision's
    # own module, so a `wants` entry this module never touches reads as inert.
    # And it is the load-bearing fact, not a formality — it is what keeps a
    # NAMED owner going to `adjudicate_glyph_owner` wherever that contest can
    # hear it, and turns it into a refusal only where it cannot.
    contested = bool(ev.rows(Q.GLYPH_BAND_DISTANCE))
    return _human_says_no(ev, detail, contested=contested)


# ─────────────────────────────────────────────────────────────────────────────
# §LEDGER — the geometry
# ─────────────────────────────────────────────────────────────────────────────


def _ledger_geometry(ev: Evidence, box_row) -> Tuple[Optional[float],
                                                     List[str]]:
    """This box's centre as a STAFF STEP, in PAGE pixels, and the rows used.

    ⚠️ PAGE FRAME, NEVER CANONICAL. `Q.STAFF_LINES` and `Q.STAFF_SPACING` are
    the staff's own page-pixel measurements; `Q.GLYPH_BOX`'s canonical box is
    measured inside ONE cell rescaled so the staff span is constant, so the
    two are not the same quantity and comparing them is the fault
    `Q.ONSET_COLUMN` paid for.
    """
    page_box = (box_row.detail or {}).get("bbox_page_px")
    staff = ev.subject.at(Kind.STAFF)
    lines = ev.rows(Q.STAFF_LINES, scope=Scope.SELF_AND_ANCESTORS,
                    subject=staff)
    spacing = ev.rows(Q.STAFF_SPACING, scope=Scope.SELF_AND_ANCESTORS,
                      subject=staff)
    if not page_box or not lines or not spacing:
        return None, []
    step = _staff_step(page_box, lines[-1].value, spacing[-1].value)
    if step is None:
        return None, []
    return step, [lines[-1].id, spacing[-1].id]


def _beyond_spaces(step: float) -> float:
    """How far OUTSIDE the staff band, in spaces. 0 inside, + on either side."""
    if step < 0.0:
        return -step / 2.0
    if step > _BAND_TOP_STEP:
        return (step - _BAND_TOP_STEP) / 2.0
    return 0.0


def _line_gap_spaces(step: float) -> float:
    """|distance to the nearest of the staff's own five lines|, in spaces."""
    return min(abs(step - t) for t in _LINE_STEPS) / 2.0


def _rung_offset_spaces(step: float) -> Optional[float]:
    """|distance to the nearest whole space beyond line 1 or line 5|.

    `None` inside the band, where the question does not arise — there is no
    rung step in there to be near.
    """
    b = _beyond_spaces(step)
    if b <= 0.0:
        return None
    return abs(b - round(b))


def _is_notehead_class(name: Any) -> bool:
    """GATHER's own notehead test, imported not restated (see
    `review.human_evidence.NOTEHEAD_PREFIX`, which imports it from
    `gather._NOTEHEAD_PREFIX`)."""
    from ..review.human_evidence import NOTEHEAD_PREFIX
    return str(name).startswith(NOTEHEAD_PREFIX)


def _heads_on_the_rung(ev: Evidence, box_row, space: float,
                       step: Optional[float]) -> Dict[str, Any]:
    """Sean's second convention, measured: is there a NOTE on this rung?

    Every `notehead*` box in the SAME CELL whose x range overlaps the rung's,
    measured in the cell's own canonical frame against the cell's own staff
    space (`Q.CELL_STAFF_SPACE`) — one ruler for all three numbers. The staff
    STEP (page pixels) is used for one thing only: which way is OUT.

    Returns the facts, not a verdict:
      `heads_x_overlapping`   how many heads x-overlap the rung
      `head_distance_spaces`  the nearest one's |centre - centre|, or None
      `head_outward_spaces`   the largest SIGNED distance of one of them,
                              + meaning farther from the staff than the rung
                              (None inside the band, where out is undefined)
      `head_on_the_box`       a head's box INTERSECTS the rung's box — the
                              head is standing on it, not merely near it
      `near`                  within `HEAD_NEAR_TOL_SPACES`, OR farther out
                              than the rung (the rung lies between the staff
                              and its note, which is the only place an
                              engraver prints one — `[C4]`, the unbroken
                              ladder)

    ⚠️ THE OUTWARD CLAUSE IS MEASURED, NOT ASSUMED. Of the rungs the 3.4g
    rules keep that stand PAST the 2.75-space tolerance, **5 of 23 / 43 of
    122 / 51 of 89** (p1-p4 / Litolff / Breitkopf) have an x-overlapping head
    farther out than the rung, at 2.9-4.6 spaces — the inner rungs of four-
    and five-rung ladders. A symmetric tolerance alone would refuse all 99.
    The rungs with heads ONLY between them and the staff (10 / 35 / 19) are
    what it should refuse: Sean's crop 8 is one — *"a beam for 3 eighth
    notes"*, its heads 2.975 spaces staffward.

    ⚠️ SAME CELL ONLY, as `notehead_precision._ledger_rungs_in_cell` reads
    rungs: the padding that holds a note's rungs also holds the note.

    ⚠️ A WHOLE REST THE DETECTOR BOXED AS A NOTEHEAD COUNTS AS A HEAD HERE,
    and that is a known limit rather than an oversight: `notehead_is_a_
    whole_rest` runs AFTER this decision in `adjudicate.ORDER` (it must —
    `notehead_is_not_a_notehead` reads this one, and the whole-rest decision
    sits downstream of both), so its verdict is not on the frozen log yet.
    Sean's crops 4 and 7 are exactly this case; both are INSIDE the band and
    refused by his first convention before this test is consulted.
    """
    _n, x_r, y_r, w_r, h_r = box_row.value
    rung_mid = y_r + h_r / 2.0
    # canonical y grows DOWN the page: above the staff OUT is up.
    sign: Optional[float] = None
    if step is not None and step > _BAND_TOP_STEP:
        sign = -1.0
    elif step is not None and step < 0.0:
        sign = 1.0
    cell = ev.subject.at(Kind.CELL)
    over = 0
    dists: List[float] = []
    outward: List[float] = []
    on_box = False
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        v = r.value
        if not isinstance(v, (list, tuple)) or len(v) != 5:
            continue
        if not _is_notehead_class(v[0]):
            continue
        _hn, hx, hy, hw, hh = v
        if min(hx + hw, x_r + w_r) - max(hx, x_r) <= 0.0:
            continue
        over += 1
        dy = ((hy + hh / 2.0) - rung_mid) / space
        dists.append(abs(dy))
        if sign is not None:
            outward.append(sign * dy)
        if min(hy + hh, y_r + h_r) - max(hy, y_r) > 0.0:
            on_box = True
    nearest = min(dists) if dists else None
    out_max = max(outward) if outward else None
    near = ((nearest is not None and nearest <= HEAD_NEAR_TOL_SPACES)
            or (out_max is not None and out_max > 0.0))
    return {
        "heads_x_overlapping": over,
        "head_distance_spaces": (None if nearest is None
                                 else round(nearest, 4)),
        "head_outward_spaces": None if out_max is None else round(out_max, 4),
        "head_on_the_box": on_box,
        "near": near,
    }


# ─────────────────────────────────────────────────────────────────────────────
# The seven decisions
#
# ⚠️ SEVEN NAMED FUNCTIONS AND ONE BODY, AND THE SHAPE IS DELIBERATE. A
# factory returning closures would give every spec a `fn.__name__` that
# `inventory._never_read` cannot find in the source it parses (it looks for a
# `FunctionDef` named `spec.name`), so every declared `wants` would be
# reported as unread — a derived check silently disabled by a code-style
# choice. Seven two-line functions keep the AST honest.
# ─────────────────────────────────────────────────────────────────────────────

#: The reason a glyph NO rule condemns decides `False` with, per family.
#: ⚠️ `False` WITH A REASON, NEVER AN ABSTENTION — the distinction
#: `adjudicate_notehead_is_a_whole_rest` and `..._is_not_a_notehead` both
#: draw: *we looked and found nothing wrong with it* is not *we could not
#: tell*, and only one of those two is a fact about the page.
_OK = {
    Q.LEDGER_IS_NOT_A_LEDGER: "ledger_line",
    Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL: "accidental",
    Q.REST_IS_NOT_A_REST: "rest",
    Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO: "arpeggiato",
    Q.ARC_IS_NOT_AN_ARC: "arc",
    Q.DYNAMIC_IS_NOT_A_DYNAMIC: "dynamic",
    Q.ARTICULATION_IS_NOT_AN_ARTICULATION: "articulation",
}

#: Every reason a HUMAN-ONLY family decision can return. Derived from the two
#: human reasons plus its own `ok` word, so a family cannot grow a reason
#: without the table above growing with it.
def _human_only_reasons(quantity: str) -> Tuple[str, ...]:
    return HUMAN_REFUSAL_REASONS + (_OK[quantity],)


def _class_detail(ev: Evidence) -> Tuple[Dict[str, Any], Tuple[str, ...]]:
    """`(detail seeded with the detector's class, the box row's id)`."""
    detail: Dict[str, Any] = {}
    box_row = _glyph_box_row(ev)
    if box_row is None:
        return detail, ()
    if isinstance(box_row.value, (list, tuple)) and len(box_row.value) == 5:
        detail["class"] = box_row.value[0]
    return detail, (box_row.id,)


def _refused_by_a_human(ev: Evidence, detail: Dict[str, Any]
                        ) -> Optional[Ruling]:
    """The refusal six of the seven share, and the seventh runs first.

    ⚠️ THE TWO REASONS ARE RETURNED AS LITERALS AND NOT AS THE VARIABLE THE
    PARSER HANDED BACK, which looks like a pointless expansion and is not:
    `brakes.vocabulary_gap` asks *is every declared reason one a `Ruling` site
    in this module can actually carry*, and it answers by reading the
    `reason=` slot's AST. A computed reason makes the whole MODULE
    UNRESOLVED — every decision in it, not just the one — so a shared
    `reason=reason` here would have put seven decisions beyond the reach of
    the check that exists to catch a declared-and-unreachable reason. The
    branch is the price of keeping that check able to fail.

    ⚠️ IT NEVER ABSTAINS. A human who left no row is not a missing
    measurement; it is the absence of a refusal, which is a fact about the
    box. Abstaining here would put six whole gathered families into
    `no_staff_geometry` on every page nobody has reviewed.
    """
    human = _human_refusal(ev, detail)
    if human is None:
        return None
    row, reason = human
    if reason == HUMAN_OTHER_STAFF:
        return Ruling(value=True, reason="human_other_staff",
                      used=(row.id,), detail=detail)
    return Ruling(value=True, reason="human_not_a_symbol",
                  used=(row.id,), detail=detail)


@decision(
    quantity=Q.LEDGER_IS_NOT_A_LEDGER,
    composed_from=(Q.GLYPH_BOX, Q.STAFF_LINES, Q.STAFF_SPACING,
                   Q.CELL_STAFF_SPACE, Q.HUMAN_BOX_VERDICT,
                   Q.GLYPH_BAND_DISTANCE, Q.LEDGER_INK_UNDER),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_BOX, Q.STAFF_LINES, Q.STAFF_SPACING, Q.CELL_STAFF_SPACE,
           Q.HUMAN_BOX_VERDICT, Q.GLYPH_BAND_DISTANCE, Q.LEDGER_INK_UNDER),
    subjects_from=Q.GLYPH_BOX,
    subjects_classed=("ledgerLine",),
    reasons=HUMAN_REFUSAL_REASONS + ("inside_the_staff", "on_a_staff_line",
                                     "tall_not_a_rung", "no_head_on_the_rung",
                                     "ink_under_the_rung", "ledger_line",
                                     "rung_without_boxed_head",
                                     ABSTAIN.NO_STAFF_GEOMETRY),
    mode=Mode.ADDITIVE,
)
def adjudicate_ledger_is_not_a_ledger(ev: Evidence) -> Ruling:
    """Is this box the detector called a ledger line actually a rung?

    See the module docstring §LEDGER for Sean's convention, for the
    measurement of all three candidate rules on three records, and for why
    `not_at_a_rung_step` is built, recorded and NOT shipped.

    ⚠️ THE HUMAN IS FIRST AND OUTSIDE THE GEOMETRY GATE, for the reason
    `notehead_precision` states one file along: every other rule here needs a
    unit, and putting the human's reading after the gate would throw it away
    on exactly the cells where the machine can say least.

    ⚠️ IT REFUSES, IT DOES NOT DELETE. The `Q.GLYPH_BOX` row stays; what
    changes is that `notehead_precision._ledger_rungs_in_cell` stops counting
    the rung and `export` counts the refusal by name.

    ⚠️⚠️ AND IT CANNOT REACH GATHER'S OWN LADDER, WHICH IS THE FINDING THIS
    DECISION MUST STATE RATHER THAN PAPER OVER. `glyph_owner`'s strongest
    tier reads `Q.GLYPH_LADDER`, and that row is built in GATHER
    (`gather._observe_ladder`) from an anonymous list of rung rectangles: it
    records `expected` and `found` as COUNTS and names NONE of the ledger
    glyphs it matched. The rung -> glyph join does not exist on the record, so
    no ADJUDICATE refusal can discount a GATHER-counted rung without a GATHER
    change — and a GATHER change is invisible to `readjudicate` and needs two
    full re-gathers to price (CLAUDE.md §6b). The join DOES exist in
    ADJUDICATE's own ledger search, where the rungs are glyph subjects, and
    that is where the discount is applied.
    """
    detail, _used = _class_detail(ev)
    refused = _refused_by_a_human(ev, detail)
    if refused is not None:
        return refused

    box_row = _glyph_box_row(ev)
    if box_row is None or not isinstance(box_row.value, (list, tuple)) \
            or len(box_row.value) != 5:
        return Ruling.abstain(ABSTAIN.NO_STAFF_GEOMETRY)

    used = [box_row.id]

    # ⚠️⚠️ THE ORDER, 3.4g-2, AND WHY. Human (above) -> POSITION (inside the
    # band, then on an outer line: need nothing but the staff) -> SHAPE (tall,
    # and only where no head stands ON the box) -> NOTES (no head on or near
    # the rung). `tall` must precede the head rule or it could never fire on
    # a tall box with no head near it, a declared reason made unreachable.
    # Position precedes the head rule because the head tolerance was
    # MEASURED on boxes OUTSIDE the band and is applied only where it was
    # measured; inside the band Sean's first convention settles it whatever a
    # head does (the head facts are still recorded, for every box that has a
    # cell unit, so a box both conventions condemn shows both).

    # ── the cell's own unit, and the head facts, in the CELL frame ──────────
    #
    # ⚠️ A height and a head distance are lengths inside one cell and
    # `Q.CELL_STAFF_SPACE` is that cell's own staff space; the step is a
    # position on a staff and lives in page pixels. Each is measured in the
    # frame its own unit is in, and neither number is compared with the
    # other — the step only says which way is OUT.
    _name, _x, _y, w_c, h_c = box_row.value
    space = _cell_staff_space(ev)
    step, geom_rows = _ledger_geometry(ev, box_row)
    tall = False
    heads: Optional[Dict[str, Any]] = None
    if space is not None:
        detail["height_spaces"] = round(h_c / space, 4)
        detail["aspect_h_over_w"] = round(h_c / w_c, 4) if w_c else None
        heads = _heads_on_the_rung(ev, box_row, space, step)
        detail.update({k: v for k, v in heads.items() if k != "near"})
        # ── tall_not_a_rung: tall AND no head standing ON it (3.4g-2) ──────
        # ⚠️ RE-MEASURED ON ITS ONE MISS, NOT RETUNED: Sean's crop 9
        # (`glyph/4/1/2/5/14`) is a real rung at 0.68 spaces whose box has
        # swallowed the ink of the head standing on it (nearest head 0.085
        # spaces, eight x-overlapping) — on a MERGING plate the height was
        # measuring the head. The 0.5 floor is unchanged; what changed is
        # that a box a head stands ON is not a barline or a beam whatever it
        # measures. "On" is the two boxes INTERSECTING, which needs no
        # constant. Crop 8 (a beam, heads 2.975 spaces off) still fires.
        tall = (h_c / space > TALL_MIN_HEIGHT_SPACES
                and not heads["head_on_the_box"])

    if step is None:
        # ⚠️ DECLINED, NOT DEFAULTED. Without the staff's own lines in the
        # box's own frame no position rule can run, and a ledger box of
        # unknown position is not thereby a rung. The height rule needs no
        # position, so it still speaks.
        if tall:
            return Ruling(value=True, reason="tall_not_a_rung",
                          used=tuple(used), detail=detail)
        return Ruling.abstain(ABSTAIN.NO_STAFF_GEOMETRY)
    used += geom_rows

    detail["staff_step"] = round(step, 4)
    beyond = _beyond_spaces(step)
    detail["beyond_the_band_spaces"] = round(beyond, 4)
    gap = _line_gap_spaces(step)
    detail["line_gap_spaces"] = round(gap, 4)

    # ⚠️ COMPUTED UNCONDITIONALLY, BEFORE ANY SHIPPED RULE RETURNS, so the
    # held-back measurement stays on the record even where a shipped rule
    # already condemns the box for a different reason — the same discipline
    # `notehead_precision`'s `unladdered_signal` keeps.
    off = _rung_offset_spaces(step)
    detail["rung_step_signal"] = {
        "offset_spaces": None if off is None else round(off, 4),
        "would_fire": off is None or off > RUNG_STEP_TOL_SPACES,
        "ships": RUNG_STEP_SHIPS,
    }

    # ── inside_the_staff: Sean's FIRST convention, 2026-09-24 (`[C90]`) ─────
    # *"the ledger lines will only be on the outside of the staff"*. A box
    # whose centre lies in the band between line 1 and line 5 is not a rung,
    # whatever its distance to a line — which is what `on_a_staff_line`
    # could not say about a box in the MIDDLE of a space (Sean's crops 1 and
    # 10: *"middle of the staff, where there would never be a ledger line"*).
    # ⚠️ NO TOLERANCE, AND THAT IS THE HONEST SHAPE: the band's edges ARE
    # lines 1 and 5, so a box registered a hair outside them is caught by
    # `on_a_staff_line` below at its measured tolerance, not by widening the
    # band with a number the convention does not state.
    if beyond <= 0.0:
        return Ruling(value=True, reason="inside_the_staff",
                      used=tuple(used), detail=detail)

    # ── on_a_staff_line: the OUTER lines only, since 3.4g-2 ─────────────────
    # Everything inside the band is refused above, so this now reaches only a
    # box just OUTSIDE line 1 or line 5 and within the measured registration
    # scatter of it — a staff-line fragment the band test cannot see.
    if gap <= ON_A_STAFF_LINE_TOL_SPACES:
        return Ruling(value=True, reason="on_a_staff_line",
                      used=tuple(used), detail=detail)

    if tall:
        return Ruling(value=True, reason="tall_not_a_rung",
                      used=tuple(used), detail=detail)

    # ── no BOXED head: Sean's SECOND convention (`[C91]`), WITNESSED ─────────
    # *"only happen if there are actual notes in the staff"*. No notehead
    # box x-overlapping the rung within the measured tolerance, and none
    # farther out than it.
    #
    # ⚠️⚠️ ROADMAP 3.4g-3: NO BOXED HEAD IS *CANNOT TELL*, NOT *NO HEAD*.
    # Sean, 2026-09-27, on the four crops 3.4g-2 refused here: two were REAL
    # rungs whose printed notehead the detector never boxed. The detector's
    # recall is the one witness that fails where heads fuse with their
    # rungs, so on its own it may not refuse (CLAUDE.md §2 rule 8). The
    # paper is the second witness — `Q.LEDGER_INK_UNDER`, GATHER's ink
    # fraction in a notehead-sized window on the rung — and only it resolves:
    #   ink well above its own background -> KEPT, `ink_under_the_rung`
    #   ink at the paper's floor          -> REFUSED, `no_head_on_the_rung`
    #   in between, or no witness at all  -> ABSTAINED,
    #                                        `rung_without_boxed_head`
    # An abstained rung is NOT a kept rung for any consumer that counts kept
    # rungs; see FINDINGS §3.4g-3 for the one consumer that does not yet
    # honour that (`notehead_precision._ledger_rungs_in_cell`, lane 2.7b).
    # ⚠️ WITHOUT A CELL UNIT THE HEAD RULE CANNOT RUN AND DOES NOT GUESS:
    # the box falls through to `ledger_line` exactly as it did before 3.4g-2.
    if heads is not None and not heads["near"]:
        witness = _ink_under_the_rung(ev)
        detail["ink_witness"] = witness
        if witness is None:
            declined = ev.refusals(Q.LEDGER_INK_UNDER)
            if declined:
                detail["ink_witness_declined"] = declined[-1].reason
        if witness is not None:
            used.append(witness["row"])
            under, back = witness["under"], witness["background"]
            if back is not None and under - back >= LEDGER_INK_KEPT_MIN:
                return Ruling(value=False, reason="ink_under_the_rung",
                              used=tuple(used), detail=detail)
            if under <= LEDGER_INK_REFUSED_MAX:
                return Ruling(value=True, reason="no_head_on_the_rung",
                              used=tuple(used), detail=detail)
        return Ruling(value=None, reason="rung_without_boxed_head",
                      used=tuple(used), detail=detail)
    return Ruling(value=False, reason="ledger_line", used=tuple(used),
                  detail=detail)


def _ink_under_the_rung(ev: Evidence) -> Optional[Dict[str, Any]]:
    """GATHER's `Q.LEDGER_INK_UNDER` on this glyph, or `None`.

    ⚠️ AN ABSTENTION IS NOT A READING OF EMPTY PAPER. GATHER files
    `no_mask` / `no_staff_geometry` where it could not look; `ev.rows`
    returns observations only, so those arrive here as `None` — declined,
    and the decision abstains rather than reading 0.0 into a refusal.
    """
    rows = ev.rows(Q.LEDGER_INK_UNDER)
    if not rows:
        return None
    row = rows[-1]
    try:
        under = float(row.value)
    except (TypeError, ValueError):
        return None
    d = row.detail or {}
    back = d.get("ink_background")
    # ⚠️ ALL FIVE OF GATHER'S NUMBERS RIDE ON THE VERDICT, so the viewer and
    # a crop can show WHICH window saw the head and what the paper beside it
    # read -- a threshold crossed by one window is a different fact from one
    # crossed by all three.
    return {"row": row.id, "under": round(under, 4),
            "background": None if back is None else round(float(back), 4),
            "best_window": d.get("ink_best_window"),
            "windows": d.get("ink_windows"),
            "background_windows": d.get("ink_background_windows")}


@decision(
    quantity=Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL,
    composed_from=(Q.GLYPH_BOX, Q.HUMAN_BOX_VERDICT,
                   Q.GLYPH_BAND_DISTANCE),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_BOX, Q.HUMAN_BOX_VERDICT,
           Q.GLYPH_BAND_DISTANCE),
    subjects_from=Q.GLYPH_BOX,
    subjects_classed=("accidental",),
    reasons=_human_only_reasons(Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL),
    mode=Mode.ADDITIVE,
)
def adjudicate_accidental_is_not_an_accidental(ev: Evidence) -> Ruling:
    """Is this box the detector called an accidental a symbol at all?

    HUMAN WITNESS ONLY — see the module docstring. Two of Sean's eighteen
    were `accidentalFlat` and one `accidentalNatural`, and two more were the
    accidentals he marked `belongs to Violin II`, which `glyph_owner` could
    not hear because its domain is the contested NOTEHEAD population.
    `owner:other` reaches this decision and refuses them on the Viola.
    """
    detail, used = _class_detail(ev)
    refused = _refused_by_a_human(ev, detail)
    if refused is not None:
        return refused
    return Ruling(value=False, reason="accidental", used=used, detail=detail)


@decision(
    quantity=Q.REST_IS_NOT_A_REST,
    composed_from=(Q.GLYPH_BOX, Q.REST, Q.HUMAN_BOX_VERDICT,
                   Q.GLYPH_BAND_DISTANCE),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_BOX, Q.REST, Q.HUMAN_BOX_VERDICT,
           Q.GLYPH_BAND_DISTANCE),
    subjects_from=Q.REST,
    reasons=_human_only_reasons(Q.REST_IS_NOT_A_REST),
    mode=Mode.ADDITIVE,
)
def adjudicate_rest_is_not_a_rest(ev: Evidence) -> Ruling:
    """Is this box the detector called a rest a symbol at all?

    HUMAN WITNESS ONLY. ⚠️ NOT A SECOND REST GEOMETRY: the rest's SLOT is
    lane 2.12b-cal's open question (`rhythm.py`), and a rival copy of it here
    would be the second reader of one fact this project keeps paying for.
    `Q.REST` is read for the domain — every rest glyph and only those.
    """
    _ = ev.rows(Q.REST)       # the domain's own quantity, declared and read
    detail, used = _class_detail(ev)
    refused = _refused_by_a_human(ev, detail)
    if refused is not None:
        return refused
    return Ruling(value=False, reason="rest", used=used, detail=detail)


@decision(
    quantity=Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO,
    composed_from=(Q.GLYPH_BOX, Q.HUMAN_BOX_VERDICT,
                   Q.GLYPH_BAND_DISTANCE),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_BOX, Q.HUMAN_BOX_VERDICT,
           Q.GLYPH_BAND_DISTANCE),
    subjects_from=Q.GLYPH_BOX,
    subjects_classed=("arpeggiato",),
    reasons=_human_only_reasons(Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO),
    mode=Mode.ADDITIVE,
)
def adjudicate_arpeggiato_is_not_an_arpeggiato(ev: Evidence) -> Ruling:
    """Is this box the detector called an arpeggiato a symbol at all?

    HUMAN WITNESS ONLY, and its only consumer is the EXPORT census: the
    family has no quantity (`gather_coverage.FAMILY_TO_Q["arpeggiato"] is
    None`) and no exporter writes one. Three of Sean's eighteen were these.
    """
    detail, used = _class_detail(ev)
    refused = _refused_by_a_human(ev, detail)
    if refused is not None:
        return refused
    return Ruling(value=False, reason="arpeggiato", used=used, detail=detail)


@decision(
    quantity=Q.ARC_IS_NOT_AN_ARC,
    composed_from=(Q.GLYPH_BOX, Q.ARC_BOX, Q.HUMAN_BOX_VERDICT,
                   Q.GLYPH_BAND_DISTANCE),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_BOX, Q.ARC_BOX, Q.HUMAN_BOX_VERDICT,
           Q.GLYPH_BAND_DISTANCE),
    subjects_from=Q.ARC_BOX,
    reasons=_human_only_reasons(Q.ARC_IS_NOT_AN_ARC),
    mode=Mode.ADDITIVE,
)
def adjudicate_arc_is_not_an_arc(ev: Evidence) -> Ruling:
    """Is this box the detector called a slur or a tie a symbol at all?

    HUMAN WITNESS ONLY. ⚠️ NOT a second opinion on `Q.ARC_KIND`: *slur or
    tie* and *a symbol or not* are different questions and this asks only the
    second.
    """
    _ = ev.rows(Q.ARC_BOX)       # the domain's own quantity, declared and read
    detail, used = _class_detail(ev)
    refused = _refused_by_a_human(ev, detail)
    if refused is not None:
        return refused
    return Ruling(value=False, reason="arc", used=used, detail=detail)


@decision(
    quantity=Q.DYNAMIC_IS_NOT_A_DYNAMIC,
    composed_from=(Q.GLYPH_BOX, Q.DYNAMIC_LETTER, Q.HUMAN_BOX_VERDICT,
                   Q.GLYPH_BAND_DISTANCE),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_BOX, Q.DYNAMIC_LETTER, Q.HUMAN_BOX_VERDICT,
           Q.GLYPH_BAND_DISTANCE),
    subjects_from=Q.DYNAMIC_LETTER,
    reasons=_human_only_reasons(Q.DYNAMIC_IS_NOT_A_DYNAMIC),
    mode=Mode.ADDITIVE,
)
def adjudicate_dynamic_is_not_a_dynamic(ev: Evidence) -> Ruling:
    """Is this box the detector called a dynamic letter a symbol at all?

    HUMAN WITNESS ONLY. Its consumer is `adjudicate_dynamic`, which must not
    spell a refused letter into a word — one refused `f` beside a real one is
    the difference between `f` and `ff`.
    """
    _ = ev.rows(Q.DYNAMIC_LETTER)       # the domain's own quantity, declared and read
    detail, used = _class_detail(ev)
    refused = _refused_by_a_human(ev, detail)
    if refused is not None:
        return refused
    return Ruling(value=False, reason="dynamic", used=used, detail=detail)


@decision(
    quantity=Q.ARTICULATION_IS_NOT_AN_ARTICULATION,
    composed_from=(Q.GLYPH_BOX, Q.ARTICULATION_MARK, Q.HUMAN_BOX_VERDICT,
                   Q.GLYPH_BAND_DISTANCE),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_BOX, Q.ARTICULATION_MARK, Q.HUMAN_BOX_VERDICT,
           Q.GLYPH_BAND_DISTANCE),
    subjects_from=Q.ARTICULATION_MARK,
    reasons=_human_only_reasons(Q.ARTICULATION_IS_NOT_AN_ARTICULATION),
    mode=Mode.ADDITIVE,
)
def adjudicate_articulation_is_not_an_articulation(ev: Evidence) -> Ruling:
    """Is this box the detector called an articulation a symbol at all?

    HUMAN WITNESS ONLY. Its consumer is `export._place_articulations`.
    """
    _ = ev.rows(Q.ARTICULATION_MARK)       # the domain's own quantity, declared and read
    detail, used = _class_detail(ev)
    refused = _refused_by_a_human(ev, detail)
    if refused is not None:
        return refused
    return Ruling(value=False, reason="articulation", used=used, detail=detail)


#: Every family refusal, and the quantity that names it. ⚠️ DERIVED FROM
#: `_OK`, never typed twice: `export.py` counts by walking this, so a family
#: added above is counted without a second list being remembered.
FAMILY_REFUSALS: Tuple[str, ...] = tuple(_OK)
