"""ROADMAP 2.136 step 2 -- the two WIRING faults that kept INFER's bar-math rule
(`collapse_narrowed_by_bar`, STAGED) from settling bars whose heads are all
unbeamed, behind ONE flag `OMR_INFER_CARRIED_METER_FIX`, default OFF.

  W1  `_printed_meter_roots` compared a CARRIED meter with the source system's
      OPENING segment; a carry carries the segment in force at the source's END.
  W2  `_bar_heads_are_clean` dropped a head standing beyond the staff although a
      DECIDED `Q.GLYPH_OWNER` names THIS staff (the ledger lines name the owner).

Each RED test is the case that is refused on main (flag unset/OFF) and settled
with the flag ON; each has a refusal that must STAY refused with it ON:
the 2.80 Contrabass bar (a missed rest fills the same gap), 2.97's refused
single (a bare stem never shortened to an eighth with no flag/beam), a bar with
two different landings, a bar holding a tuplet (2.102), an owner that is
abstained or another staff's, a head boxed twice.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import evaluate, infer, inferences
from tools.omr.staged.record import (Kind, Log, Outcome, Q, READERS, Subject,
                                     Verdict)
from tools.omr.tests.test_staged_bare_stem_2_81 import _cell, _staff, _sub, _system
from tools.omr.tests.test_staged_missed_rest_2_80 import ink
from tools.omr.tests.test_staged_narrowed_bar_2_97 import (CELL as _unused,  # noqa: F401
                                                           _InferBar, _box, _lines)

FLAG = infer.CARRIED_METER_FIX_ENV


def _run(log, *, on):
    env = {FLAG: "1" if on else "0"}
    with mock.patch.dict(os.environ, env, clear=False):
        return infer.run(log, evaluate.Report([], [], []))


def _fired(rep):
    return [i for i in rep.inferred
            if i[0] == infer.Inference.COLLAPSE_NARROWED_BY_BAR.value]


def _val(log, g):
    return log.verdict(Q.DURATION, _sub(0, g))


def _decline(log, *, on):
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}, clear=False):
        return inferences.solve_bare_stem_bar(log, _cell(), any_reason=True).decline


class _CarriedBar(_InferBar):
    """A bar in 6/8 whose system CARRIES the meter from system 5, which opens in
    9/8 and prints a return to 6/8 at its bar 1 (Brahms 1/i): the source's top
    level reads 9/8, the segment in force at its end is 6/8."""

    def __init__(self, *a, src_segments=None, **kw):
        super().__init__(6, 8, *a, **kw)
        self.src_segments = src_segments or [
            {"numerator": 9, "denominator": 8, "from_cell": 0},
            {"numerator": 6, "denominator": 8, "from_cell": 1}]

    def finish(self):
        from tools.omr.tests.test_staged_missed_rest_2_80 import clear_ink
        if self.ink_read:
            clear_ink(self.log, _cell(0, self.cell_idx))
        log = self.log
        log.record(Verdict(
            id=self._id(), subject=_cell(0, self.cell_idx), quantity=Q.EVENT,
            outcome=Outcome.DECIDED,
            value={"events": [{"glyphs": e} for e in self.events]},
            decider="test:events", reason="grouped"))
        rows = [log.observe(_staff(i), Q.METER_TEMPLATE, 0.9,
                            reader=READERS.TEMPLATE, frame="page")
                for i in range(3)]
        first = self.src_segments[0]
        voted = log.record(Verdict(
            id=self._id(), subject=Subject(Kind.SYSTEM, page=0, system=5),
            quantity=Q.METER, outcome=Outcome.DECIDED,
            value={"numerator": first["numerator"],
                   "denominator": first["denominator"],
                   "segments": self.src_segments},
            decider="adjudicate_meter", reason="voted",
            used=tuple(r.id for r in rows),
            basis=tuple(r.id for r in rows)))
        log.record(Verdict(
            id=self._id(), subject=_system(), quantity=Q.METER,
            outcome=Outcome.DECIDED,
            value={"numerator": 6, "denominator": 8,
                   "segments": [{"numerator": 6, "denominator": 8,
                                 "from_cell": 0}]},
            decider="adjudicate_meter", reason="carried",
            used=(voted.id,), basis=(voted.id,)))
        log.freeze()
        return log


def _unbeamed_pair_bar(**kw):
    """6/8 = 3.0 quarters: one decided quarter + two heads each narrowed
    {eighth (1 beam), quarter}; with no eighth evidence only the quarter is
    admitted, so the bar lands exactly when BOTH take the quarter."""
    b = _CarriedBar(**kw)
    b.decided(1.0)
    g1 = b.narrowed_chord(1)[0]
    g2 = b.narrowed_chord(1)[0]
    return b, g1, g2


class TestW1TheCarryIsComparedWithTheSegmentInForceAtTheSourcesEnd(
        unittest.TestCase):

    def test_a_6_8_carried_after_a_9_8_then_6_8_system_settles_the_pair_RED(self):
        b, g1, g2 = _unbeamed_pair_bar()
        log = b.finish()
        self.assertEqual(len(_fired(_run(log, on=True))), 2)   # one proposal per head
        for g in (g1, g2):
            v = _val(log, g)
            self.assertEqual(v.outcome, Outcome.DECIDED)
            self.assertEqual(v.value["beats"], 1.0)
            self.assertEqual(v.value["beam_levels"], 0)
            # GUESSED: an INFER collapse, both of the reader's candidates kept
            self.assertTrue(v.decider.startswith("infer:"))
            self.assertEqual(len(v.candidates), 2)

    def test_CONTROL_with_the_flag_OFF_it_is_refused_as_on_main(self):
        b, g1, g2 = _unbeamed_pair_bar()
        log = b.finish()
        self.assertEqual(_decline(log, on=False), "meter_not_from_the_print")
        self.assertEqual(_fired(_run(log, on=False)), [])
        self.assertEqual(_val(log, g1).outcome, Outcome.NARROWED)

    def test_the_default_is_OFF_and_a_typo_leaves_it_off(self):
        for word, on in (("", False), ("yess", False), ("0", False),
                         ("1", True), ("true", True), ("ON", True)):
            b, g1, _g2 = _unbeamed_pair_bar()
            log = b.finish()
            with mock.patch.dict(os.environ, {FLAG: word}):
                infer.run(log, evaluate.Report([], [], []))
            want = Outcome.DECIDED if on else Outcome.NARROWED
            self.assertEqual(_val(log, g1).outcome, want, word)
        b, g1, _g2 = _unbeamed_pair_bar()
        log = b.finish()
        env = {k: v for k, v in os.environ.items() if k != FLAG}
        with mock.patch.dict(os.environ, env, clear=True):
            infer.run(log, evaluate.Report([], [], []))
        self.assertEqual(_val(log, g1).outcome, Outcome.NARROWED)

    def test_a_carry_that_REALLY_changed_is_still_refused(self):
        """The source ends in 9/8; the carried verdict says 6/8: a carry that
        disagrees with what the source ended on is not the printed reading."""
        b, _g1, _g2 = _unbeamed_pair_bar(src_segments=[
            {"numerator": 6, "denominator": 8, "from_cell": 0},
            {"numerator": 9, "denominator": 8, "from_cell": 1}])
        log = b.finish()
        self.assertEqual(_decline(log, on=True), "meter_not_from_the_print")
        self.assertEqual(_fired(_run(log, on=True)), [])

    def test_a_meter_the_bars_chose_is_still_no_umpire(self):
        b, _g1, _g2 = _unbeamed_pair_bar()
        log = b.finish()
        cur = log.verdict(Q.METER, _system())
        log.record(Verdict(
            id=log._next_id("vrd"), subject=_system(), quantity=Q.METER,
            outcome=Outcome.DECIDED, value=cur.value, decider="adjudicate_meter",
            reason="carry_outweighed_by_the_bars", used=cur.used,
            supersedes=cur.id))
        self.assertEqual(_decline(log, on=True), "meter_not_from_the_print")


class TestW2AnOwnedHeadStaysInTheBar(unittest.TestCase):

    CLEAN = [(10, 100, 24, 112), (40, 110, 54, 122), (70, 120, 84, 132),
             (100, 125, 114, 137)]
    ABOVE = (10, 70, 24, 82)       # centre 76: 2.4 spaces above the top line (100)

    def _bar(self, owner=None, owner_value=None, boxes=None, tuplet=False,
             neighbour=False):
        """3 quarters + a head narrowed {eighth, quarter} in 4/4; glyph 0 stands
        2.4 spaces above the staff (staff lines 100..140, space 10)."""
        b = _InferBar()
        for _ in range(3):
            b.decided(1.0)
        g = b.narrowed_chord(1)[0]
        boxes = list(boxes or self.CLEAN)
        boxes[0] = self.ABOVE
        for i, bx in enumerate(boxes):
            _box(b.log, _sub(0, i, b.cell_idx), *bx)
        _lines(b.log, _staff(0))
        if owner is not None:
            b.log.record(Verdict(
                id=b._id(), subject=_sub(0, 0, b.cell_idx), quantity=Q.GLYPH_OWNER,
                outcome=owner,
                value=None if owner is Outcome.ABSTAINED else (
                    owner_value if owner_value is not None else _staff(0).to_key()),
                decider="adjudicate_glyph_owner", reason="ledger_note_first"))
        if neighbour:      # staff 1 holds a kept box on glyph 3's ink
            _box(b.log, Subject(Kind.GLYPH, page=0, system=0, staff=1, cell=0,
                                glyph=0), 100, 125, 114, 137)
        if tuplet:
            b.log.observe(_sub(0, 9, b.cell_idx), Q.TUPLET_MARKER, "tuplet3",
                          reader=READERS.DETECTOR, frame="cell", x0=0, x1=10,
                          x_center=5)
        return b.finish(), g

    def test_a_head_above_the_staff_with_a_DECIDED_owner_naming_this_staff_RED(self):
        log, g = self._bar(Outcome.DECIDED)
        self.assertEqual(len(_fired(_run(log, on=True))), 1)
        v = _val(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertTrue(v.decider.startswith("infer:"))
        self.assertEqual(len(v.candidates), 2)

    def test_CONTROL_with_the_flag_OFF_the_same_bar_is_refused_as_on_main(self):
        log, g = self._bar(Outcome.DECIDED)
        self.assertEqual(_decline(log, on=False), "heads_not_this_staffs_own")
        self.assertEqual(_val(log, g).outcome, Outcome.NARROWED)

    def test_an_ABSTAINED_owner_keeps_it_refused(self):
        log, _g = self._bar(Outcome.ABSTAINED)
        self.assertEqual(_decline(log, on=True), "heads_not_this_staffs_own")

    def test_no_owner_verdict_keeps_it_refused(self):
        log, _g = self._bar(None)
        self.assertEqual(_decline(log, on=True), "heads_not_this_staffs_own")

    def test_an_owner_naming_ANOTHER_staff_keeps_it_refused(self):
        """The head leaves this bar altogether (`_left_the_bar`: a relocated
        copy), so the bar is a different sum and settles nothing."""
        log, g = self._bar(Outcome.DECIDED, owner_value=_staff(1).to_key())
        self.assertEqual(_fired(_run(log, on=True)), [])
        self.assertEqual(_val(log, g).outcome, Outcome.NARROWED)

    def test_a_head_boxed_twice_is_still_refused_even_when_owned(self):
        boxes = list(self.CLEAN)
        boxes[3] = boxes[2]                     # glyph 3 on glyph 2's ink
        log, _g = self._bar(Outcome.DECIDED, boxes=boxes)
        self.assertEqual(_decline(log, on=True), "heads_not_this_staffs_own")

    def test_a_head_the_NEIGHBOUR_staff_also_boxed_is_still_refused(self):
        log, _g = self._bar(Outcome.DECIDED, neighbour=True)
        self.assertEqual(_decline(log, on=True), "heads_not_this_staffs_own")

    def test_a_tuplet_bar_is_still_refused_even_when_owned(self):
        log, _g = self._bar(Outcome.DECIDED, tuplet=True)
        self.assertEqual(_decline(log, on=True), "tuplet_in_bar")


class TestWhatStaysRefusedWithTheFlagOn(unittest.TestCase):

    def test_the_2_80_contrabass_bar_a_missed_rest_fills_the_same_gap(self):
        """Unexplained ink (a rest-sized piece no glyph explains) and a
        lengthening past the reader's best: refused, flag ON, carried meter."""
        b = _CarriedBar(ink_read=False)
        b.decided(1.0)
        g1 = b.narrowed_chord(1)[0]
        g2 = b.narrowed_chord(1)[0]
        ink(b.log, (10, 10, 40, 40), cell=_cell(0, b.cell_idx))
        log = b.finish()
        self.assertEqual(_fired(_run(log, on=True)), [])
        self.assertEqual(_val(log, g1).outcome, Outcome.NARROWED)
        self.assertEqual(_val(log, g2).outcome, Outcome.NARROWED)

    def test_2_97s_refused_single_a_bare_stem_is_never_made_an_eighth(self):
        """6/8: 1 + 1.5 + x = 3 needs x = 0.5; only an eighth would land it, and
        the head has no flag or beam on its stem."""
        b = _CarriedBar()
        b.decided(1.0)
        b.decided(1.5)
        (g,) = b.narrowed_chord(1)            # 1 + 1.5 + x = 3 -> x = 0.5
        log = b.finish()
        self.assertEqual(_fired(_run(log, on=True)), [])
        self.assertEqual(_val(log, g).outcome, Outcome.NARROWED)

    def test_the_eighth_is_settled_only_where_the_stem_carries_a_flag(self):
        b = _CarriedBar()
        b.decided(1.0)
        b.decided(1.5)
        (g,) = b.narrowed_chord(1, detail={"flag_levels": 1})
        log = b.finish()
        _run(log, on=True)
        self.assertEqual(_val(log, g).value["beats"], 0.5)

    def test_a_bar_with_two_different_landings_is_left_narrowed(self):
        """Two heads, 1.5 quarters of room... each {0.5 w/ beam evidence, 1.0}:
        (1.0, 0.5) and (0.5, 1.0) both land -- the rule may not choose."""
        b = _CarriedBar()
        b.decided(1.5)
        ev = {"beams_by_stem": 1}
        g1 = b.narrowed_chord(1, detail=ev)[0]
        g2 = b.narrowed_chord(1, detail=ev)[0]
        log = b.finish()
        self.assertEqual(_fired(_run(log, on=True)), [])
        self.assertEqual(_val(log, g1).outcome, Outcome.NARROWED)
        self.assertEqual(_val(log, g2).outcome, Outcome.NARROWED)

    def test_a_bar_holding_a_tuplet_marker_is_refused(self):
        b, g1, _g2 = _unbeamed_pair_bar()
        b.log.observe(_sub(0, 9, b.cell_idx), Q.TUPLET_MARKER, "tuplet3",
                      reader=READERS.DETECTOR, frame="cell", x0=0, x1=10,
                      x_center=5)
        log = b.finish()
        self.assertEqual(_decline(log, on=True), "tuplet_in_bar")
        self.assertEqual(_val(log, g1).outcome, Outcome.NARROWED)

    def test_a_decided_neighbour_is_never_overturned(self):
        b, g1, g2 = _unbeamed_pair_bar()
        log = b.finish()
        d0 = _val(log, 0)
        _run(log, on=True)
        self.assertEqual(_val(log, 0).id, d0.id)


if __name__ == "__main__":
    unittest.main()
