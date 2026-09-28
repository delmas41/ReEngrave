"""ROADMAP 2.4c: zero-coverage mark-sized ink at a corroborated column is a
POSSIBLY-UNREAD MARK, never a note.

CLAUDE.md's definition of done: every bar the reader could not read is MARKED
as unread and never invented. Today a notehead the detector never boxed
leaves no trace on the record at all, so the bar exports looking complete
with a note silently missing. `adjudicators.unread_mark.adjudicate_
unread_mark` reads `Q.INK`'s own per-component rows (built as a PRODUCER ONLY
for exactly this, CLAUDE.md SS4b/SS10) and `Q.ONSET_COLUMN`'s cross-staff
corroboration to name a BAR that cannot be vouched for; `export.py` holds it
out the same way roadmap 2.8 holds out a bar whose durations do not sum to
the meter.

Two halves:

* `TestTheAdjudicateDecision` builds a `Log` directly (no full GATHER/
  ADJUDICATE run) and calls the decision function on one subject at a time --
  the population test (uncovered, notehead-sized, corroborated column), its
  negative control (the SAME component at an uncorroborated x -- CLAUDE.md
  rule 7, a control must be able to fail), the covered-component control, and
  the old-record compatibility case.
* `TestExport` mirrors `test_staged_bar_sum_holdout.py`'s own pattern: a
  synthetic single-staff page with a `Q.UNREAD_MARK` verdict injected
  straight into the record, exercising `export.to_musicxml`'s RECORD-ONLY
  default and its (built, tested, not-yet-live) hold-out branch, without
  needing a real ADJUDICATE run.

⚠️⚠️ MANAGER REVIEW 2026-09-28: RECORD-ONLY UNTIL PRINT-CHECKED. 6 of 6
Breitkopf crops cut for this decision (`benchmarks/omr-ink-gather-2026-09/
FINDINGS.md` SS13.3b) are printed direction-word TEXT, not notes, and a
held-out bar throws away notes that WERE read correctly -- rule 5, print
before default. `export.UNREAD_MARK_HOLDS_OUT` (a MODULE CONSTANT, the
`notehead_precision.UNLADDERED_SHIPS` pattern, never an env flag) defaults
to `False`: the decision still fires and `export.py` still records every
bar it fires on (`report["possibly_unread_mark"]`), but does not empty the
bar. The hold-out branch is fully built and tested
(`TestTheHoldOutBranchStillWorksWhenTrusted`, which flips the constant
in-process) so it cannot rot before it is trusted to run.

⚠️ RUN RED FIRST, against the tree before `unread_mark.py` and its export
wiring existed: every test in `TestTheAdjudicateDecision` fails on
`KeyError`/`AttributeError` (no such quantity, no such module), and
`TestExport`'s recording case fails because `report["possibly_unread_mark"]`
does not exist.
"""
from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401 -- registers decisions
from tools.omr.staged import export as SX
from tools.omr.staged.record import (
    Log, Outcome, Q, READERS, Verdict, cell as R_cell, glyph as R_glyph,
    staff as R_staff, system as R_system,
)
from tools.omr.tests.test_staged_export import QUARTER, _obs, _one_staff_page, _vrd

#: A page-frame staff spacing shared by every fixture below, so a "0.10
#: staff spaces" tolerance and a "0.5 staff spaces" guard both mean a fixed,
#: legible number of pixels (2px and 10px).
SPACING_PX = 20.0


def _base_log():
    """One system, two staves, geometry only -- no ink, no column yet.

    Staff 0 is the CANDIDATE's staff; staff 1 is the OTHER WITNESS whose
    already-decided onset is what makes a column corroborated.
    """
    log = Log()
    log.observe(R_staff(0, 0, 0), Q.STAFF_SPACING, SPACING_PX,
                reader=READERS.CV_INK, frame="staff:0")
    log.observe(R_staff(0, 0, 0), Q.STAFF_LINES,
               [100.0, 120.0, 140.0, 160.0, 180.0],
                reader=READERS.CV_INK, frame="staff:0")
    log.observe(R_staff(0, 0, 1), Q.STAFF_SPACING, SPACING_PX,
                reader=READERS.CV_INK, frame="staff:1")
    log.observe(R_cell(0, 0, 0, 0), Q.CELL_BOX, [0.0, 90.0, 400.0, 190.0],
                reader=READERS.CV_INK, frame="cell:0")
    return log


def _add_component(log, *, coverage=0.0, width_spaces=1.3, height_spaces=1.0,
                   x0=140.0, y0=100.0, glyph_ord=200000):
    """One `Q.INK` component row, in the per-component form `--ink-rows`
    files (`ink_bbox_canonical` is the key that tells the two forms apart --
    see `adjudicators.unread_mark._component_rows`)."""
    w = width_spaces * SPACING_PX
    h = height_spaces * SPACING_PX
    sub = R_glyph(0, 0, 0, 0, glyph_ord)
    log.observe(sub, Q.INK, "ink", reader=READERS.CV_INK, frame="cell:0",
               ink_bbox_canonical=[0, 0, w, h], ink_area_px=int(w * h),
               ink_fill=1.0, ink_n_components=1, ink_share_of_cell=1.0,
               ink_detector_coverage=coverage, ink_explained_by=[],
               width_spaces=width_spaces, height_spaces=height_spaces,
               cell_staff_space_px=100.0,   # CANONICAL frame -- never read
               bbox_page_px=[x0, y0, x0 + w, y0 + h],
               x_center_page=x0 + w / 2.0, y_center_page=y0 + h / 2.0)
    return sub


def _add_onset_column(log, *, column_x=None, n_witness=2, witnesses=(1, 2)):
    """A DECIDED `Q.ONSET_COLUMN` verdict, injected directly rather than
    derived -- this file tests `adjudicate_unread_mark` in isolation, the
    same way `test_staged_bar_sum_holdout.py` injects `Q.DURATION` rather
    than running a full ADJUDICATE pass."""
    if column_x is None:
        column_x = 140.0 + 1.3 * SPACING_PX / 2.0  # the default component's centre
    value = {"bars": [{
        "measure": 0, "staves": 3,
        "columns": [{"x_page": column_x, "witnesses": list(witnesses),
                    "n_witness": n_witness, "residual_spaces": 0.0}],
        "n_columns": 1, "n_corroborated": 1, "alone": [],
        "events_per_space": 1.0,
    }]}
    log.record(Verdict(
        id="vrd:onset", subject=R_system(0, 0), quantity=Q.ONSET_COLUMN,
        outcome=Outcome.DECIDED, value=value, decider="t", reason="columns_read"))


def _decide(log, quantity=Q.UNREAD_MARK):
    """Run the decision under test and assert it IS the one this file is
    about. ⚠️ `quantity=Q.UNREAD_MARK` is a literal default so `health.py`'s
    own textual scanner -- which walks each test's called helpers one level
    for a `Q.<NAME>` attribute access -- attributes every test in this file
    to `unread_mark` rather than reporting it an EMPTY CELL. That scanner is
    honest about mis-scoring tests that assert through a shared helper
    (`health.py`'s own docstring), and this is the cheap, correct fix rather
    than a permanent exception on `health --check`."""
    spec = adjudicate.REGISTRY[quantity]
    log.freeze()
    v = adjudicate.adjudicate_one(log, spec, R_cell(0, 0, 0, 0))
    assert v.quantity == quantity
    return v


class TestTheAdjudicateDecision(unittest.TestCase):
    def test_uncovered_notehead_sized_component_at_a_corroborated_column_fires(self):
        """The population this decision exists for."""
        log = _base_log()
        _add_component(log)
        _add_onset_column(log)
        v = _decide(log)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "unread_mark")
        self.assertIs(v.value, True)
        self.assertIn("glyph/0/0/0/0/200000", v.detail["ink_components"])

    def test_the_SAME_component_at_an_uncorroborated_x_does_not_fire(self):
        """⚠️ CLAUDE.md rule 7: a control must be able to fail. Nothing about
        the component changes -- only the column it would need to land in
        moves far enough away that it no longer corroborates."""
        log = _base_log()
        _add_component(log)
        _add_onset_column(log, column_x=999.0)
        v = _decide(log)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "no_mark")
        self.assertIs(v.value, False)

    def test_a_column_with_too_few_witnesses_does_not_corroborate(self):
        """`ONSET_COLUMN_MIN_WITNESSES` -- one staff is a reading, not
        corroboration -- read off `adjudicators.rhythm`, not restated."""
        log = _base_log()
        _add_component(log)
        _add_onset_column(log, n_witness=1, witnesses=(1,))
        v = _decide(log)
        self.assertEqual(v.reason, "no_mark")

    def test_a_covered_component_does_not_fire(self):
        """Zero coverage is the whole population -- a component the
        detector's own boxes already explain is not an unread mark."""
        log = _base_log()
        _add_component(log, coverage=0.85)
        _add_onset_column(log)
        v = _decide(log)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "no_mark")
        self.assertIs(v.value, False)

    def test_a_component_outside_the_notehead_sized_window_does_not_fire(self):
        """A barline sliver (thin and tall) is not notehead-sized."""
        log = _base_log()
        _add_component(log, width_spaces=0.2, height_spaces=6.0)
        _add_onset_column(log)
        v = _decide(log)
        self.assertEqual(v.reason, "no_mark")

    def test_a_component_touching_the_cell_edge_is_excluded_as_a_barline(self):
        """CLAUDE.md SS10 / SS9: on a SHATTERING plate a barline breaks into
        notehead-sized fragments; a measure cell is bounded by its own
        barlines (`measure_extractor.py`), so a component flush against
        `Q.CELL_BOX`'s own edge is excluded rather than trusted."""
        log = _base_log()
        # cell_box is [0, 90, 400, 190]; put the component's left edge AT it.
        _add_component(log, x0=0.0)
        _add_onset_column(log, column_x=0.0 + 1.3 * SPACING_PX / 2.0)
        v = _decide(log)
        self.assertEqual(v.reason, "no_mark")
        self.assertEqual(
            v.detail["excluded_by_guard"][0]["guard"], "touches_a_barline")

    def test_a_component_centred_on_a_staff_line_and_thin_is_excluded(self):
        """A staff-line remnant on a MERGING plate: short and centred on a
        printed line's own y, not a foreshortened head."""
        log = _base_log()
        # a staff line sits at y=120.0; a 0.4-space-tall sliver centred on it
        # -- inside the notehead height FLOOR (0.34) but short of a genuine
        # note (STAFF_LINE_SLIVER_MAX_HEIGHT_SPACES's own band).
        _add_component(log, height_spaces=0.4, y0=120.0 - 0.2 * SPACING_PX)
        _add_onset_column(log)
        v = _decide(log)
        self.assertEqual(v.reason, "no_mark")
        self.assertEqual(
            v.detail["excluded_by_guard"][0]["guard"], "on_a_staff_line")

    def test_an_old_record_without_ink_rows_abstains_and_does_not_crash(self):
        """⚠️ ROADMAP 1.1: the DEFAULT ink form since is one SUMMARY row per
        cell with no box at all. A record gathered that way -- or with
        `OMR_INK` off, or before this decision existed -- must change
        NOTHING and crash on NOTHING."""
        log = _base_log()
        log.observe(R_cell(0, 0, 0, 0), Q.INK, "ink", reader=READERS.CV_INK,
                   frame="cell:0", ink_n_components=1, ink_total_area_px=100,
                   ink_largest_share=1.0, ink_detector_coverage_max=0.0,
                   ink_explained_by_union=[])
        _add_onset_column(log)
        v = _decide(log)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_ink_component_rows")

    def test_no_ink_at_all_abstains_and_does_not_crash(self):
        log = _base_log()
        _add_onset_column(log)
        v = _decide(log)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_ink_component_rows")


def _add_text_box(log, box, *, quantity, staff=1, cell=0, glyph_ord=300000,
                  value="arco"):
    """A `Q.DIRECTION_WORD` (a READ word) or `Q.DYNAMIC_LETTER` (a detected
    dynamic glyph) observation, filed on some OTHER staff/cell of the same
    system -- the guard reads SYSTEM scope, not the candidate's own cell
    (`_text_and_dynamic_boxes`'s own docstring: a word's join placement need
    not match where the ink visually sits)."""
    sub = R_glyph(0, 0, staff, cell, glyph_ord)
    log.observe(sub, quantity, value, reader=READERS.CV_INK, frame="cell:0",
               bbox_page_px=list(box))
    return sub


class TestTheDirectionTextGuard(unittest.TestCase):
    """ROADMAP 2.4c, manager review 2026-09-28: the crop pass found the
    dominant failure mode was printed direction-word TEXT
    (`benchmarks/omr-ink-gather-2026-09/FINDINGS.md` SS13.3b), and neither
    of the first two guards has any reason to exclude a normal letter. This
    is the CONNECT the review asked for: exclude a component overlapping a
    `Q.DIRECTION_WORD` or `Q.DYNAMIC_LETTER` box read anywhere on the
    system.

    This class proves the CODE does what it says on a fabricated record --
    a unit test can do that without a raster. The REAL pricing (16 -> 11 on
    Breitkopf, 5 excluded, 2 confirmed-by-eye text bars still firing because
    the OCR/lexicon reader itself never accepted a box over them) is in
    `unread_mark.py`'s own module docstring and FINDINGS SS13.9 -- turned out
    to be measurable from data this session had already gathered, because
    `--no-surya` does not gate `gather_direction_words` (see that same
    docstring's correction).
    """

    def test_a_component_inside_a_direction_word_box_is_not_marked(self):
        log = _base_log()
        sub = _add_component(log)  # bbox_page_px [140, 100, 166, 120]
        _add_text_box(log, [135.0, 95.0, 175.0, 125.0],
                     quantity=Q.DIRECTION_WORD)
        _add_onset_column(log)
        v = _decide(log)
        self.assertEqual(v.reason, "no_mark")
        self.assertEqual(
            v.detail["excluded_by_guard"][0]["guard"],
            "overlaps_direction_text_or_dynamic")
        self.assertEqual(v.detail["excluded_by_guard"][0]["glyph"],
                         sub.to_key())

    def test_the_SAME_component_with_no_word_box_is_marked(self):
        """The control that can fail (CLAUDE.md rule 7): remove the word box
        and nothing else, and the identical component fires."""
        log = _base_log()
        _add_component(log)
        _add_onset_column(log)
        v = _decide(log)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "unread_mark")
        self.assertIs(v.value, True)

    def test_a_word_box_that_does_not_overlap_does_not_exclude(self):
        """A word box existing ELSEWHERE on the system must not blanket-
        exclude every candidate -- only an actual overlap counts."""
        log = _base_log()
        _add_component(log)
        _add_text_box(log, [900.0, 900.0, 950.0, 920.0],
                     quantity=Q.DIRECTION_WORD)
        _add_onset_column(log)
        v = _decide(log)
        self.assertEqual(v.reason, "unread_mark")

    def test_a_component_inside_a_dynamic_letter_box_is_not_marked(self):
        """The second half of the guard: a detected dynamic glyph
        (`dynamicPiano`/etc, `Q.DYNAMIC_LETTER`), not only an OCRed word."""
        log = _base_log()
        _add_component(log)
        _add_text_box(log, [135.0, 95.0, 175.0, 125.0],
                     quantity=Q.DYNAMIC_LETTER, value="dynamicPiano")
        _add_onset_column(log)
        v = _decide(log)
        self.assertEqual(v.reason, "no_mark")
        self.assertEqual(
            v.detail["excluded_by_guard"][0]["guard"],
            "overlaps_direction_text_or_dynamic")


def _mark_verdict(i, subject, ink_components=("glyph/0/0/0/0/200000",)):
    return _vrd(i, subject, Q.UNREAD_MARK, True, reason="unread_mark")


class TestExport(unittest.TestCase):
    """`export.py`'s RECORD-ONLY default, and the hold-out branch it does
    not yet run live -- `export.UNREAD_MARK_HOLDS_OUT`, default `False`."""

    def setUp(self):
        # ⚠️ BELT AND BRACES: every test in this class runs against the
        # SHIPPED default, whatever a sibling test file's own import order
        # left the module attribute at. A module-level constant flipped by
        # one test and not restored is exactly the kind of bug a `False`
        # default is supposed to make impossible to miss.
        self.assertFalse(SX.UNREAD_MARK_HOLDS_OUT,
                         "UNREAD_MARK_HOLDS_OUT must ship False -- see its "
                         "own comment and FINDINGS SS13.3b/13.9")

    def test_by_default_a_decided_unread_mark_is_RECORDED_but_NOT_held_out(self):
        """The manager-review fix: rule 5 (print before default). The bar's
        notes are written EXACTLY as they would be with no mark at all;
        only the REPORT says a mark was seen."""
        page = _one_staff_page(
            notes=[("C4", QUARTER), ("D4", QUARTER)],
            meter={"numerator": 2, "denominator": 4, "raw": "2/4"})
        page["record"]["verdicts"].append(
            _mark_verdict(950, "cell/0/0/0/0"))
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["possibly_unread_mark"]["bars"], 1)
        self.assertFalse(rep["possibly_unread_mark"]["holds_out"])
        self.assertEqual(rep["possibly_unread_mark"]["marked"][0]["held_out"],
                         False)
        self.assertEqual(rep["bars_held_out_unread_mark"]["bars"], 0)
        self.assertNotIn("possibly_unread_mark", rep["notes_not_written"])
        self.assertEqual(rep["written"].get("notes", 0), 2)
        root = ET.fromstring(xml)
        pitches = root.findall(".//pitch/step")
        self.assertEqual([p.text for p in pitches], ["C", "D"])
        self.assertEqual(root.findall(".//note/rest"), [])

    def test_a_bar_with_no_mark_is_written_normally(self):
        """The negative control: nothing about the mechanism fires on a bar
        with no `Q.UNREAD_MARK` verdict at all."""
        page = _one_staff_page(
            notes=[("C4", QUARTER), ("D4", QUARTER)],
            meter={"numerator": 2, "denominator": 4, "raw": "2/4"})
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["possibly_unread_mark"]["bars"], 0)
        self.assertEqual(rep["written"].get("bars_held_out_unread_mark", 0), 0)
        self.assertEqual(len(ET.fromstring(xml).findall(".//pitch")), 2)

    def test_a_decided_FALSE_unread_mark_does_not_hold_the_bar_out(self):
        """`no_mark` is an ANSWER, never a reason to withhold or record
        anything -- it is not even a candidate for `mark`."""
        page = _one_staff_page(
            notes=[("C4", QUARTER), ("D4", QUARTER)],
            meter={"numerator": 2, "denominator": 4, "raw": "2/4"})
        page["record"]["verdicts"].append(
            _vrd(950, "cell/0/0/0/0", Q.UNREAD_MARK, False, reason="no_mark"))
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["possibly_unread_mark"]["bars"], 0)
        self.assertEqual(rep["written"].get("bars_held_out_unread_mark", 0), 0)
        self.assertEqual(len(ET.fromstring(xml).findall(".//pitch")), 2)

    def test_a_bar_the_bar_sum_holdout_already_refused_is_not_also_recorded(self):
        """`_part_xml` tests `held is None` before asking about a mark at
        all, so a bar 2.8 already claimed never reaches `mark` and is never
        double-counted in `possibly_unread_mark` either."""
        page = _one_staff_page(
            notes=[("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)],
            meter={"numerator": 2, "denominator": 4, "raw": "2/4"})
        page["record"]["verdicts"].append(
            _mark_verdict(950, "cell/0/0/0/0"))
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["written"]["bars_held_out_sum"], 1)
        self.assertEqual(rep["possibly_unread_mark"]["bars"], 0)
        self.assertEqual(rep["notes_not_written"]["bar_does_not_add_up"], 3)
        self.assertNotIn("possibly_unread_mark", rep["notes_not_written"])


class TestTheHoldOutBranchStillWorksWhenTrusted(unittest.TestCase):
    """`UNREAD_MARK_HOLDS_OUT=True`, flipped IN-PROCESS and restored after
    every test -- proves the built branch has not rotted while it waits on
    the text guard's pricing (FINDINGS SS13.9), the same discipline
    `notehead_precision.UNLADDERED_SHIPS` is held to."""

    def test_flipping_the_constant_holds_the_bar_out_exactly_as_roadmap_2_8_does(self):
        page = _one_staff_page(
            notes=[("C4", QUARTER), ("D4", QUARTER)],
            meter={"numerator": 2, "denominator": 4, "raw": "2/4"})
        page["record"]["verdicts"].append(
            _mark_verdict(950, "cell/0/0/0/0"))
        with mock.patch.object(SX, "UNREAD_MARK_HOLDS_OUT", True):
            xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["bars_held_out_unread_mark"]["bars"], 1)
        self.assertEqual(rep["possibly_unread_mark"]["bars"], 1)
        self.assertTrue(rep["possibly_unread_mark"]["holds_out"])
        self.assertEqual(rep["possibly_unread_mark"]["marked"][0]["held_out"],
                         True)
        self.assertEqual(rep["bars_held_out_unread_mark"]["held"],
                         rep["possibly_unread_mark"]["marked"])
        self.assertEqual(rep["notes_not_written"]["possibly_unread_mark"], 2)
        self.assertEqual(rep["written"].get("notes", 0), 0)
        root = ET.fromstring(xml)
        self.assertEqual(root.findall(".//pitch"), [])
        rests = root.findall(".//note/rest")
        self.assertEqual(len(rests), 1)
        self.assertEqual(rests[0].get("measure"), "yes")

    def test_it_is_still_not_counted_under_the_bar_sum_refusal(self):
        """Two mechanisms, two names -- a reader must be able to tell which
        one held a bar out without re-deriving the rule, even once both are
        live."""
        page = _one_staff_page(
            notes=[("C4", QUARTER), ("D4", QUARTER)],
            meter={"numerator": 2, "denominator": 4, "raw": "2/4"})
        page["record"]["verdicts"].append(
            _mark_verdict(950, "cell/0/0/0/0"))
        with mock.patch.object(SX, "UNREAD_MARK_HOLDS_OUT", True):
            _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["written"].get("bars_held_out_sum", 0), 0)
        self.assertEqual(rep["written"]["bars_held_out_unread_mark"], 1)
        self.assertNotIn("bar_does_not_add_up", rep["notes_not_written"])

    def test_the_flip_does_not_leak_to_a_later_call(self):
        """The constant is module state; a test that flips it and forgets to
        restore would silently turn the hold-out on for every test after
        it. `mock.patch.object` restores on exit -- this proves that."""
        page = _one_staff_page(
            notes=[("C4", QUARTER), ("D4", QUARTER)],
            meter={"numerator": 2, "denominator": 4, "raw": "2/4"})
        page["record"]["verdicts"].append(
            _mark_verdict(950, "cell/0/0/0/0"))
        with mock.patch.object(SX, "UNREAD_MARK_HOLDS_OUT", True):
            pass
        self.assertFalse(SX.UNREAD_MARK_HOLDS_OUT)
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["bars_held_out_unread_mark"]["bars"], 0)
        self.assertEqual(rep["written"].get("notes", 0), 2)


if __name__ == "__main__":
    unittest.main()
