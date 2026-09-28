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
  straight into the record, exercising `export.to_musicxml`'s hold-out
  branch without needing a real ADJUDICATE run.

⚠️ RUN RED FIRST, against the tree before `unread_mark.py` and its export
wiring existed: every test in `TestTheAdjudicateDecision` fails on
`KeyError`/`AttributeError` (no such quantity, no such module), and
`TestExport`'s positive case fails because `report["bars_held_out_unread_
mark"]` does not exist and the bar is written as read.
"""
from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

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


def _mark_verdict(i, subject, ink_components=("glyph/0/0/0/0/200000",)):
    return _vrd(i, subject, Q.UNREAD_MARK, True, reason="unread_mark")


class TestExport(unittest.TestCase):
    """`export.py`'s own hold-out branch, the same shape as roadmap 2.8's."""

    def test_a_bar_with_a_decided_unread_mark_is_held_out(self):
        page = _one_staff_page(
            notes=[("C4", QUARTER), ("D4", QUARTER)],
            meter={"numerator": 2, "denominator": 4, "raw": "2/4"})
        page["record"]["verdicts"].append(
            _mark_verdict(950, "cell/0/0/0/0"))
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["bars_held_out_unread_mark"]["bars"], 1)
        self.assertEqual(rep["notes_not_written"]["possibly_unread_mark"], 2)
        self.assertEqual(rep["written"].get("notes", 0), 0)
        root = ET.fromstring(xml)
        self.assertEqual(root.findall(".//pitch"), [])
        rests = root.findall(".//note/rest")
        self.assertEqual(len(rests), 1)
        self.assertEqual(rests[0].get("measure"), "yes")

    def test_it_is_not_counted_under_the_bar_sum_refusal(self):
        """Two mechanisms, two names -- a reader must be able to tell which
        one held a bar out without re-deriving the rule."""
        page = _one_staff_page(
            notes=[("C4", QUARTER), ("D4", QUARTER)],
            meter={"numerator": 2, "denominator": 4, "raw": "2/4"})
        page["record"]["verdicts"].append(
            _mark_verdict(950, "cell/0/0/0/0"))
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["written"].get("bars_held_out_sum", 0), 0)
        self.assertEqual(rep["written"]["bars_held_out_unread_mark"], 1)
        self.assertNotIn("bar_does_not_add_up", rep["notes_not_written"])

    def test_a_bar_with_no_mark_is_written_normally(self):
        """The negative control: nothing about the mechanism fires on a bar
        with no `Q.UNREAD_MARK` verdict at all."""
        page = _one_staff_page(
            notes=[("C4", QUARTER), ("D4", QUARTER)],
            meter={"numerator": 2, "denominator": 4, "raw": "2/4"})
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["written"].get("bars_held_out_unread_mark", 0), 0)
        self.assertEqual(len(ET.fromstring(xml).findall(".//pitch")), 2)

    def test_a_decided_FALSE_unread_mark_does_not_hold_the_bar_out(self):
        """`no_mark` is an ANSWER, never a reason to withhold anything."""
        page = _one_staff_page(
            notes=[("C4", QUARTER), ("D4", QUARTER)],
            meter={"numerator": 2, "denominator": 4, "raw": "2/4"})
        page["record"]["verdicts"].append(
            _vrd(950, "cell/0/0/0/0", Q.UNREAD_MARK, False, reason="no_mark"))
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["written"].get("bars_held_out_unread_mark", 0), 0)
        self.assertEqual(len(ET.fromstring(xml).findall(".//pitch")), 2)

    def test_a_bar_the_bar_sum_holdout_already_refused_is_not_double_refused(self):
        """A bar can be held out for at most ONE reason -- `_part_xml` tests
        `held is None` before asking about a mark, so the two mechanisms
        cannot both fire and double-count the same notes."""
        page = _one_staff_page(
            notes=[("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)],
            meter={"numerator": 2, "denominator": 4, "raw": "2/4"})
        page["record"]["verdicts"].append(
            _mark_verdict(950, "cell/0/0/0/0"))
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["written"]["bars_held_out_sum"], 1)
        self.assertEqual(rep["written"].get("bars_held_out_unread_mark", 0), 0)
        self.assertEqual(rep["notes_not_written"]["bar_does_not_add_up"], 3)
        self.assertNotIn("possibly_unread_mark", rep["notes_not_written"])


if __name__ == "__main__":
    unittest.main()
