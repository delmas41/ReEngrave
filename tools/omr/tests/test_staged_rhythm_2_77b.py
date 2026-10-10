"""ROADMAP 2.77b -- three reading faults Sean found in the second blind review of
the rhythm leftovers (`out/print/rhythm-leftovers-2/`), STAGED, ADJUDICATE only.

* A (crop 9, Litolff p3 `glyph/2/0/3/1/4`, a printed EIGHTH read a 16th): the
  detector boxed ONE printed head twice, once in each staff's padded cell. The
  copy filed on the staff that LOST the contest counted the beam of that
  staff's own notes (below the head, the far side of a stem that points up).
  A head's beams are the ones its OWN stem reaches: where no CV stem is
  attached, the head's own `Q.HEAD_STEM_REACH` says which way the stem runs, so
  a beam on the other side of the head is not its beam; and the loser of the
  contest has no duration of its own (its marks lie in the owner's cell, which
  the owner reads).
* B (crop 8, Litolff p3 `glyph/2/1/7/13/1`, an EIGHTH that was right before
  2.77): 2.77's "a stroke with no stem at either end is not a beam" fired on a
  sloped beam the ink reader's end-window missed although four read stems end
  inside it. A beam joins its note's stem AND another note's stem (Sean, 2.74).
* C (crop 7, Litolff p3 `glyph/3/0/7/4/13`, "a beam that connects 8th notes but
  is not a notehead"): a regular-head box 0.69 spaces tall lying 85% inside a
  read beam stroke is that beam's ink.

The geometry below is the REAL measured geometry of those cells (canonical px,
staff space 100, from the 2026-10-09 small re-gather of Litolff pages 0-3).

RUN RED FIRST on the unrepaired branch (the commit says so); every `CONTROL_`
test is green before and after, so a rule that refuses or credits everything
cannot pass.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, adjudicators            # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict

from tools.omr.tests.test_staged_duration import CELL, _staff_space


def _head(log, gi, box, cls="noteheadBlackInSpace"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead")
    return g


def _stem(log, box):
    x, y, w, h = box
    return log.observe(CELL, Q.STEM, (x, y, w, h), reader=READERS.CV_LINES,
                       frame="cell:0", x0=x, x1=x + w,
                       y_center=y + h / 2.0, image="no_staff",
                       staff_lines_erased=True)


def _stroke(log, box, *, cv=True):
    x, y, w, h = box
    return log.observe(CELL, Q.BEAM_STROKE, (x, y, w, h),
                       reader=READERS.CV_LINES if cv else READERS.DETECTOR,
                       frame="cell:0", x0=x, x1=x + w, y_center=y + h / 2.0,
                       image="no_staff" if cv else "original",
                       staff_lines_erased=cv)


def _ink(log, stroke, *, ratio, sag, ends, thickness_px=60.0):
    """The real `Q.BEAM_STROKE_INK` shape, with `thickness_px` (the median
    vertical run of the stroke's own ink) -- 2.77b's rule 3 reads it."""
    x0, x1 = stroke.detail["x0"], stroke.detail["x1"]
    ends_d = [{"found": e, "x": (x0 if i == 0 else x1) if e else None}
              for i, e in enumerate(ends)]
    return log.observe(CELL, Q.BEAM_STROKE_INK, 0.6,
                       reader=READERS.CV_BEAM_SHAPE, frame="cell:0",
                       beam_row_id=stroke.id, thickness_px=thickness_px,
                       line_px=28.0, thickness_ratio=ratio,
                       thickness_spaces=thickness_px / 100.0,
                       sagitta_spaces=sag, end_stems=ends_d, columns=100,
                       cover=1.0, band=[0.0, thickness_px])


def _owner(log, sub, value, outcome=Outcome.DECIDED):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=Q.GLYPH_OWNER,
        outcome=outcome, value=value, decider="t", reason="x"))


def _reach(log, g, direction, up_ext=4.4):
    return log.observe(g, Q.HEAD_STEM_REACH, direction,
                       reader=READERS.CV_HEAD_STEM_REACH, frame="page",
                       head_box_page=[0.0, 0.0, 20.0, 16.0], sp=16.0,
                       up_ext=up_ext if direction == "up" else 0.0,
                       down_ext=up_ext if direction == "down" else 0.0,
                       up_tip_y=None, down_tip_y=None,
                       up_clipped=False, down_clipped=False)


def _duration(log, g):
    adjudicate.run(log)
    return log.verdict(Q.DURATION, g)


# ═════════════════════════════════════════════════════════════════════════════
# A -- a head's beams are the ones its OWN stem reaches
# ═════════════════════════════════════════════════════════════════════════════

class TestALosingCopyHasNoDurationOfItsOwn(unittest.TestCase):
    """Crop 9: the contest's loser counted the other staff's beam."""

    def _fixture(self, owner=None, outcome=Outcome.DECIDED):
        log = Log()
        _staff_space(log, 100)
        g = _head(log, 0, (561, 1, 159, 133), "noteheadBlackOnLine")
        if owner is not None:
            _owner(log, g, owner, outcome)
        return log, g

    def test_a_copy_the_contest_awarded_to_another_staff_abstains_RED(self):
        log, g = self._fixture(owner="staff/0/0/1")
        v = _duration(log, g)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "owned_by_another_staff")

    def test_CONTROL_the_owner_keeps_its_duration(self):
        log, g = self._fixture(owner="staff/0/0/0")
        v = _duration(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)

    def test_CONTROL_an_ABSTAINED_owner_does_not_abstain_the_duration(self):
        """Rule 8 cuts the other way too: a contest nobody won names no
        loser, so nothing here is another staff's."""
        log, g = self._fixture(owner=None, outcome=Outcome.ABSTAINED)
        _owner(log, g, None, Outcome.ABSTAINED)
        v = _duration(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)

    def test_CONTROL_an_uncontested_head_is_untouched(self):
        log, g = self._fixture()
        v = _duration(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)


class TestAStemTheCvNeverFoundStillSaysWhichWayItRuns(unittest.TestCase):
    """`Q.HEAD_STEM_REACH` is the head's own ink: an up-stem's beam is ABOVE
    the head. A beam below it is the next voice's (or the next staff's)."""

    def _fixture(self, direction, *, beam_above=False):
        log = Log()
        _staff_space(log, 100)
        g = _head(log, 0, (100, 100, 140, 120), "noteheadBlackOnLine")
        # a beam over the head's column, two read stems standing on it so it
        # passes every ink test; none of the stems touches the head's box
        y = 20 if beam_above else 300
        if beam_above:
            _stem(log, (300, 20, 30, 200))
            _stem(log, (400, 20, 30, 200))
        else:
            _stem(log, (110, 300, 30, 200))
            _stem(log, (400, 300, 30, 200))
        s = _stroke(log, (100, y, 330, 60))
        _ink(log, s, ratio=2.4, sag=0.01, ends=(True, True))
        if direction:
            _reach(log, g, direction)
        return log, g

    def test_an_UP_stem_does_not_own_a_beam_below_it_RED(self):
        """...and where that beam was the head's ONLY candidate mark the head
        is NARROWED, never decided a quarter from the absence of a mark: the
        stem's tip was never examined (no CV stem is attached) -- rule 8."""
        log, g = self._fixture("up")
        v = _duration(log, g)
        self.assertEqual(v.detail["beam_side"], "up")
        self.assertEqual(v.detail["beams_far_side"], 1)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beam_discounted_uncertain")
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates),
                         [0.5, 1.0])

    def test_CONTROL_an_UP_stem_owns_a_beam_ABOVE_it(self):
        """The positive control: the SAME head and ruler reading with the beam
        on the stem's own side counts it -- so the rule is not 'refuse all'."""
        log, g = self._fixture("up", beam_above=True)
        v = _duration(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beams_far_side"], 0)

    def test_CONTROL_a_DOWN_stem_owns_the_same_beam(self):
        """The positive control: the stem turned the other way counts the
        beam below it."""
        log, g = self._fixture("down")
        v = _duration(log, g)
        self.assertEqual(v.detail["beams_far_side"], 0)
        self.assertEqual(v.value["beats"], 0.5)

    def test_a_DOWN_stem_is_read_from_the_ruler_RED(self):
        log, g = self._fixture("down")
        v = _duration(log, g)
        self.assertEqual(v.detail["beam_side"], "down")

    def test_CONTROL_a_short_run_beside_the_head_is_a_neighbouring_head_not_a_stem(
            self):
        """Measured: the ruler agrees with the head's own CV stem on 306 of 307
        heads at 2.0 spaces or more, and on 77-93% below it (a stacked
        neighbour's ink). A 1.2-space run says nothing about the side."""
        log2 = Log()
        _staff_space(log2, 100)
        g2 = _head(log2, 0, (100, 100, 140, 120), "noteheadBlackOnLine")
        _stem(log2, (110, 300, 30, 200))
        _stem(log2, (400, 300, 30, 200))
        s2 = _stroke(log2, (100, 300, 330, 60))
        _ink(log2, s2, ratio=2.4, sag=0.01, ends=(True, True))
        _reach(log2, g2, "up", up_ext=1.2)
        v = _duration(log2, g2)
        self.assertIsNone(v.detail["beam_side"])
        self.assertEqual(v.detail["beams_far_side"], 0)

    def test_CONTROL_a_stem_that_runs_both_ways_is_no_side(self):
        log, g = self._fixture("both")
        v = _duration(log, g)
        self.assertIsNone(v.detail["beam_side"])

    def test_CONTROL_without_a_reach_row_nothing_changes(self):
        log, g = self._fixture(None)
        v = _duration(log, g)
        self.assertIsNone(v.detail["beam_side"])
        self.assertEqual(v.detail["beams_far_side"], 0)


# ═════════════════════════════════════════════════════════════════════════════
# B -- two stems that END inside a stroke are a stem each side of a beam
# ═════════════════════════════════════════════════════════════════════════════

class TestBStemsEndingInsideAStrokeCreditIt(unittest.TestCase):
    """Crop 8: a 4-head chord under a sloped beam; the ink reader's end window
    found no stem at either end of it, four read stems end inside it."""

    def _tile8(self, log):
        _staff_space(log, 100)
        g = _head(log, 1, (410, 1087, 136, 140), "noteheadBlackOnLine")
        _head(log, 0, (106, 976, 146, 137), "noteheadBlackOnLine")
        _head(log, 2, (576, 1094, 160, 139), "noteheadBlackOnLine")
        _head(log, 3, (241, 1073, 162, 158), "noteheadBlackOnLine")
        for b in ((508, 687, 38, 514), (210, 706, 32, 387),
                  (343, 738, 45, 482), (692, 807, 32, 400)):
            _stem(log, b)
        beam = _stroke(log, (211, 629, 482, 139))
        row = _stroke(log, (230, 1143, 520, 44))      # the ledger line through the heads
        led = R.glyph(0, 0, 0, 0, 6)
        log.observe(led, Q.GLYPH_BOX, ("ledgerLine", 226, 1158, 200, 19),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.6,
                    category="ledger")
        _ink(log, beam, ratio=2.724, sag=0.0478, ends=(False, False),
             thickness_px=79.0)
        _ink(log, row, ratio=3.931, sag=0.0099, ends=(False, True),
             thickness_px=114.0)
        return g

    def test_tile_8_the_sloped_beam_over_a_chord_is_counted_EIGHTH_RED(self):
        log = Log()
        g = self._tile8(log)
        v = _duration(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beams_not_by_ink"], 0)

    def _bar_under_a_beam(self, log, n_inside):
        """A thick straight stroke (the foot of a dynamic letter) 36 px BELOW
        the tips of the stems that end on the real beam above it."""
        _staff_space(log, 100)
        g = _head(log, 0, (412, 431, 136, 130), "noteheadBlackOnLine")
        # stems that end at y 864 (their tips); the bar lies at y 900-932
        for b in ((419, 451, 31, 413), (244, 464, 38, 412),
                  (575, 464, 38, 400)):
            _stem(log, b)
        bar = _stroke(log, (283, 900, 243, 32))
        _ink(log, bar, ratio=3.036, sag=0.0033, ends=(False, False),
             thickness_px=32.0)
        # n_inside extra stems whose tips END inside the bar
        for k in range(n_inside):
            _stem(log, (300 + 90 * k, 700, 25, 215))
        return g

    def test_CONTROL_stems_that_end_ABOVE_a_bar_do_not_credit_it(self):
        log = Log()
        g = self._bar_under_a_beam(log, 0)
        v = _duration(log, g)
        self.assertEqual(v.detail["beams_not_by_ink_why"],
                         {"no_stem_at_ends": 1})

    def test_CONTROL_ONE_stem_ending_inside_is_not_a_beam(self):
        """Sean: a beam joins its note's stem AND another note's stem."""
        log = Log()
        g = self._bar_under_a_beam(log, 1)
        v = _duration(log, g)
        self.assertEqual(v.detail["beams_not_by_ink_why"],
                         {"no_stem_at_ends": 1})

    def test_TWO_stems_ending_inside_the_same_bar_are_a_beam(self):
        log = Log()
        g = self._bar_under_a_beam(log, 2)
        v = _duration(log, g)
        self.assertEqual(v.detail["beams_not_by_ink"], 0)


# ═════════════════════════════════════════════════════════════════════════════
# C -- a regular-head box no taller than the beam it lies in is the beam's ink
# ═════════════════════════════════════════════════════════════════════════════

class TestCABoxLyingInAReadBeamIsNotAHead(unittest.TestCase):
    """Crop 7 (Litolff p3 cell 3/0/7/4): `noteheadBlackInSpace`, 1.23 x 0.69
    spaces, lying 85% inside a stem-down beam [458,794,412,63] (2.36 staff
    lines thick, straight, a stem found at BOTH ends)."""

    def _cell(self, box=(750, 785, 123, 69), cls="noteheadBlackInSpace", *,
              ratio=2.357, ends=(True, True), stems=((838, 464, 25, 394),
                                                     (656, 470, 32, 400))):
        log = Log()
        _staff_space(log, 100)
        g = _head(log, 0, box, cls)
        for b in stems:
            _stem(log, b)
        beam = _stroke(log, (458, 794, 412, 63))
        _ink(log, beam, ratio=ratio, sag=0.0008, ends=ends, thickness_px=66.0)
        return log, g

    def _refusal(self, log, g):
        adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
        return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)

    def test_tile_7_the_box_on_the_beam_is_refused_as_a_beam_piece_RED(self):
        log, g = self._cell()
        v = self._refusal(log, g)
        self.assertTrue(v.value)
        self.assertEqual(v.reason, "is_a_beam_piece")

    def test_CONTROL_the_same_x_a_HEAD_SIZED_box_is_not_refused(self):
        """A head standing at the stroke's end is ~1.1 spaces tall -- taller
        than the beam is thick."""
        log, g = self._cell(box=(750, 740, 123, 118))
        v = self._refusal(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_a_FLAT_box_away_from_any_beam_is_not_refused(self):
        """Flatness alone refuses nothing: print-confirmed heads are boxed
        0.34-0.69 spaces tall (a head cut by the crop, a partial box)."""
        log, g = self._cell(box=(100, 300, 123, 69))
        v = self._refusal(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_a_small_cue_head_beside_the_beam_is_not_refused(self):
        log, g = self._cell(box=(500, 700, 100, 80),
                            cls="noteheadBlackSmall")
        v = self._refusal(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_a_flat_cue_class_box_ON_the_beam_is_left_alone(self):
        """The rule judges REGULAR heads (`geometry.is_regular_notehead`): a
        `*Small` class is a different population this rule did not measure."""
        log, g = self._cell(cls="noteheadBlackSmall")
        v = self._refusal(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_a_THIN_stroke_is_no_beam_so_nothing_is_its_ink(self):
        log, g = self._cell(ratio=1.2)
        v = self._refusal(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_a_stroke_no_stem_stands_on_is_not_a_beam_either(self):
        log, g = self._cell(ends=(True, False), stems=())
        v = self._refusal(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_a_box_only_half_inside_the_stroke_is_not_refused(self):
        log, g = self._cell(box=(750, 827, 123, 69))
        v = self._refusal(log, g)
        self.assertFalse(v.value)

    def test_the_tile_7_head_beside_it_keeps_its_value_when_the_box_is_gone(
            self):
        """Consequence, not just the verdict: with the false box refused the
        row of real heads still reads (the duration decision is unchanged
        for them)."""
        log, g = self._cell()
        h2 = _head(log, 5, (832, 428, 149, 128), "noteheadBlackOnLine")
        adjudicate.run(log)
        self.assertEqual(
            log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h2).reason, "notehead")


if __name__ == "__main__":
    unittest.main()
