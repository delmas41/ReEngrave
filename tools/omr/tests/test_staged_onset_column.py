"""A column through a SYSTEM is an instant of music — read across the staves.

⚠️ COHERENCE, NOT ACCURACY. These assert what the decision DOES with evidence
it is handed; whether Brahms's staves really line up is measured in
`benchmarks/omr-onset-columns-2026-09/FINDINGS.md`, on real ink, against a
null.

⚠️ THE POINT OF THIS FILE. `Q.EVENT` decides simultaneity WITHIN a staff and
stops at `Kind.CELL`. A conductor's page is 14 to 26 independent readings of
one stretch of time, and until 2026-09-09 nothing in the record compared them
— the only large source of REDUNDANT evidence on a page went unread. It could
not be read: `Q.GLYPH_BOX` carried only a CANONICAL x, measured inside one
rescaled cell, so two staves' positions were not the same quantity.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators.rhythm import (
    ONSET_COLUMN_MIN_WITNESSES, ONSET_COLUMN_TOLERANCE_SPACES)
from tools.omr.staged.record import Log, Outcome, Q, READERS

SYSTEM = R.system(0, 0)
SPACING = 20.0


def _spacing(log, staff, px=SPACING):
    log.observe(R.staff(0, 0, staff), Q.STAFF_SPACING, px,
                reader=READERS.GEOMETRY, frame="page")


def _head(log, staff, cell, gi, page_x, *, canonical_x=None, page=True):
    """One notehead. `page_x` is the PAGE frame; `canonical_x` the cell's own.

    ⚠️ The two default to the same number only for convenience. Every test
    that matters here sets them apart, because the whole decision exists
    because they are different quantities.
    """
    g = R.glyph(0, 0, staff, cell, gi)
    frame = f"cell:{cell}"
    cx = page_x if canonical_x is None else canonical_x
    detail = {"category": "notehead"}
    if page:
        detail["x_center_page"] = float(page_x)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                reader=READERS.DETECTOR, frame=frame, score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", cx - 5, 0, 10, 10),
                reader=READERS.DETECTOR, frame=frame, score=0.9, **detail)
    return g


def _decide(log):
    log.freeze()
    adjudicate._ensure_decisions()
    for cell in log.subjects(R.Kind.CELL):
        adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.EVENT], cell)
    return adjudicate.adjudicate_one(
        log, adjudicate.REGISTRY[Q.ONSET_COLUMN], SYSTEM)


class TestItIsWiredAtAll(unittest.TestCase):

    def test_it_is_registered_and_runs_AFTER_the_within_staff_grouping(self):
        adjudicate._ensure_decisions()
        self.assertIn(Q.ONSET_COLUMN, adjudicate.REGISTRY)
        order = list(adjudicate.ORDER)
        self.assertIn(Q.ONSET_COLUMN, order)
        # ⚠️ Consuming `Q.EVENT` rather than re-clustering the glyphs is the
        # design; running before it would leave nothing to consume and quietly
        # invite a second, disagreeing answer to the same question.
        self.assertLess(order.index(Q.EVENT), order.index(Q.ONSET_COLUMN))

    def test_it_declares_the_unit_it_measures_in(self):
        # A tolerance counted in staff spaces is only meaningful if the
        # spacing is on the record; `Evidence` refuses an undeclared read.
        spec = adjudicate.REGISTRY[Q.ONSET_COLUMN]
        self.assertIn(Q.STAFF_SPACING, spec.wants)
        self.assertIn(Q.STAFF_SPACING, spec.composed_from)

    def test_it_is_ADDITIVE_and_never_overturns_a_pitch_or_a_duration(self):
        spec = adjudicate.REGISTRY[Q.ONSET_COLUMN]
        self.assertEqual(spec.mode.value, "additive")
        self.assertNotIn(Q.PITCH, spec.implicates)
        self.assertNotIn(Q.DURATION, spec.implicates)


class TestAColumnIsCorroboration(unittest.TestCase):

    def test_two_staves_sounding_at_one_x_are_ONE_column(self):
        log = Log()
        _spacing(log, 0); _spacing(log, 1)
        _head(log, 0, 0, 0, 100.0)
        _head(log, 1, 0, 0, 101.0)
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "columns_read")
        cols = v.value["bars"][0]["columns"]
        self.assertEqual(len(cols), 1)
        self.assertEqual(cols[0]["witnesses"], [0, 1])
        self.assertEqual(v.detail["n_corroborated"], 1)
        self.assertEqual(v.detail["n_alone"], 0)

    def test_a_staff_alone_at_its_x_is_REPORTED_not_moved(self):
        log = Log()
        _spacing(log, 0); _spacing(log, 1)
        _head(log, 0, 0, 0, 100.0)
        _head(log, 1, 0, 0, 101.0)
        _head(log, 1, 0, 1, 400.0)      # staff 1 sounds where staff 0 is silent
        v = _decide(log)
        bar = v.value["bars"][0]
        self.assertEqual(bar["n_columns"], 2)
        self.assertEqual(bar["n_corroborated"], 1)
        self.assertEqual(bar["alone"], [400.0])

    def test_the_residual_is_the_spread_of_the_column_in_STAFF_SPACES(self):
        log = Log()
        _spacing(log, 0); _spacing(log, 1)
        _head(log, 0, 0, 0, 100.0)
        _head(log, 1, 0, 0, 101.0)      # 1 px on a 20 px spacing = 0.05
        v = _decide(log)
        self.assertAlmostEqual(
            v.value["bars"][0]["columns"][0]["residual_spaces"], 0.05, places=4)

    def test_the_DENSITY_travels_with_the_verdict(self):
        # ⚠️ Corroboration read without density is a count of how many staves
        # the page prints. The null control measures 0.29 on this corpus.
        log = Log()
        _spacing(log, 0); _spacing(log, 1)
        for gi, x in enumerate((100.0, 200.0, 300.0)):
            _head(log, 0, 0, gi, x)
            _head(log, 1, 0, gi, x + 1.0)
        v = _decide(log)
        self.assertIsNotNone(v.value["bars"][0]["events_per_space"])


class TestTheFrameIsTheWholePoint(unittest.TestCase):

    def test_glyph_ORDINALS_that_collide_across_staves_are_NOT_one_column(self):
        """⚠️⚠️ THE REGRESSION TEST FOR A BUG THAT WAS WRITTEN AND MEASURED.

        `Subject.glyph` counts within its CELL. Keying the page-x lookup on
        that ordinal alone is correct at `Kind.CELL` (where `adjudicate_event`
        does it) and WRONG here at `Kind.SYSTEM`: glyph 0 of staff 0 and glyph
        0 of staff 1 are different ink at the same ordinal, and one entry took
        the other's x. On the real Brahms page it produced a plausible 1,062
        columns of which 699 had a residual of EXACTLY ZERO — fourteen staves
        agreeing to the float, which no scan does.
        """
        log = Log()
        _spacing(log, 0); _spacing(log, 1)
        _head(log, 0, 0, 0, 100.0)
        _head(log, 1, 0, 0, 900.0)      # same ordinal, a bar apart
        v = _decide(log)
        bar = v.value["bars"][0]
        self.assertEqual(bar["n_columns"], 2)
        self.assertEqual(bar["n_corroborated"], 0)
        self.assertEqual(sorted(bar["alone"]), [100.0, 900.0])

    def test_a_CANONICAL_x_is_never_used_as_a_fallback(self):
        """Two staves whose canonical x agree and whose page x do not.

        ⚠️ This is not hypothetical: a cell is rescaled so the staff span is
        constant, so two staves' canonical frames coincide by construction and
        agreeing there means nothing.
        """
        log = Log()
        _spacing(log, 0); _spacing(log, 1)
        _head(log, 0, 0, 0, 100.0, canonical_x=50.0)
        _head(log, 1, 0, 0, 900.0, canonical_x=50.0)
        v = _decide(log)
        self.assertEqual(v.value["bars"][0]["n_corroborated"], 0)

    def test_no_page_frame_ABSTAINS_by_name(self):
        log = Log()
        _spacing(log, 0); _spacing(log, 1)
        _head(log, 0, 0, 0, 100.0, page=False)
        _head(log, 1, 0, 0, 101.0, page=False)
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_page_frame")

    def test_no_staff_spacing_ABSTAINS_rather_than_assuming_a_unit(self):
        log = Log()
        _head(log, 0, 0, 0, 100.0)
        _head(log, 1, 0, 0, 101.0)
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_page_frame")


class TestTheToleranceIsAStaffSpaceCount(unittest.TestCase):

    def _two_staves_apart(self, px, spacing):
        log = Log()
        _spacing(log, 0, spacing); _spacing(log, 1, spacing)
        _head(log, 0, 0, 0, 100.0)
        _head(log, 1, 0, 0, 100.0 + px)
        return _decide(log).value["bars"][0]["n_columns"]

    def test_the_same_pixel_gap_merges_on_a_coarse_staff_and_splits_on_a_fine_one(self):
        gap = 3.0
        coarse = 3.0 / (ONSET_COLUMN_TOLERANCE_SPACES * 0.9)   # gap < tol
        fine = 3.0 / (ONSET_COLUMN_TOLERANCE_SPACES * 1.5)     # gap > tol
        self.assertEqual(self._two_staves_apart(gap, coarse), 1)
        self.assertEqual(self._two_staves_apart(gap, fine), 2)


class TestItAbstainsRatherThanInventing(unittest.TestCase):

    def test_one_staff_is_not_corroboration(self):
        log = Log()
        _spacing(log, 0)
        _head(log, 0, 0, 0, 100.0)
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "single_staff")
        self.assertGreaterEqual(ONSET_COLUMN_MIN_WITNESSES, 2)

    def test_nothing_to_align_when_no_staff_grouped_anything(self):
        log = Log()
        _spacing(log, 0); _spacing(log, 1)
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "nothing_to_align")


class TestItConsumesTheGroupingRatherThanRedoingIt(unittest.TestCase):

    def test_a_chord_reaches_the_column_as_ONE_event(self):
        """Two noteheads of one chord are one point, not two witnesses.

        ⚠️ If this decision re-clustered the glyphs it would count a chord as
        two events at one x — and a staff playing chords would look like the
        best-corroborated staff on the page.
        """
        log = Log()
        _spacing(log, 0); _spacing(log, 1)
        _head(log, 0, 0, 0, 100.0)
        _head(log, 0, 0, 1, 101.0)      # the same chord, on staff 0
        _head(log, 1, 0, 0, 100.5)
        v = _decide(log)
        col = v.value["bars"][0]["columns"][0]
        self.assertEqual(col["witnesses"], [0, 1])
        self.assertEqual(col["n_witness"], 2)


if __name__ == "__main__":
    unittest.main()
