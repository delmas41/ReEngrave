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
                                 CELL_EDGE_TOLERANCE_PAGE_PX,
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

#: ⚠️⚠️ ROADMAP 3.4g-3 — THE SECOND WITNESS'S THRESHOLDS, on
#: `Q.LEDGER_INK_UNDER` (the ink fraction in a notehead-sized window on the
#: rung, stroke removed, off the staff-erased raster; `gather.
#: ledger_ink_under`). Sean, 2026-09-27: of the four rungs 3.4g-2 refused
#: `no_head_on_the_rung`, TWO were real rungs whose head the detector never
#: boxed — so "no boxed head" is *cannot tell*, and the paper decides.
#:
#:   KEPT (`ink_under_the_rung`)  under >= `LEDGER_INK_KEPT_MIN` AND
#:                                under - background >=
#:                                `LEDGER_INK_KEPT_CONTRAST_MIN`
#:   REFUSED (`no_head_on_the_rung`, two witnesses)
#:                                under <= `LEDGER_INK_REFUSED_MAX`
#:   otherwise                    the abstention stands
#:
#: ⚠️ MEASURED, NOT CHOSEN — `benchmarks/omr-family-refusals-2026-09/probe/
#: ledger_ink_hist.py` on a real arm gather of Litolff pdf pages 1-12
#: (4,947 ledger boxes; FINDINGS §3.4g-3). Positives = kept rungs with a
#: notehead box ON the rung (n 548); negatives = boxes refused
#: `inside_the_staff` / `on_a_staff_line` (n 3,821).
#:   * `LEDGER_INK_KEPT_MIN` 0.55 = the positives' p5 of `under` (0.574),
#:     floored to 0.05.
#:   * `LEDGER_INK_KEPT_CONTRAST_MIN` 0.10 = the positives' p5 of
#:     under - background (0.098), to 0.05. Together they keep 501 of 548
#:     positives (0.91).
#:   * `LEDGER_INK_REFUSED_MAX` 0.05: 0 of 548 positives read at or below it
#:     (their minimum is 0.076); 1,024 of 3,821 negatives do.
#: ⚠️ THE NEGATIVES CANNOT BOUND THE KEEP SIDE, and that is stated rather
#: than hidden: inside the band the erased raster still holds the staff's
#: own notes, so 23% of negatives clear both keep thresholds. The keep rule
#: is only ever applied to a box that is OUTSIDE the band, off every line,
#: rung-thick and has no boxed head — the population where a head-sized
#: blot of ink is least likely to be anything else. RED (the windows
#: swapped, background read as `under`): AUC 0.786 against 0.931 for the
#: real window, so the window measures something its neighbourhood does not.
LEDGER_INK_KEPT_MIN = 0.55
LEDGER_INK_KEPT_CONTRAST_MIN = 0.10
LEDGER_INK_REFUSED_MAX = 0.05


def _glyph_box_row(ev: Evidence):
    rows = ev.rows(Q.GLYPH_BOX)
    return rows[-1] if rows else None


# ─────────────────────────────────────────────────────────────────────────────
# §REST-DUPLICATE — ROADMAP 2.15. One physical rest, boxed more than once.
# ─────────────────────────────────────────────────────────────────────────────
#
# ⚠️⚠️ MEASURED, NOT THE WORK ORDER'S OWN GUESS. ROADMAP 2.15 said the two
# boxes of its own named example "overlap substantially"; the record
# disagrees. `glyph/2/1/0/7/0` / `.../1` (Brahms, provenance c19cbca7)
# measure IoU 0.16 -- moderate, not substantial -- and a crop of it
# (`benchmarks/omr-bar-sum-holdout-2026-09/out/print/r215-*`) shows ONE
# filled rectangle (a whole rest) with two detector boxes side by side, each
# covering roughly half of it: the SHATTERING plate (CLAUDE.md SS10)
# fragmented one mark's ink and the detector drew a box per fragment.
#
# The record's own IoU distribution, over every pair of rest glyphs with a
# STANDING decided `Q.DURATION` verdict in one cell on both documents
# (Brahms whole-movement 20260928T110702Z and the Litolff shared record --
# ⚠️ SUPERSESSION MUST BE RESOLVED FIRST: a naive read of `outcome ==
# "decided"` over every verdict row counts an EVALUATE-stage revision
# alongside the ADJUDICATE-stage reading it superseded as if they were two
# glyphs, and manufactured 214 fake "duplicates" -- all ONE subject twice --
# on the clean engraved control before that bug was found and fixed in the
# probe), splits into three populations, not one:
#
#   genuinely unrelated   IoU exactly 0.0 -- 1,284/1,713 same-class pairs on
#                         Brahms, 83/154 on Litolff. The smallest NONZERO
#                         pair the other direction (Litolff, 0.0019) is two
#                         boxes roughly 1,000 canonical units apart, one of
#                         them a misdetection nowhere near the other.
#   one mark, same class  ANY nonzero overlap, up to 0.71 on BOTH documents
#                         and never higher -- crops across that whole range
#                         (Brahms 0.05, 0.16, 0.37, 0.71) each show ONE
#                         rectangle, two boxes. No gap exists inside this
#                         population; the gap is between it and zero.
#   one mark, role-twin   DIFFERENT classes (`rest8th`/`rest16th` etc.), IoU
#                         clustered 0.80-1.00 on Brahms -- a crop shows one
#                         hook-shaped mark with both boxes drawn almost
#                         exactly on top of each other.
#
# So ONE threshold serves both same-class and different-class pairs: it
# sits inside the empty gap above "exactly 0" and above the Litolff noise
# floor (0.0019, 0.016) and below every crop-confirmed real pair (0.028 and
# up). ⚠️ `Q.DURATION` HAS NOT RUN YET at this point in `adjudicate.ORDER`
# (`Q.REST_IS_NOT_A_REST` is scheduled before it), so "do the two boxes
# AGREE" is read off the CLASS `Q.REST`/`Q.GLYPH_BOX` already filed at
# GATHER, never off a beats figure this decision cannot see -- which is
# also why this is not the second rest-slot geometry the module docstring
# warns against: it never asks what VALUE a box means, only whether two
# boxes are the same ink.
REST_DUPLICATE_IOU_MIN = 0.02


def _rest_box_iou(a: Any, b: Any) -> float:
    """IoU of two `Q.GLYPH_BOX` VALUE tuples `(class, x, y, w, h)`.

    ⚠️ CANONICAL, NOT PAGE PIXELS, and that is safe ONLY because both boxes
    come from `_cell_rest_boxes`'s domain -- the SAME cell. A canonical box
    is rescaled PER CELL (CLAUDE.md SS10: "a canonical cell frame cannot
    answer a cross-staff question"), so two boxes sharing one cell share one
    rescaling and the ratio is exact; comparing across cells this way would
    not be, and nothing here does.
    """
    _, x0a, y0a, wa, ha = a
    _, x0b, y0b, wb, hb = b
    x1a, y1a = x0a + wa, y0a + ha
    x1b, y1b = x0b + wb, y0b + hb
    iw = max(0.0, min(x1a, x1b) - max(x0a, x0b))
    ih = max(0.0, min(y1a, y1b) - max(y0a, y0b))
    inter = iw * ih
    union = wa * ha + wb * hb - inter
    return inter / union if union > 0 else 0.0


def _cell_rest_boxes(ev: Evidence, cell) -> Dict[Any, Any]:
    """Every rest glyph's `Q.GLYPH_BOX` row in THIS glyph's own cell, keyed
    by subject -- including this glyph's own.

    ⚠️ SAME CELL ONLY, `_ledger_rungs_in_cell`'s own rule (this module's
    §LEDGER docstring): the crop that makes a cell wide enough to hold a
    note also holds the rest ink a duplicate detection would fragment, and a
    physical mark that is genuinely one cell wide never needs a wider
    search. `Q.REST` names the domain, `Q.GLYPH_BOX` carries the geometry --
    two reads of two quantities already in `wants`, not a new one.
    """
    rest_subjects = {r.subject for r in
                     ev.rows(Q.REST, scope=Scope.SELF_AND_DESCENDANTS,
                             subject=cell)}
    out: Dict[Any, Any] = {}
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        if r.subject in rest_subjects:
            out[r.subject] = r
    return out


def _rest_duplicate_priority(row) -> Tuple[float, int]:
    """Higher wins: detector confidence first, then the LOWER glyph index --
    an arbitrary but total and DETERMINISTIC tie-break, so two glyphs
    evaluating each other always agree on which one survives."""
    score = row.score if row.score is not None else 0.0
    idx = row.subject.glyph if row.subject.glyph is not None else 0
    return (score, -idx)


def _duplicate_box_refusal(ev: Evidence, this_row, detail: Dict[str, Any]
                           ) -> Optional[Ruling]:
    """ROADMAP 2.15: is this box the SAME physical mark as another rest
    glyph the detector boxed in this cell?

    ⚠️ TWO OUTCOMES, SYMMETRIC BY CONSTRUCTION, NEVER A THIRD. Every glyph
    in an overlapping cluster runs this SAME rule over the SAME evidence
    (no shared state between calls), so:

    * a SAME-CLASS overlapping pair is one mark under two readings that
      would otherwise both reach EXPORT and both be summed -- ROADMAP
      2.15's whole complaint. The pair converges on exactly one survivor
      (`_rest_duplicate_priority`'s max) and the other is refused
      `rest_is_a_duplicate_box`.
    * a DIFFERENT-CLASS overlapping pair is one mark whose VALUE this
      decision cannot tell -- CLAUDE.md rule 8, "a fallback never converts
      cannot tell into an answer" -- so BOTH are refused. The bar loses
      this event's contribution; ROADMAP 2.8 holds the bar out if that now
      leaves it short, which is the right outcome for ink nobody could read
      to one value, and the right one FOR EXPORT to reach on its own
      (`export._place_notes` already honours a decided `Q.REST_IS_NOT_A_
      REST`, so no export-side change is needed for either outcome).

    A glyph that disagrees with ANY overlapping sibling is refused for the
    disagreement even if it would also have won a same-class comparison
    against a different sibling -- disagreement is the more conservative
    reading and wins.
    """
    cell = ev.subject.at(Kind.CELL)
    if cell is None:
        return None
    this_val = this_row.value
    if not isinstance(this_val, (list, tuple)) or len(this_val) != 5:
        return None
    this_class = this_val[0]
    this_priority = _rest_duplicate_priority(this_row)

    disagreeing: List[str] = []
    better: Optional[Any] = None
    for subj, row in _cell_rest_boxes(ev, cell).items():
        if subj == ev.subject:
            continue
        other_val = row.value
        if not isinstance(other_val, (list, tuple)) or len(other_val) != 5:
            continue
        if _rest_box_iou(this_val, other_val) < REST_DUPLICATE_IOU_MIN:
            continue
        if other_val[0] != this_class:
            disagreeing.append(row.id)
            continue
        if _rest_duplicate_priority(row) > this_priority:
            better = row

    if disagreeing:
        detail["duplicate_disagrees_with"] = list(disagreeing)
        return Ruling(value=True, reason="rest_is_a_duplicate_box",
                      used=(this_row.id,) + tuple(disagreeing), detail=detail)
    if better is not None:
        detail["duplicate_of"] = better.id
        return Ruling(value=True, reason="rest_is_a_duplicate_box",
                      used=(this_row.id, better.id), detail=detail)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# §REST-PLACEMENT — ROADMAP 2.33. Sean, 2026-09-29
# (`docs/DECISIONS.md`, `benchmarks/omr-owner-domain-2026-09/
# PLACEMENT-CONVENTIONS.md` Rests row): *"whole and half [rests] will always
# be found geometrically near the horizontal middle of the bar -- I saw some
# false whole and half rests far off to one side"*, and *"I don't think rests
# are found as high as note heads on the ledger lines."* Narrowed and
# recalibrated across the same conversation, in order:
#
#   1. answering the first quote, Sean confirmed the CENTRING rule is for
#      WHOLE rests only: *"a whole rest = the bar, centred"*. Half and
#      smaller rests do NOT get a blanket off-centre refusal -- *"based upon
#      the other notes in a measure there will be a limited space
#      geometrically where the rest can be"*, i.e. a BEAT-SLOT rule keyed on
#      the bar's other events, not a bar-wide fraction. That fuller rule is
#      DESIGNED, not built -- see the docstring above
#      `_rest_overlaps_notehead_refusal` below for what is built instead and
#      why, and `benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` §20 for
#      the design written out in full.
#   2. answering the second quote with a numeric window (2.5 spaces beyond
#      the outer line), Sean added a correction from his own observation:
#      *"I did see some 8th note rests outside the staff but not nearly as
#      far as note heads."* So the window is PER REST CLASS, not one number
#      -- tight for whole/half/quarter (which this project has never seen
#      leave the staff at all) and wider for 8th-and-smaller (which Sean has
#      seen do it, displaced for a second voice, `REST_VOICE_DISPLACEMENT_
#      MIN_STEPS` in `rhythm.py`). CALIBRATED TO SEAN'S OBSERVATION, NOT
#      MEASURED -- no crop was pulled this pass (2026-09-29's process
#      decision: conceptual wiring, no crop batches); both tiers are
#      CONVENTION ASSUMED and are falsified by a print crop showing a
#      tight-tier rest genuinely printed beyond its own window, or a
#      wide-tier rest printed farther out than 2.5 spaces.
#   3. a THIRD, independent cause Sean named from his own crops: *"a notehead
#      looked a little bit like a whole note rest when the notehead was cut
#      in half by the image crop -- all examples where the rests were in a
#      staff above or below the main staff."* A notehead sliced by the
#      cell's own top or bottom edge leaves a flat black rectangle -- exactly
#      a `restWhole`/`restHBar` silhouette -- and it is a CROP ARTEFACT, not
#      a placement question, so it gets its own direct-cause refusal
#      (`_rest_clipped_by_crop_refusal`) rather than being folded into the
#      vertical window. The two overlap in what they catch (a fragment flush
#      against the edge is also, ordinarily, far beyond the staff), and both
#      are kept: the window is the geometric backstop, the crop check is the
#      named cause.
#
# ⚠️ ALL THREE RUN BEFORE `Q.GLYPH_OWNER`, STRUCTURALLY, NOT BY ANY GATE
# WRITTEN HERE. `adjudicate.ORDER` schedules `Q.REST_IS_NOT_A_REST` before
# `Q.GLYPH_OWNER` (the same slot `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` holds, and for
# the same reason: a question about what a box IS must be settled before the
# questions that assume the answer). So a rest this file refuses can never
# have a DECIDED `Q.GLYPH_OWNER` verdict on the record yet to contradict --
# there is nothing to fight, and no code here pretends otherwise by reading a
# verdict that cannot exist. `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` is the one
# exception: it runs BEFORE this file's rest checks (beside the ledger, ahead
# of `Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL`/`Q.REST_IS_NOT_A_REST` in `ORDER`),
# so `_rest_overlaps_notehead_refusal` below is a real CONNECTION to an
# already-decided verdict, not a guess about one still in flight.
# ─────────────────────────────────────────────────────────────────────────────

#: Rule 1 (restWhole only): how far a rest's centre may sit from the bar's
#: own horizontal centre, as a fraction of the FULL bar width, before it is
#: refused. 1/6 is "the middle third" stated geometrically -- the band
#: [1/3, 2/3] of the bar has half-width 1/6 around the centre -- the smallest
#: named fraction that reads as "near the middle" rather than a tuned number;
#: CLAUDE.md rule 5 ("print before default") is not violated because nothing
#: here defaults ON agreement with a reading, but see the module-level note
#: above: no crop confirms this exact fraction, so it is CONVENTION ASSUMED.
REST_WHOLE_CENTER_MAX_OFFSET_FRACTION = 1.0 / 6.0

#: Rule 2 (every rest class): how far beyond the staff band (`_beyond_spaces`,
#: the SAME "spaces past line 1 or line 5" measurement `_LEDGER` uses) a
#: rest's centre may sit before it is refused as belonging to some OTHER
#: staff's ink rather than a legitimate mark on this one. Two tiers:
#:
#:   TIGHT (1.0 space) -- whole/half/quarter and the two bar-filling long
#:   rests (`restHNr`, `restHBar`): this project has never observed one of
#:   these leave the printed staff at all; 1.0 is a small margin over "never"
#:   for registration scatter, not a measured tail.
#:   WIDE (2.5 spaces) -- 8th and smaller, per Sean's own correction
#:   (*"I did see some 8th note rests outside the staff but not nearly as
#:   far as note heads"*): far enough to admit a genuinely displaced-voice
#:   8th/16th rest (`REST_VOICE_DISPLACEMENT_MIN_STEPS` in `rhythm.py`, which
#:   never leaves the staff band at all -- a DIFFERENT, narrower convention
#:   about which VOICE a rest belongs to, not which STAFF), and short of how
#:   far a note on a ledger line goes (CLAUDE.md §10's Brahms C Horn 2, 4.5
#:   spaces below its staff).
#:
#: Unknown/unlisted classes fall back to the TIGHT tier -- the conservative
#: default matches "abstain rather than answer" only in spirit; here the
#: geometry is not abstained, just held to the stricter of the two observed
#: bounds until a class is actually seen wide.
REST_VERTICAL_TIGHT_BEYOND_SPACES = 1.0
REST_VERTICAL_WIDE_BEYOND_SPACES = 2.5
REST_VERTICAL_WIDE_CLASSES = frozenset((
    "rest8th", "rest16th", "rest32nd", "rest64th", "rest128th",
))


def _rest_vertical_limit_spaces(cls: Any) -> float:
    name = str(cls).lower() if cls is not None else ""
    for wide in REST_VERTICAL_WIDE_CLASSES:
        if name == wide.lower():
            return REST_VERTICAL_WIDE_BEYOND_SPACES
    return REST_VERTICAL_TIGHT_BEYOND_SPACES


#: Rule 3's overlap floor. NOT a new measurement -- the SAME test
#: (`_rest_box_iou`, the SAME geometric fact: two detector boxes drawn on one
#: mark) at the SAME floor `REST_DUPLICATE_IOU_MIN` was measured at (module
#: docstring §REST-DUPLICATE): the empty gap between "genuinely unrelated"
#: (IoU exactly 0.0) and the smallest crop-confirmed real pair holds for any
#: pair of classes the test is applied to, not only a rest-vs-rest pair.
REST_NOTEHEAD_OVERLAP_IOU_MIN = REST_DUPLICATE_IOU_MIN


def _cell_box_page_px(ev: Evidence) -> Optional[List[float]]:
    """This bar's own page-pixel rectangle, `(x0, y0, x1, y1)`, or `None`.

    ⚠️ A DUPLICATE OF `notehead_precision._cell_box_page`, ON PURPOSE, THE
    SAME SHAPE AS `_cell_staff_space` ALREADY DUPLICATED BETWEEN THE TWO
    FILES. `inventory._never_read`'s AST walk follows a same-module helper
    call, and (since 2.27c) one hop through a `from . import X` MODULE
    import — but not a direct `from .module import name` NAME import, which
    is what importing the function itself would be. A cross-module import
    here would leave `Q.CELL_BOX` declared in `wants` and reported as never
    read, exactly the "inert declaration" `inventory --check` exists to
    catch — so the reader is one line, local, and real.
    """
    rows = ev.rows(Q.CELL_BOX, scope=Scope.SELF_AND_ANCESTORS)
    if not rows or not isinstance(rows[-1].value, (list, tuple)) \
            or len(rows[-1].value) != 4:
        return None
    return [float(v) for v in rows[-1].value]


def _rest_off_center_refusal(ev: Evidence, this_row, detail: Dict[str, Any]
                             ) -> Optional[Ruling]:
    """Rule 1: is this WHOLE rest's centre far from the bar's own centre?

    ⚠️ CALLER RESTRICTS TO `restWhole` -- see the section docstring, Sean's
    own narrowing. This function does not re-check the class.

    ⚠️ NO EVENT/VOICE READ, AND NONE IS NEEDED. `adjudicate.ORDER` places
    `Q.REST_IS_NOT_A_REST` before `Q.EVENT` and `Q.VOICES` (both want
    `Q.DURATION`, itself after this one), so this rule could not read either
    even if the convention wanted it to -- and Sean's own narrowing says it
    should not: a whole rest denoting one voice's silence for the WHOLE bar
    is centred regardless of what another voice is doing (a second voice's
    own rest is vertically, never horizontally, displaced -- rule 2 and
    `rhythm.py`'s `_rest_voice_side`).

    ⚠️ THE CELL FRAME HAS NO HORIZONTAL PAD. `measure_extractor`'s own cut
    grows the cell VERTICALLY only (its own module docstring: "bounded by
    adjacent barlines and the staff's vertical band (WITH SOME PADDING)" --
    the padding is named for the vertical band alone), so `Q.CELL_BOX`'s own
    [x0, x1] IS the bar's horizontal extent and no second measurement is
    invented here.
    """
    cell_box = _cell_box_page_px(ev)
    page_box = (this_row.detail or {}).get("bbox_page_px")
    if cell_box is None or not page_box or len(page_box) != 4:
        # ⚠️ DECLINED, NOT DEFAULTED -- no page frame for the bar or the
        # glyph, no opinion (the same shape `_clipped_fragment` returns
        # `False` for a missing frame).
        return None
    bx0, _by0, bx1, _by1 = cell_box
    width = bx1 - bx0
    if width <= 0:
        return None
    rx0, _ry0, rx1, _ry1 = page_box
    centre = (rx0 + rx1) / 2.0
    offset = abs(centre - (bx0 + bx1) / 2.0) / width
    detail["bar_centre_offset_fraction"] = round(offset, 4)
    if offset > REST_WHOLE_CENTER_MAX_OFFSET_FRACTION:
        return Ruling(value=True, reason="rest_off_center",
                      used=(this_row.id,), detail=detail)
    return None


def _rest_clipped_by_crop_refusal(ev: Evidence, this_row,
                                  detail: Dict[str, Any]) -> Optional[Ruling]:
    """Rule 3 (named third in the section docstring, checked first below):
    is this box flush against the CELL's own crop edge?

    ⚠️ THE EDGE TEST IS IMPORTED, NOT RESTATED -- `notehead_precision.
    _clipped_fragment`'s own edge half, `CELL_EDGE_TOLERANCE_PAGE_PX` against
    `_cell_box_page_px`'s page-pixel cell box (a duplicate reader, not a
    duplicate constant -- see that function's own docstring for why).
    That function ALSO gates on
    height (a notehead sliver reads short); this one does not, because
    Sean's own case is the opposite shape -- a notehead cut in HALF by the
    crop can measure a NORMAL rest height while being pure crop artefact, so
    a height gate here would let the exact case through. The edge test alone
    is what a `restWhole`/`restHBar`-shaped fragment shares with the real
    thing being cut.

    ⚠️ NEVER RELOCATED. The neighbour staff's own cell holds its own
    detection of the same ink (CLAUDE.md §10's ledger-line rule states this
    for cross-staff ink generally); this refuses ON THIS STAFF and stops
    there.
    """
    page_box = (this_row.detail or {}).get("bbox_page_px")
    cell_box = _cell_box_page_px(ev)
    if not page_box or len(page_box) != 4 or cell_box is None:
        return None
    py0, py1 = page_box[1], page_box[3]
    cy0, cy1 = cell_box[1], cell_box[3]
    dist = min(abs(py0 - cy0), abs(py1 - cy1))
    detail["edge_distance_page_px"] = round(dist, 3)
    if dist <= CELL_EDGE_TOLERANCE_PAGE_PX:
        return Ruling(value=True, reason="rest_clipped_by_crop",
                      used=(this_row.id,), detail=detail)
    return None


def _rest_vertical_window_refusal(ev: Evidence, this_row,
                                  detail: Dict[str, Any]) -> Optional[Ruling]:
    """Rule 2: is this rest's centre farther outside the staff band than its
    own class is ever seen to go?

    ⚠️ THE GEOMETRY IS SHARED WITH THE LEDGER, NOT COPIED FOR THIS RULE --
    `_ledger_geometry` and `_beyond_spaces` measure "how many spaces past
    line 1 or line 5", the identical question a ledger rung answers about
    itself. A rest and a ledger box are read by the same ruler because they
    ARE the same question about two different classes of ink.
    """
    step, geom_rows = _ledger_geometry(ev, this_row)
    if step is None:
        return None
    beyond = _beyond_spaces(step)
    detail["beyond_the_band_spaces"] = round(beyond, 4)
    limit = _rest_vertical_limit_spaces(detail.get("class"))
    detail["vertical_limit_spaces"] = limit
    if beyond > limit:
        return Ruling(value=True, reason="rest_outside_its_staff",
                      used=(this_row.id,) + tuple(geom_rows), detail=detail)
    return None


def _cell_notehead_boxes(ev: Evidence, cell) -> Dict[Any, Any]:
    """Every NOTEHEAD glyph's `Q.GLYPH_BOX` row in this cell, keyed by
    subject. The mirror of `_cell_rest_boxes` above, over `Q.NOTEHEAD_CLASS`'s
    domain instead of `Q.REST`'s."""
    notehead_subjects = {r.subject for r in
                         ev.rows(Q.NOTEHEAD_CLASS,
                                scope=Scope.SELF_AND_DESCENDANTS,
                                subject=cell)}
    out: Dict[Any, Any] = {}
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        if r.subject in notehead_subjects:
            out[r.subject] = r
    return out


def _rest_overlaps_notehead_refusal(ev: Evidence, this_row,
                                    detail: Dict[str, Any]
                                    ) -> Optional[Ruling]:
    """The decisive sub-rule Sean's beat-slot design (section docstring, item
    1) reduces to WITHOUT waiting on `Q.EVENT`/`Q.VOICES`: this glyph's own
    ink cannot simultaneously BE a rest (an absence of ink at that position)
    and sit on top of a notehead's ink, in ANY voice -- overlapping detector
    boxes on one cell are two readings of ONE mark (§REST-DUPLICATE's own
    argument), never two symbols legitimately sharing one spot regardless of
    which voice either belongs to. So this needs no voice count and no onset
    column, and answers a narrower question than the full design: not "is
    this rest's position explained by the bar's other events" but "is this
    rest's BOX the same ink as a notehead's BOX" -- the one case the design
    forces a verdict about today. The full beat-slot rule (a rest's onset
    from its voice's preceding durations, checked against `Q.ONSET_COLUMN`
    and the horizontal gap between neighbouring events) is NAMED, NOT BUILT
    -- `benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` §20.

    ⚠️ A NOTEHEAD ALREADY REFUSED PROVES NOTHING. If the overlapping box's
    own `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` verdict is DECIDED refused, its ink
    might be the SAME misread mark this rest box also mis-boxed (two guesses
    about one thing, not a rest sitting on a real note) -- CLAUDE.md rule 8,
    a cannot-tell case is not converted into a refusal. Reading that verdict
    here is safe only because `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` runs BEFORE this
    decision in `adjudicate.ORDER` (see the section docstring); a verdict
    read one line earlier in the same stage would be `None` regardless of
    what the record eventually decides, and this function would then, and
    only then, be guessing.
    """
    cell = ev.subject.at(Kind.CELL)
    if cell is None:
        return None
    this_val = this_row.value
    if not isinstance(this_val, (list, tuple)) or len(this_val) != 5:
        return None
    overlapping: List[str] = []
    for subj, row in _cell_notehead_boxes(ev, cell).items():
        other_val = row.value
        if not isinstance(other_val, (list, tuple)) or len(other_val) != 5:
            continue
        if _rest_box_iou(this_val, other_val) < REST_NOTEHEAD_OVERLAP_IOU_MIN:
            continue
        refusal = ev.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, subject=subj)
        if (refusal is not None and refusal.outcome == "decided"
                and refusal.value):
            continue
        overlapping.append(row.id)
    if overlapping:
        detail["rest_overlaps_notehead"] = list(overlapping)
        return Ruling(value=True, reason="rest_overlaps_a_notehead",
                      used=(this_row.id,) + tuple(overlapping), detail=detail)
    return None


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
# The seven decisions, plus 3.4g-4's three
#
# ⚠️ NAMED FUNCTIONS AND ONE BODY EACH, AND THE SHAPE IS DELIBERATE. A
# factory returning closures would give every spec a `fn.__name__` that
# `inventory._never_read` cannot find in the source it parses (it looks for a
# `FunctionDef` named `spec.name`), so every declared `wants` would be
# reported as unread — a derived check silently disabled by a code-style
# choice. Ten two-line functions keep the AST honest.
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
    # ── roadmap 3.4g-4 ──────────────────────────────────────────────────────
    Q.FLAG_IS_NOT_A_FLAG: "flag",
    Q.KEYSIG_MARKER_IS_NOT_A_MARKER: "keysig_marker",
    Q.TUPLET_MARKER_IS_NOT_A_MARKER: "tuplet_marker",
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
            if (under >= LEDGER_INK_KEPT_MIN and back is not None
                    and under - back >= LEDGER_INK_KEPT_CONTRAST_MIN):
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
                   Q.GLYPH_BAND_DISTANCE, Q.CELL_BOX, Q.STAFF_LINES,
                   Q.STAFF_SPACING, Q.NOTEHEAD_CLASS,
                   Q.NOTEHEAD_IS_NOT_A_NOTEHEAD),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_BOX, Q.REST, Q.HUMAN_BOX_VERDICT,
           Q.GLYPH_BAND_DISTANCE, Q.CELL_BOX, Q.STAFF_LINES,
           Q.STAFF_SPACING, Q.NOTEHEAD_CLASS, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD),
    subjects_from=Q.REST,
    reasons=HUMAN_REFUSAL_REASONS + (_OK[Q.REST_IS_NOT_A_REST],
                                     "rest_is_a_duplicate_box",
                                     "rest_clipped_by_crop",
                                     "rest_off_center",
                                     "rest_outside_its_staff",
                                     "rest_overlaps_a_notehead"),
    mode=Mode.ADDITIVE,
)
def adjudicate_rest_is_not_a_rest(ev: Evidence) -> Ruling:
    """Is this box the detector called a rest a symbol at all?

    HUMAN WITNESS, THEN ROADMAP 2.15's DUPLICATE-BOX GEOMETRY, THEN ROADMAP
    2.33's THREE PLACEMENT REFUSALS (module docstring §REST-PLACEMENT, in
    the order they are checked below):

      1. `rest_clipped_by_crop`  -- flush against the cell's own crop edge
                                    (a notehead sliced in half by the crop
                                    reads as this shape; checked FIRST as
                                    the direct, named cause).
      2. `rest_off_center`       -- WHOLE rests only, far from the bar's own
                                    horizontal centre.
      3. `rest_outside_its_staff` -- any rest class, farther outside the
                                    staff band than that class is ever seen
                                    to go (a per-class window, tight for
                                    whole/half/quarter, wider for 8th and
                                    smaller).
      4. `rest_overlaps_a_notehead` -- this box's ink is also a decided
                                    notehead's ink; two symbols cannot share
                                    one mark.

    ⚠️ NOT A SECOND REST-VALUE GEOMETRY: the rest's SLOT (which LINE it hangs
    on, and so what it is WORTH) is lane 2.12b-cal's open question
    (`rhythm.py`), and a rival copy of that here would be the second reader
    of one fact this project keeps paying for. 2.15's question, and 2.33's,
    are narrower and do not touch it: not *what is this rest worth*, but *is
    this box the SAME PHYSICAL INK as another mark*, or *is it geometrically
    where this project has ever seen its class printed* -- answered from
    `Q.GLYPH_BOX`'s geometry, `Q.REST`'s class and `Q.CELL_BOX`/`Q.STAFF_
    LINES`/`Q.STAFF_SPACING`'s frame, all already filed at GATHER, never from
    a slot reading. `Q.REST` is read for the domain — every rest glyph and
    only those.
    """
    _ = ev.rows(Q.REST)       # the domain's own quantity, declared and read
    detail, used = _class_detail(ev)
    refused = _refused_by_a_human(ev, detail)
    if refused is not None:
        return refused
    box_row = _glyph_box_row(ev)
    if box_row is not None:
        dup = _duplicate_box_refusal(ev, box_row, detail)
        if dup is not None:
            return dup
        clipped = _rest_clipped_by_crop_refusal(ev, box_row, detail)
        if clipped is not None:
            return clipped
        if str(detail.get("class")) == "restWhole":
            off_center = _rest_off_center_refusal(ev, box_row, detail)
            if off_center is not None:
                return off_center
        vertical = _rest_vertical_window_refusal(ev, box_row, detail)
        if vertical is not None:
            return vertical
        overlap = _rest_overlaps_notehead_refusal(ev, box_row, detail)
        if overlap is not None:
            return overlap
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


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 3.4g-4 — the three families 3.4g's first pass did not cover
#
# ⚠️ Sean's second and third stage-review passes (Clarinet p12, Viola p2)
# found them: the flag family (a `duplicate` on a `flag8thDown`, page 2) and
# the key-marker family named by the ROADMAP work order; the tuplet numeral
# is 3.4g's own closing line, *"a human witness reaches EVERY gathered
# family"* — `tuplet`/`fingering3` were the one family left with a gathered
# quantity (`Q.TUPLET_MARKER`) and no precision decision at all.
#
# ⚠️ FLAG AND TUPLET USE `subjects_from=Q.FLAG` / `Q.TUPLET_MARKER` — THEIR
# OWN GATHERED QUANTITY — EXACTLY AS REST/ARC/DYNAMIC/ARTICULATION DO, and
# NEVER a `Q.GLYPH_BOX` class narrowing, because a bare class-prefix narrowing
# is a documented footgun in this tree already: `key_signature_
# corroboration.py`'s own `startswith("key")` "also catches `keyboardPedalUp`
# — a PEDAL marking." `subjects_for`'s class narrowing matches `str.
# startswith` against the WHOLE lower-cased class name, not against
# `class_aliases`' family boundary, so a decision keyed on the bare `key`
# prefix would silently widen its domain to a family `gather_coverage.
# FAMILY_TO_Q` maps to `None`.
#
# `Q.KEYSIG_MARKER` cannot take that same route — `gather.
# _gather_keysig_markers` files it on the STAFF, not on a glyph, so
# `subjects_from=Q.KEYSIG_MARKER` at `scope=Kind.GLYPH` would find no glyph to
# collapse to. Its domain is therefore `Q.GLYPH_BOX` narrowed by
# `subjects_classed=("keySharp", "keyFlat", "keyNatural")` — `gather.
# _KEYSIG_CLASSES` exactly, not the bare `key` prefix above.
#
# The tuplet family has the SAME shape the key marker's `subjects_classed`
# avoids, which is why `subjects_from` is the exact quantity and not a class
# name at all: `gather_coverage.FAMILY_TO_Q` maps the WHOLE `tuplet` family
# (`tuplet0`-`9`, `tupletBracket`) and the WHOLE `fingering` family to
# `Q.TUPLET_MARKER`, but `gather._TUPLET_CLASSES = ("tuplet3", "fingering3",
# "tupletBracket", "tupleBracket")` only ever FILES four literal class names
# under it — `tuplet0/1/2/4-9` are a digit the tuplet reader never acts on
# ("only 3:2 is acted on at all") and `fingering1/2/4/5` are ordinary piano
# fingerings, neither ever reaching a `Q.TUPLET_MARKER` row at all. Reading
# `Q.TUPLET_MARKER` itself is therefore already exactly the population
# `adjudicate_tuplet` can read, with no separate list to keep in step with
# `_TUPLET_CLASSES`.
# ─────────────────────────────────────────────────────────────────────────────


@decision(
    quantity=Q.FLAG_IS_NOT_A_FLAG,
    composed_from=(Q.GLYPH_BOX, Q.FLAG, Q.HUMAN_BOX_VERDICT,
                   Q.GLYPH_BAND_DISTANCE),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_BOX, Q.FLAG, Q.HUMAN_BOX_VERDICT, Q.GLYPH_BAND_DISTANCE),
    subjects_from=Q.FLAG,
    reasons=_human_only_reasons(Q.FLAG_IS_NOT_A_FLAG),
    mode=Mode.ADDITIVE,
)
def adjudicate_flag_is_not_a_flag(ev: Evidence) -> Ruling:
    """Is this box the detector called a flag a symbol at all?

    HUMAN WITNESS ONLY, on the same pattern REST/ARC/DYNAMIC/ARTICULATION
    take in 3.4g: `subjects_from=Q.FLAG` rather than a `Q.GLYPH_BOX` class
    narrowing, because `gather_rhythm_marks` files `Q.FLAG` on every
    `flag*`-prefixed glyph 1:1 — no widening the way `Q.ACCIDENTAL_STAFF_
    POSITION` excludes key-signature shapes. Its consumer is `rhythm.
    _attached_flags`: a refused flag is a glyph a human struck out and must
    not hand an unbeamed notehead its hook count.
    """
    _ = ev.rows(Q.FLAG)       # the domain's own quantity, declared and read
    detail, used = _class_detail(ev)
    refused = _refused_by_a_human(ev, detail)
    if refused is not None:
        return refused
    return Ruling(value=False, reason="flag", used=used, detail=detail)


@decision(
    quantity=Q.KEYSIG_MARKER_IS_NOT_A_MARKER,
    composed_from=(Q.GLYPH_BOX, Q.HUMAN_BOX_VERDICT, Q.GLYPH_BAND_DISTANCE),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_BOX, Q.HUMAN_BOX_VERDICT, Q.GLYPH_BAND_DISTANCE),
    subjects_from=Q.GLYPH_BOX,
    subjects_classed=("keySharp", "keyFlat", "keyNatural"),
    reasons=_human_only_reasons(Q.KEYSIG_MARKER_IS_NOT_A_MARKER),
    mode=Mode.ADDITIVE,
)
def adjudicate_keysig_marker_is_not_a_marker(ev: Evidence) -> Ruling:
    """Is this `key*` box the detector drew in the header a symbol at all?

    HUMAN WITNESS ONLY. `Q.KEYSIG_MARKER` names no glyph of its own
    (`gather._gather_keysig_markers` files it on the STAFF), so this
    decision's subjects are the `key*` `Q.GLYPH_BOX` rows the marker rows are
    built from — exactly the glyphs a human box-labels in the stage review.
    Its consumer is `header._staff_reading`'s marker-run intake, which rejoins
    a refused glyph to the marker row it produced by frame, class and point
    (the same join `ownership._keysig_marker_row` makes in the opposite
    direction) and drops it before `_marker_run` ever sees it.
    """
    detail, used = _class_detail(ev)
    refused = _refused_by_a_human(ev, detail)
    if refused is not None:
        return refused
    return Ruling(value=False, reason="keysig_marker", used=used,
                  detail=detail)


@decision(
    quantity=Q.TUPLET_MARKER_IS_NOT_A_MARKER,
    composed_from=(Q.GLYPH_BOX, Q.TUPLET_MARKER, Q.HUMAN_BOX_VERDICT,
                   Q.GLYPH_BAND_DISTANCE),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_BOX, Q.TUPLET_MARKER, Q.HUMAN_BOX_VERDICT,
           Q.GLYPH_BAND_DISTANCE),
    subjects_from=Q.TUPLET_MARKER,
    reasons=_human_only_reasons(Q.TUPLET_MARKER_IS_NOT_A_MARKER),
    mode=Mode.ADDITIVE,
)
def adjudicate_tuplet_marker_is_not_a_marker(ev: Evidence) -> Ruling:
    """Is this box the detector called a tuplet numeral or bracket a symbol
    at all?

    HUMAN WITNESS ONLY, `subjects_from=Q.TUPLET_MARKER` rather than a
    `Q.GLYPH_BOX` class narrowing — `gather._TUPLET_CLASSES` already files
    exactly `tuplet3`, `tupletBracket` and `fingering3` under it (see the
    module comment above for why the wider `tuplet`/`fingering` FAMILIES are
    not named: most of their classes never reach this quantity at all). Its
    consumer is `rhythm.adjudicate_tuplet`, which must not read a 3:2 ratio
    off a marker a human struck out.
    """
    _ = ev.rows(Q.TUPLET_MARKER)  # the domain's own quantity, declared and read
    detail, used = _class_detail(ev)
    refused = _refused_by_a_human(ev, detail)
    if refused is not None:
        return refused
    return Ruling(value=False, reason="tuplet_marker", used=used,
                  detail=detail)


#: Every family refusal, and the quantity that names it. ⚠️ DERIVED FROM
#: `_OK`, never typed twice: `export.py` counts by walking this, so a family
#: added above is counted without a second list being remembered.
FAMILY_REFUSALS: Tuple[str, ...] = tuple(_OK)
