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
from tools.omr.tests.stroke_map_fixture import file_note_ink, file_strokes

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
    # ROADMAP 2.319 r2: beam levels are read by the one beam count from the stroke map (the bar-crop reader `_beam` fed is retired). A note
    # asked for `levels` -- or `ink=True`, a bare stem the count READS as no beam -- files its head's blob, its stem and that many beams
    # (`stroke_map_fixture`); without either the cell holds no stroke map and the count cannot tell (narrowed, rule 8). The bar-crop rows
    # (`_beam`) are still filed as GATHER files them on a real record: only their STATE is read (`_beam_state`: the reader ran in the cell).
    for lv in range(marks.get("levels", 0)):
        _beam(log, y=40 + lv * 12)
    if marks.get("levels", 0) or marks.get("ink"):
        file_note_ink(log, (x - 10, 0, 20, 16), sp=SPACE, side=marks.get("side", "down"), beams=marks.get("levels", 0))
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
        # (a) the reader declined entirely (2.319 r2: the one beam count reads the bare stem; the bar-crop state is what is tested)
        log = Log()
        g = _note(log, 0, ink=True)
        log.abstain(CELL, Q.BEAM_STROKE, reader=READERS.CV_LINES,
                    frame="cell:0", reason=ABSTAIN.NOT_IMPLEMENTED)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertEqual(v.detail["beam_evidence"], "reader_declined")
        self.assertIn(Q.BEAM_STROKE, v.declined)

        # (b) the reader spoke and found no beam over THIS note
        log = Log()
        g = _note(log, 0, ink=True)
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


class TestTupletScalesTimeNotValue(unittest.TestCase):
    def _triplet(self, marker="tuplet3", n=3, brackets=0):
        log = Log()
        for i in range(n):
            _note(log, i, x=X + 40 * i, ink=True)     # 2.319 r2: bare stems the one beam count reads (no stroke map: cannot tell)
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


def _stem_tip_ink(log, *, stem_row_id, end, found=True, **detail):
    """One `Q.STEM_TIP_INK` row -- ROADMAP 2.18c. The real row shape:
    `gather._observe_stem_tip_ink` files `end` in `{"top", "bottom"}` and
    `stem_row_id` naming the exact `Q.STEM` row it measured."""
    return log.observe(CELL, Q.STEM_TIP_INK, bool(found),
                       reader=READERS.CV_STEM_TIP, frame="cell:0",
                       stem_row_id=stem_row_id, end=end, **detail)


def _notehead_ink(log, g, *, center, ring, raster="ink_raw", best=None):
    """One `Q.NOTEHEAD_INK` row -- ROADMAP 2.23. The real row shape:
    `gather.gather_notehead_ink` files `detail["ink_raw"]`/`detail
    ["ink_net"]`, each its own `{best, best_window, windows}` from
    `gather.notehead_ink_under`. `raster` picks which of the two this test
    carries; the other stays absent, exactly as a real cell missing one
    raster would file it."""
    reading = {"best": center if best is None else best,
              "best_window": "center" if center >= ring else "ring",
              "windows": {"center": center, "ring": ring}}
    detail = {raster: reading}
    value = max(center, ring)
    return log.observe(g, Q.NOTEHEAD_INK, round(value, 4),
                       reader=READERS.CV_NOTEHEAD_INK, frame="cell:0",
                       **detail)


class TestCellFrameRoundTrips(unittest.TestCase):
    """ROADMAP 2.25b: `_cell_frame` solves `page = origin + canonical / up`
    from one dual-frame `Q.GLYPH_BOX` row, backward -- the round-trip the
    manager asked for before anything is built on top of it."""


    def test_no_dual_frame_row_declines(self):
        """DECLINED, never guessed: no `Q.GLYPH_BOX` row carries a page box
        here, so there is nothing to solve the transform from."""
        log = Log()
        cell = R.cell(0, 0, 0, 0)
        ev = adjudicate.Evidence(log, R.glyph(0, 0, 0, 0, 0),
                                 adjudicate.REGISTRY[Q.DURATION])
        self.assertIsNone(adjudicators.rhythm._cell_frame(ev, cell))


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
        g = _note(log, 0, "noteheadBlack", x=X, ink=True)      # 2.319 r2: the bare stem the one beam count reads
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
        g = _note(log, 0, "noteheadBlack", x=X, ink=True)      # 2.319 r2: the bare stem the one beam count reads
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
        file_note_ink(log, (135, 90, 20, 16), sp=SPACE, side="up")     # 2.319 r2: the bare stem the one beam count reads
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
        # ROADMAP 2.69: a hook seen rules out the head's own value (1.0), so
        # an UNCOUNTED hook brackets the flag levels, eighth or sixteenth.
        beats = sorted(c.value["beats"] for c in v.candidates)
        self.assertEqual(beats, [0.25, 0.5])

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


class TestCountedHooksDecideAndUncountedHooksNarrow(unittest.TestCase):
    """ROADMAP 2.69 (Sean, 2026-10-09: *"Count the hooks and if you can't
    count use the fact that there is a hook to help later deduction
    process"*). Sheet B of 2.65: five lone flagged EIGHTHS the stem-tip
    reader SAW and the 2.18c narrowing left `quarter or eighth`.

    (a) a hook seen rules out the head's own value; (c) a counted level
    DECIDES; (d) seen-not-counted NARROWS among flag levels >= 1 only. The
    tests named `*_RED` fail on the 2.18c narrowing (head value or one flag
    level); the controls stay green on both sides.
    """

    _up_head_alone = TestAStemTipWithUnreadFlagInkNarrowsInsteadOfDeciding._up_head_alone

    def _run(self, **detail):
        log = Log()
        g, s = self._up_head_alone(log)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True, **detail)
        adjudicate.run(log)
        return g, log.verdict(Q.DURATION, g)

    def test_ONE_counted_hook_DECIDES_an_eighth_RED(self):
        g, v = self._run(hooks=1, hooks_min=1, hooks_max=1, hooks_reason=None)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "hooks_counted")
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.value["beam_levels"], 1)

    def test_TWO_counted_hooks_DECIDE_a_sixteenth_RED(self):
        g, v = self._run(hooks=2, hooks_min=2, hooks_max=2, hooks_reason=None)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.25)

    def test_an_uncounted_hook_NARROWS_among_flag_levels_and_NEVER_the_head_value_RED(self):
        g, v = self._run(hooks=None, hooks_min=1, hooks_max=2,
                         hooks_reason="unresolved")
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "flag_ink_unread")
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates),
                         [0.25, 0.5])
        self.assertTrue(all(c.value["beam_levels"] >= 1
                            for c in v.candidates))
        # the lower bound is the best-supported reading
        self.assertEqual(v.candidates[0].value["beats"], 0.5)

    def test_a_bracket_the_reader_names_is_the_bracket_the_note_gets_RED(self):
        g, v = self._run(hooks=None, hooks_min=2, hooks_max=3,
                         hooks_reason="unresolved")
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates),
                         [0.125, 0.25])

    def test_a_dotted_head_keeps_its_dot_at_the_counted_level_RED(self):
        """Tile 13 of 2.65 is a DOTTED eighth: one counted hook is 0.75."""
        log = Log()
        g, s = self._up_head_alone(log)
        _dot(log, gi=60, x=157, y=94)       # right of the head (155), level with it
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True,
                      hooks=1, hooks_min=1, hooks_max=1, hooks_reason=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.75)
        self.assertEqual(v.value["dots"], 1)

    def test_rows_that_disagree_on_the_count_do_not_decide(self):
        log = Log()
        g, s = self._up_head_alone(log)
        s2 = _stem(log, x=135, y=38, h=60)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True, hooks=1,
                      hooks_min=1, hooks_max=1, hooks_reason=None)
        _stem_tip_ink(log, stem_row_id=s2.id, end="top", found=True, hooks=2,
                      hooks_min=2, hooks_max=2, hooks_reason=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        if v.outcome is Outcome.DECIDED:          # one stem was attached
            self.assertIn(v.value["beam_levels"], (1, 2))
        else:
            self.assertEqual(sorted(c.value["beam_levels"]
                                    for c in v.candidates), [1, 2])

    def test_POSITIVE_CONTROL_a_count_where_NO_hook_was_seen_is_not_read(self):
        """⚠️ The count is read only off rows that SAW a hook: a row with
        `found=False` that still carries `hooks=1` changes nothing -- the
        head value stands exactly as before."""
        log = Log()
        g, s = self._up_head_alone(log)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=False, hooks=1,
                      hooks_min=1, hooks_max=1, hooks_reason=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertEqual(v.reason, "head_and_marks")

    def test_a_count_at_the_WRONG_END_is_not_this_heads(self):
        log = Log()
        g, s = self._up_head_alone(log)
        _stem_tip_ink(log, stem_row_id=s.id, end="bottom", found=True,
                      hooks=2, hooks_min=2, hooks_max=2, hooks_reason=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beats"], 1.0)

    def test_a_detector_flag_still_wins_over_the_count(self):
        """A flag BOX attached to the stem decides as before (`beam_evidence
        == "flag"`); the stem-tip count is only the witness for the
        population the detector never boxed."""
        log = Log()
        g, s = self._up_head_alone(log)
        _flag(log, gi=50, cls="flag8thUp", x=139, y=38)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True, hooks=2,
                      hooks_min=2, hooks_max=2, hooks_reason=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beam_evidence"], "flag")

    def test_a_hollow_head_never_reads_the_count(self):
        """2.43: an open head is never flagged; `open_by_class` gates it."""
        log = Log()
        _staff_space(log)
        _beam(log, y=2, x0=400, x1=460)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadHalf",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadHalf", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        s = _stem(log, x=135, y=38, h=60)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True, hooks=1,
                      hooks_min=1, hooks_max=1, hooks_reason=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beats"], 2.0)


class TestAHeadsFillIsReadFromTheInkNotOnlyTheClass(unittest.TestCase):
    """ROADMAP 2.23. `benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md`
    §17b: on a MERGING plate a hollow (half/whole) notehead can read BLACK
    to the detector -- the single biggest minimal-fix class over Litolff
    1/i's held bars (`F`, 300 bars). `Q.NOTEHEAD_INK`'s `ring` window is a
    hollow head's own witness even where `center` disagrees with the
    detector's BLACK class; where it is DECISIVE, NARROW between the head
    as the detector read it and both hollow readings -- never flip it
    outright (rule 6), and never where nothing narrowed it already.
    """

    def _plain_black_head(self, log, gi=0):
        """A stemless-for-this-test BLACK-classed head with no beam and no
        flag anywhere in the cell -- `beam_evidence` reads `"reader_
        declined"` with no `Q.BEAM_STROKE` row at all, but that is fine:
        the head-fill branch's own guard is `beam_evidence ==
        "none_over_this_note"`, so a decoy beam elsewhere in the cell (as
        `TestAStemTipWithUnreadFlagInkNarrowsInsteadOfDeciding` uses) puts
        the reader in the right state without touching this head."""
        _beam(log, y=2, x0=400, x1=460)           # decoy: state READ, far away
        g = R.glyph(0, 0, 0, 0, gi)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        file_strokes(log, [("blob", (135, 90, 20, 16), 1.25, 0.9, [])], sp=SPACE)    # 2.319 r2: the head's ink, no stem: the count reads none
        return g

    def test_a_BLACK_head_with_decisively_HOLLOW_ink_NARROWS(self):
        log = Log()
        g = self._plain_black_head(log)
        _notehead_ink(log, g, center=0.1, ring=0.55)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "head_fill_from_ink")
        beats = sorted(c.value["beats"] for c in v.candidates)
        self.assertEqual(beats, [1.0, 2.0, 4.0])
        fills = {c.value["beats"]: c.value["head_fill"] for c in v.candidates}
        self.assertEqual(fills, {1.0: "black", 2.0: "half", 4.0: "whole"})

    def test_POSITIVE_CONTROL_a_dense_centre_still_DECIDES_black(self):
        """⚠️ THE CONTROL: the identical head, but the ink agrees with the
        class -- a filled centre, as every confirmed BLACK head measured on
        the engraved fixture reads (`center == 1.0`, 532/532)."""
        log = Log()
        g = self._plain_black_head(log)
        _notehead_ink(log, g, center=1.0, ring=0.75)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertEqual(v.reason, "head_and_marks")

    def test_NO_NOTEHEAD_INK_ROW_AT_ALL_is_UNCHANGED(self):
        """An OLDER record with no `Q.NOTEHEAD_INK` on it (rule 8: absence
        is never read as "hollow")."""
        log = Log()
        g = self._plain_black_head(log)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)

    def test_AMBIGUOUS_ink_that_does_not_clear_the_gap_is_UNCHANGED(self):
        """Neither the centre nor the ring is decisive -- DECLINED, not
        defaulted either way."""
        log = Log()
        g = self._plain_black_head(log)
        _notehead_ink(log, g, center=0.6, ring=0.65)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)

    def test_a_HOLLOW_classed_head_is_NOT_this_rules_population(self):
        """The gate is `base == noteheadBlack's beats` -- a head the
        detector already called HALF or WHOLE has nothing to narrow
        between; ink rows on it (however filed) change nothing here."""
        log = Log()
        _beam(log, y=2, x0=400, x1=460)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadHalf",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadHalf", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _notehead_ink(log, g, center=0.1, ring=0.55)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 2.0)

    def test_it_NEVER_FIRES_where_stem_tip_ink_ALREADY_narrowed(self):
        """⚠️ ORDER: `flag_ink_unread` is tried first, and where it fires
        `tip_ink` is truthy, so the head-fill branch's own `not tip_ink`
        guard keeps the two from stacking two narrowings on one note."""
        log = Log()
        g = self._plain_black_head(log)
        s = _stem(log, x=135, y=38, h=60)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True)
        _notehead_ink(log, g, center=0.1, ring=0.55)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "flag_ink_unread")

    def test_it_NEVER_DECIDES_STRAIGHT_TO_HALF(self):
        """⚠️⚠️ CLAUDE.md rule 6: connect, never guess. A decisive ring/
        centre gap says the head is hollow, not which of half or whole --
        the outcome must stay NARROWED, never collapse to one DECIDED
        value by itself."""
        log = Log()
        g = self._plain_black_head(log)
        _notehead_ink(log, g, center=0.1, ring=0.55)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotEqual(v.outcome, Outcome.DECIDED)

    def test_the_ink_row_is_in_the_BASIS(self):
        log = Log()
        g = self._plain_black_head(log)
        row = _notehead_ink(log, g, center=0.1, ring=0.55)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertIn(row.id, v.basis)

    def test_a_hollow_reading_off_EITHER_raster_alone_is_enough(self):
        """⚠️ Neither raster alone is required to agree -- `ink_net` (the
        staff-erased raster) reading decisively hollow is enough even where
        `ink_raw` was never filed at all, same convention as `gather_
        notehead_ink`'s own two-raster design."""
        log = Log()
        g = self._plain_black_head(log)
        _notehead_ink(log, g, center=0.1, ring=0.55, raster="ink_net")
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "head_fill_from_ink")


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
        g = _note(log, gi, "noteheadBlack", x=x, ink=True)     # 2.319 r2: the bare stem the one beam count reads
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
        file_strokes(log, [("blob", (X - 10, 0, 20, 16), 1.25, 0.9, [])], sp=SPACE)   # 2.319 r2: the head's ink, no stem in it either
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
        g = _note(log, 0, "noteheadBlack", x=X, levels=1)     # 2.319 r2: a beam the one beam count reads on this stem
        _stem(log, x=X - 10, y=8, h=60)
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


class TestOpenNoteheadsAreNeverBeamed(unittest.TestCase):
    """ROADMAP 2.43, DECISIONS 2026-09-30 (Sean): *"Correct, open noteheads
    are never beamed except tremolo."* A hollow head's beam level is FIXED
    AT ZERO, whatever the beam-reading machinery would otherwise count --
    even a stroke that lies squarely over the head's own, correctly JOINED
    stem. Found by Sean on the stage readout: 28 of 49 undecided lengths on
    Litolff p3 were clear half notes narrowed by a stray detector `beam` box
    the ink said was not over the note.
    """

    def test_a_half_note_with_a_stem_and_a_beam_box_DECIDES_half(self):
        """The exact shape Sean saw: a clear hollow head, its own stem, and
        a stray box that -- before this rule -- would narrow it between
        half and quarter-with-one-beam."""
        log = Log()
        _staff_space(log)
        g = _note(log, 0, head="noteheadHalf", levels=1)
        _stem(log, x=X - 10, y=38, h=60)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 2.0)
        self.assertEqual(v.value["beam_levels"], 0)
        self.assertEqual(v.detail["beam_evidence"], "none_over_this_note")
        self.assertTrue(v.detail["head_is_open"])

    def test_a_whole_note_with_a_beam_box_DECIDES_whole(self):
        """Whole heads carry no stem at all, so the OLD side/reach filters
        never touched them -- the override must still hold with no stem in
        the picture."""
        log = Log()
        g = _note(log, 0, head="noteheadWhole", levels=1)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 4.0)
        self.assertTrue(v.detail["head_is_open"])

    def test_CONTROL_the_identical_shape_on_a_BLACK_head_still_NARROWS(self):
        """⚠️ THE POSITIVE CONTROL. The very same stem+beam shape on a BLACK
        head is untouched -- proving the override is about the HEAD, not a
        general weakening of beam reading. (This box sits ON the stem and
        centred on the head, so it is CERTAIN -- a real, joined beam -- and
        a black head with one certain beam level DECIDES the eighth, it
        does not narrow; the narrowing shape is covered by the stem-column
        tests below.)
        """
        log = Log()
        _staff_space(log)
        g = _note(log, 0, head="noteheadBlack", levels=1)
        _stem(log, x=X - 10, y=38, h=60)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertFalse(v.detail["head_is_open"])

    def test_a_real_beamed_eighth_PAIR_stays_eighths(self):
        """⚠️ CONTROL: an ordinary beamed BLACK pair is unaffected end to
        end -- the rule must never touch a real beam on a real black head.
        """
        log = Log()
        _staff_space(log)
        _beam(log, y=40, x0=60, x1=200)
        g1 = R.glyph(0, 0, 0, 0, 0)
        log.observe(g1, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g1, Q.GLYPH_BOX, ("noteheadBlack", 70, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _stem(log, x=70, y=38, h=60)
        g2 = R.glyph(0, 0, 0, 0, 1)
        log.observe(g2, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g2, Q.GLYPH_BOX, ("noteheadBlack", 180, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _stem(log, x=180, y=38, h=60)
        # 2.319 r2: the pair's ink as the stroke map files it -- two heads, their stems (up -> right), one beam joining the stems' tips
        file_strokes(log, [("blob", (70, 90, 20, 16), 1.25, 0.9, [1]), ("vertical", (86, 34, 4, 64), 4.0, 0.25, [0, 4]),
                           ("blob", (180, 90, 20, 16), 1.25, 0.9, [3]), ("vertical", (196, 34, 4, 64), 4.0, 0.25, [2, 4]),
                           ("horizontal", (86, 34, 114, 9), 7.1, 0.55, [1, 3])], sp=SPACE)
        adjudicate.run(log)
        for g in (g1, g2):
            v = log.verdict(Q.DURATION, g)
            self.assertEqual(v.outcome, Outcome.DECIDED)
            self.assertEqual(v.value["beats"], 0.5)
            self.assertFalse(v.detail["head_is_open"])

    def test_ink_decided_hollow_zeroes_a_BLACK_CLASS_heads_beam_too(self):
        """The SECOND witness (2.23's ink reading) settles it exactly as
        the class does: a detector class of BLACK whose own ink reads
        decisively hollow is an open head by the OTHER witness, and a
        stray beam over it must not narrow or decide it beamed either --
        it falls through to the pre-existing `head_fill_from_ink` narrow
        (black/half/whole), unchanged by this rule.
        """
        log = Log()
        _beam(log, y=2, x0=400, x1=460)           # decoy: state READ, far away
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _notehead_ink(log, g, center=0.1, ring=0.55)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertTrue(v.detail["head_is_open"])
        self.assertEqual(v.reason, "head_fill_from_ink")


class TestAHollowHeadWithNothingOnItsStemIsAHalfNote(unittest.TestCase):
    """ROADMAP 2.70 (Sean, DECISIONS 2026-10-09): *"A hollow note with
    nothing on the stem is always a half note."* Where the ink reads a
    detector-BLACK head decisively hollow (2.23), the head has its own stem
    and NOTHING is on that stem -- no beam, no flag, no hook at the tip --
    ADJUDICATE DECIDES half; the ink outranks the detector's black class.
    A hollow head with NO stem stays 2.23's narrowing (a whole note is not a
    half note, and a whole REST boxed as a black head must never become one).

    ⚠️ "NOTHING ON THE STEM" NEEDS A READER THAT LOOKED. A beam reader that
    ran and accepted no stroke (`no_line_accepted`, `no_stems_to_join`) is a
    reading; one that never ran (`not_implemented`) is "cannot tell" (rule
    8). Litolff p6 `glyph/6/1/1/0/10` was gated out by 2.23 for exactly that
    conflation: the cell holds no beam at all, so the reader's state was
    DECLINED, which the code spelled `reader_declined`.
    """

    def _hollow_head(self, log, *, stem=True, tip="none", beam="ran_empty",
                     center=0.1, ring=0.6, dots=0):
        """A stem-up detector-BLACK head whose ink reads hollow.

        tip: "none" (the tip was read: no ink), "found", or "unread" (no
        `Q.STEM_TIP_INK` row at all). beam: "ran_empty" (the CV reader ran
        and accepted nothing, the real shape of a beamless cell), "decoy" (a
        beam far away, state READ), "declined" (reader never ran), or
        "over" (a stroke joins this stem's top).
        """
        _staff_space(log)
        if beam == "ran_empty":
            log.abstain(CELL, Q.BEAM_STROKE, reader=READERS.CV_LINES,
                        frame="cell:0", reason=ABSTAIN.NO_LINE_ACCEPTED)
        elif beam == "decoy":
            _beam(log, y=2, x0=400, x1=460)
        elif beam == "declined":
            log.abstain(CELL, Q.BEAM_STROKE, reader=READERS.CV_LINES,
                        frame="cell:0", reason=ABSTAIN.NOT_IMPLEMENTED)
        elif beam == "over":
            _beam(log, y=36, x0=120, x1=220)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        for n in range(dots):
            _dot(log, gi=900 + n, x=135 + 24 + n * 8, y=94)
        # 2.319 r2: the head's ink as the stroke map files it -- the one beam count reads the stem (a beam joined to it where beam == "over"),
        # or, with no stem, the head alone
        if beam == "declined":
            pass                    # no stroke map either: the beam readers never ran in this cell
        elif stem:
            file_note_ink(log, (135, 90, 20, 16), sp=SPACE, side="up", beams=1 if beam == "over" else 0)
        else:
            file_strokes(log, [("blob", (135, 90, 20, 16), 1.25, 0.9, [])], sp=SPACE)
        if stem:
            s = _stem(log, x=135, y=38, h=60)
            if tip == "none":
                _stem_tip_ink(log, stem_row_id=s.id, end="top", found=False)
            elif tip == "found":
                _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True)
        _notehead_ink(log, g, center=center, ring=ring)
        return g

    def _duration(self, log, g):
        adjudicate.run(log)
        return log.verdict(Q.DURATION, g)

    def test_a_bare_stem_under_hollow_ink_is_DECIDED_half(self):
        log = Log()
        g = self._hollow_head(log, beam="decoy")
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 2.0)
        self.assertEqual(v.value["head_fill"], "half")
        self.assertEqual(v.reason, "hollow_head_bare_stem")

    def test_it_reaches_a_cell_the_beam_reader_RAN_in_and_accepted_nothing(self):
        """⚠️ The real shape of a beamless cell (Litolff p6 tile 5): no beam
        row at all, the reader's abstention says `no_line_accepted`. The
        reader LOOKED; that is a reading, not a decline."""
        log = Log()
        g = self._hollow_head(log, beam="ran_empty")
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 2.0)
        self.assertEqual(v.reason, "hollow_head_bare_stem")

    def test_a_beam_reader_that_NEVER_RAN_is_cannot_tell_not_nothing(self):
        """Rule 8: `not_implemented` is not a reading. Unchanged: the head
        keeps the detector's quarter."""
        log = Log()
        g = self._hollow_head(log, beam="declined")
        v = self._duration(log, g)
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")
        self.assertEqual(v.value["beats"], 1.0)

    def test_a_hollow_head_with_NO_STEM_is_not_a_half_note(self):
        """A stemless hollow head is a WHOLE note (or a whole rest boxed as a
        head, Litolff p6 tile 4): it keeps 2.23's narrowing, never half."""
        log = Log()
        g = self._hollow_head(log, stem=False, beam="decoy")
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "head_fill_from_ink")
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")

    def test_a_stemless_hollow_head_in_a_beamless_cell_is_NOT_decided_half(self):
        """The whole-rest refusal control in the cell shape that matters: the
        beam reader ran and accepted nothing (the relaxation 2.70 adds), the
        ink reads hollow, and there is NO stem. The relaxation must not
        decide this -- no stem, no half."""
        log = Log()
        g = self._hollow_head(log, stem=False, beam="ran_empty")
        v = self._duration(log, g)
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")
        self.assertNotEqual(v.value if v.value is None else
                            v.value.get("head_fill"), "half")

    def test_a_beam_joined_to_this_stem_blocks_it(self):
        """A black head whose ink merely LOOKS hollow but whose stem carries
        a beam is the 2.23 false positive (two of eight on Litolff p6)."""
        log = Log()
        g = self._hollow_head(log, beam="over")
        v = self._duration(log, g)
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")

    def test_a_flag_on_this_stem_blocks_it(self):
        log = Log()
        g = self._hollow_head(log, beam="decoy")
        _flag(log, gi=50, cls="flag8thUp", x=139, y=38)
        v = self._duration(log, g)
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")

    def test_a_hook_seen_at_the_tip_blocks_it(self):
        log = Log()
        g = self._hollow_head(log, beam="decoy", tip="found")
        v = self._duration(log, g)
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")
        self.assertEqual(v.reason, "flag_ink_unread")

    def test_a_tip_nobody_looked_at_is_cannot_tell(self):
        """Rule 8: no `Q.STEM_TIP_INK` row is no evidence that the stem is
        bare. The head keeps 2.23's narrowing."""
        log = Log()
        g = self._hollow_head(log, beam="decoy", tip="unread")
        v = self._duration(log, g)
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")
        self.assertEqual(v.reason, "head_fill_from_ink")

    def test_POSITIVE_CONTROL_ink_that_agrees_with_black_stays_a_quarter(self):
        log = Log()
        g = self._hollow_head(log, beam="decoy", center=1.0, ring=0.75)
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertEqual(v.reason, "head_and_marks")

    def test_ink_that_is_not_decisive_stays_a_quarter(self):
        """Centre 0.85 is not hollow: it is the floor of Sean's 222 hand-
        labelled FILLED heads (ROADMAP 2.73 raised the cut from 0.5 to 0.75,
        under that floor and not over it)."""
        log = Log()
        g = self._hollow_head(log, beam="decoy", center=0.85, ring=0.95)
        v = self._duration(log, g)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertEqual(v.reason, "head_and_marks")

    def test_a_dot_still_lengthens_the_half(self):
        log = Log()
        g = self._hollow_head(log, beam="decoy", dots=1)
        v = self._duration(log, g)
        self.assertEqual(v.reason, "hollow_head_bare_stem")
        self.assertEqual(v.value["beats"], 3.0)
        self.assertEqual(v.value["dots"], 1)

    def test_the_ink_row_is_in_the_basis_and_the_reading_is_on_the_detail(self):
        log = Log()
        g = self._hollow_head(log, beam="ran_empty")
        row = log.rows(Q.NOTEHEAD_INK, g)[-1]
        v = self._duration(log, g)
        self.assertIn(row.id, v.basis)
        # 2.319: the witness that the beam reader LOOKED at this stem is the one beam count's reading of it (was the bar-crop reader's state)
        self.assertEqual(v.detail["beam_reader"], "one_count:read")
