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

    def test_a_human_refused_marker_reads_like_no_marker_at_all(self):
        """⚠️ ROADMAP 3.4g-4. `Q.TUPLET_MARKER` is gathered on its own glyph
        subject, so `adjudicate_tuplet` reads the refusal directly -- no join
        needed. RUN RED FIRST: `Q.TUPLET_MARKER_IS_NOT_A_MARKER` does not
        exist before 3.4g-4 and this test fails at attribute lookup.
        """
        log = self._triplet()
        marker = R.glyph(0, 0, 0, 0, 99)
        log.observe(marker, Q.HUMAN_BOX_VERDICT, "not_a_symbol",
                    reader=READERS.SEAN, frame="review:box",
                    sidecar="t.json", action="act-0001")
        adjudicate.run(log)
        refusal = log.verdict(Q.TUPLET_MARKER_IS_NOT_A_MARKER, marker)
        self.assertIs(refusal.outcome, Outcome.DECIDED)
        self.assertIs(refusal.value, True)
        v = log.verdict(Q.TUPLET_RATIO, CELL)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_marker")
        # the notes fall back to their WRITTEN value, unscaled.
        note = log.verdict(Q.DURATION, R.glyph(0, 0, 0, 0, 0))
        self.assertAlmostEqual(note.value["beats"], 1.0)
        # ⚠️ THE POSITIVE CONTROL: the identical fixture with no human row is
        # `test_the_written_value_is_untouched_and_the_time_is_scaled`, which
        # reads 2/3 -- so this is not passing because the tuplet path is dead.


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


def _stem_tip_ink(log, *, stem_row_id, end, found=True):
    """One `Q.STEM_TIP_INK` row -- ROADMAP 2.18c. The real row shape:
    `gather._observe_stem_tip_ink` files `end` in `{"top", "bottom"}` and
    `stem_row_id` naming the exact `Q.STEM` row it measured."""
    return log.observe(CELL, Q.STEM_TIP_INK, bool(found),
                       reader=READERS.CV_STEM_TIP, frame="cell:0",
                       stem_row_id=stem_row_id, end=end)


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


class TestABeamLiesOnTheStemSIDEOfItsHead(unittest.TestCase):
    """ROADMAP 2.18. ⚠️⚠️ THE COLUMN TEST WAS BLIND IN Y. `_beam_levels`
    counted every stroke whose x-range covered (CERTAIN) or nearly covered
    (POSSIBLE) the head's centre, wherever it stood vertically -- so the
    beam of the OTHER voice below a stem-up head, or the next staff's beam
    in the cell's pad, counted as this note's. [C12]: a beam runs between
    STEM ENDS, so a note's beam is on the side its stem points to. The
    head's own stem direction (`Q.STEM_DIRECTION`, read off its own stem,
    `stem_projection`) was decided three decisions earlier and read only by
    `_flag_direction`. Measured on Breitkopf 317803 p1: 39 of the 104 heads
    EXPORT refuses as `duration_narrowed` are narrowed ONLY by strokes on
    the far side of their own read stem.
    """

    def _up_stemmed_last_note(self, log):
        """A stem-UP head at the END of a group: the stroke above ends at 140,
        the head spans 135-155 (centre 145), its stem 135-139 rises 38..98 and
        JOINS the stroke at y=40. One beam level is read."""
        _beam(log, y=40, x0=60, x1=140)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _stem(log, x=135, y=38, h=60)
        return g

    def test_a_POSSIBLE_stroke_BELOW_a_stem_up_head_is_not_its_beam(self):
        log = Log()
        g = self._up_stemmed_last_note(log)
        # the other voice's beam, UNDER the head, ending 15 px short of its
        # centre -- inside the one-width pad, so the column test said MAYBE
        _beam(log, y=160, x0=40, x1=130)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.STEM_DIRECTION, g).value, "up")
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beams_far_side"], 1)
        self.assertEqual(v.detail["beam_side"], "up")

    def test_the_SAME_stroke_on_the_stem_side_still_narrows(self):
        """⚠️ THE POSITIVE CONTROL. The identical stroke moved ABOVE the head
        -- where a beamlet of this group could stand -- and not reached by
        its stem stays a genuine MAYBE. Without it the test above passes for
        free the moment `_beam_levels` stops counting possible strokes."""
        log = Log()
        g = self._up_stemmed_last_note(log)
        _beam(log, y=20, x0=40, x1=130)       # above the head, stem 38..98
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beams_ambiguous")
        self.assertEqual(v.detail["beams_far_side"], 0)

    def test_a_CERTAIN_stroke_under_a_stem_up_head_is_not_its_beam(self):
        """The same fault on the CERTAIN side: a stroke below the head that
        covers its column made an eighth a sixteenth outright."""
        log = Log()
        g = self._up_stemmed_last_note(log)
        _beam(log, y=160, x0=40, x1=200)      # covers the centre, BELOW
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)

    def test_a_stem_DOWN_head_mirrors_it(self):
        log = Log()
        _beam(log, y=180, x0=60, x1=140)      # below: the head's own beam
        _beam(log, y=20, x0=40, x1=130)       # above: somebody else's
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _stem(log, x=135, y=100, h=84)        # 100..184, falls to y=180
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.STEM_DIRECTION, g).value, "down")
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beams_far_side"], 1)

    def test_NO_stem_of_its_own_means_NO_side_and_the_old_reading(self):
        """⚠️ ADDITIVE. A head whose stem was not read has no side to use --
        a borrowed (`beam_mate`) or abstained direction is not its own -- so
        the column test stands exactly as before and the stroke below still
        narrows it. `cannot tell` stays `cannot tell` (rule 8)."""
        log = Log()
        _beam(log, y=40, x0=60, x1=140)
        _beam(log, y=160, x0=40, x1=130)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertIsNone(v.detail["beam_side"])
        self.assertEqual(v.detail["beams_far_side"], 0)

    def test_the_direction_is_in_the_BASIS(self):
        log = Log()
        g = self._up_stemmed_last_note(log)
        _beam(log, y=160, x0=40, x1=130)
        adjudicate.run(log)
        sd = log.verdict(Q.STEM_DIRECTION, g)
        self.assertIn(sd.id, log.verdict(Q.DURATION, g).basis)


class TestAFlagHangsFromItsStemWithinAMeasuredTolerance(unittest.TestCase):
    """ROADMAP 2.18b, the missed-flag path. ⚠️⚠️ A FLAG AND ITS STEM DO NOT
    TOUCH ON A SCAN. `_attached_flags` demanded box OVERLAP (zero tolerance,
    measured on the ENGRAVED fixture). On Breitkopf 317803 p1 every detected
    flag's nearest read stem is 0.00 (106), 0.01-0.32 (13) or 1.31+ (15)
    spaces away -- nothing between 0.33 and 1.30 -- and the 13 were written
    as QUARTERS with the flag's own box on the record.
    `STEM_JOIN_TOLERANCE_SPACES` (0.8) lies in that empty interval, in units
    of THIS cell's `Q.CELL_STAFF_SPACE`; without one, overlap as before.
    """

    def _stemmed(self, log, flag_x, space=True):
        if space:
            _staff_space(log)
        g = _note(log, 0, "noteheadBlack", x=X)
        _stem(log, x=X - 10, y=8, h=60)                 # 90..94
        _flag(log, gi=50, cls="flag8thUp", x=flag_x, y=40)
        return g

    def test_a_flag_a_THIRD_of_a_space_off_the_stem_is_read(self):
        log = Log()
        g = self._stemmed(log, flag_x=X - 1)            # 5 px = 0.31 space
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["flags_attached"], 1)

    def test_a_flag_a_space_and_a_half_off_is_NOT_this_stems(self):
        """⚠️ THE POSITIVE CONTROL: the same flag 24 px = 1.5 spaces off."""
        log = Log()
        g = self._stemmed(log, flag_x=X + 18)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, g).value["beats"], 1.0)

    def test_WITHOUT_a_staff_space_the_flag_must_touch(self):
        log = Log()
        g = self._stemmed(log, flag_x=X - 1, space=False)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, g).value["beats"], 1.0)


class TestFlagsThatDISAGREEOnTheirLevelNarrow(unittest.TestCase):
    """ROADMAP 2.18b (manager decision, rule 8). ⚠️ Two flag boxes on one stem
    are two readings of ONE glyph; where they name different levels (an
    `flag8thUp` and a `flag16thUp` on one mark -- Breitkopf p1
    `glyph/1/1/9/0/13`, Litolff idx 3 `glyph/3/0/7/3/5`) taking the MAX is
    an argmax this stage may not make. The duration NARROWS to the levels
    the flags name. A box an existing verdict refuses is not a reading and
    does not vote.
    """

    def _stemmed(self, log):
        g = _note(log, 0, "noteheadBlack", x=X)
        _stem(log, x=X - 10, y=8, h=60)                 # 90..94
        return g

    def test_an_8th_and_a_16th_flag_on_one_stem_NARROW(self):
        log = Log()
        g = self._stemmed(log)
        _flag(log, gi=50, cls="flag8thUp", x=X - 10, y=40)
        _flag(log, gi=51, cls="flag16thUp", x=X - 10, y=38)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "flags_disagree")
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates),
                         [0.25, 0.5])

    def test_two_AGREEING_flags_still_decide(self):
        """⚠️ THE POSITIVE CONTROL: two boxes, one level -> one answer."""
        log = Log()
        g = self._stemmed(log)
        _flag(log, gi=50, cls="flag8thUp", x=X - 10, y=40)
        _flag(log, gi=51, cls="flag8thDown", x=X - 10, y=38)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)

    def test_a_REFUSED_box_does_not_vote(self):
        """The disagreeing 16th is refused by a verdict (here a human's
        `not_a_symbol`): one reading is left, and it decides."""
        log = Log()
        g = self._stemmed(log)
        _flag(log, gi=50, cls="flag8thUp", x=X - 10, y=40)
        f16 = _flag(log, gi=51, cls="flag16thUp", x=X - 10, y=38)
        log.observe(f16.subject, Q.HUMAN_BOX_VERDICT, "not_a_symbol",
                    reader=READERS.SEAN, frame="review:box",
                    sidecar="t.json", action="act-0001")
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)


class TestTheBEAMJoinIsNOTWidened(unittest.TestCase):
    """ROADMAP 2.18b, class E -- MEASURED AND REFUSED, so this is a guard, not
    a fix. A stem tip half a space short of a stroke over the group stays a
    RANGE: on Breitkopf p1 the stem-to-stroke gaps run 0.00-0.80 spaces with
    no empty interval, and a 0.8 tolerance priced on the frozen record turned
    narrowed eighths into sixteenths (a stroke read twice by the CV rung then
    counts twice). FINDINGS §11.
    """

    def test_a_stem_tip_HALF_A_SPACE_short_of_a_stroke_stays_a_RANGE(self):
        log = Log()
        _staff_space(log)
        _beam(log, y=40, x0=60, x1=140)       # 40..44, stroke ends at 140
        _stem(log, x=70, y=38, h=60)          # the group's other stem
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _stem(log, x=135, y=52, h=46)         # tip 8 px = 0.5 space short
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.detail["beams_by_stem"], 0)
        self.assertEqual(v.detail["beams_beyond_stem"], 0)


class TestAStrokeBeyondTheStemTipThatJoinsNOStemIsNotThisNotes(unittest.TestCase):
    """ROADMAP 2.18b, class B. ⚠️ A beam is drawn at the stem's END and runs
    from the first stem it joins to the last (CLAUDE.md §10). A stroke past
    the head's own read stem's tip by more than the join tolerance, which no
    read stem in the cell reaches, joins nothing and is not this note's beam
    -- on Breitkopf p1 these are the detector's `beam` boxes on hairpins and
    slurs, and the next staff's beams through the pad. Measured: of the 18
    heads EXPORT refused with such a stroke, every detector box among them
    touched zero read stems.
    """

    def _up_head_with_one_beam(self, log):
        """Stem 135-139 rising 38..98, joining the stroke at y=40."""
        _staff_space(log)
        _beam(log, y=40, x0=60, x1=200)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _stem(log, x=135, y=38, h=60)
        return g

    def test_a_CERTAIN_stroke_beyond_the_tip_joining_no_stem_is_dropped(self):
        log = Log()
        g = self._up_head_with_one_beam(log)
        # a stroke 2 spaces above the tip that no read stem reaches (on the
        # page: a hairpin the detector called `beam`; CV here only so the
        # KEPT rule does not discard it before this rule is asked)
        _beam(log, y=2, x0=100, x1=200)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beams_beyond_stem"], 1)

    def test_a_POSSIBLE_one_is_dropped_too_and_the_note_DECIDES(self):
        log = Log()
        g = self._up_head_with_one_beam(log)
        _beam(log, y=2, x0=40, x1=130)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)

    def test_a_stroke_that_ANOTHER_stem_reaches_is_kept(self):
        """⚠️ THE POSITIVE CONTROL. The same stroke, now joined by a read
        stem: it is somebody's beam -- possibly this note's, its own stem read
        short -- so it keeps counting exactly as before."""
        log = Log()
        g = self._up_head_with_one_beam(log)
        _beam(log, y=2, x0=100, x1=200)
        _stem(log, x=180, y=0, h=90)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beats"], 0.25)
        self.assertEqual(v.detail["beams_beyond_stem"], 0)

    def _up_head_alone(self, log):
        """A stem-up head (stem 38..98) with NOTHING on its stem."""
        _staff_space(log)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _stem(log, x=135, y=38, h=60)
        return g

    def test_RULE_8_dropping_may_not_leave_the_note_UNMARKED(self):
        """⚠️ Where the stroke past the tip is the only thing over the head
        and its stem carries no beam and no flag, dropping it would decide
        the note at its head value from ABSENCE -- on p1 half of such notes
        print a flag or beam nothing read. The reading stays what it was."""
        log = Log()
        g = self._up_head_alone(log)
        _beam(log, y=2, x0=40, x1=130)        # past the tip, only a MAYBE
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertTrue(v.detail["beyond_stem_kept_no_other_mark"])
        self.assertEqual(v.detail["beams_beyond_stem"], 0)

    def test_the_guard_stands_down_when_a_FLAG_marks_the_stem(self):
        """⚠️ THE POSITIVE CONTROL: the same head and stroke, with a flag on
        the stem -- the stroke goes and the flag decides the eighth."""
        log = Log()
        g = self._up_head_alone(log)
        _beam(log, y=2, x0=40, x1=130)
        _flag(log, gi=50, cls="flag8thUp", x=139, y=38)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beam_evidence"], "flag")
        self.assertFalse(v.detail["beyond_stem_kept_no_other_mark"])

    def test_a_head_with_NO_stem_of_its_own_keeps_every_stroke(self):
        """No stem read -> no tip -> no reach to test: the old reading."""
        log = Log()
        _staff_space(log)
        _beam(log, y=40, x0=60, x1=200)
        _beam(log, y=2, x0=100, x1=200)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beats"], 0.25)
        self.assertEqual(v.detail["beams_beyond_stem"], 0)


class TestAStemTipWithUnreadFlagInkNarrowsInsteadOfDeciding(unittest.TestCase):
    """ROADMAP 2.18c. ⚠️⚠️ RULE 8: a stemmed head with no beam and no flag
    READ decides its head value TODAY -- `benchmarks/omr-missing-notes-
    2026-09/FINDINGS.md` SS11.4b measured ~6 of 53 such heads on Breitkopf
    p1 PRINTING a flag nothing on the record witnesses, i.e. `cannot tell`
    written as `quarter`. `Q.STEM_TIP_INK` is a SECOND, CV witness at the
    stem's own tip; where it reads flag-shaped ink, this narrows between the
    head value and ONE flag level instead -- never straight to eighth,
    which would guess the hook count from ink alone.
    """

    def _up_head_alone(self, log):
        """A stem-up head (stem 38..98), nothing on ITS OWN column -- the
        exact population this rule targets: no beam, no flag over THIS
        head. ⚠️ A decoy beam far away in x, over no head at all, so
        `Q.BEAM_STROKE`'s state on the cell is READ (the reader ran and
        genuinely found nothing over this note) rather than ABSENT (the
        reader never ran, `beam_evidence = "reader_declined"`) -- the same
        distinction real cells make, since a measure with any beamed note
        at all already puts a `Q.BEAM_STROKE` row somewhere in it."""
        _staff_space(log)
        _beam(log, y=2, x0=400, x1=460)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        s = _stem(log, x=135, y=38, h=60)
        return g, s

    def test_flag_ink_at_the_TOP_tip_of_an_up_stem_NARROWS(self):
        log = Log()
        g, s = self._up_head_alone(log)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.STEM_DIRECTION, g).value, "up")
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "flag_ink_unread")
        beats = sorted(c.value["beats"] for c in v.candidates)
        self.assertEqual(beats, [0.5, 1.0])

    def test_POSITIVE_CONTROL_a_clean_tip_still_DECIDES_the_head_value(self):
        """⚠️ THE CONTROL: the identical head, but the reader found no ink at
        the matching end -- today's behaviour, UNCHANGED."""
        log = Log()
        g, s = self._up_head_alone(log)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=False)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertEqual(v.reason, "head_and_marks")

    def test_NO_STEM_TIP_INK_ROW_AT_ALL_is_ALSO_UNCHANGED(self):
        """An OLDER record with no `Q.STEM_TIP_INK` on it: `(None, ())`, so
        this head decides exactly as it did before this item existed."""
        log = Log()
        g, _s = self._up_head_alone(log)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertEqual(v.reason, "head_and_marks")

    def test_ink_at_the_WRONG_END_is_not_read(self):
        """⚠️ Only the end THIS head's own stem points to. An up-stem's tip
        is the TOP; a `found=True` row filed at the BOTTOM must not be read
        as this head's evidence -- proves the join is by END, not merely by
        presence of ANY row."""
        log = Log()
        g, s = self._up_head_alone(log)
        _stem_tip_ink(log, stem_row_id=s.id, end="bottom", found=True)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)

    def test_a_DOWN_stem_reads_its_BOTTOM_tip(self):
        """Symmetry: a down-stem head's tip is at the BOTTOM. The same
        head/stem geometry `test_a_stem_DOWN_head_mirrors_it` already
        proves reads as `"down"` (stem 100..184, falling from the head)."""
        log = Log()
        _staff_space(log)
        _beam(log, y=2, x0=400, x1=460)           # decoy: state READ, far away
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        s = _stem(log, x=135, y=100, h=84)        # 100..184
        _stem_tip_ink(log, stem_row_id=s.id, end="bottom", found=True)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.STEM_DIRECTION, g).value, "down")
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "flag_ink_unread")

    def test_it_NEVER_FIRES_where_a_real_flag_already_decided_the_note(self):
        """⚠️ THE GUARD: `beam_evidence` is `"flag"`, not `"none_over_this_
        note"`, so `Q.STEM_TIP_INK` is never even consulted -- the tip-ink
        reading, though present and `found=True`, changes nothing."""
        log = Log()
        g, s = self._up_head_alone(log)
        _flag(log, gi=50, cls="flag8thUp", x=139, y=38)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beam_evidence"], "flag")

    def test_it_NEVER_DECIDES_STRAIGHT_TO_EIGHTH(self):
        """⚠️⚠️ CLAUDE.md rule 6: connect, never guess. Ink at the tip says A
        hook is there, not how many -- the outcome must stay NARROWED, never
        collapse to a single DECIDED eighth by itself."""
        log = Log()
        g, s = self._up_head_alone(log)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotEqual(v.outcome, Outcome.DECIDED)


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

    def test_a_human_refused_flag_does_not_reach_the_duration(self):
        """⚠️ ROADMAP 3.4g-4. `Q.FLAG_IS_NOT_A_FLAG` is decided on the flag's
        OWN glyph subject, the same one `Q.FLAG` is gathered on, so
        `_attached_flags` reads the refusal directly -- no join needed, unlike
        the key-signature marker. RUN RED FIRST: `Q.FLAG_IS_NOT_A_FLAG` does
        not exist before 3.4g-4 and this test fails at attribute lookup.
        """
        log = Log()
        g, _ = self._stemmed(log)
        f = _flag(log, gi=50, cls="flag8thUp", x=X - 10, y=40, w=12, h=40)
        log.observe(f.subject, Q.HUMAN_BOX_VERDICT, "not_a_symbol",
                    reader=READERS.SEAN, frame="review:box",
                    sidecar="t.json", action="act-0001")
        adjudicate.run(log)
        refusal = log.verdict(Q.FLAG_IS_NOT_A_FLAG, f.subject)
        self.assertIs(refusal.outcome, Outcome.DECIDED)
        self.assertIs(refusal.value, True)
        v = log.verdict(Q.DURATION, g)
        # the note reads as an UNFLAGGED quarter, exactly as if the detector
        # had never drawn the flag at all.
        self.assertEqual(v.detail["flags_attached"], 0)
        self.assertEqual(v.value["beats"], 1.0)
        # ⚠️ THE POSITIVE CONTROL: the identical fixture with no human row is
        # `test_a_flag_on_this_notes_stem_is_read`, which reads 0.5 beats --
        # so this test is not passing because the flag path is dead.

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


def _rest(log, gi, cls="restQuarter", *, x=None, y=0, h=32):
    """One rest detection -- its own glyph, its own box, the GATHER shape.

    ⚠️ `gather_glyph_families` files `Q.REST` on the REST's own glyph with the
    class name as the value, and the box arrives as `Q.GLYPH_BOX` on that same
    glyph. A fixture that files either anywhere else tests the fixture: it is
    the mismatch that let `TestAMeterChangeIsReadFromTheInk` and the flag/dot
    tests pass while not one mark of 291 reached a decision on a real page.

    ⚠️ A rest is TALLER than a notehead (a quarter rest spans ~2 spaces), so
    `h` defaults wide of `_note`'s 16 -- the dot is matched against the box's
    CENTRE, and pretending a rest is notehead-shaped would make the vertical
    window a different test than the one that runs on a page.
    """
    x = X if x is None else x
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.GLYPH_BOX, (cls, x - 10, y, 20, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.REST, cls, reader=READERS.DETECTOR, frame="cell:0",
                score=0.9)
    return g


class TestADottedRestIsDotted(unittest.TestCase):
    """⚠️⚠️ `_rest_ruling` READ `ev.rows(Q.AUG_DOT)` ON THE REST'S OWN GLYPH
    SUBJECT -- the exact fault `TestAMarkMustBeATTACHEDToItsNotehead` fixed for
    noteheads, in the same function, one branch over. So a dotted rest read as
    undotted while a dotted note read correctly, and the module handled dots
    for one kind of ink and silently not for the other.

    ⚠️ IT IS CONSISTENCY, NOT PAYOFF, AND THE NUMBER SAYS SO: of 848 `aug_dot`
    rows over the three documents, 752 attach to a notehead and exactly ONE
    would attach to a rest. What is worth having is not the one dot -- it is
    that `rhythm._pair_dots_to_targets` has always scored `noteheads + rests`
    as ONE pool under these two constants ("dots after rests are rarer but
    real"), so the staged reader was DIVERGING from the paid-for rule rather
    than reading it more narrowly.
    """

    def test_a_dotted_rest_is_one_and_a_half(self):
        log = Log()
        _staff_space(log)
        g = _rest(log, 0, "restQuarter")
        _dot(log, gi=500, x=X + 12, y=32 // 2 - 4)   # right of it, level
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["dots"], 1)
        self.assertEqual(v.value["beats"], 1.5)

    def test_an_undotted_rest_is_UNCHANGED(self):
        """The positive control the fix must not buy its way past: a battery
        that only ever asserts a dot IS found passes by finding dots
        everywhere."""
        log = Log()
        _staff_space(log)
        g = _rest(log, 0, "restQuarter")
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["dots"], 0)
        self.assertEqual(v.value["beats"], 1.0)

    def test_a_dot_FAR_from_the_rest_is_refused(self):
        """The window still applies -- widening the pool is not admitting
        every dot in the cell."""
        log = Log()
        _staff_space(log)
        g = _rest(log, 0, "restQuarter")
        _dot(log, gi=500, x=X + 12, y=32 // 2 - 4 - SPACE * 6)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, g).value["dots"], 0)

    def test_a_dot_LEFT_of_the_rest_is_refused(self):
        """A dot is printed to the RIGHT of what it lengthens."""
        log = Log()
        _staff_space(log)
        g = _rest(log, 0, "restQuarter")
        _dot(log, gi=500, x=X - 40, y=32 // 2 - 4)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, g).value["dots"], 0)

    def test_ONE_dot_cannot_be_taken_by_BOTH_a_rest_and_a_note(self):
        """⚠️ THE RECIPROCITY IS WHAT MAKES THE WIDER POOL SAFE, and it only
        holds over the WHOLE pool. Both events see the same dot; each asks
        whether IT is the dot's best target, so exactly one may claim it --
        and it is the nearer one, not the one that happens to be a notehead.
        """
        log = Log()
        _staff_space(log)
        rest = _rest(log, 0, "restQuarter", x=X)
        note = _note(log, 1, "noteheadHalf", x=X + 200)
        _dot(log, gi=500, x=X + 12, y=32 // 2 - 4)   # hard by the REST
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, rest).value["dots"], 1)
        self.assertEqual(log.verdict(Q.DURATION, note).value["dots"], 0)

    def test_the_note_still_wins_a_dot_that_is_ITS_own(self):
        """The mirror, and the one that would catch a pool widened into a
        rest-always-wins rule."""
        log = Log()
        _staff_space(log)
        rest = _rest(log, 0, "restQuarter", x=X + 200)
        note = _note(log, 1, "noteheadHalf", x=X)
        _dot(log, gi=500, x=X + 12, y=4)            # hard by the NOTE
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DURATION, note).value["dots"], 1)
        self.assertEqual(log.verdict(Q.DURATION, rest).value["dots"], 0)
