"""Duration, tuplets, and the one bounded loop in the pipeline.

⚠️ COHERENCE, NOT ACCURACY.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, evaluate
from tools.omr.staged import adjudicators, consequences  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import (ABSTAIN, AlreadyAdjudicated, Log, Outcome,
                                     Q, READERS, Scope, State, Verdict)

CELL = R.cell(0, 0, 0, 0)


X = 100          # every synthetic notehead sits in the same column


def _note(log, gi, head="noteheadBlack", x=None, **marks):
    """⚠️ `x` defaults to the shared column X. Notes that must NOT share a
    beam need their own x -- beams are cell-scoped, so two notes in one column
    see the same strokes."""
    x = X if x is None else x
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, head, reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (head, x - 10, 0, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    for _ in range(marks.get("dots", 0)):
        log.observe(g, Q.AUG_DOT, (1, 1), reader=READERS.DETECTOR,
                    frame="cell:0", score=0.8)
    for lv in range(marks.get("levels", 0)):
        _beam(log, y=40 + lv * 12)
    return g


def _beam(log, *, y, x0=X - 40, x1=X + 40, reader=READERS.CV_LINES):
    """One beam STROKE, cell-scoped, with an x-range -- the real row shape.

    ⚠️ A level is not a field on a beam. How many strokes cover a NOTE is an
    interpretation `adjudicate_duration` performs over these rows; emitting a
    level here would put the arbitration in the gathering phase.
    """
    return log.observe(CELL, Q.BEAM_STROKE, (x0, y, x1 - x0, 4),
                       reader=reader, frame="cell:0",
                       x0=x0, x1=x1, y_center=y,
                       image="no_staff" if reader == READERS.CV_LINES
                       else "original",
                       staff_lines_erased=reader == READERS.CV_LINES)


class TestDurationComposes(unittest.TestCase):
    def test_a_plain_head(self):
        log = Log()
        g = _note(log, 0, "noteheadHalf")
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, g).value["beats"], 2.0)

    def test_a_dot_adds_half_of_what_stands(self):
        """⚠️ And a SECOND dot adds half again, not another half of the head."""
        log = Log()
        g = _note(log, 0, "noteheadHalf", dots=2)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, g).value["beats"], 3.5)

    def test_a_beam_level_halves(self):
        log = Log()
        g = _note(log, 0, "noteheadBlack", levels=2)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, g).value["beats"], 0.25)

    def test_THREE_beam_states_stay_distinct(self):
        """⚠️ A duration right BECAUSE THE BEAMS WERE READ and one right
        because the note HAPPENED TO BE UNBEAMED are different facts, and the
        second must not be promoted to the first when the CV rung lands."""
        # (a) the reader declined entirely
        log = Log()
        g = _note(log, 0)
        log.abstain(CELL, Q.BEAM_STROKE, reader=READERS.CV_LINES,
                    frame="cell:0", reason=ABSTAIN.NOT_IMPLEMENTED)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertEqual(v.detail["beam_evidence"], "reader_declined")
        self.assertIn(Q.BEAM_STROKE, v.declined)

        # (b) the reader spoke and found no beam over THIS note
        log = Log()
        g = _note(log, 0)
        _beam(log, y=40, x0=500, x1=600)     # elsewhere in the cell
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertEqual(v.detail["beam_evidence"], "none_over_this_note")
        self.assertEqual(v.declined, ())

        # (c) the reader spoke and beams cover it
        log = Log()
        g = _note(log, 0, levels=1)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, g).detail["beam_evidence"],
                         "read")

    def test_a_YOLO_beam_is_kept_only_where_no_CV_beam_explains_it(self):
        """⚠️ A YOLO box bounds the STACK, not a stroke: a box over two strokes
        contributes a centre in the GAP between them and three sixteenths read
        as three eighths. Unioning cost pooled 0.1917 vs 0.1861; REPLACING
        scores five edits better and is refused because it throws real beams
        away."""
        log = Log()
        g = _note(log, 0, levels=2)                 # two CV strokes
        _beam(log, y=46, reader=READERS.DETECTOR)   # a box spanning both
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.detail["cv_beams"], 2)
        self.assertEqual(v.detail["yolo_beams"], 1)
        self.assertEqual(v.detail["yolo_kept"], 0, "the box overlaps CV ink")
        self.assertEqual(v.value["beam_levels"], 2)

    def test_a_YOLO_beam_the_CV_rung_MISSED_is_kept(self):
        """The Phase-4f reason is still half true: replacing outright throws
        real beams away."""
        log = Log()
        g = _note(log, 0)
        _beam(log, y=40, reader=READERS.DETECTOR)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.detail["yolo_kept"], 1)
        self.assertEqual(v.value["beam_levels"], 1)


class TestTupletScalesTimeNotValue(unittest.TestCase):
    def _triplet(self, marker="tuplet3", n=3, brackets=0):
        log = Log()
        for i in range(n):
            _note(log, i)
        if brackets:
            for b in range(brackets):
                log.observe(R.glyph(0, 0, 0, 0, 90 + b), Q.TUPLET_MARKER,
                            "tupletBracket", reader=READERS.DETECTOR,
                            frame="cell:0", score=0.8, is_bracket=True)
        else:
            log.observe(R.glyph(0, 0, 0, 0, 99), Q.TUPLET_MARKER, marker,
                        reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                        is_bracket=False)
        return log

    def test_the_written_value_is_untouched_and_the_time_is_scaled(self):
        """⚠️ A triplet's noteheads are ORDINARY eighths on the page. MusicXML's
        <type> and LilyPond's `8` both want the WRITTEN value inside a tuplet."""
        log = self._triplet()
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.value["written"], 1.0)
        self.assertAlmostEqual(v.value["beats"], 2.0 / 3.0)

    def test_fingering3_is_read_as_a_tuplet_marker(self):
        """⚠️ DSv2's tuplet3/fingering3 split is POSITIONAL and the detector
        reproduces it badly: 33 `fingering3` against 16 `tuplet3` over twelve
        works, and ALL 33 sit in a cell holding a real triplet."""
        log = self._triplet(marker="fingering3")
        adjudicate.run(log)
        self.assertIsNotNone(log.verdict(Q.TUPLET_RATIO, CELL).value)

    def test_a_group_of_the_wrong_size_ABSTAINS(self):
        log = self._triplet(n=4)
        adjudicate.run(log)
        v = log.verdict(Q.TUPLET_RATIO, CELL)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "wrong_member_count")

    def test_two_unnumbered_brackets_ABSTAIN(self):
        """An unnumbered bracket is read only when it covers exactly one group
        in the cell."""
        log = self._triplet(brackets=2)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.TUPLET_RATIO, CELL).reason,
                         "ambiguous_bracket")

    def test_the_tuplet_decides_BEFORE_the_duration(self):
        """⚠️ Found by wiring them, not by reasoning: ORDER had duration first,
        so every triplet would have exported at its written value -- the exact
        fault the ratio exists to fix."""
        order = list(adjudicate.ORDER)
        self.assertLess(order.index(Q.TUPLET_RATIO), order.index(Q.DURATION))


class TestTheOneBoundedLoop(unittest.TestCase):
    """⚠️ Durations vote the meter; the meter then re-reads the durations. The
    BOUND is what replaces a fixpoint."""

    def _bar(self, levels_for_last=0):
        log = Log()
        for i in range(3):
            _note(log, i, levels=levels_for_last if i == 2 else 0)
        log.observe(R.staff(0, 0, 0), Q.METER_TEMPLATE, (4, 4),
                    reader=READERS.TEMPLATE, frame="header_window",
                    score=0.9, raw="4/4")
        return log

    def test_a_unique_beam_level_lands_the_bar_and_is_applied(self):
        # 1 + 1 + 0.5 = 2.5 against 4.0; dropping the last note's level gives
        # 1 + 1 + 1 = 3.0 -- still not 4.0, so nothing fires. Use a bar that
        # a single +/-1 CAN land: 1 + 1 + 2 (a half read as a quarter).
        log = Log()
        _note(log, 0)
        _note(log, 1)
        _note(log, 2, "noteheadBlack", levels=1)   # 0.5, should be 2.0
        log.observe(R.staff(0, 0, 0), Q.METER_TEMPLATE, (2, 4),
                    reader=READERS.TEMPLATE, frame="header_window",
                    score=0.9, raw="2/4")
        adjudicate.run(log)
        report = evaluate.run(log)
        # 1 + 1 + 0.5 = 2.5 vs 2.0; level 1 -> 2 gives 0.25 -> 2.25. No unique
        # landing, so the bar keeps its warning. THAT is the guard.
        self.assertEqual([f for f in report.fired
                          if f[0] == "reconcile_duration"], [])

    def test_it_REFUSES_when_more_than_one_member_could_explain_it(self):
        """⚠️ 'Certain about the GROUP, silent about the MEMBER', implemented.
        Two identical notes both able to land the bar means the evidence does
        not distinguish them, so NOTHING changes."""
        log = Log()
        _note(log, 0, "noteheadBlack", levels=1)
        _note(log, 1, "noteheadBlack", levels=1)
        log.observe(R.staff(0, 0, 0), Q.METER_TEMPLATE, (1, 4),
                    reader=READERS.TEMPLATE, frame="header_window",
                    score=0.9, raw="1/4")
        adjudicate.run(log)
        report = evaluate.run(log)
        self.assertEqual([f for f in report.fired
                          if f[0] == "reconcile_duration"], [])

    def test_a_bar_that_already_fits_is_left_alone(self):
        log = Log()
        for i in range(4):
            _note(log, i)
        log.observe(R.staff(0, 0, 0), Q.METER_TEMPLATE, (4, 4),
                    reader=READERS.TEMPLATE, frame="header_window",
                    score=0.9, raw="4/4")
        adjudicate.run(log)
        report = evaluate.run(log)
        self.assertEqual([f for f in report.fired
                          if f[0] == "reconcile_duration"], [])

    def test_the_revision_is_DECLARED_or_the_guard_fires(self):
        """⚠️ Without `revises=Q.DURATION` on the adjudicator, `Log.record`
        raises `AlreadyAdjudicated` -- which is the no-fixpoint guard working,
        not a bug."""
        self.assertEqual(adjudicate.REGISTRY[Q.DURATION].revises, Q.DURATION)

    def test_the_rule_is_downhill_and_carries_a_bound(self):
        rule = [r for r in evaluate.RULES
                if r.consequence is evaluate.Consequence.RECONCILE_DURATION][0]
        evaluate.check_downhill(rule.cause, rule.effect)
        self.assertIn("UNIQUE", rule.bound)
        self.assertIn("+/-1", rule.bound)


class TestSlotIndex(unittest.TestCase):
    def test_a_named_staff_records_its_instrument(self):
        log = Log()
        sub = R.staff(0, 0, 2)
        log.observe(sub, Q.STAFF_ORDINAL, 2, reader=READERS.GEOMETRY,
                    frame="system")
        log.observe(sub, Q.MARGIN_LABEL, "Flauti", reader=READERS.TEXT_LAYER,
                    frame="system_margin")
        log.observe(R.system(0, 0), Q.SYSTEM_STAFF_COUNT, 4,
                    reader=READERS.GEOMETRY, frame="system")
        adjudicate.run(log)
        v = log.verdict(Q.SLOT_INDEX, sub)
        self.assertEqual(v.value, 2)
        self.assertEqual(v.reason, "named")

    def test_an_unnamed_staff_says_its_slot_is_POSITIONAL(self):
        """⚠️ The verdict must distinguish a positional slot from a named one,
        because the partition gate measured 3 of 27 staves misgrouped exactly
        where identity was deduced rather than read."""
        log = Log()
        sub = R.staff(0, 0, 1)
        log.observe(sub, Q.STAFF_ORDINAL, 1, reader=READERS.GEOMETRY,
                    frame="system")
        log.observe(R.system(0, 0), Q.SYSTEM_STAFF_COUNT, 3,
                    reader=READERS.GEOMETRY, frame="system")
        adjudicate.run(log)
        v = log.verdict(Q.SLOT_INDEX, sub)
        self.assertEqual(v.reason, "full_lineup")
        self.assertIn("positional", v.detail["note"])


if __name__ == "__main__":
    unittest.main()


class TestTheRemainingConsequences(unittest.TestCase):
    """⚠️ COHERENCE. Each rule is checked for the thing its `bound` promises."""

    def test_the_key_supplies_a_DEFAULT_that_an_accidental_overrides(self):
        """⚠️ Sean states both scopes in one sentence: the signature is
        part-scoped and until-revoked; an inline accidental is bar-scoped AND
        pitch-scoped and OVERRIDES it."""
        from tools.omr.staged.record import Outcome as O
        log = Log()
        st = R.staff(0, 0, 0)
        g0, g1 = R.glyph(0, 0, 0, 0, 0), R.glyph(0, 0, 0, 0, 1)
        for g, name in ((g0, "F5"), (g1, "F4")):
            log.record(Verdict(id=log._next_id("vrd"), subject=g,
                               quantity=Q.PITCH, outcome=O.DECIDED,
                               value=name, decider="t", reason="r"))
        # g1 carries its own accidental already
        log.record(Verdict(id=log._next_id("vrd"), subject=g1,
                           quantity=Q.ACCIDENTAL, outcome=O.DECIDED,
                           value="natural", decider="t", reason="r"))
        log.record(Verdict(id=log._next_id("vrd"), subject=st,
                           quantity=Q.KEY_SIGNATURE, outcome=O.DECIDED,
                           value=1, decider="t", reason="r"))
        log.freeze()
        evaluate.run(log)
        self.assertEqual(log.verdict(Q.ACCIDENTAL, g0).value, "#")
        self.assertEqual(log.verdict(Q.ACCIDENTAL, g1).value, "natural")

    def test_C_major_alters_nothing(self):
        from tools.omr.staged.record import Outcome as O
        log = Log()
        st, g = R.staff(0, 0, 0), R.glyph(0, 0, 0, 0, 0)
        log.record(Verdict(id=log._next_id("vrd"), subject=g, quantity=Q.PITCH,
                           outcome=O.DECIDED, value="F5", decider="t",
                           reason="r"))
        log.record(Verdict(id=log._next_id("vrd"), subject=st,
                           quantity=Q.KEY_SIGNATURE, outcome=O.DECIDED,
                           value=0, decider="t", reason="r"))
        log.freeze()
        evaluate.run(log)
        self.assertIsNone(log.verdict(Q.ACCIDENTAL, g))

    def test_a_moved_glyph_SUPERSEDES_rather_than_deletes(self):
        """⚠️ A contest resolved by deleting the loser leaves nothing to
        re-examine when the identity that decided it turns out wrong."""
        from tools.omr.staged.record import Outcome as O
        log = Log()
        loser, winner = R.staff(0, 0, 0), R.staff(0, 0, 1)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.GLYPH_BAND_DISTANCE, 3.0, reader=READERS.GEOMETRY,
                    frame="page", candidate=winner.to_key(), own=False,
                    position_in_candidate=4.0)
        log.record(Verdict(id=log._next_id("vrd"), subject=winner,
                           quantity=Q.CLEF, outcome=O.DECIDED, value="treble",
                           decider="t", reason="r"))
        first = log.record(Verdict(id=log._next_id("vrd"), subject=g,
                                   quantity=Q.PITCH, outcome=O.DECIDED,
                                   value="WRONG", decider="t", reason="r"))
        log.record(Verdict(id=log._next_id("vrd"), subject=g,
                           quantity=Q.GLYPH_OWNER, outcome=O.DECIDED,
                           value=winner.to_key(), decider="t", reason="r"))
        log.freeze()
        evaluate.run(log)
        now = log.verdict(Q.PITCH, g)
        self.assertEqual(now.supersedes, first.id)
        self.assertEqual(now.value, "B4")
        self.assertIsNotNone(log.row(first.id), "the loser is still on record")

    def test_a_moved_glyph_gets_NO_pitch_where_the_new_staff_has_no_clef(self):
        from tools.omr.staged.record import Outcome as O
        log = Log()
        winner = R.staff(0, 0, 1)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.GLYPH_BAND_DISTANCE, 3.0, reader=READERS.GEOMETRY,
                    frame="page", candidate=winner.to_key(), own=False,
                    position_in_candidate=4.0)
        log.record(Verdict(id=log._next_id("vrd"), subject=g,
                           quantity=Q.GLYPH_OWNER, outcome=O.DECIDED,
                           value=winner.to_key(), decider="t", reason="r"))
        log.freeze()
        evaluate.run(log)
        self.assertIsNone(log.verdict(Q.PITCH, g))

    def test_a_part_name_carries_its_SLOT_in_the_basis(self):
        """⚠️ A name is stamped per SLOT and written onto every staff of that
        slot on every page -- 93 `Tp.` staves once exported as Trumpet on one
        document. The basis makes the blast radius traceable."""
        from tools.omr.staged.record import Outcome as O
        log = Log()
        st = R.staff(0, 0, 0)
        slot = log.record(Verdict(id=log._next_id("vrd"), subject=st,
                                  quantity=Q.SLOT_INDEX, outcome=O.DECIDED,
                                  value=0, decider="t", reason="r"))
        log.record(Verdict(id=log._next_id("vrd"), subject=st,
                           quantity=Q.INSTRUMENT, outcome=O.DECIDED,
                           value={"name": "Horn"}, decider="t", reason="r"))
        log.freeze()
        evaluate.run(log)
        v = log.verdict(Q.PART_NAME, st)
        self.assertEqual(v.value, "Horn")
        self.assertIn(slot.id, v.basis)

    def test_every_live_rule_is_downhill_and_bounded(self):
        for r in evaluate.RULES:
            with self.subTest(rule=r.consequence.value):
                evaluate.check_downhill(r.cause, r.effect)
                self.assertGreater(len(r.bound), 40)
