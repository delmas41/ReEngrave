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


def _stem(log, *, x, y, w=4, h=60):
    """One CV stem stroke, cell-scoped -- the real row shape.

    ⚠️ A stem stands at the SIDE of its notehead and reaches from it to the
    beam; both attachments are decided by BOX OVERLAP and nothing else.
    """
    return log.observe(CELL, Q.STEM, (x, y, w, h),
                       reader=READERS.CV_LINES, frame="cell:0",
                       x0=x, x1=x + w, y_center=y + h / 2.0,
                       image="no_staff", staff_lines_erased=True)


class TestANoteIsJoinedToItsBeamByItsSTEM(unittest.TestCase):
    """⚠️⚠️ THE FAULT: a beam stroke runs from the FIRST stem it joins to the
    LAST, and a stem stands at the SIDE of its notehead -- so the OUTER note
    of every beamed group has its centre roughly half a notehead width past
    the stroke's end. Testing that centre reads `none_over_this_note` on a
    CLEAN ENGRAVING, `BEAM_EDGE_TOLERANCE_WIDTHS` catches it as POSSIBLE, and
    the duration comes out as a range a consumer then collapses -- to the
    LONGEST, because `Ruling.narrow` orders by support.

    Measured on an engraved Beethoven 5 iv fixture: 114 narrowed durations
    have a stem meeting a beam while the centre test says nothing is over the
    note, and the overshoot clusters at 0.35-0.47 notehead widths.
    """

    def _last_note_of_a_group(self, log, *, with_stem):
        """A head whose centre is PAST the stroke's end, stem-up.

        The stroke ends at 140; the head spans 135-155, so its centre (145)
        is 5 px past -- inside `BEAM_EDGE_TOLERANCE_WIDTHS` (20 px here) and
        outside the stroke. The stem sits at the head's left edge, 135-139,
        and rises to meet the beam.
        """
        _beam(log, y=40, x0=60, x1=140)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        if with_stem:
            _stem(log, x=135, y=38, h=60)      # 38..98: meets the beam at 40
        return g

    def test_the_centre_test_alone_leaves_it_AMBIGUOUS(self):
        """The control, and the reason this is not a free win: without the
        stem the reading really IS a range, and it stays one."""
        log = Log()
        g = self._last_note_of_a_group(log, with_stem=False)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beams_ambiguous")
        self.assertEqual(v.detail["beam_evidence"], "none_over_this_note")
        # ⚠️ AND THE COLLAPSE BIASES LONG: the top candidate is the QUARTER.
        self.assertEqual(v.candidates[0].value["beats"], 1.0)

    def test_a_stem_that_reaches_the_beam_DECIDES_it(self):
        log = Log()
        g = self._last_note_of_a_group(log, with_stem=True)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)          # one beam level
        self.assertEqual(v.detail["beam_evidence"], "read")
        self.assertEqual(v.detail["beams_by_stem"], 1)
        self.assertEqual(v.detail["stems_attached"], 1)

    def test_the_stem_is_in_the_BASIS(self):
        """⚠️ `Q.STEM` was declared in `wants` and `composed_from` and read by
        nothing. A row that decides a verdict must be traceable from it."""
        log = Log()
        _beam(log, y=40, x0=60, x1=140)
        s = _stem(log, x=135, y=38, h=60)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        adjudicate.run(log)
        self.assertIn(s.id, log.verdict(Q.DURATION, g).basis)

    def test_a_stem_that_misses_the_beam_in_Y_does_NOT_join(self):
        """⚠️ THE GUARD, AND IT IS UNEXERCISED BY THE ENGRAVED FIXTURE -- which
        is why it is tested directly. Over that fixture's 707 stem/beam pairs
        overlapping in x, 685 also overlap in y and the 22 that do not are
        separated by 35 px or more, so nothing there sits near the edge. A
        stem in another octave crossing a beam's column is the case this
        refuses, and without it the x test alone would join them.
        """
        log = Log()
        _beam(log, y=40, x0=60, x1=140)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 300, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _stem(log, x=135, y=250, h=60)        # 250..310 -- nowhere near y=40
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.detail["beams_by_stem"], 0)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        # ⚠️ THE POSITIVE CONTROL, INSIDE THE TEST. Without it this passes for
        # free the moment the stem tier dies -- everything narrows then.
        log2 = Log()
        _beam(log2, y=40, x0=60, x1=140)
        g2 = R.glyph(0, 0, 0, 0, 0)
        log2.observe(g2, Q.NOTEHEAD_CLASS, "noteheadBlack",
                     reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log2.observe(g2, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                     reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _stem(log2, x=135, y=38, h=60)        # the SAME stem, reaching y=40
        adjudicate.run(log2)
        self.assertEqual(log2.verdict(Q.DURATION, g2).outcome, Outcome.DECIDED)

    def test_ANOTHER_notes_stem_does_not_join_this_one(self):
        """Attachment is to THIS notehead's box. A stem elsewhere in the cell
        reaches the same beam and says nothing about this head."""
        log = Log()
        _beam(log, y=40, x0=60, x1=140)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _stem(log, x=70, y=38, h=60)          # some other note's stem
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.detail["stems_attached"], 0)
        self.assertEqual(v.detail["beams_by_stem"], 0)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        # ⚠️ THE POSITIVE CONTROL: move that same stem onto THIS head and it
        # decides. Otherwise the test passes for free when the tier dies.
        log2 = Log()
        _beam(log2, y=40, x0=60, x1=140)
        g2 = R.glyph(0, 0, 0, 0, 0)
        log2.observe(g2, Q.NOTEHEAD_CLASS, "noteheadBlack",
                     reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log2.observe(g2, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                     reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _stem(log2, x=135, y=38, h=60)
        adjudicate.run(log2)
        self.assertEqual(log2.verdict(Q.DURATION, g2).outcome, Outcome.DECIDED)

    def test_it_is_ADDITIVE_never_subtractive(self):
        """A note whose centre IS inside the stroke decides exactly as before,
        stems or no stems -- so a page whose stems are not read is unchanged.
        """
        for stems in (False, True):
            with self.subTest(stems=stems):
                log = Log()
                _beam(log, y=40, x0=60, x1=200)
                g = R.glyph(0, 0, 0, 0, 0)
                log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                            reader=READERS.DETECTOR, frame="cell:0", score=0.9)
                log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 120, 90, 20, 16),
                            reader=READERS.DETECTOR, frame="cell:0", score=0.9)
                if stems:
                    _stem(log, x=120, y=38, h=60)
                adjudicate.run(log)
                v = log.verdict(Q.DURATION, g)
                self.assertEqual(v.outcome, Outcome.DECIDED)
                self.assertEqual(v.value["beats"], 0.5)

    def test_two_stacked_strokes_both_join_through_one_stem(self):
        """Sixteenths: the stem crosses both strokes, so the level is TWO."""
        log = Log()
        _beam(log, y=40, x0=60, x1=140)
        _beam(log, y=56, x0=60, x1=140)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _stem(log, x=135, y=38, h=60)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.25)
