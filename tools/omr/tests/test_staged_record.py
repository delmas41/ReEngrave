"""Coherence tests for the staged pipeline's record layer.

⚠️ NOT ACCURACY TESTS. Nothing here asserts that any reading is RIGHT. They
assert that the machinery keeps its promises: that a decision gets what it
declared, that an abstention reads as an abstention, and that the
circularity check refuses the edges the project has already been bitten by.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import record as R
from tools.omr.staged.record import (ABSTAIN, AlreadyAdjudicated, Kind, Log,
                                     Outcome, Q, READERS, Scope, State,
                                     Subject, UphillConsequence, Verdict)


class TestSubject(unittest.TestCase):
    def test_roundtrip(self):
        for sub in (R.DOCUMENT, R.page(2), R.system(2, 1), R.staff(2, 1, 3),
                    R.cell(2, 1, 3, 4), R.glyph(2, 1, 3, 4, 5)):
            self.assertEqual(Subject.from_key(sub.to_key()), sub)

    def test_a_subject_may_not_carry_a_finer_coordinate(self):
        """A page-scope row with a staff number is a category error, and
        catching it here is cheaper than discovering the row is unreachable."""
        with self.assertRaises(ValueError):
            Subject(Kind.PAGE, page=1, staff=2)

    def test_a_subject_needs_its_coarser_coordinates(self):
        with self.assertRaises(ValueError):
            Subject(Kind.STAFF, page=1)

    def test_containment_and_ancestry(self):
        st = R.staff(0, 1, 2)
        self.assertTrue(R.system(0, 1).contains(st))
        self.assertFalse(R.system(0, 0).contains(st))
        self.assertEqual([a.to_key() for a in st.ancestors()],
                         ["system/0/1", "page/0", "document"])


class TestThreeStates(unittest.TestCase):
    """⚠️ The module's reason to exist."""

    def setUp(self):
        self.log = Log()
        self.sub = R.staff(0, 0, 0)

    def test_read_declined_absent_are_distinguishable(self):
        self.log.observe(self.sub, Q.CLEF_GLYPH, "clefG",
                         reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        self.log.abstain(self.sub, Q.CLEF_LOCATED, reader=READERS.CV_LOCATOR,
                         frame="header_window", reason=ABSTAIN.OCCUPIED)
        self.assertIs(self.log.state(Q.CLEF_GLYPH, self.sub), State.READ)
        self.assertIs(self.log.state(Q.CLEF_LOCATED, self.sub), State.DECLINED)
        self.assertIs(self.log.state(Q.CLEF_SEED, self.sub), State.ABSENT)

    def test_a_declined_reading_carries_its_reason(self):
        """DECLINED is information; ABSENT is not. If they collapse, the
        reason is what gets lost -- which is exactly what happens today when
        `_assign_groups` writes the same `group_index = 0` from all four of
        its branches."""
        self.log.abstain(self.sub, Q.BRACKET_BLOCK, reader=READERS.GEOMETRY,
                         frame="system", reason=ABSTAIN.SYSTEM_TOO_SMALL)
        (row,) = self.log.refusals(Q.BRACKET_BLOCK, self.sub)
        self.assertEqual(row.reason, ABSTAIN.SYSTEM_TOO_SMALL)

    def test_measured_zero_is_not_absence(self):
        """The distinction a sentinel destroys."""
        self.log.observe(self.sub, Q.STAFF_SKEW, 0.0,
                         reader=READERS.GEOMETRY, frame="page")
        self.assertIs(self.log.state(Q.STAFF_SKEW, self.sub), State.READ)
        self.assertEqual(self.log.rows(Q.STAFF_SKEW, self.sub)[0].value, 0.0)

    def test_no_score_is_not_a_zero_score(self):
        row = self.log.observe(self.sub, Q.STAFF_LINES, [1, 2, 3, 4, 5],
                               reader=READERS.GEOMETRY, frame="page")
        self.assertIsNone(row.score)


class TestClosedVocabulary(unittest.TestCase):
    def test_a_misspelled_quantity_is_refused(self):
        """An open string space would make a typo indistinguishable from an
        absent reading -- the same failure the row types exist to prevent."""
        log = Log()
        with self.assertRaises(ValueError):
            log.observe(R.staff(0, 0, 0), "clef_glyf", "x",
                        reader=READERS.DETECTOR, frame="cell:0")

    def test_a_misspelled_abstention_reason_is_refused(self):
        log = Log()
        with self.assertRaises(ValueError):
            log.abstain(R.staff(0, 0, 0), Q.CLEF_GLYPH,
                        reader=READERS.DETECTOR, frame="cell:0",
                        reason="because")


class TestVerdictShape(unittest.TestCase):
    def test_abstained_may_not_carry_a_value(self):
        with self.assertRaises(ValueError):
            Verdict(id="vrd:1", subject=R.staff(0, 0, 0), quantity=Q.CLEF,
                    outcome=Outcome.ABSTAINED, value="treble",
                    decider="t", reason="r")

    def test_decided_must_carry_a_value(self):
        with self.assertRaises(ValueError):
            Verdict(id="vrd:1", subject=R.staff(0, 0, 0), quantity=Q.CLEF,
                    outcome=Outcome.DECIDED, value=None,
                    decider="t", reason="r")


class TestSinglePassRegime(unittest.TestCase):
    """⚠️ No fixpoint, enforced by the machine rather than promised."""

    def setUp(self):
        self.log = Log()
        self.sub = R.staff(0, 0, 0)

    def _verdict(self, **kw):
        base = dict(id=self.log._next_id("vrd"), subject=self.sub,
                    quantity=Q.CLEF, outcome=Outcome.DECIDED, value="treble",
                    decider="t", reason="r")
        base.update(kw)
        return Verdict(**base)

    def test_a_second_adjudication_without_revises_is_refused(self):
        self.log.record(self._verdict())
        with self.assertRaises(AlreadyAdjudicated):
            self.log.record(self._verdict(value="bass"))

    def test_a_declared_revision_is_allowed(self):
        first = self.log.record(self._verdict())
        second = self.log.record(self._verdict(value="bass",
                                               supersedes=first.id))
        self.assertEqual(self.log.verdict(Q.CLEF, self.sub).id, second.id)

    def test_superseding_something_in_your_own_basis_is_refused(self):
        """That is the fixpoint. Do not build one."""
        first = self.log.record(self._verdict())
        with self.assertRaises(UphillConsequence):
            self.log.record(self._verdict(value="bass", supersedes=first.id,
                                          basis=(first.id,)))

    def test_current_value_is_a_query_not_a_field(self):
        """Nothing caches "the current clef", so nothing can go stale the way
        clef_final (9 of 20), key_signature_final (19 of 26) and
        time_signature_final (no keeper at all) did."""
        first = self.log.record(self._verdict())
        self.log.record(self._verdict(value="alto", supersedes=first.id))
        self.assertEqual(self.log.verdict(Q.CLEF, self.sub).value, "alto")


class TestScopeQueries(unittest.TestCase):
    def test_descendants(self):
        log = Log()
        for i in range(3):
            log.observe(R.staff(0, 0, i), Q.STAFF_ORDINAL, i,
                        reader=READERS.GEOMETRY, frame="system")
        rows = log.rows(Q.STAFF_ORDINAL, R.system(0, 0),
                        scope=Scope.SELF_AND_DESCENDANTS)
        self.assertEqual(len(rows), 3)


if __name__ == "__main__":
    unittest.main()
