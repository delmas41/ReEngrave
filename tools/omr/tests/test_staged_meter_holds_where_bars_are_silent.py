"""ROADMAP 2.22b -- a carried meter HOLDS where the bars are silent.

Sean, 2026-09-28 (docs/DECISIONS.md): "A meter change holds until the plate
prints a change back; the return is always printed." CLAUDE.md §10: "The
carry is WEIGHED by the bars, not gated." Applied by the manager (FINDINGS
§17g): where too few bars can be summed to check a carried meter, and none
of those that can contradicts it, the carry is DECIDED (`carried_uncontested`)
instead of abstaining `carry_not_corroborated`. On Brahms 1/i that
abstention blocked `size_measure_rest` and `reconcile_duration` on the
systems of 3,058 held bars while the FILE wrote 6/8 there anyway.

RED on the unrepaired tree: the four `TestTheCarryHolds` tests. Controls,
GREEN on both trees (`TestWhereItStillAbstains`): a bar that contradicts it (too few to outweigh, but not
silent); bars that outweigh it (2.12k's case); a system whose own staves
read a meter-shaped thing; a printed change witnessed unread on this system
(2.12l); and a movement boundary (4.2).
"""
from __future__ import annotations

import unittest
from unittest import mock

from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm as rhythm_mod
from tools.omr.staged.record import Outcome, Q, READERS, Log
from tools.omr.tests.test_staged_movements import (
    _bars, _measure_partition, _opening, _run_meter, _set_movement_spans,
    _staff_count)

N = 3


def _two_systems(*, dst_bars=0, dst_beats=4.0, n_cells=3):
    """System (0,0) READS 4/4 on every staff; system (1,0) reads nothing and
    holds `dst_bars` assessable bars measuring `dst_beats`."""
    log = Log()
    src, dst = R.system(0, 0), R.system(1, 0)
    _staff_count(log, src, N)
    _opening(log, src, 4, 4, n_staves=N)
    _staff_count(log, dst, N)
    _measure_partition(log, dst, N, n_cells)
    if dst_bars:
        _bars(log, dst, N, n_bars=dst_bars, beats=dst_beats)
    return log, src, dst


class TestTheCarryHolds(unittest.TestCase):

    def test_SILENT_bars_the_carried_meter_is_DECIDED(self):
        log, src, dst = _two_systems(dst_bars=0)
        _run_meter(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, rhythm_mod.METER_CARRIED_UNCONTESTED)
        self.assertEqual((v.value["numerator"], v.value["denominator"]), (4, 4))
        self.assertEqual(v.detail["carried_from"], src.to_key())
        self.assertEqual(v.detail["state"], "too_few_assessable_bars")
        # basis = the carry source's own verdict
        self.assertIn(log.verdict(Q.METER, src).id, v.basis)

    def test_ONE_agreeing_bar_is_still_silent_and_the_carry_holds(self):
        log, _src, dst = _two_systems(dst_bars=1, dst_beats=4.0)
        _run_meter(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, rhythm_mod.METER_CARRIED_UNCONTESTED)

    def test_an_uncontested_carry_is_not_a_carry_SOURCE(self):
        """A carry never chains onto a carry: the third system still names
        the system that READ the meter, and the true distance to it."""
        log, src, _dst = _two_systems(dst_bars=0)
        far = R.system(2, 0)
        _staff_count(log, far, N)
        _measure_partition(log, far, N, 3)
        _run_meter(log)
        v = log.verdict(Q.METER, far)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.detail["carried_from"], src.to_key())
        self.assertEqual(v.detail["pages_since_read"], 2)


    def test_the_unread_change_is_NAMED_on_the_abstention(self):
        """The witnessed-unread control's abstention says WHERE (arm only:
        the key is 2.22b's)."""
        log, _src, dst = _two_systems(dst_bars=0)
        real = rhythm_mod._meter_digit_witness_cells

        def witness(ev, total_staves):
            if ev.subject == dst:
                return {1: tuple(range(N))}
            return real(ev, total_staves)

        with mock.patch.object(rhythm_mod, "_meter_digit_witness_cells",
                               side_effect=witness):
            _run_meter(log)
        v = log.verdict(Q.METER, dst)
        self.assertEqual(v.detail["unread_change_on_this_system_at_cell"], 1)


class TestWhereItStillAbstains(unittest.TestCase):
    """Controls: GREEN before and after 2.22b."""

    def test_CONTROL_a_bar_that_CONTRADICTS_it_is_not_silence(self):
        log, _src, dst = _two_systems(dst_bars=1, dst_beats=3.0)
        _run_meter(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "carry_not_corroborated")
        self.assertEqual(v.detail["bars_disagree"], 1)

    def test_CONTROL_bars_that_OUTWEIGH_it_still_abstain(self):
        log, _src, dst = _two_systems(dst_bars=3, dst_beats=3.0)
        _run_meter(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "carry_outweighed_by_the_bars")

    def test_CONTROL_a_system_that_READ_a_meter_shape_is_not_uncontested(self):
        """One staff of three reads 3/4 on the destination: the reading
        fails coverage and falls back to the carry, but something meter-
        shaped IS printed here, so the carry is not uncontested."""
        log, _src, dst = _two_systems(dst_bars=0)
        log.observe(R.staff(dst.page, dst.system, 0), Q.METER_TEMPLATE,
                    (3, 4), reader=READERS.TEMPLATE, frame="header_window",
                    score=0.7, raw="3/4")
        _run_meter(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertNotEqual(v.reason, "carried_uncontested")

    def test_CONTROL_a_printed_change_witnessed_UNREAD_here_abstains(self):
        """2.12l: a quorum of this system's staves refused a stacked pair at
        cell 1 as meter digits -- a change IS printed here, value unread.
        The carried meter cannot be asserted across it."""
        log, _src, dst = _two_systems(dst_bars=0)
        real = rhythm_mod._meter_digit_witness_cells

        def witness(ev, total_staves):
            if ev.subject == dst:
                return {1: tuple(range(N))}
            return real(ev, total_staves)

        with mock.patch.object(rhythm_mod, "_meter_digit_witness_cells",
                               side_effect=witness):
            _run_meter(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "carry_not_corroborated")

    def test_CONTROL_a_MOVEMENT_BOUNDARY_is_never_crossed(self):
        log, _src, dst = _two_systems(dst_bars=0)
        _set_movement_spans(log, [
            {"number": 1, "first_page": 0, "first_system": None,
             "last_page": 0, "last_system": None},
            {"number": 2, "first_page": 1, "first_system": None,
             "last_page": 5, "last_system": None}])
        _run_meter(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_evidence")


if __name__ == "__main__":
    unittest.main()
