"""ROADMAP 2.58c -- why a mark seen 2+ times had no owner, by cause.

The 10-07 day records: Litolff 148 of 1,420 notehead groups (Brahms 40 of
3,076) carry no DECIDED `glyph_owner` on any member. 146 (35) are groups that
were never contested and all sit on ONE staff -- an owner, with nothing to
file. The rest are the real gaps: a contested copy that looked and could not
tell (rule 8: stays unowned), and conflicts between copies cut from different
padded crops.

THE RULES, stated before any count (see `reconcile_group_owners`):
  3. a box refused as a note neither supplies an owner nor blocks one;
  4. ONE ledger-backed staff against nearness-only dissent -> the ledger
     staff owns the group (CLAUDE.md §10: ledgers name the owner, nearness
     is a hint);
  5. anything else that disagrees files nothing.
Every refusal has a positive control in the same class.
"""

import unittest

from tools.omr.staged import gather as G
from tools.omr.staged.adjudicators import ownership as OWN
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict
from tools.omr.staged import record as R

BOX = (0, 0, 20, 20)


def _log(placements):
    """`placements` = [(staff, cell)] -- one notehead box per entry, all
    stacked on the same ink so they cluster into ONE mark group."""
    log = Log()
    subs = []
    for i, (staff, cell) in enumerate(placements):
        sub = R.glyph(0, 0, staff, cell, i)
        log.observe(sub, Q.GLYPH_BOX, ("x", 0, 0, 1, 1),
                    reader=READERS.DETECTOR, frame="cell:0",
                    score=0.9 - 0.1 * i, category="notehead",
                    bbox_page_px=[BOX[0] + i, BOX[1], BOX[2] + i, BOX[3]])
        subs.append(sub)
    assert G.mark_groups_from_log(log) == 1
    return log, subs


def _own(log, sub, value, reason="x", outcome=Outcome.DECIDED):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=Q.GLYPH_OWNER,
        outcome=outcome, value=value, decider="t", reason=reason))


def _abstain(log, sub, reason="far_no_rungs"):
    return _own(log, sub, None, reason, Outcome.ABSTAINED)


def _refuse(log, sub):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub,
        quantity=Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, outcome=Outcome.DECIDED,
        value=True, decider="t", reason="x"))


S0, S1 = "staff/0/0/0", "staff/0/0/1"


class TestWhyAGroupHasNoDecidedOwner(unittest.TestCase):
    def test_never_contested_on_one_staff_is_an_owner_the_filing_staff(self):
        log, (a, b) = _log([(0, 0), (0, 1)])
        c = OWN.reconcile_group_owners(log)
        self.assertEqual(c["owned_by_filing_staff"], 1)
        self.assertNotIn("unowned_split_uncontested", c)
        self.assertNotIn("unowned_abstained", c)
        # nothing to file: no verdict is invented for an undisputed mark
        self.assertIsNone(log.verdict(Q.GLYPH_OWNER, a))
        self.assertIsNone(log.verdict(Q.GLYPH_OWNER, b))

    def test_control_never_contested_on_TWO_staves_is_not_an_owner(self):
        log, (a, b) = _log([(0, 0), (1, 0)])
        c = OWN.reconcile_group_owners(log)
        self.assertEqual(c["unowned_split_uncontested"], 1)
        self.assertNotIn("owned_by_filing_staff", c)

    def test_every_copy_looked_and_could_not_tell_stays_unowned(self):
        log, (a, b) = _log([(0, 0), (1, 0)])
        _abstain(log, a)
        _abstain(log, b)
        c = OWN.reconcile_group_owners(log)
        self.assertEqual(c["unowned_abstained"], 1)
        self.assertEqual(c["all_silent"], 1)
        self.assertNotIn("owned_by_filing_staff", c)
        self.assertIsNone(log.verdict(Q.GLYPH_OWNER, a).value)   # rule 8


class TestARefusedBoxDoesNotVote(unittest.TestCase):
    def test_a_refused_twin_does_not_block_the_one_real_owner(self):
        log, (a, b, c3) = _log([(0, 0), (1, 0), (0, 1)])
        _own(log, a, S0, "ledger_note_first")
        _own(log, b, S1, "distance")       # a numeral's ruling, refused below
        _refuse(log, b)
        _abstain(log, c3)
        census = OWN.reconcile_group_owners(log)
        self.assertEqual(census.get("conflict", 0), 0)
        self.assertEqual(census["refused_ignored"], 1)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, c3).value, S0)
        # the refused box's own ruling is left alone, not rewritten
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, b).value, S1)

    def test_control_the_same_twin_NOT_refused_is_a_real_conflict(self):
        log, (a, b, c3) = _log([(0, 0), (1, 0), (0, 1)])
        _own(log, a, S0, "ledger_note_first")
        _own(log, b, S1, "ledger_direction")
        _abstain(log, c3)
        census = OWN.reconcile_group_owners(log)
        self.assertEqual(census["conflict"], 1)
        self.assertIsNone(log.verdict(Q.GLYPH_OWNER, c3).value)

    def test_an_owner_that_exists_only_on_a_refused_twin_is_not_adopted(self):
        log, (a, b) = _log([(0, 0), (1, 0)])
        _abstain(log, a)
        _own(log, b, S1, "ladder")
        _refuse(log, b)
        census = OWN.reconcile_group_owners(log)
        self.assertIsNone(log.verdict(Q.GLYPH_OWNER, a).value)
        self.assertEqual(census["unowned_abstained"], 1)

    def test_control_the_same_owner_on_a_real_twin_IS_adopted(self):
        log, (a, b) = _log([(0, 0), (1, 0)])
        _abstain(log, a)
        _own(log, b, S1, "ladder")
        OWN.reconcile_group_owners(log)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, a).value, S1)


class TestLedgerBeatsNearness(unittest.TestCase):
    def _pair(self, ra, rb, oa=S0, ob=S1):
        log, (a, b) = _log([(0, 0), (1, 0)])
        _own(log, a, oa, ra)
        _own(log, b, ob, rb)
        return log, a, b

    def test_a_ledger_staff_against_nearness_alone_takes_the_group(self):
        log, a, b = self._pair("ledger_note_first", "distance")
        census = OWN.reconcile_group_owners(log)
        self.assertEqual(census["conflict_resolved_by_ledger"], 1)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, b).value, S0)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, a).value, S0)
        # superseded visibly: both rulings stay on the record
        self.assertEqual(len(log.verdicts(Q.GLYPH_OWNER, b)), 2)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, b).detail["overruled"], S1)

    def test_control_two_ledger_readings_that_disagree_stay_a_conflict(self):
        log, a, b = self._pair("ledger_note_first", "ledger_direction")
        census = OWN.reconcile_group_owners(log)
        self.assertEqual(census["conflict"], 1)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, b).value, S1)

    def test_control_a_ledger_staff_against_the_staff_band_stays_a_conflict(self):
        """`staff_band` is a head INSIDE a known staff -- not a hint."""
        log, a, b = self._pair("ledger_note_first", "staff_band")
        self.assertEqual(OWN.reconcile_group_owners(log)["conflict"], 1)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, b).value, S1)

    def test_control_nearness_against_nearness_stays_a_conflict(self):
        log, a, b = self._pair("distance", "distance")
        self.assertEqual(OWN.reconcile_group_owners(log)["conflict"], 1)

    def test_control_two_ledger_staves_against_each_other_with_a_distance_third(self):
        log, (a, b, c3) = _log([(0, 0), (1, 0), (0, 1)])
        _own(log, a, S0, "ledger_note_first")
        _own(log, b, S1, "ledger_direction")
        _own(log, c3, S1, "distance")
        self.assertEqual(OWN.reconcile_group_owners(log)["conflict"], 1)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, c3).value, S1)


if __name__ == "__main__":
    unittest.main()
