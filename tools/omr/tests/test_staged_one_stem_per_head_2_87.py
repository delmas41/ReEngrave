"""ROADMAP 2.87, `OMR_STEM_FINDER=one_stem_per_head` -- STAGED ADJUDICATE, inside
`adjudicate_head_stem` (the forcing is LOCAL to the stems a head touches).

CONVENTION (Sean 2026-10-11): every stem touches a notehead, and every black notehead
has exactly ONE stem -- except a UNISON, where two voices share one head and go in
DIFFERENT directions (Sean: *"They would go in different directions"*): an up stem at
the head's right, a down stem at its left, and no other head.

  * tile 10 (Brahms 317803 pdf 0, staff 11 bar 2, `q1322` over `q1319`, a third apart;
    Sean: *"The top one has a stem going up and the bottom has a stem going down"*):
    the down stroke merges into the upper head's left edge, so the upper head is
    NARROWED between the up stroke and the down stroke. The down stroke also stands on
    the lower head, which has no other stem, so the upper head can only take the up
    one. FOLLOWS from the two conventions -> collapse to its own candidate.
  * a unison head: both strokes touch only that head -> NOT collapsed; its own reason
    word `unison_two_voices` (still both candidates).
  * two strokes the SAME way on one head are not a unison: today's plain narrowing.

WHAT WOULD FALSIFY IT: a black head that truly carries two same-direction stems, or a
second head box that is a duplicate of the first (a duplicate does not claim a stem:
it must stand at a different staff position). NOT CONFIRMED beyond tile 10.

RED first: against the tree before this commit, tile 10 stays narrowed `two_stems`
and the unison keeps the plain `two_stems` reason.
"""
from __future__ import annotations

import os
import unittest

from tools.omr.line_detection import STEM_FINDER_ENV
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

CELL = R.cell(0, 0, 0, 0)
H = (100.0, 100.0, 20.0, 16.0)          # the head under test (x, y, w, h)


def _head(log, gi, box):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack",) + tuple(box),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    return g


def _stem(log, x, y, h, w=4.0):
    return log.observe(CELL, Q.STEM, (x, y, w, h), reader=READERS.CV_LINES,
                       frame="cell:0")


def _join(log, g):
    log.freeze()
    adjudicate._ensure_decisions()
    spec = adjudicate.REGISTRY[Q.HEAD_STEM]
    adjudicate.adjudicate_one(log, spec, g)
    return log.verdict(Q.HEAD_STEM, g)


def _space(log):
    log.observe(CELL, Q.CELL_STAFF_SPACE, 16.0, reader=READERS.GEOMETRY,
                frame="cell:0")


class _Base(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.get(STEM_FINDER_ENV)
        os.environ[STEM_FINDER_ENV] = "one_stem_per_head"

    def tearDown(self):
        if self._old is None:
            os.environ.pop(STEM_FINDER_ENV, None)
        else:
            os.environ[STEM_FINDER_ENV] = self._old

    def tile10(self, *, k_box=(100.0, 116.0, 20.0, 16.0)):
        """H with an up stroke at its right and a down stroke at its left that also
        stands on the head K below it (a third apart)."""
        log = Log()
        _space(log)
        h = _head(log, 0, H)
        k = _head(log, 1, k_box)
        up = _stem(log, 118, 40, 68)                 # 40..108, right of H
        down = _stem(log, 100, 108, 82)              # 108..190, left of H and K
        return log, h, k, up, down


class TestTile10(_Base):

    def test_the_upper_head_takes_the_up_stem_and_the_lower_the_down(self):
        log, h, k, up, down = self.tile10()
        vh = _join(log, h)
        self.assertIs(vh.outcome, Outcome.DECIDED, (vh.reason, vh.detail))
        self.assertEqual(vh.value, up.id)
        self.assertEqual(vh.reason, "stem_by_one_per_head")
        vk = log.verdict(Q.HEAD_STEM, k) or _join_again(log, k)
        self.assertEqual(vk.value, down.id)

    def test_off_it_is_todays_narrowing(self):
        os.environ[STEM_FINDER_ENV] = ""
        log, h, k, up, down = self.tile10()
        vh = _join(log, h)
        self.assertIs(vh.outcome, Outcome.NARROWED)
        self.assertEqual(vh.reason, "two_stems")

    def test_a_duplicate_box_at_the_same_position_does_not_claim_the_stem(self):
        """Control that can fail: K one pixel below H is the same note read twice, not a
        second note, so it forces nothing (and the signature is then a unison)."""
        log, h, k, up, down = self.tile10(k_box=(100.0, 101.0, 20.0, 16.0))
        vh = _join(log, h)
        self.assertIsNot(vh.outcome, Outcome.DECIDED, (vh.reason, vh.detail))

    def test_a_lower_head_with_another_stem_of_its_own_does_not_claim_it(self):
        """K also touches a second stroke, so K could take that one: no forcing."""
        log, h, k, up, down = self.tile10()
        _stem(log, 118, 116, 80)                     # another stroke at K's right
        vh = _join(log, h)
        self.assertIsNot(vh.outcome, Outcome.DECIDED, (vh.reason, vh.detail))


def _join_again(log, g):
    adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.HEAD_STEM], g)
    return log.verdict(Q.HEAD_STEM, g)


class TestUnison(_Base):

    def test_two_heads_a_third_apart_that_both_touch_both_strokes_are_not_a_unison(self):
        """Brahms 317803 p1 (crop b_uni1): two stacked heads, both strokes merge into
        both heads. There IS another head, so it is not one head with two voices."""
        log = Log()
        _space(log)
        h = _head(log, 0, H)
        _head(log, 1, (100.0, 116.0, 20.0, 16.0))
        _stem(log, 118, 40, 85)                      # ends inside the lower head too
        _stem(log, 100, 90, 100)                     # reaches up to the upper head too
        v = _join(log, h)
        self.assertEqual(v.reason, "two_stems", (v.outcome, v.detail))

    def test_one_head_up_right_and_down_left_is_two_voices_not_a_collapse(self):
        log = Log()
        _space(log)
        h = _head(log, 0, H)
        up = _stem(log, 118, 40, 68)
        down = _stem(log, 100, 108, 82)
        v = _join(log, h)
        self.assertIs(v.outcome, Outcome.NARROWED, (v.reason, v.detail))
        self.assertEqual(v.reason, "unison_two_voices")
        self.assertEqual({c.value for c in v.candidates}, {up.id, down.id})

    def test_two_strokes_the_same_way_are_not_a_unison(self):
        """Negative control (Sean: they would go in different directions): two UP
        strokes on one head stay today's plain narrowing."""
        log = Log()
        _space(log)
        h = _head(log, 0, H)
        _stem(log, 118, 40, 68)
        _stem(log, 100, 36, 72)
        v = _join(log, h)
        self.assertIs(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "two_stems")

    def test_two_strokes_both_down_are_not_a_unison_either(self):
        log = Log()
        _space(log)
        h = _head(log, 0, H)
        _stem(log, 118, 108, 80)
        _stem(log, 100, 108, 82)
        v = _join(log, h)
        self.assertEqual(v.reason, "two_stems")

    def test_off_the_unison_keeps_the_plain_reason(self):
        os.environ[STEM_FINDER_ENV] = ""
        log = Log()
        _space(log)
        h = _head(log, 0, H)
        _stem(log, 118, 40, 68)
        _stem(log, 100, 108, 82)
        self.assertEqual(_join(log, h).reason, "two_stems")


if __name__ == "__main__":
    unittest.main()
