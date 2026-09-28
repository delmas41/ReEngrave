"""Unread-mark subject — ROADMAP 2.4c.

CLAUDE.md's definition of done: *"every bar the reader could not read is
MARKED as unread and never invented"* (plan SS4). Today a notehead the
detector never boxed leaves NO trace on the record at all -- the bar exports
looking complete, with a note silently missing. `Q.INK` (`gather.gather_ink`,
CLAUDE.md SS4b) was built as a PRODUCER ONLY, "read by nothing on purpose",
for exactly this: a connected piece of a cell's ink that no detection
explains is evidence something was printed and not read, independent of
what it is.

⚠️ THIS DECISION NAMES A MARK, NEVER A NOTE. No pitch, no duration, no class
is claimed -- only that a bar holds ink the record cannot account for at a
column another staff of the same system corroborates. Rule 6 (CLAUDE.md SS2):
a wiring change may CONNECT a decision; it may never let one GUESS.

## The population, and why each test is there

1. **Zero coverage** (`ink_detector_coverage == 0.0`). `gather_ink`'s own
   field already means "the detections account for NONE of this ink" --
   deliberately excluding wide boxes (`staff`, `slur`) from what counts as
   "explaining" (`_explaining_detections`), so a component is not waved
   through just because a staff line's own bounding box happens to cross it.
   Reusing this field rather than re-deriving overlap is CONNECT, not GUESS.

2. **Notehead-sized.** `NOTEHEAD_INK_WIDTH_SPACES` / `_HEIGHT_SPACES`.
   The floor (1.0 staff spaces wide) is `notehead_precision.
   TOO_NARROW_MIN_SPACES`, IMPORTED rather than restated -- the same width
   floor measured at 0 of 103 confirmed noteheads cost
   (`benchmarks/omr-notehead-width-2026-09/FINDINGS.md`). The ceiling (1.8)
   is that same FINDINGS' own measured p5-p95 band for a print-confirmed
   notehead's box, "1.26-1.78 spaces wide", rounded outward. The height
   band's floor (0.34) is that FINDINGS' own "the shortest print-confirmed
   head is 0.340 spaces tall"; its ceiling is held symmetric with the width
   ceiling, since a component much taller than it is wide is what
   `omr-ink-gather-2026-09`'s own probe already calls a `blob` (a merge, not
   one mark) at a coarser cut (>=4x4 spaces).

3. **Corroborated column.** `Q.ONSET_COLUMN`'s own per-system verdict
   (`adjudicators.rhythm.adjudicate_onset_column`) is READ, never
   re-derived: a bar's column list, filtered to columns with
   `n_witness >= ONSET_COLUMN_MIN_WITNESSES` witnessed by staves OTHER than
   this component's own, within `ONSET_COLUMN_TOLERANCE_SPACES` of this
   component's page x-centre. Both constants are IMPORTED from
   `adjudicators.rhythm`, the same tolerance measured against a
   circular-shift null for the identical question ("are these two staves at
   the same x") -- CLAUDE.md SS6b: "reuse the constant this repo already
   measured ... rather than inventing a second notion of the same thing."

## The two guards against the plate facts (CLAUDE.md SS10)

⚠️ CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: the exact
tolerances below (`BARLINE_TOUCH_TOLERANCE_SPACES`,
`STAFF_LINE_SLIVER_MAX_HEIGHT_SPACES`, `STAFF_LINE_SLIVER_Y_TOLERANCE_SPACES`)
are NOT print-measured the way the width floor and the column tolerance are
-- nobody was available to ask. They are stated defensively, at values
smaller than the notehead-sized window itself so they narrow rather than
replace it, and are reported on every fired verdict's `detail` so a crop
pass can falsify them directly. A crop where the excluded component IS a
real head, or a KEPT one is plate residue, falsifies the corresponding
guard.

* **Touches a barline x** -- `measure_extractor.py`: a measure cell is
  bounded by adjacent barlines (SS3), so `Q.CELL_BOX`'s own left/right edge
  IS the barline the cell was cut at. On a SHATTERING plate (Breitkopf) a
  barline breaks into fragments, and a fragment near the cell edge can be
  notehead-sized. A component within `BARLINE_TOUCH_TOLERANCE_SPACES` of
  either edge is excluded.
* **Lies on a staff line's y** -- on a MERGING plate (Litolff) a staff-line
  remnant bridges glyphs and survives as a flat sliver; a component both
  SHORT (`STAFF_LINE_SLIVER_MAX_HEIGHT_SPACES` -- inside the notehead-sized
  window's own floor, but well short of a genuine note's height) and
  centred within `STAFF_LINE_SLIVER_Y_TOLERANCE_SPACES` of
  one of `Q.STAFF_LINES`' five y-values is excluded. This is deliberately
  narrower than "sits on a line" in the ordinary sense -- CLAUDE.md SS10
  itself: a note standing on a printed line is completely normal and would
  span roughly a full staff space straddling it, not sit thinly astride it.

## Stage

ADJUDICATE: the answer FOLLOWS from rows already on the record (`Q.INK`,
`Q.ONSET_COLUMN`, `Q.STAFF_LINES`, `Q.CELL_BOX`) or the decision abstains.
Nothing here is INFER's business -- there is no candidate to narrow, only a
test that passes or does not.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..adjudicate import Evidence, Mode, Ruling, decision
from ..record import ABSTAIN, Kind, Outcome, Q, Scope
from .notehead_precision import TOO_NARROW_MIN_SPACES
from .rhythm import ONSET_COLUMN_MIN_WITNESSES, ONSET_COLUMN_TOLERANCE_SPACES

#: `benchmarks/omr-notehead-width-2026-09/FINDINGS.md` SS2: a print-confirmed
#: notehead's box runs 1.26-1.78 staff spaces wide at p5-p95 on both
#: acceptance scans; the floor is that FINDINGS' own measured width floor,
#: imported rather than restated.
NOTEHEAD_INK_WIDTH_SPACES: Tuple[float, float] = (TOO_NARROW_MIN_SPACES, 1.8)
#: Same FINDINGS: the shortest print-confirmed head measured is 0.340 spaces
#: tall; the ceiling is held symmetric with the width ceiling (a component
#: much taller than it is wide is a merge, not one mark).
NOTEHEAD_INK_HEIGHT_SPACES: Tuple[float, float] = (0.34, 1.8)

#: ⚠️ NOT PRINT-MEASURED -- see the module docstring's CONVENTION ASSUMED
#: note. Half a staff space, well inside the notehead-sized window, so it
#: narrows the population rather than replacing the size test.
BARLINE_TOUCH_TOLERANCE_SPACES = 0.5
#: ⚠️ NOT PRINT-MEASURED. ⚠️⚠️ MUST STAY ABOVE `NOTEHEAD_INK_HEIGHT_SPACES`'S
#: OWN 0.34 FLOOR OR THIS GUARD IS DEAD CODE -- a component thin enough to
#: fail the height floor never reaches this test at all, caught by a test
#: that fabricated exactly that (RED: `test_a_component_centred_on_a_staff_
#: line_and_thin_is_excluded` raised `KeyError` on an empty `excluded_by_
#: guard`, not on a wrong verdict). 0.5 is comfortably inside the notehead
#: window and comfortably short of a genuine note's own height (~0.7-1.5 on
#: the reach probe's own population).
STAFF_LINE_SLIVER_MAX_HEIGHT_SPACES = 0.5
STAFF_LINE_SLIVER_Y_TOLERANCE_SPACES = 0.15


def _component_rows(ev: Evidence) -> List[Any]:
    """Every descendant `Q.INK` row that carries a per-component box.

    ⚠️ A SUMMARY-FORM RECORD (roadmap 1.1's default since) FILES `Q.INK` ONE
    ROW PER CELL WITH NO BOX AT ALL -- `ink_bbox_canonical` is the one key
    that tells the two forms apart, because a summary row's `detail` never
    carries it (`gather.gather_ink`'s own docstring). This decision NEEDS
    the per-component form (`--ink-rows` / `OMR_INK` + `ink_component_rows=
    True` at GATHER); on a record without it, every row here is filtered out
    and the decision abstains rather than silently finding nothing.
    """
    return [r for r in ev.rows(Q.INK, scope=Scope.SELF_AND_DESCENDANTS)
            if isinstance(r.detail, dict) and "ink_bbox_canonical" in r.detail]


def _notehead_sized(d: Dict[str, Any]) -> bool:
    w, h = d.get("width_spaces"), d.get("height_spaces")
    if w is None or h is None:
        return False
    return (NOTEHEAD_INK_WIDTH_SPACES[0] <= w <= NOTEHEAD_INK_WIDTH_SPACES[1]
            and NOTEHEAD_INK_HEIGHT_SPACES[0] <= h
            <= NOTEHEAD_INK_HEIGHT_SPACES[1])


def _touches_a_barline(d: Dict[str, Any], cell_box: Optional[List[float]],
                       spacing_px: float) -> bool:
    page_box = d.get("bbox_page_px")
    if not page_box or len(page_box) != 4 or not cell_box or len(cell_box) != 4:
        return False
    tol = BARLINE_TOUCH_TOLERANCE_SPACES * spacing_px
    x0, x1 = page_box[0], page_box[2]
    cx0, cx1 = cell_box[0], cell_box[2]
    return abs(x0 - cx0) <= tol or abs(x1 - cx1) <= tol


def _on_a_staff_line(d: Dict[str, Any], lines_y_page: Optional[List[float]],
                     spacing_px: float) -> bool:
    if not lines_y_page:
        return False
    h_spaces = d.get("height_spaces")
    if h_spaces is None or h_spaces > STAFF_LINE_SLIVER_MAX_HEIGHT_SPACES:
        return False
    page_box = d.get("bbox_page_px")
    if not page_box or len(page_box) != 4:
        return False
    y_center = (page_box[1] + page_box[3]) / 2.0
    tol = STAFF_LINE_SLIVER_Y_TOLERANCE_SPACES * spacing_px
    return any(abs(y_center - ly) <= tol for ly in lines_y_page)


def _staff_lines_page(ev: Evidence, staff_subj) -> Optional[List[float]]:
    rows = ev.rows(Q.STAFF_LINES, subject=staff_subj)
    if not rows or not isinstance(rows[-1].value, (list, tuple)):
        return None
    try:
        return [float(v) for v in rows[-1].value]
    except (TypeError, ValueError):
        return None


def _staff_spacing_page(ev: Evidence, staff_subj) -> Optional[float]:
    """This staff's own line spacing, in PAGE pixels.

    ⚠️⚠️ NOT `Q.INK`'s own `cell_staff_space_px` -- that field is the
    component's CANONICAL-frame unit (`gather_ink` computes it from
    `cell.image_no_staff`, the rescaled crop `_upscale_to_canonical`
    produces), while `bbox_page_px`, `Q.CELL_BOX` and `Q.STAFF_LINES` are all
    PAGE pixels. The two units differ by the cell's own upscale factor, which
    is why `Q.ONSET_COLUMN`'s own tolerance conversion
    (`adjudicators.rhythm._system_spacing`) reads `Q.STAFF_SPACING` rather
    than anything off the ink row -- mixing the two frames here reproduced
    exactly the "canonical x compared to a page x" fault CLAUDE.md SS10 and
    `Q.ONSET_COLUMN`'s own history both name, caught by the reach probe
    finding real candidates this decision then silently excluded.
    """
    rows = ev.rows(Q.STAFF_SPACING, subject=staff_subj)
    if not rows:
        return None
    try:
        v = float(rows[-1].value)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def _cell_box(ev: Evidence) -> Optional[List[float]]:
    rows = ev.rows(Q.CELL_BOX)
    if not rows or not isinstance(rows[-1].value, (list, tuple)) \
            or len(rows[-1].value) != 4:
        return None
    return [float(v) for v in rows[-1].value]


def _corroborated_column(x_center_page: float, staff_idx: int,
                         bar: Dict[str, Any], tol_px: float
                         ) -> Optional[Dict[str, Any]]:
    for col in bar.get("columns", ()):
        if col.get("n_witness", 0) < ONSET_COLUMN_MIN_WITNESSES:
            continue
        if staff_idx in col.get("witnesses", ()):
            # this staff already reads an event there -- not an UNREAD mark
            continue
        if abs(col["x_page"] - x_center_page) <= tol_px:
            return col
    return None


@decision(
    quantity=Q.UNREAD_MARK,
    scope=Kind.CELL,
    wants=(Q.INK, Q.ONSET_COLUMN, Q.STAFF_LINES, Q.CELL_BOX, Q.STAFF_SPACING),
    subjects_from=Q.INK,
    reasons=("unread_mark", "no_mark", "no_ink_component_rows",
             "no_onset_column", "no_page_frame"),
    mode=Mode.ADDITIVE,
    composed_from=(Q.INK, Q.ONSET_COLUMN, Q.STAFF_LINES, Q.CELL_BOX,
                  Q.STAFF_SPACING),
)
def adjudicate_unread_mark(ev: Evidence) -> Ruling:
    """Does this BAR hold ink the record cannot account for, at a
    corroborated column?

    ⚠️ ADDITIVE, NEVER A GATE: this decision does not touch any note or rest
    another decision placed. It says the BAR as a whole cannot be vouched
    for; `export.py` is where that becomes a hold-out (roadmap 2.4c, the
    same mechanism roadmap 2.8 built for a bar whose durations do not sum to
    the meter).

    Decided `True` ("unread_mark") only where EVERY test passes on at least
    one component: zero detector coverage, notehead-sized, at a corroborated
    column, and neither guard excludes it. Decided `False` ("no_mark") where
    the data needed to test was present (component-form ink, a decided
    `Q.ONSET_COLUMN` covering this bar) but nothing in the bar meets all the
    tests -- an answer, not a gap, exactly the reasoning
    `adjudicate_notehead_is_not_a_notehead` gives for its own `False` branch.
    Abstains only where the INPUT itself is missing.
    """
    comps = _component_rows(ev)
    if not comps:
        return Ruling.abstain("no_ink_component_rows")

    cell = ev.subject
    system_subj = cell.at(Kind.SYSTEM)
    staff_subj = cell.at(Kind.STAFF)
    onset = ev.verdict(Q.ONSET_COLUMN, subject=system_subj)
    if onset is None or onset.outcome is not Outcome.DECIDED \
            or not isinstance(onset.value, dict):
        return Ruling.abstain("no_onset_column")
    bar = next((b for b in onset.value.get("bars", ())
               if b.get("measure") == cell.cell), None)
    if bar is None or "columns" not in bar:
        return Ruling.abstain("no_onset_column")

    lines_y = _staff_lines_page(ev, staff_subj)
    cell_box = _cell_box(ev)
    spacing_px = _staff_spacing_page(ev, staff_subj)

    used = [onset.id]
    #: ⚠️ TWO DIFFERENT "NOTHING HAPPENED"S, KEPT APART. A cell where no
    #: component even passes the coverage/size pre-filter has been LOOKED AT
    #: and answered `False` (`notehead_is_not_a_notehead`'s own reasoning for
    #: its False branch); a cell where a pre-filtered candidate exists but
    #: this staff carries no page frame at all cannot be tested and must
    #: abstain. Collapsing the two mislabels the overwhelming majority
    #: (every cell with no candidate ink) as a frame failure -- caught by
    #: comparing this decision's own abstain population against the
    #: candidates it should have seen (`debug_abstain.py`, RED before this
    #: split existed).
    any_prefilter_candidate = False
    tested_any_with_frame = False
    excluded: List[Dict[str, Any]] = []
    for row in comps:
        d = row.detail or {}
        if float(d.get("ink_detector_coverage", 1.0)) != 0.0:
            continue
        if not _notehead_sized(d):
            continue
        any_prefilter_candidate = True
        page_box = d.get("bbox_page_px")
        if not page_box or len(page_box) != 4 or not spacing_px:
            continue
        tested_any_with_frame = True
        x_center = (page_box[0] + page_box[2]) / 2.0

        if cell_box is not None and _touches_a_barline(d, cell_box, spacing_px):
            excluded.append({"glyph": row.subject.to_key(),
                             "guard": "touches_a_barline"})
            continue
        if _on_a_staff_line(d, lines_y, spacing_px):
            excluded.append({"glyph": row.subject.to_key(),
                             "guard": "on_a_staff_line"})
            continue

        tol_px = spacing_px * ONSET_COLUMN_TOLERANCE_SPACES
        col = _corroborated_column(x_center, cell.staff, bar, tol_px)
        if col is None:
            continue

        detail: Dict[str, Any] = {
            "ink_components": [row.subject.to_key()],
            "width_spaces": d.get("width_spaces"),
            "height_spaces": d.get("height_spaces"),
            "bbox_page_px": page_box,
            "column_x_page": col["x_page"],
            "column_witnesses": list(col.get("witnesses", ())),
            "column_n_witness": col.get("n_witness"),
            "excluded_by_guard": excluded,
        }
        return Ruling(value=True, reason="unread_mark",
                      used=tuple(used + [row.id]), detail=detail)

    if any_prefilter_candidate and not tested_any_with_frame:
        return Ruling.abstain("no_page_frame")
    return Ruling(value=False, reason="no_mark", used=tuple(used),
                 detail={"excluded_by_guard": excluded} if excluded else {})
