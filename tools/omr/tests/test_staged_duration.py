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


SPACE = 16       # one staff space in the synthetic cell's own frame


def _staff_space(log, space=SPACE):
    """The cell's own staff-space unit -- NOT a constant on a real page.

    ⚠️ `CANONICAL_STAFF_SPAN_PX / 4 = 100` is only the nominal:
    `_upscale_to_canonical` scales a too-wide cell by WIDTH instead, and on the
    engraved Beethoven 5 iv fixture the half-step reads 50 px on 84 cells and
    28, 23 or 19 on 67 more. The dot window is expressed in staff spaces, so it
    cannot be evaluated without this row.
    """
    return log.observe(CELL, Q.CELL_STAFF_SPACE, float(space),
                       reader=READERS.GEOMETRY, frame="cell:0")


def _note(log, gi, head="noteheadBlack", x=None, **marks):
    """⚠️ `x` defaults to the shared column X. Notes that must NOT share a
    beam need their own x -- beams are cell-scoped, so two notes in one column
    see the same strokes.

    ⚠️⚠️ A DOT IS ITS OWN DETECTION, WITH ITS OWN GLYPH INDEX AND ITS OWN BOX,
    AND THIS HELPER USED TO PRETEND OTHERWISE. It wrote `Q.AUG_DOT` onto the
    NOTEHEAD's subject at a fixed `(1, 1)` -- a subject shape `gather` never
    produces -- so `test_a_dot_adds_half_of_what_stands` passed while not one
    dot of 157 on a real three-page record reached a duration. A synthetic
    fixture that does not have the shape of the real log is a test that passes
    for free.
    """
    x = X if x is None else x
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, head, reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (head, x - 10, 0, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    n_dots = marks.get("dots", 0)
    if n_dots:
        _staff_space(log)
    for n in range(n_dots):
        # to the RIGHT of the head, level with it
        _dot(log, gi=1000 + gi * 10 + n, x=x + 12 + n * 8, y=4)
    for lv in range(marks.get("levels", 0)):
        _beam(log, y=40 + lv * 12)
    return g


def _dot(log, *, gi, x, y, w=4, h=8):
    """One `augmentationDot` detection -- its own glyph, its own box."""
    d = R.glyph(0, 0, 0, 0, gi)
    log.observe(d, Q.GLYPH_BOX, ("augmentationDot", x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.8)
    return log.observe(d, Q.AUG_DOT, (x + w / 2.0, y + h / 2.0),
                       reader=READERS.DETECTOR, frame="cell:0", score=0.8)


def _flag(log, *, gi, cls, x, y, w=12, h=40):
    """One flag detection -- its own glyph, its own box.

    ⚠️ A flag is drawn FROM the stem's far end, so its box meets the stem's.
    """
    f = R.glyph(0, 0, 0, 0, gi)
    log.observe(f, Q.GLYPH_BOX, (cls, x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    return log.observe(f, Q.FLAG, cls, reader=READERS.DETECTOR,
                       frame="cell:0", score=0.9,
                       x_center=x + w / 2.0, y_center=y + h / 2.0)


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


class TestAMarkMustBeATTACHEDToItsNotehead(unittest.TestCase):
    """⚠️⚠️ `Q.FLAG` AND `Q.AUG_DOT` ARE GATHERED ON THE MARK'S OWN GLYPH
    SUBJECT AND WERE READ ON THE NOTEHEAD'S. Measured on a three-page engraved
    record: **134 flag rows and 157 dot rows, 0 on a notehead subject, 0
    durations carrying a dot, `beam_evidence == "flag"` zero times.** It
    accounted for both directions of the residual wrong bar sums, confirmed
    against the encoding the page was rendered from — m211 read
    `quarter + 8th-rest` x4 = 6.0 where the truth holds 100 EIGHTHS (the
    missing flag), and m207/m208 read a plain half at 2.0 where 8 parts play a
    DOTTED HALF (the missing dot).
    """

    def _stemmed(self, log, gi=0, x=None):
        """A head with a stem hanging from it, and a flag meeting its far end.

        ⚠️ `_note` puts the head at y 0..16, so the stem must START there --
        a stem that merely shares the head's column and hangs below it in
        empty space is not attached to it, which is the whole point.
        """
        x = X if x is None else x
        g = _note(log, gi, "noteheadBlack", x=x)
        st = _stem(log, x=x - 10, y=8, h=60)          # 8..68, meets the head
        return g, st

    # ── flags ───────────────────────────────────────────────────────────────

    def test_a_flag_on_this_notes_stem_is_read(self):
        log = Log()
        g, _ = self._stemmed(log)
        f = _flag(log, gi=50, cls="flag8thUp", x=X - 10, y=40, w=12, h=40)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beam_evidence"], "flag")
        self.assertEqual(v.detail["flags_attached"], 1)
        self.assertIn(f.id, v.basis)

    def test_ONE_sixteenth_flag_is_TWO_levels_not_one(self):
        """⚠️ A FLAG CLASS NAMES A VALUE, IT IS NOT A TALLY. The old line was
        `levels = len(flags)`, so a single `flag16thUp` -- one glyph, two
        hooks -- would have read as an EIGHTH. Counting glyphs is right for
        beam strokes, which are drawn one per level, and wrong for flags."""
        log = Log()
        g, _ = self._stemmed(log)
        _flag(log, gi=50, cls="flag16thDown", x=X - 10, y=40, w=12, h=40)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.detail["flag_levels"], 2)
        self.assertEqual(v.value["beats"], 0.25)

    def test_ANOTHER_notes_flag_does_not_reach_this_one(self):
        log = Log()
        g, _ = self._stemmed(log, gi=0, x=X)
        self._stemmed(log, gi=1, x=X + 300)
        _flag(log, gi=50, cls="flag8thUp", x=X + 290, y=40, w=12, h=40)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.detail["flags_attached"], 0)
        self.assertEqual(v.value["beats"], 1.0)
        # ⚠️ THE POSITIVE CONTROL, INSIDE THE TEST: the OTHER note does take
        # it, so this is not passing because the flag path is dead.
        other = log.verdict(Q.DURATION, R.glyph(0, 0, 0, 0, 1))
        self.assertEqual(other.value["beats"], 0.5)

    def test_a_flag_with_no_stem_to_hang_on_is_not_claimed(self):
        """⚠️ THE ATTACHMENT IS THE STEM, and that is strictly stronger than
        the legacy rule, which matches on x-centre proximity and says in its
        own docstring that it cannot enforce stem direction because the stem
        "isn't reliably available from a 0-stem detector". On this path it is.
        """
        log = Log()
        g = _note(log, 0, "noteheadBlack")           # no stem
        _flag(log, gi=50, cls="flag8thUp", x=X - 10, y=40, w=12, h=40)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.detail["flags_attached"], 0)
        self.assertEqual(v.value["beats"], 1.0)
        # positive control: give it its stem and the same flag is read
        log2 = Log()
        g2, _ = self._stemmed(log2)
        _flag(log2, gi=50, cls="flag8thUp", x=X - 10, y=40, w=12, h=40)
        adjudicate.run(log2)
        self.assertEqual(log2.verdict(Q.DURATION, g2).value["beats"], 0.5)

    def test_a_BEAM_outranks_a_flag(self):
        """A beamed note carries no flag; where both are read the beam wins,
        exactly as before -- the flag rung only fires when no beam covers."""
        log = Log()
        g, _ = self._stemmed(log)
        _beam(log, y=40, x0=X - 60, x1=X + 60)
        _flag(log, gi=50, cls="flag16thUp", x=X - 10, y=40, w=12, h=40)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.detail["beam_evidence"], "read")
        self.assertEqual(v.value["beats"], 0.5)

    # ── dots ────────────────────────────────────────────────────────────────

    def test_a_dot_to_the_right_lengthens_the_note(self):
        log = Log()
        _staff_space(log)
        g = _note(log, 0, "noteheadHalf")
        d = _dot(log, gi=60, x=X + 12, y=4)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beats"], 3.0)
        self.assertEqual(v.detail["dots_attached"], 1)
        self.assertIn(d.id, v.basis)

    def test_a_dot_HALF_A_SPACE_UP_still_belongs_to_its_note(self):
        """⚠️ A DOT DOES NOT SIT AT ITS NOTE'S HEIGHT. A note in a space takes
        its dot in the same space; a note ON A LINE takes it in the space
        ABOVE. Over 116 dots the signed offsets are bimodal -- 52 at 0.00
        spaces and 52 at +0.50 -- which is what the asymmetric window is for.
        """
        log = Log()
        _staff_space(log)
        g = _note(log, 0, "noteheadHalf")           # head centre y = 8
        _dot(log, gi=60, x=X + 12, y=4 - SPACE // 2)   # centre 8 - 8 = 0
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, g).value["beats"], 3.0)

    def test_a_dot_far_BELOW_is_refused_and_the_window_is_ASYMMETRIC(self):
        """The window reaches 0.75 spaces above and only 0.25 below, because a
        dot goes above its note or level with it and NEVER under. A symmetric
        window ties on a double stop and double-dots the upper note."""
        log = Log()
        _staff_space(log)
        g = _note(log, 0, "noteheadHalf")
        _dot(log, gi=60, x=X + 12, y=4 + SPACE // 2)   # half a space BELOW
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, g).value["beats"], 2.0)
        # ⚠️ POSITIVE CONTROL, INSIDE THE TEST: the SAME offset ABOVE is taken.
        log2 = Log()
        _staff_space(log2)
        g2 = _note(log2, 0, "noteheadHalf")
        _dot(log2, gi=60, x=X + 12, y=4 - SPACE // 2)
        adjudicate.run(log2)
        self.assertEqual(log2.verdict(Q.DURATION, g2).value["beats"], 3.0)

    def test_a_dot_to_the_LEFT_belongs_to_no_note_here(self):
        log = Log()
        _staff_space(log)
        g = _note(log, 0, "noteheadHalf")
        _dot(log, gi=60, x=X - 40, y=4)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, g).value["beats"], 2.0)

    def test_ONE_dot_goes_to_ONE_note_the_nearer_one(self):
        """⚠️ THE CLAIM IS RECIPROCAL, which is what makes a per-glyph decision
        safe. The legacy rule assigns each dot to its own nearest target,
        globally; this decision sees one notehead, so it asks the same question
        from the other end -- a dot is claimed only where THIS head is the best
        target the dot has. Two heads can never both take one dot."""
        log = Log()
        _staff_space(log)
        far = _note(log, 0, "noteheadHalf", x=X)
        near = _note(log, 1, "noteheadHalf", x=X + 60)
        _dot(log, gi=60, x=X + 72, y=4)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, near).value["beats"], 3.0)
        self.assertEqual(log.verdict(Q.DURATION, far).value["beats"], 2.0)

    def test_with_NO_staff_space_row_no_dot_is_claimed(self):
        """⚠️ The window is in STAFF SPACES and the unit is NOT a constant --
        `_upscale_to_canonical` scales a too-wide cell by WIDTH, and on the
        engraved fixture the half-step reads 50 px on 84 cells and 28, 23 or 19
        on 67 more. With no unit the decision declines the dot rather than
        measuring against a number written for another frame."""
        log = Log()
        g = _note(log, 0, "noteheadHalf")            # no _staff_space(log)
        _dot(log, gi=60, x=X + 12, y=4)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertIsNone(v.detail["staff_space"])
        self.assertEqual(v.value["beats"], 2.0)
        # positive control: the same dot with the unit present IS claimed
        log2 = Log()
        _staff_space(log2)
        g2 = _note(log2, 0, "noteheadHalf")
        _dot(log2, gi=60, x=X + 12, y=4)
        adjudicate.run(log2)
        self.assertEqual(log2.verdict(Q.DURATION, g2).value["beats"], 3.0)
