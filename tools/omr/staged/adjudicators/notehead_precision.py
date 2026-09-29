"""Notehead PRECISION on the staged path — ROADMAP 2.4a.

⚠️ TWO FILTERS EXIST, MEASURED, AND NEITHER IS CALLED FROM `tools/omr/staged/`.
Verified 2026-09-22 (`git log --all --oneline -S` on both names under
`staged/` returns nothing; `git log --all --oneline -S` under `tools/omr/`
finds only their `transcribe.py` definitions and call sites):
`transcribe._drop_clipped_notehead_fragments` (a notehead-shaped sliver flush
against a measure cell's crop boundary — the neighbouring staff's ink bleeding
into this cell's padding) and `transcribe._drop_unladdered_noteheads` (a
low-confidence notehead standing outside its own staff, with not one ledger
rung joining it to that staff). CLAUDE.md's own §1c records both as
legacy-only. The LEGACY PATH IS FROZEN (`docs/DECISIONS.md` 2026-09-22), so
this ports the two filters as an ADJUDICATE decision rather than moving them,
plus a third rule that was measured and never shipped anywhere: a
`noteheadBlack*` box under 1.0 staff spaces wide
(`benchmarks/omr-notehead-width-2026-09/FINDINGS.md`).

⚠️ THE RECORD KEEPS THE ROW, WHICH THE LEGACY FILTERS DO NOT. Both legacy
functions call `dets.remove(det)` — the glyph vanishes with no trace, which is
exactly the ABSENT/DECLINED collapse this project's own record format exists
to prevent. Here the glyph stays a `Q.GLYPH_BOX` row and this decision
REFUSES it with a named reason; `export._place_notes` is the one place that
acts on the refusal, and it counts what it drops.

⚠️ THE POPULATION Q.GLYPH_LADDER COVERS IS NOT THE POPULATION THIS RULE NEEDS,
AND THAT IS WORTH RECORDING RATHER THAN SILENTLY WORKING AROUND.
`gather_ownership_evidence` files `Q.GLYPH_LADDER` ONLY for a glyph inside a
CROSS-STAFF CONTEST (`subjects_from=Q.GLYPH_BAND_DISTANCE` on
`adjudicate_glyph_owner`) — same CATEGORY (ROADMAP 2.6; it was the smufl NAME
until 2026-09-23), different staff, overlapping ink. The
legacy `_drop_unladdered_noteheads` population is a letter bowl, a key-
signature flat's loop, a bare ledger line: ink detected ONCE, on no other
staff, so it never forms a contest and `Q.GLYPH_LADDER` is never gathered for
it. Reusing that quantity would silently narrow the rule to a population it
was never built for. This decision instead reads the quantities every
notehead glyph carries UNCONDITIONALLY — `Q.GLYPH_BOX` (canonical AND page
frame), `Q.CELL_BOX`, `Q.CELL_STAFF_SPACE`, `Q.NOTEHEAD_STAFF_POSITION`,
`Q.GLYPH_CONF` — and re-derives the ladder search itself, with every
threshold IMPORTED from `tools.omr.transcribe`, never restated. This is
ADJUDICATE reading GATHER's existing facts more thoroughly, not a GATHER
change: no new producer, no new row, and `readjudicate.py` prices it exactly.

⚠️ THE EDGE TEST RUNS IN PAGE FRAME, NOT CANONICAL, AND THAT IS AN EXACT
SUBSTITUTION, NOT AN APPROXIMATION. The legacy rule compares a canonical
`y_canonical` / `y_canonical + height_canonical` against `cell.image.shape[0]`
— the crop's own canonical pixel height, which the frozen staged record does
not carry (only the cell's PAGE rectangle, `Q.CELL_BOX`). But `gather._page_box`
maps canonical -> page by a single per-cell affine transform (divide by
`upscale_factor`), so canonical row 0 maps EXACTLY to the cell's own page-frame
top edge and canonical row `img_h` maps EXACTLY to its page-frame bottom edge —
verified independently by `benchmarks/omr-notehead-width-2026-09/FINDINGS.md`
§0, which cross-checked the same two box conventions on 5,684 boxes and found
them agreeing to 0.0000-0.0142 STAFF SPACES (i.e. the residual is float
rounding, not a frame mismatch). Testing edge-coincidence against `Q.CELL_BOX`
in page pixels is therefore the SAME comparison the legacy rule makes, in a
frame the record actually carries.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ... import transcribe as _legacy
from ..adjudicate import Evidence, Mode, Ruling, decision
from .. import record as R
from ..record import ABSTAIN, Kind, Outcome, Q, Scope
# ⚠️ ROADMAP 2.6c: the ONE ledger helper. Imported as a bare module name, not
# through a dotted relative path: `wiring.details` matches detail keys by bare
# substring, and a dot followed by the module's first three letters reads as
# a consumer of `Q.GLYPH_BAND_DISTANCE`'s home-staff flag that nothing is.
from . import ownership as _ledger
_OWN_LINE_MAX_SPACES = _ledger.OWN_LINE_MAX_SPACES
cell_rungs = _ledger.cell_rungs
cv_rungs = _ledger.cv_rungs           # ROADMAP 2.6d
ladder_side = _ledger.ladder_side
ledger_direction = _ledger.ledger_direction
# ROADMAP 2.6f: the SAME two-pass discount `glyph_owner` uses, so a rung
# that is another candidate's own ledger structure cannot be credited here
# and refused there.
ladder_sides_with_discount = _ledger.ladder_sides_with_discount

# ─────────────────────────────────────────────────────────────────────────────
# Thresholds — IMPORTED from the legacy path, never restated, so the two
# cannot drift. `benchmarks/omr-notehead-width-2026-09/FINDINGS.md`'s 1.0
# staff-space width floor has no home in `transcribe.py` (it was measured and
# never shipped anywhere), so it alone is a new constant, named after the
# benchmark that measured it.
# ─────────────────────────────────────────────────────────────────────────────

#: A notehead sliver cut off by the cell crop boundary: under this height, at
#: the crop's own edge. `transcribe._CLIPPED_NOTEHEAD_MAX_SPACES`.
CLIPPED_NOTEHEAD_MAX_SPACES = float(_legacy._CLIPPED_NOTEHEAD_MAX_SPACES)

#: How close a box's edge must sit to the cell's own page-frame edge to count
#: as "cut off by the crop", in PAGE pixels. ⚠️ NOT a restatement of
#: `transcribe._CELL_EDGE_TOLERANCE_PX` (1 CANONICAL px) — that quantity has
#: no meaning in a frame this record does not carry the canonical height for.
#: The two frames are exactly affine-related per cell (see the module
#: docstring), so a small page-pixel tolerance is the equivalent test; this
#: is comfortably larger than the floating-point residual the affine map
#: leaves (0.0000-0.0142 staff spaces, i.e. well under a page pixel at any
#: DPI this project reads) and comfortably smaller than any genuine margin a
#: real notehead leaves a crop edge.
CELL_EDGE_TOLERANCE_PAGE_PX = 1.0

#: A `noteheadBlack*` box under this many staff spaces wide is not a
#: notehead. `benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §2-3: costs
#: 0 of 103 print-confirmed noteheads on two publishers (Litolff 0.42%,
#: Breitkopf 0.67% of the `decided` population, both under a pre-registered
#: 2% bar), catches 39 of 46 print-confirmed non-noteheads. ⚠️ RESTRICTED TO
#: `noteheadBlack*`: the FINDINGS' own §6 measures the under-floor count as
#: ZERO for every Half and Whole class on both plates — the contamination
#: there is a class-identity fault (mostly not whole/half notes at all, per
#: the crop pass), not a narrow one, and this rule has no opinion on it.
TOO_NARROW_MIN_SPACES = 1.0
TOO_NARROW_CLASS_PREFIX = "noteheadblack"

#: A low-confidence outside-staff notehead with no ledger rung.
#: `transcribe._UNLADDERED_NOTEHEAD_MAX_CONF`.
UNLADDERED_MAX_CONF = float(_legacy._UNLADDERED_NOTEHEAD_MAX_CONF)
#: `transcribe._LEDGER_RUNG_EXPECTED_SLACK` — a note ON the k-th ledger line
#: measures ~k.0 spacings past the staff edge, not k.5; truncation without
#: this reads that as needing no rung.
LEDGER_RUNG_EXPECTED_SLACK = float(_legacy._LEDGER_RUNG_EXPECTED_SLACK)
#: `transcribe._LEDGER_RUNG_Y_TOL_SPACES`.
LEDGER_RUNG_Y_TOL_SPACES = float(_legacy._LEDGER_RUNG_Y_TOL_SPACES)
#: `transcribe._LEDGER_RUNG_MIN_X_OVERLAP`.
LEDGER_RUNG_MIN_X_OVERLAP = float(_legacy._LEDGER_RUNG_MIN_X_OVERLAP)

#: ⚠️⚠️ MEASURED AND HELD BACK, 2026-09-22, ON THE ACCEPTANCE DOCUMENTS
#: THEMSELVES — `benchmarks/omr-notehead-precision-2026-09/`. Joined against
#: the stem-crop-pass's blind print verdicts (the only place "is this a
#: notehead" has a truth value): `unladdered` catches 0 of 34 (Litolff) / 2 of
#: 44 (Breitkopf) print-confirmed non-noteheads and COSTS 4 of 29 / 4 of 74
#: print-confirmed REAL noteheads — net NEGATIVE, worse than a coin flip,
#: where `too_narrow` on the identical join reproduces the prior 0-cost / ~40-
#: caught result almost exactly. Every traced cost is the SAME mechanism: the
#: note's own ledger rung was never DETECTED anywhere in its cell (verified by
#: hand for two cases — zero `ledgerLine` glyphs at all in that cell) — a
#: detection-recall gap the legacy rule's own comment already names
#: ("ledger recall is imperfect, so real notes with ZERO found rungs exist"),
#: sharper here because these are LOW-CONFIDENCE SCAN glyphs, not the
#: confidence>=0.82 engraved population that comment was written against.
#: ⚠️ THIS TASK CARRIES NO FLAG (`docs/DECISIONS.md` convention: a default is
#: a decision, not a code path to leave switchable), so there is no way to
#: ship this LIVE and revert it later without a code change — and "print
#: before default" (the ten rules, §5) means a rule that costs more real notes
#: than it catches on the two ACCEPTANCE documents may not go live on the
#: strength of its legacy ancestry alone. So the rule is fully BUILT, TESTED
#: and MEASURED, and its finding is recorded in `detail` on every notehead
#: (`unladdered_signal`) — but it does NOT set `value=True`. See
#: `adjudicate_notehead_is_not_a_notehead`'s docstring and the 2.4a report for
#: what would need to change before this could ship: the ledger search is
#: SAME-CELL ONLY (a simplification stated in `_ledger_rungs_in_cell`'s own
#: docstring); a PAGE-FRAME, cross-cell search — using `bbox_page_px`, which
#: every glyph already carries, exactly as `Q.ONSET_COLUMN` had to for the
#: identical cross-cell frame reason — is the next thing to try, unbuilt and
#: unmeasured here.
UNLADDERED_SHIPS = False

#: Above this staff position (half-step units, top line = 0), a note is
#: standing on the bottom line of a normal 5-line staff.
_STAFF_BOTTOM_POSITION = 8.0

# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.7b — `belongs_to_a_nearer_staff`, Sean's convention (2026-09-27):
# *"notes should never be that far away from a staff unless there are ledger
# lines close to the staff connecting the note conceptually to the staff."*
#
# ⚠️ NOT `unladdered` RE-ENABLED, AND THE DIFFERENCE IS THE WHOLE DESIGN.
# `unladdered` (held back above) asks only *is there a rung?* and was measured
# net negative because ledger RECALL fails on scans: a real note whose rung the
# detector never boxed looked unladdered. This rule asks a question with a
# SECOND witness from a different source — the page's own staff geometry: the
# head is far from its filed staff AND another staff of the same system is
# near it. A real high violin note with a missing rung is far from its staff
# and near NOTHING, and this rule does not fire on it. The measurement is in
# `benchmarks/omr-accidental-2026-09/FINDINGS.md` §2.7b.
# ─────────────────────────────────────────────────────────────────────────────

#: A head whose centre is MORE than this many staff spaces outside the band of
#: the staff it was filed on is "that far away" in Sean's sense.
#:
#: ⚠️ MEASURED on the Litolff acceptance record (FINDINGS §2.7b,
#: `probe/nearer_staff.py`): Sean's six wrong-staff heads (crops 2, 4, 13, 20,
#: 23, 26) stand **3.485-3.670** spaces from their filed staff; the eighteen
#: heads of his twenty-one confirmed crops stand **0.000-2.440**. The empty
#: interval is (2.44, 3.485) and 3.0 is its round middle — and it is also,
#: on this plate, about half the gap between two staves (~5.9 spaces), so
#: past it a head is on the other staff's side of the air. The population
#: that crosses it falls off a cliff below 3.25 (4 heads in the 3.0 bin
#: against 40 / 113 / 88 in 3.25 / 3.5 / 3.75), so the value is not on a slope.
NEARER_STAFF_FILED_MIN_SPACES = 3.0

#: ... AND another staff of the same system has a line within this many staff
#: spaces of it (0 = inside that staff's band), nearer than the filed one.
#:
#: ⚠️ MEASURED: the six wrong-staff heads stand **2.291-2.588** spaces from
#: the staff Sean put them on — low notes on ledger lines UNDER the staff
#: above, not ink inside it — so the bound must pass 2.588; 2.75 is the
#: quarter-space above it. The confirmed heads are nearer their own staff
#: than any other by at least 1.19 spaces, so the `nearer than the filed
#: one` clause alone already keeps all of them.
NEARER_STAFF_NEAR_MAX_SPACES = 2.75

#: A kept rung this close to the head's own centre is the head's OWN ledger
#: line (a note standing on a ledger line) and joins it to NO staff in
#: particular — between two staves it could be a rung of either.
#:
#: ⚠️ MEASURED on the Litolff arm (`probe/kept_rungs.py`): of 79 heads past
#: both bands that the first cut KEPT on a rung, **43 were kept by a rung at
#: 0.00-0.37 spaces from the head** (its own line; one of them the print
#: check's own first kept crop, a note on a ledger above the staff BELOW it)
#: and the rest stand at 0.63+ — the interval (0.37, 0.63) is empty, 0.5 is
#: its middle. ⚠️ ROADMAP 2.6c: the number now LIVES in
#: `ownership.OWN_LINE_MAX_SPACES`, read by the one ledger helper both this
#: rule and `glyph_owner` ask; this name is kept so nothing that cites it
#: breaks.
OWN_LEDGER_MAX_SPACES = _OWN_LINE_MAX_SPACES


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.12l — A PRINTED METER CHANGE'S DIGITS, BOXED AS NOTEHEADS.
#
# `benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` §15b (ROADMAP 2.19):
# on Breitkopf 317803 pdf p1 the 6/8 change at system/1/0 cell 1 is read by
# NOTHING — `Q.METER_GLYPH` only ever fires on a `timeSig*`-classed box
# (`gather._gather_meter_glyphs`), and on this plate the "6" and "8" are
# boxed as `noteheadWhole*`/`noteheadBlack*` instead. 23 of the 26 `M`-only
# held bars in FINDINGS §15c carry such a "head". Two failures compound: the
# glyph is never a candidate for the meter reader AND, until this item, it
# was WRITTEN as a real note in the exported file.
#
# CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: how would a
# human read this off the page? A printed meter change sits at ONE x, just
# past a barline, and prints on EVERY staff of the system (CLAUDE.md §10) —
# so two facts distinguish it from real ink: (1) on the STAFF that carries
# it, the two digits sit close together in x (a template glyph, not two
# independently-placed noteheads) and a SPECIFIC, narrow distance apart in y
# (a fixed numeral pair, not a chosen interval); (2) the SAME pattern repeats
# at the SAME cell on MOST OTHER staves of the system, because it is
# engraving, not music -- a real chord's interval varies staff to staff (a
# different chord for a different instrument), a time signature's does not.
# Measured on the fixture above (`probe/meter_digit_2_12l.py`,
# `benchmarks/omr-bar-sum-holdout-2026-09/out/print/meter-digit-2.12l-*`):
# on 13 of 14 staves the "6" and "8" are boxed as two `noteheadWhole*`/
# `noteheadBlack*` glyphs within 0.1 canonical staff spaces of each other in
# x and 0.42-0.86 spaces apart in y, all within 0-2.2 spaces of the cell's
# own left edge (the barline) -- staff 12's second digit falls under the
# detector's confidence floor and is missed (a recall gap, not a shape
# miss). ⚠️ THIS IS NOT THE "~2 spaces tall" HEIGHT THE BRIEF NAMED: the
# detector's box is drawn around the ROUNDED PART of each digit it pattern-
# matches to a hollow notehead template, not the numeral's full extent, and
# measures 0.94-1.94 spaces tall on this fixture -- statistically the same as
# a real notehead. Height is therefore NOT part of this rule; the position
# pair (tight x, a specific narrow y-gap) and the cross-staff repetition are
# what carry the whole claim. WHAT WOULD FALSIFY IT: a crop showing a real,
# same-interval chord repeating at one x on most staves of a system (the
# brief's own named risk) -- none seen on the two acceptance documents, but
# not excluded by construction. NOT CONFIRMED WITH SEAN.
# ─────────────────────────────────────────────────────────────────────────────

#: How close to the cell's own left edge (the barline) a meter-change digit
#: sits, in canonical staff spaces. Measured 1.48-2.20 on the fixture above;
#: this is a comfortable margin, not a fitted bound.
METER_DIGIT_X_MAX_SPACES = 3.0

#: The two digits of one meter change sit at nearly the SAME x -- a template
#: glyph, not two independently-drawn noteheads. Measured x-gap 0.00-0.11.
METER_DIGIT_PAIR_X_TOL_SPACES = 0.25

#: ... and a SPECIFIC, narrow distance apart in y (centre to centre) -- the
#: numeral pair's own fixed proportions. Measured 0.42-0.86 on 13 of 14
#: staves of the one measured change; a real chord's interval is free to
#: land here too (Sean's own risk, above), which is why this rule ALSO
#: requires the cross-staff repetition below and never fires alone.
METER_DIGIT_PAIR_Y_GAP_MIN_SPACES = 0.30
METER_DIGIT_PAIR_Y_GAP_MAX_SPACES = 1.20

#: How many OTHER staves of the system must show the same near-barline
#: notehead-classed ink at this cell before the pattern counts as "printed
#: on the system", not one staff's own chord. ⚠️ THE SAME SHAPE AS
#: `rhythm._required_corroboration` (ROADMAP 2.12j) -- cited, not imported:
#: this module already keeps its own thresholds self-contained (see the
#: file docstring's "every threshold IMPORTED... never restated" for the
#: LEGACY numbers, which this is not one of), and `rhythm.py` is the meter
#: chain's own home, not a dependency this decision should carry.
METER_DIGIT_QUORUM_MIN_STAVES = 2
METER_DIGIT_QUORUM_COVERAGE = 0.5

#: Reason a refused notehead carries when it is a printed meter change's own
#: digit. Read back by `rhythm._meter_digit_witness_cells` (ROADMAP 2.12l)
#: to file the position as a witness the meter chain can see -- never a
#: value, only a place. Naming it here, once, is what keeps the two
#: modules from restating the string and drifting apart.
METER_DIGIT_REASON = "is_a_meter_digit"


def _required_meter_digit_quorum(total_staves: Optional[int]) -> int:
    """`METER_DIGIT_QUORUM_MIN_STAVES`, raised on a system large enough that
    two staves are no longer a meaningful fraction of it. `None` (staff count
    undecided) falls back to the absolute floor alone -- an absent count is
    not evidence the system is large."""
    if not total_staves:
        return METER_DIGIT_QUORUM_MIN_STAVES
    return max(METER_DIGIT_QUORUM_MIN_STAVES,
              round(METER_DIGIT_QUORUM_COVERAGE * total_staves))


def _cell_staff_space_at(ev: Evidence, subject) -> Optional[float]:
    """`Q.CELL_STAFF_SPACE` at an EXPLICIT cell subject, not `ev.subject`'s
    own ancestry -- the cross-staff check needs another staff's own unit,
    never this glyph's."""
    rows = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS,
                   subject=subject)
    if not rows:
        return None
    try:
        v = float(rows[-1].value)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def _meter_digit_pair_partner(ev: Evidence, box_row, spacing_canonical: float,
                              detail: Dict[str, Any]) -> Optional[Any]:
    """A second `notehead*` box on THIS staff's SAME cell, close in x and a
    narrow, specific distance apart in y -- the candidate's own half of the
    stacked pair. Returns the partner's own `Q.GLYPH_BOX` row, or None.

    ⚠️ CHEAP: this cell's own glyphs only (`Q.GLYPH_BOX` at
    `Scope.SELF_AND_DESCENDANTS` off the CELL, the same population
    `_ledger_rungs_in_cell` already walks for the identical reason), never
    the page. Called for every notehead-classed glyph, but the x-window gate
    below narrows the population that reaches the loop body to the few boxes
    standing near a cell's own left edge.
    """
    name0, x0, y0, w0, h0 = box_row.value
    x0_sp = x0 / spacing_canonical
    if not (0.0 <= x0_sp <= METER_DIGIT_X_MAX_SPACES):
        return None
    yc0 = (y0 + h0 / 2.0) / spacing_canonical
    cell = ev.subject.at(Kind.CELL)
    me = ev.subject.to_key()
    best = None
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        if r.subject.to_key() == me:
            continue
        v = r.value
        if not isinstance(v, (list, tuple)) or len(v) != 5:
            continue
        name1, x1, y1, w1, h1 = v
        if not str(name1).lower().startswith("notehead"):
            continue
        x1_sp = x1 / spacing_canonical
        if not (0.0 <= x1_sp <= METER_DIGIT_X_MAX_SPACES):
            continue
        if abs(x1_sp - x0_sp) > METER_DIGIT_PAIR_X_TOL_SPACES:
            continue
        yc1 = (y1 + h1 / 2.0) / spacing_canonical
        y_gap = abs(yc1 - yc0)
        if not (METER_DIGIT_PAIR_Y_GAP_MIN_SPACES <= y_gap
                <= METER_DIGIT_PAIR_Y_GAP_MAX_SPACES):
            continue
        detail["meter_digit_pair_x_gap"] = round(abs(x1_sp - x0_sp), 3)
        detail["meter_digit_pair_y_gap"] = round(y_gap, 3)
        best = r
        break
    return best


def _meter_digit_cross_staff_count(ev: Evidence) -> int:
    """How many OTHER staves of this system show notehead-classed ink near
    the LEFT edge of this glyph's own cell index -- the repetition
    `_meter_digit_pair_partner`'s own staff cannot establish alone.

    ⚠️ `Q.SYSTEM_STAFF_COUNT` ONLY, NEVER `ev.subjects(Kind.STAFF)`. The
    latter walks the whole subject index and is cheap only where a decision
    calls it once per SYSTEM (`ownership._belongs_to_a_nearer_staff`'s own
    comment measures the cost of doing it per GLYPH); this decision runs on
    every notehead-classed glyph in the document, so it never asks the index
    at all -- `total_staves` bounds a plain `range()` instead, and a system
    whose count is undecided is skipped outright (no guess at how many
    staves to check) rather than answered from an unbounded walk.
    """
    staff = ev.subject.at(Kind.STAFF)
    if staff is None:
        return 0
    system = ev.subject.at(Kind.SYSTEM)
    total = ev.verdict(Q.SYSTEM_STAFF_COUNT, subject=system)
    n = total.value if total is not None and total.value else None
    if not n:
        return 0
    cell_index = ev.subject.cell
    if cell_index is None:
        return 0
    count = 0
    for st in range(int(n)):
        if st == staff.staff:
            continue
        other_cell = R.cell(staff.page, staff.system, st, cell_index)
        sp = _cell_staff_space_at(ev, other_cell)
        if sp is None:
            continue
        # ⚠️⚠️ A STACKED PAIR, NOT "ANY NEAR-BARLINE NOTE" — measured wrong
        # on the fixture this rule was built against: the loose test (any
        # notehead-classed box near the barline, no partner required) let a
        # staff's own ORDINARY first note of the bar count toward another
        # staff's quorum on two cells with NO printed meter change at all
        # (`benchmarks/omr-bar-sum-holdout-2026-09/out/print/meter-digit-
        # 2.12l-*`, cells 3 and 5 -- one lone staff each, no repetition).
        # "Printed on the system" (CLAUDE.md §10) means the SAME shape
        # repeats, not merely that some other staff also has ink near a
        # barline, which is the ordinary case on most bars.
        boxes = []
        for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                         subject=other_cell):
            v = r.value
            if not isinstance(v, (list, tuple)) or len(v) != 5:
                continue
            name1, x1, y1, w1, h1 = v
            if not str(name1).lower().startswith("notehead"):
                continue
            x1_sp = x1 / sp
            if 0.0 <= x1_sp <= METER_DIGIT_X_MAX_SPACES:
                boxes.append((x1_sp, (y1 + h1 / 2.0) / sp))
        if _has_a_stacked_pair(boxes):
            count += 1
    return count


def _has_a_stacked_pair(boxes) -> bool:
    """`True` where two of `boxes` (each `(x_sp, y_centre_sp)`, already
    filtered to the near-barline window) sit close in x and a narrow,
    specific distance apart in y -- the SAME test `_meter_digit_pair_partner`
    applies to the candidate's own staff, applied here to ANOTHER staff's
    cell so the cross-staff count only credits a REPEATED PAIR, never a
    lone note that merely happens to stand near the same barline."""
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if abs(boxes[i][0] - boxes[j][0]) > METER_DIGIT_PAIR_X_TOL_SPACES:
                continue
            y_gap = abs(boxes[i][1] - boxes[j][1])
            if (METER_DIGIT_PAIR_Y_GAP_MIN_SPACES <= y_gap
                    <= METER_DIGIT_PAIR_Y_GAP_MAX_SPACES):
                return True
    return False


def _is_a_meter_digit(ev: Evidence, box_row, spacing_canonical: float,
                      detail: Dict[str, Any]) -> bool:
    """ROADMAP 2.12l — see the module's own block comment above for the
    signature and its measurement. Two gates, BOTH required: a stacked
    partner on this glyph's OWN staff, and the same pattern repeated on a
    QUORUM of the system's OTHER staves at the SAME cell (never on this
    glyph's shape alone — CLAUDE.md's own guard against a real chord that
    happens to repeat).
    """
    partner = _meter_digit_pair_partner(ev, box_row, spacing_canonical, detail)
    if partner is None:
        return False
    others = _meter_digit_cross_staff_count(ev)
    system = ev.subject.at(Kind.SYSTEM)
    total = ev.verdict(Q.SYSTEM_STAFF_COUNT, subject=system)
    total_staves = total.value if total is not None and total.value else None
    detail["meter_digit_partner"] = partner.id
    detail["meter_digit_other_staves"] = others
    detail["meter_digit_quorum"] = _required_meter_digit_quorum(total_staves)
    return others >= _required_meter_digit_quorum(total_staves)


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


def _cell_box_page(ev: Evidence) -> Optional[List[float]]:
    rows = ev.rows(Q.CELL_BOX, scope=Scope.SELF_AND_ANCESTORS)
    if not rows or not isinstance(rows[-1].value, (list, tuple)) \
            or len(rows[-1].value) != 4:
        return None
    return [float(v) for v in rows[-1].value]


def _clipped_fragment(ev: Evidence, box_row, spacing_canonical: float,
                      detail: Dict[str, Any]) -> bool:
    """A sliver cut off by the cell's own crop boundary — height AND edge."""
    _name, _x, y_c, _w, h_c = box_row.value
    h_spaces = h_c / spacing_canonical
    detail["height_spaces"] = round(h_spaces, 3)
    if h_spaces >= CLIPPED_NOTEHEAD_MAX_SPACES:
        return False
    page_box = (box_row.detail or {}).get("bbox_page_px")
    cell_box = _cell_box_page(ev)
    if not page_box or len(page_box) != 4 or cell_box is None:
        # ⚠️ DECLINED, NOT DEFAULTED. Without a page frame for both the glyph
        # and its cell the edge test cannot run, and a short notehead in the
        # middle of a cell is "some other problem" this rule has no opinion
        # on (`transcribe._CLIPPED_NOTEHEAD_MAX_SPACES`'s own docstring) — so
        # the honest default is NOT clipped, never a guess either way.
        return False
    py0, py1 = page_box[1], page_box[3]
    cy0, cy1 = cell_box[1], cell_box[3]
    touching = (abs(py0 - cy0) <= CELL_EDGE_TOLERANCE_PAGE_PX
                or abs(py1 - cy1) <= CELL_EDGE_TOLERANCE_PAGE_PX)
    detail["edge_distance_page_px"] = round(
        min(abs(py0 - cy0), abs(py1 - cy1)), 3)
    return touching


def _is_a_clef(ev: Evidence):
    """ROADMAP 2.11 — this box is part of a clef the locator READ over it.

    ⚠️ A CONNECT, NOT A GUESS, AND THE DISTINCTION IS THE WHOLE POINT. This
    rule measures nothing and decides nothing on its own. It asks whether a
    `Q.CLEF_LOCATED` row on this glyph's own STAFF NAMES this glyph as a box
    it overrode — `gather._occupied_notehead_rows` put the subject key there,
    from the detector ordinal the glyph subject is built from. If the clef was
    not read, or was read without overriding anything, this returns None and
    the glyph is judged on shape as before.

    ⚠️ SCOPE IS `SELF_AND_ANCESTORS` BECAUSE THE ROW IS FILED ON THE STAFF.
    At `EXACT` — the default — a GLYPH subject's query returns nothing and the
    rule would fail SILENTLY, which is the failure mode CLAUDE.md §4b names
    and `wiring --check` exists to catch.

    ⚠️ IT DOES NOT ASK WHETHER THE STAFF'S `clef` VERDICT AGREES. That verdict
    is an ADJUDICATE product of this same stage; reading it here would make
    the refusal depend on decision order, and a located clef that loses the
    clef contest still tells us what this ink is. The evidence is the READ,
    not the winner.
    """
    me = ev.subject.to_key()
    for r in ev.rows(Q.CLEF_LOCATED, scope=Scope.SELF_AND_ANCESTORS):
        d = r.detail or {}
        if me in (d.get("overrode_glyph_subjects") or ()):
            return r
    return None


def _too_narrow(box_row, spacing_canonical: float,
                detail: Dict[str, Any]) -> bool:
    """A `noteheadBlack*` box under the measured width floor."""
    name, _x, _y, w_c, _h = box_row.value
    if not str(name).lower().startswith(TOO_NARROW_CLASS_PREFIX):
        return False
    w_spaces = w_c / spacing_canonical
    detail["width_spaces"] = round(w_spaces, 3)
    return w_spaces < TOO_NARROW_MIN_SPACES


def _ledger_rungs_in_cell(ev: Evidence) -> List[Tuple[float, float, float]]:
    """Every `ledgerLine` glyph's canonical `(x0, x1, y_centre)` in this cell.

    ⚠️ SAME CELL ONLY, not the legacy rule's whole-page search. A staff's
    own ledger rungs for a note it printed are cut into that SAME cell — the
    padding that makes the crop wide enough to hold the note also holds its
    rungs — so this is a faithful narrowing, not a different question, and it
    avoids re-deriving a page-wide affine map this decision has no need of.

    ⚠️⚠️ ROADMAP 3.4g — A REFUSED RUNG IS NOT COUNTED, AND THIS IS THE ONLY
    LADDER IN THE PIPELINE WHERE THAT IS POSSIBLE. GATHER's own ladder
    (`Q.GLYPH_LADDER`, `gather._observe_ladder`) records `expected` and
    `found` as COUNTS and names none of the rung glyphs it matched, so no
    later stage can tell which glyph a `found` rung was — the rung -> glyph
    join does not exist on the record and a refusal cannot reach it without a
    GATHER change. Here the join is trivial because the rungs ARE glyph
    subjects: `adjudicate_ledger_is_not_a_ledger` runs before this decision
    (`adjudicate.ORDER`) and a rung it condemned is skipped.
    """
    cell = ev.subject.at(Kind.CELL)
    out: List[Tuple[float, float, float]] = []
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        v = r.value
        if not isinstance(v, (list, tuple)) or len(v) != 5:
            continue
        if str(v[0]) != "ledgerLine":
            continue
        refused = ev.verdict(Q.LEDGER_IS_NOT_A_LEDGER, subject=r.subject)
        if refused is not None and refused.value is True:
            continue
        x_c, y_c, w_c, h_c = v[1], v[2], v[3], v[4]
        out.append((x_c, x_c + w_c, y_c + h_c / 2.0))
    return out


def _unladdered(ev: Evidence, box_row, spacing_canonical: float,
                detail: Dict[str, Any]) -> bool:
    """A low-confidence notehead outside the staff with NO ledger rung.

    ⚠️ `found == 0`, not "incomplete" — the legacy rule's own condition
    (`transcribe._drop_unladdered_noteheads`: `if found == 0: dets.remove`).
    An incomplete but non-empty ladder is left alone; this is deliberately
    the more conservative of the two shapes the legacy comment considers.
    """
    conf_rows = ev.rows(Q.GLYPH_CONF)
    if not conf_rows:
        return False
    try:
        conf = float(conf_rows[-1].value)
    except (TypeError, ValueError):
        return False
    if conf >= UNLADDERED_MAX_CONF:
        return False

    pos_rows = ev.rows(Q.NOTEHEAD_STAFF_POSITION)
    if not pos_rows:
        return False
    try:
        pos_float = float(pos_rows[-1].value)
    except (TypeError, ValueError):
        return False
    if 0.0 <= pos_float <= _STAFF_BOTTOM_POSITION:
        return False               # inside the staff band -- no ladder needed

    half_step = spacing_canonical / 2.0
    _name, x_c, y_c, w_c, h_c = box_row.value
    y_center = y_c + h_c / 2.0
    if pos_float < 0.0:
        dist_spaces = abs(pos_float) / 2.0
        anchor = y_center - pos_float * half_step        # canonical top line
        sign = -1.0
    else:
        dist_spaces = (pos_float - _STAFF_BOTTOM_POSITION) / 2.0
        anchor = y_center - (pos_float - _STAFF_BOTTOM_POSITION) * half_step
        sign = 1.0
    n_expected = int(dist_spaces + LEDGER_RUNG_EXPECTED_SLACK)
    detail["ledger_expected"] = n_expected
    if n_expected <= 0:
        return False

    rungs = _ledger_rungs_in_cell(ev)
    tol = LEDGER_RUNG_Y_TOL_SPACES * spacing_canonical
    min_overlap = LEDGER_RUNG_MIN_X_OVERLAP * max(1.0, w_c)
    x0, x1 = x_c, x_c + w_c
    found = 0
    for k in range(1, n_expected + 1):
        want_y = anchor + sign * k * spacing_canonical
        for rx0, rx1, ry in rungs:
            if abs(ry - want_y) > tol:
                continue
            if min(rx1, x1) - max(rx0, x0) < min_overlap:
                continue
            found += 1
            break
    detail["ledger_found"] = found
    return found == 0


def _band_spaces(y: float, line_ys, spacing: float) -> Optional[float]:
    """Distance from `y` to a staff's five-line band, in its staff spaces.

    ⚠️ GATHER's own arithmetic (`gather._band_distance_spaces`), CALLED, not
    restated, so this rule's distance and the contest's `Q.GLYPH_BAND_DISTANCE`
    are one number and cannot drift.
    """
    from ..gather import _band_distance_spaces
    try:
        ys = [float(v) for v in line_ys]
        sp = float(spacing)
    except (TypeError, ValueError):
        return None
    if len(ys) < 2 or sp <= 0:
        return None
    return _band_distance_spaces(y, ys, sp)


def _staff_geometry(ev: Evidence, staff) -> Optional[Tuple[List[float],
                                                           float, List[str]]]:
    lines = ev.rows(Q.STAFF_LINES, subject=staff)
    spacing = ev.rows(Q.STAFF_SPACING, subject=staff)
    if not lines or not spacing:
        return None
    try:
        ys = sorted(float(v) for v in lines[-1].value)
        sp = float(spacing[-1].value)
    except (TypeError, ValueError):
        return None
    if len(ys) < 2 or sp <= 0:
        return None
    return ys, sp, [lines[-1].id, spacing[-1].id]


def _belongs_to_a_nearer_staff(ev: Evidence, box_row, contested_by,
                               detail: Dict[str, Any]
                               ) -> Optional[Tuple[str, List[str]]]:
    """ROADMAP 2.7b — `(near staff key, rows used)` where this head is far
    from the staff it was filed on, joined to it by no kept rung, and close to
    another staff of its system. `None` otherwise (and the facts it measured
    are left in `detail["nearer_staff_signal"]` either way).

    Four conditions, ALL in the PAGE frame (`Q.STAFF_LINES`, `Q.STAFF_SPACING`
    and `bbox_page_px`, the three facts every staff and glyph carries):

      1. the head's centre is more than `NEARER_STAFF_FILED_MIN_SPACES` outside
         the band of its FILED staff (CLAUDE.md §10: the cell pad is 4-6
         spaces and reaches the next staff's ink — the pad is what put it
         here, not the engraver);
      2. another staff of the SAME system has a line within
         `NEARER_STAFF_NEAR_MAX_SPACES` of it, and is nearer than the filed
         one;
      3. the ledger lines do NOT name the filed staff: Sean's exception is a
         LADDER from the filed staff that reaches the note, asked of
         `ownership.ledger_direction` — the one helper `glyph_owner` asks
         too (ROADMAP 2.6c) — over the KEPT rungs of the head's cell and the
         near staff's same-index cell (3.4g-2's `ledger_is_not_a_ledger`
         VERDICTS are read, never the raw boxes, so a staff-line fragment
         cannot vouch for the note; the head's OWN ledger line says the note
         stands on a ledger, not whose; one stray rung, such as a chord-
         mate's own line, is not a ladder);
      4. the near staff does NOT hold a twin of this ink: a glyph carrying a
         `Q.GLYPH_BAND_DISTANCE` row that names the near staff is inside
         `glyph_owner`'s contest (ROADMAP 2.6), which decides who owns it and
         DROPS the loser there. Refusing it here as well would be two answers
         to one question — and would drop the winner too if the contest kept
         it on this staff. So this rule YIELDS, and says so in `detail`.

    ⚠️ DROPPED, NEVER RELOCATED (CLAUDE.md §10). The head is refused on the
    staff it was filed on; nothing is added to the near staff. Where the near
    staff's own cell did not detect the ink (no twin), the note goes missing
    rather than being written a staff too high at the wrong pitch — Sean's
    trade: a missing note is visible as a gap, a wrong one has to be hunted.
    """
    page_box = (box_row.detail or {}).get("bbox_page_px")
    staff = ev.subject.at(Kind.STAFF)
    if not page_box or len(page_box) != 4 or staff is None:
        return None
    mine = _staff_geometry(ev, staff)
    if mine is None:
        return None
    ys, sp, used = mine
    y = (float(page_box[1]) + float(page_box[3])) / 2.0
    filed = _band_spaces(y, ys, sp)
    if filed is None:
        return None
    signal: Dict[str, Any] = {"filed_spaces": round(filed, 3)}
    detail["nearer_staff_signal"] = signal
    if filed <= NEARER_STAFF_FILED_MIN_SPACES:
        return None

    # ⚠️ THE ADJACENT STAFF ON THE HEAD'S OWN SIDE, AND ONLY THAT ONE. Staff
    # indices run down the system in page order, so the only staff that can
    # be nearer than the filed one lies on the side the head stands on, and
    # the nearest of those is the adjacent one. NOT `ev.subjects(Kind.
    # STAFF)`: `Log._index` clears that cache on every verdict write, so a
    # per-head call walks the whole index once per head — measured, the
    # Litolff whole-movement ADJUDICATE ran past 31 CPU-minutes against ~20.
    # A system's top staff has no staff above it; a bottom staff's
    # neighbour below is simply absent from the record, which is the truth.
    if staff.staff is None or (y < ys[0] and staff.staff == 0):
        return None
    other = R.staff(staff.page, staff.system,
                    staff.staff - 1 if y < ys[0] else staff.staff + 1)
    geo = _staff_geometry(ev, other)
    if geo is None:
        return None
    d = _band_spaces(y, geo[0], geo[1])
    if d is None:
        return None
    near = (d, other, geo[2])
    signal["near_staff"] = near[1].to_key()
    signal["near_spaces"] = round(near[0], 3)
    if near[0] > NEARER_STAFF_NEAR_MAX_SPACES or near[0] >= filed:
        return None

    # ── 3. the ledger lines name the FILED staff: Sean's exception ─────────
    # ⚠️⚠️ ROADMAP 2.6c (second half): ASKED OF THE ONE HELPER `glyph_owner`
    # asks (`ownership.ledger_direction`), never re-derived here, so the two
    # decisions cannot credit a rung differently. The first cut kept a head
    # on ANY kept rung lying between it and the filed staff, and Sean's
    # 2.7b.8 verdicts found that wrong three times in six: #4 and #22 were
    # kept by a CHORD-MATE's own ledger (the near staff's second rung, beyond
    # the head) with the filed staff's own inner rungs all absent; #10 (the
    # `s` of *sempre*) by two real rungs of the filed staff that END 1.37
    # spaces short of it. A rung now vouches for the filed staff only as part
    # of a LADDER from that staff that reaches the note (FINDINGS §2.6c.2).
    # Rungs are read from the head's cell AND the near staff's same-index
    # cell -- one bar, both pads -- with their 3.4g-2 verdicts.
    x0, x1 = float(page_box[0]), float(page_box[2])
    cell = ev.subject.at(Kind.CELL)
    near_cell = R.cell(cell.page, cell.system, near[1].staff, cell.cell)
    # ⚠️ ROADMAP 2.6d: `cv_rungs` is the SAME second reader `glyph_owner`
    # merges in -- a step the detector drew no `ledgerLine` box on, read
    # off the ink instead. One pool, so the two decisions cannot credit a
    # rung differently. ⚠️ THE COUNT IS READ HERE TOO, DIRECTLY, and not
    # only inside `cv_rungs` (an aliased cross-module call `inventory
    # --check`'s AST walk does not follow, unlike the local helpers below
    # it -- CLAUDE.md §4d's third blind spot, hit again): `signal` is where
    # every fact this decision measured but did not act on already lives.
    cv_rows = ev.rows(Q.LEDGER_RUNG_INK)
    signal["cv_rung_ink_rows"] = len(cv_rows)
    rungs = cell_rungs(ev, (cell, near_cell)) + cv_rungs(ev)
    filed_side, near_side = ladder_sides_with_discount((
        (staff.to_key(), y, x0, x1, ys, sp, rungs),
        (near[1].to_key(), y, x0, x1, geo[0], geo[1], rungs)))
    reading = ledger_direction((filed_side, near_side))
    signal["ledger"] = reading.summary()
    signal["kept_rungs_toward_filed"] = filed_side.n_toward
    if filed_side.refused:
        signal["refused_rungs_toward_filed"] = dict(filed_side.refused)
    if reading.winner == staff.to_key():
        return None

    # ── 4. a twin on the near staff: `glyph_owner` decides, not this ───────
    if near[1].to_key() in contested_by:
        signal["yields_to_glyph_owner"] = True
        return None
    return near[1].to_key(), used + near[2]


#: The two reasons a HUMAN row can refuse a box, and they are kept apart
#: because they are different claims about the page. ⚠️ ROADMAP 3.4g: every
#: per-family refusal declares BOTH, so a reader of a census can tell *there
#: is nothing here* from *there is something here and it is not this staff's*.
HUMAN_NOT_A_SYMBOL = "human_not_a_symbol"
HUMAN_OTHER_STAFF = "human_other_staff"
HUMAN_REFUSAL_REASONS = (HUMAN_NOT_A_SYMBOL, HUMAN_OTHER_STAFF)


def _human_not_a_symbol(ev: Evidence, detail: Dict[str, Any], *,
                        contested: Optional[bool] = None
                        ) -> Optional[Tuple[Any, str]]:
    """A human looked at this box and said the ink is not that kind of symbol.

    Returns `(row, reason)` — one of `HUMAN_REFUSAL_REASONS` — or None.

    ⚠️⚠️ ROADMAP 3.4 — THE ONE READ THAT MAKES A CORRECTION A WITNESS RATHER
    THAN A NOTE. `review/human_evidence.py` files `Q.HUMAN_BOX_VERDICT` on the
    glyph subject the detector already owns; this is the only place in the
    pipeline that acts on it. Everything else a review pass produces is
    reported and applied by nobody, which is the design: a stance on a VERDICT
    is never read by a stage at all.

    ⚠️ DELIBERATELY ITS OWN FUNCTION AND NOT A BRANCH IN THE BODY, so that
    roadmap 2.11's `is_a_clef` refusal — the other new reason this decision is
    about to grow, from a different lane on a different branch — lands beside
    it rather than through it.

    ⚠️ THREE OF THE FIVE LABELS, AND THE OTHER TWO ARE DECLINED HERE ON
    PURPOSE (ROADMAP 3.4c, Sean: *"and to label boxes as nothing or belongs to
    another staff etc."*). The value vocabulary is
    `review/human_evidence.HUMAN_BOX_LABELS` and it is parsed by that module's
    `human_says`, never by a second `split(":")` here:

      `not_a_symbol`              ✅ refuse. There is no symbol here.
      `duplicate_of:<glyph>`      ✅ refuse. One piece of ink is one note, and
                                     the twin he named is the one that keeps
                                     it. ⚠️ THIS DECISION DOES NOT CHECK THAT
                                     THE TWIN SURVIVES — if the human names a
                                     box that is itself refused, both go and
                                     the ink is lost. `rerun.py` measures the
                                     note count, which is where that would
                                     show; a rule that kept one of a pair
                                     alive would be a rule nobody has written.
      `is_a:<non-notehead>`       ✅ refuse, `detail.human_says` naming the
                                     class. He looked at the print and said it
                                     is a clef; a clef is not a notehead.
      `is_a:<notehead class>`     ❌ NOT a refusal. black -> half is a
                                     disagreement about WHICH head, not about
                                     whether there is one, and answering it
                                     here would delete the note instead of
                                     re-reading it. `ingest` files the new
                                     class as a human BOX of its own, so
                                     `adjudicate_duration` decides on that
                                     subject; the machine's head stands beside
                                     it and `rerun.py` reports both.
      `owner:<staff>`             ❌ a different question entirely — that is
                                     `ownership._human_owner`'s: he named a
                                     staff, and the contest awards it there.
      `owner:other`               ✅ refuse, reason `human_other_staff`.
                                     ⚠️ ROADMAP 3.4g, SEAN 2026-09-23 ON HIS
                                     OWN MARKS: *"'belongs to violin' were
                                     about the fact that they belonged to a
                                     different staff"* — the point was NOT
                                     THIS STAFF and naming the neighbour was
                                     incidental. So the answer that names no
                                     staff is the honest spelling of what he
                                     meant, and it says exactly one thing:
                                     not here. ⚠️ DROPPED, NEVER RELOCATED
                                     (CLAUDE.md §10) — and it cannot go to
                                     `glyph_owner`, which must return a STAFF
                                     KEY, so `ownership._human_owner` skips
                                     it by name and this is where it lands.
      `redrawn`                   ❌ the box is in the wrong PLACE, and what to
                                     do with the machine's own box is a
                                     decision nobody has taken. Reported by
                                     `review/feedback.py` as a human row that
                                     reached no verdict rather than quietly
                                     read as a refusal.

    ⚠️ IT DOES NOT WEIGH ANYTHING. A human reading the print is not a term
    beside the width floor; he is the ground the width floor was measured
    against (`benchmarks/omr-notehead-width-2026-09`, 255 print-adjudicated
    boxes). So this is tested FIRST and returns the row that said so.
    """
    from ..review.human_evidence import (NOTEHEAD_PREFIX as _HEAD,
                                         OWNER_OTHER as _OTHER,
                                         human_says as _says)
    mine = ev.subject.at(Kind.STAFF)
    mine = mine.to_key() if mine is not None else None
    # ⚠️⚠️ ROADMAP 3.4g. A NAMED OWNER IS A REFUSAL **ONLY WHERE THE
    # OWNERSHIP CONTEST CANNOT HEAR IT**, and the test is the record's own.
    # `adjudicate_glyph_owner`'s domain is `subjects_from=
    # Q.GLYPH_BAND_DISTANCE`, the CONTESTED population — so a glyph carrying
    # a band row is one that decision WILL decide, and reading the same row
    # here as well would file two answers to one question and rename its
    # export bucket from `owned_by_another_staff` (which says WHICH staff) to
    # a reason that does not. A glyph carrying NO band row is one `glyph_owner`
    # never sees at all: on Sean's Viola pass both of the boxes he marked
    # *belongs to Violin II* were ACCIDENTALS, and an accidental is never in
    # that contest, so his reading reached nothing. Here it reaches a refusal.
    # ⚠️ AND NEVER WHERE HE NAMED **THIS** STAFF: `human_evidence._twin_on`
    # records that the commonest `own_box` is a human pulling a glyph BACK to
    # the staff it was cut from, which is the opposite claim.
    # ⚠️ `contested` IS THE CALLER'S READ, PASSED IN, NOT TAKEN HERE. Each
    # consumer module has to read `Q.GLYPH_BAND_DISTANCE` at its own site or
    # `inventory --check` reports the declaration as inert — it follows helper
    # calls only inside the decision's OWN module — and a declared input the
    # tool cannot see is how a `wants` entry comes to mean nothing. Default
    # `None` reads the rows here, for a caller that has not looked.
    band = (bool(ev.rows(Q.GLYPH_BAND_DISTANCE)) if contested is None
            else bool(contested))
    rows = []
    for r in ev.rows(Q.HUMAN_BOX_VERDICT):
        verb, arg = _says(getattr(r, "value", None))
        if verb == "not_a_symbol" or verb == "duplicate_of":
            rows.append((r, verb, arg, HUMAN_NOT_A_SYMBOL))
        elif verb == "owner" and arg == _OTHER:
            rows.append((r, verb, arg, HUMAN_OTHER_STAFF))
        elif verb == "owner" and arg and arg != mine and not band:
            rows.append((r, verb, arg, HUMAN_OTHER_STAFF))
        elif verb == "is_a" and not str(arg or "").startswith(_HEAD):
            rows.append((r, verb, arg, HUMAN_NOT_A_SYMBOL))
    if not rows:
        return None
    row, verb, arg, reason = rows[-1]
    detail["human_reader"] = row.reader
    detail["human_row"] = row.id
    # ⚠️ WHAT HE SAID, IN HIS OWN SPELLING, ON THE VERDICT'S OWN DETAIL. A
    # refusal that records only *a human refused this* cannot be turned into a
    # fix; a refusal that records *a human says this is a clefCAlto* can.
    detail["human_says"] = (f"{verb}:{arg}" if arg is not None else verb)
    # ⚠️ The sidecar and the action id travel WITH the row, so the feedback
    # file can name the click that produced a refusal without re-reading the
    # sidecar and hoping the ids still line up.
    for k in ("sidecar", "action", "note"):
        if k in (row.detail or {}):
            detail[f"human_{k}"] = row.detail[k]
    return row, reason


@decision(
    quantity=Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
    # ⚠️ ROADMAP 2.6d adds `Q.LEDGER_RUNG_INK`: `_belongs_to_a_nearer_staff`
    # asks the same `ownership.ledger_direction` helper `glyph_owner` does,
    # over the same merged (detector + CV) rung pool.
    composed_from=(Q.GLYPH_BOX, Q.CELL_BOX, Q.CELL_STAFF_SPACE,
                  Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_CONF, Q.CLEF_LOCATED,
                  Q.HUMAN_BOX_VERDICT, Q.LEDGER_IS_NOT_A_LEDGER,
                  Q.GLYPH_BAND_DISTANCE, Q.STAFF_LINES, Q.STAFF_SPACING,
                  Q.LEDGER_RUNG_INK,
                  # ⚠️ ROADMAP 2.12l: the cross-staff quorum reads how many
                  # staves this system has, and nothing else this decision
                  # already declares carries that fact.
                  Q.SYSTEM_STAFF_COUNT),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_BOX, Q.CELL_BOX, Q.CELL_STAFF_SPACE,
          Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_CONF, Q.CLEF_LOCATED,
          Q.HUMAN_BOX_VERDICT, Q.LEDGER_IS_NOT_A_LEDGER,
          Q.GLYPH_BAND_DISTANCE, Q.STAFF_LINES, Q.STAFF_SPACING,
          Q.LEDGER_RUNG_INK, Q.SYSTEM_STAFF_COUNT),
    subjects_from=Q.NOTEHEAD_CLASS,
    reasons=HUMAN_REFUSAL_REASONS + ("is_a_clef", "clipped_fragment",
                                     "too_narrow", "belongs_to_a_nearer_staff",
                                     "is_a_meter_digit",
                                     "notehead",
                                     ABSTAIN.NO_STAFF_GEOMETRY),
    mode=Mode.ADDITIVE,
)
def adjudicate_notehead_is_not_a_notehead(ev: Evidence) -> Ruling:
    """Is this glyph the detector called a notehead actually something else?

    ⚠️ THREE MEASURED RULES SHIP, A FOURTH IS MEASURED AND HELD BACK, AND A
    HUMAN'S OWN READING OUTRANKS ALL OF THEM — none of them a GATHER filter.
    See the module docstring for where each threshold comes from and why the
    held-back one does not set the value.

    -1. `human_not_a_symbol` (roadmap 3.4) — a `Q.HUMAN_BOX_VERDICT` row
       reading `not_a_symbol`, filed by `review/human_evidence.py` from a
       review pass. Tested FIRST and OUTSIDE the geometry gate; see
       `_human_not_a_symbol`.
    0. `is_a_clef` (ROADMAP 2.11) — the CV clef locator READ a clef on this
       very box's ink, having found the box too small to be what the ink is
       (Sean, 2026-09-23). This rule MEASURES NOTHING: it reads the
       `overrode_glyph_subjects` the read itself named, so the refusal and the
       read can never disagree. It runs before the measured rules because it
       is backed by a positive identification rather than by a shape that
       looks wrong, and after the human because a human looked at the print.

    1. `clipped_fragment` — a sliver of ink flush against the cell's own crop
       boundary: a neighbouring staff's ink bleeding into this cell's
       padding, read as a hollow notehead because a flat sliver has that
       shape (`transcribe._drop_clipped_notehead_fragments`).
    2. `too_narrow` — a `noteheadBlack*` box under 1.0 staff spaces wide,
       measured against the print on two publishers and costing 0 of 103
       confirmed real noteheads (`omr-notehead-width-2026-09`), REPRODUCED
       here on the same crop-pass join (0 of 103 confirmed heads cost,
       ~40 confirmed non-noteheads caught).
    3. `unladdered` (`UNLADDERED_SHIPS = False`, see its own constant for the
       measurement) — a low-confidence notehead standing outside the staff
       with not one ledger rung joining it to that staff
       (`transcribe._drop_unladdered_noteheads`). MEASURED NET NEGATIVE on
       the two acceptance documents: costs 4 of 29 / 4 of 74 confirmed real
       noteheads against 0 of 34 / 2 of 44 confirmed non-noteheads caught.
       Its signal is still COMPUTED and recorded in `detail["unladdered_
       signal"]` on every notehead so the finding stays on the record and a
       future session can re-enable it once a page-frame, cross-cell ledger
       search is built and re-measured — it does not set `value=True`.
    2b. `belongs_to_a_nearer_staff` (ROADMAP 2.7b, SHIPS) — Sean's
       convention: a head more than `NEARER_STAFF_FILED_MIN_SPACES` outside
       its filed staff, joined to it by no KEPT rung, with another staff of
       its system nearer and within `NEARER_STAFF_NEAR_MAX_SPACES`, is that
       staff's note and not this one's. It is NOT `unladdered` re-enabled:
       that rule's single witness (a rung) failed on ledger recall; this one
       adds the page's own staff geometry as a second, independent witness,
       and a note far from its staff but near no other is untouched. It YIELDS
       to `glyph_owner` wherever the near staff holds a twin (see
       `_belongs_to_a_nearer_staff`). Dropped, never relocated.

    ⚠️ A GLYPH NONE OF THE SHIPPED RULES CONDEMNS DECIDES `False`, REASON
    `notehead` — not an abstention. Geometry was available and was tested;
    silence would read as "we could not tell" when the honest claim is "we
    looked and found nothing wrong with it", the same distinction
    `adjudicate_notehead_is_a_whole_rest` draws for the identical reason.

    ⚠️ ABSTAINS ONLY WHEN THE UNIT ITSELF IS MISSING (`Q.CELL_STAFF_SPACE`),
    which every rule above needs to convert a canonical pixel distance into
    staff spaces. A missing PAGE frame (needed only by `clipped_fragment`)
    does not abstain the whole decision — it just cannot condemn on that one
    rule, and `too_narrow` still runs.
    """
    box_row = _glyph_box_row(ev)

    # ⚠️⚠️ ROADMAP 3.4, AND IT IS FIRST — BEFORE THE GEOMETRY GATE. Every
    # other rule here abstains `no_staff_geometry` when the cell cannot supply
    # a unit, and that is right for a rule that measures. A human did not
    # measure: he looked at the print. Putting this test after the gate would
    # have thrown his reading away on exactly the cells where the machine can
    # say least, which is where he is worth most.
    human_detail: Dict[str, Any] = {}
    human = _human_not_a_symbol(ev, human_detail)
    if human is not None:
        human_row, human_reason = human
        if box_row is not None and isinstance(box_row.value, (list, tuple)) \
                and len(box_row.value) == 5:
            human_detail["class"] = box_row.value[0]
        # ⚠️ THE TWO REASONS ARE RETURNED AS LITERALS, not as the variable the
        # parser handed back. `brakes.vocabulary_gap` reads the `reason=`
        # slot's AST to ask whether every DECLARED reason is one a `Ruling`
        # here can actually carry, and a computed reason makes the whole
        # MODULE unresolved — every decision in it. The branch is the price
        # of keeping that check able to fail.
        if human_reason == HUMAN_OTHER_STAFF:
            return Ruling(value=True, reason="human_other_staff",
                          used=(human_row.id,), detail=human_detail)
        return Ruling(value=True, reason="human_not_a_symbol",
                      used=(human_row.id,), detail=human_detail)

    if box_row is None or not isinstance(box_row.value, (list, tuple)) \
            or len(box_row.value) != 5:
        return Ruling.abstain(ABSTAIN.NO_STAFF_GEOMETRY)

    # ⚠️ BEFORE THE STAFF-SPACE GUARD, because this rule needs no unit at all:
    # it cites a row that already did the geometry. Putting it after would
    # make a clef-box refusal depend on a measurement it does not use.
    clef_row = _is_a_clef(ev)
    if clef_row is not None:
        return Ruling(
            value=True, reason="is_a_clef",
            used=(clef_row.id, box_row.id),
            detail={"class": box_row.value[0],
                    "clef_read": clef_row.value,
                    "clef_frame": clef_row.frame,
                    "clef_symmetry": clef_row.score})

    spacing = _cell_staff_space(ev)
    if spacing is None:
        return Ruling.abstain(ABSTAIN.NO_STAFF_GEOMETRY)

    detail: Dict[str, Any] = {"class": box_row.value[0]}
    used = [box_row.id]

    # ⚠️ COMPUTED UNCONDITIONALLY, BEFORE THE SHIPPED RULES RETURN, so the
    # measurement stays on the record even where a shipped rule already
    # condemns the glyph for a different reason (the two populations
    # overlap: 5 of 205 / 2 of 134 `unladdered`-flagged glyphs on the two
    # documents are ALSO `too_narrow`).
    ladder_detail: Dict[str, Any] = {}
    would_unladder = _unladdered(ev, box_row, spacing, ladder_detail)
    if ladder_detail:
        detail["unladdered_signal"] = {"would_fire": would_unladder,
                                       **ladder_detail}

    if _clipped_fragment(ev, box_row, spacing, detail):
        return Ruling(value=True, reason="clipped_fragment",
                      used=tuple(used), detail=detail)
    if _too_narrow(box_row, spacing, detail):
        return Ruling(value=True, reason="too_narrow",
                      used=tuple(used), detail=detail)
    # ⚠️ ROADMAP 2.12l. AFTER THE SHAPE RULES (a sliver or a too-narrow box is
    # not a note at all regardless of what else prints at this x) and BEFORE
    # the ownership contest (a meter digit is nobody's note, so there is
    # nothing for `glyph_owner` to arbitrate). See the module's own block
    # comment above `METER_DIGIT_X_MAX_SPACES` for the signature and its
    # measurement, and `detail` for what the two gates found either way.
    meter_digit_detail: Dict[str, Any] = {}
    if _is_a_meter_digit(ev, box_row, spacing, meter_digit_detail):
        detail.update(meter_digit_detail)
        partner_id = meter_digit_detail.get("meter_digit_partner")
        return Ruling(value=True, reason="is_a_meter_digit",
                      used=tuple(used + ([partner_id] if partner_id else [])),
                      detail=detail)
    if meter_digit_detail:
        detail["meter_digit_signal"] = meter_digit_detail
    # ⚠️ ROADMAP 2.7b. AFTER THE SHAPE RULES: a sliver or a too-narrow box is
    # not a note at all, which is the load-bearing thing to say about it;
    # this rule says the ink IS a note, and another staff's. The contest
    # domain is read HERE, at the decision's own site, and passed in (the
    # reason `_human_not_a_symbol` gives): the rule must yield to
    # `glyph_owner` wherever the near staff holds a twin.
    contested_by = {(r.detail or {}).get("candidate")
                    for r in ev.rows(Q.GLYPH_BAND_DISTANCE)}
    nearer = _belongs_to_a_nearer_staff(ev, box_row, contested_by, detail)
    if nearer is not None:
        near_key, geo_used = nearer
        return Ruling(value=True, reason="belongs_to_a_nearer_staff",
                      used=tuple(used + geo_used), detail=detail)
    if UNLADDERED_SHIPS and would_unladder:
        return Ruling(value=True, reason="unladdered",
                      used=tuple(used), detail=detail)
    return Ruling(value=False, reason="notehead", used=tuple(used),
                  detail=detail)
