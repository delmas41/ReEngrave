"""ROADMAP 2.12m -- ONE notehead carrying a stem UP and a stem DOWN is two
voices, and an articulation on either side of it belongs to it (STAGED,
ADJUDICATE: `adjudicate_articulation_owner`).

Sean (DECISIONS 2026-10-10): *"When one note has stems going up and down it is
always 2 voices"*. With two voices the mark sits on the STEM side of its voice
(2.12f round 2, case (a)), and both sides of a shared head are a stem side.
Brahms 1 pdf 10, tile 7 of `out/print/2.12m-review/`: the lower staff's head
`glyph/10/0/7/5/5` carries both stems, `Q.STEM_DIRECTION` abstains
`stems_disagree` (answers down, up), the articulation decision read it as an
unread stem, and the mark went to the staff above (wrong; Sean: the note below).

Written RED against `a15e223c` (every `RED` test abstained
`stem_direction_unread` there). The refusals beside them are the same page with
ONE fact changed: a single stem (no second voice) keeps the old abstention.

FRAME: cell canonical px, larger y is LOWER; staff space 20 px, heads 20 x 20.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS

CELL = R.cell(0, 0, 0, 0)
SPACE = 20.0
HALF = SPACE / 2.0
TOP = 100.0
HEAD_W = HEAD_H = 20.0
HEAD_X = 97.0
POS = 1.0                    # the upper half of the staff, as on tile 7
MARK = R.glyph(0, 0, 0, 0, 0)


def _y_of(pos):
    return TOP + pos * HALF - HEAD_H / 2.0


def _page(*, up=True, down=True, cls="articAccentAbove"):
    log = Log()
    log.observe(CELL, Q.CELL_STAFF_SPACE, SPACE, reader=READERS.GEOMETRY,
                frame="cell:0", half_step=HALF, lines=5)
    g = R.glyph(0, 0, 0, 0, 1)
    hy = _y_of(POS)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", HEAD_X, hy, HEAD_W, HEAD_H),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead")
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, POS, reader=READERS.GEOMETRY,
                frame="cell:0", residual=0.0, rounded=1)

    def stem(x, y0, y1):
        log.observe(CELL, Q.STEM, (x, y0, 3.0, y1 - y0),
                    reader=READERS.CV_LINES, frame="cell:0", x0=x, x1=x + 3.0,
                    y_center=(y0 + y1) / 2, image="no_staff",
                    staff_lines_erased=True)
    if up:      # at the head's right edge, from the head up 3.5 spaces
        stem(HEAD_X + HEAD_W - 3.0, hy + HEAD_H / 2 - 3.5 * SPACE, hy + HEAD_H / 2)
    if down:    # at the head's left edge, from the head down 3.5 spaces
        stem(HEAD_X, hy + HEAD_H / 2, hy + HEAD_H / 2 + 3.5 * SPACE)
    mh = 8.0
    if cls.endswith("Above"):
        my = hy + HEAD_H / 2 - 3.5 * SPACE - 0.3 * SPACE - mh
    else:
        my = hy + HEAD_H / 2 + 3.5 * SPACE + 0.3 * SPACE
    cx = 107.0
    log.observe(MARK, Q.ARTICULATION_MARK, cls, reader=READERS.DETECTOR,
                frame="cell:0", score=0.8, x0=cx - 6, x1=cx + 6, y0=my,
                y1=my + mh, x_center=cx, y_center=my + mh / 2,
                side="above" if cls.endswith("Above") else "below")
    log.freeze()
    adjudicate.run(log)
    return log, g


class TestOneHeadTwoStemsIsTwoVoices(unittest.TestCase):
    def test_RED_mark_above_a_shared_head_is_the_upper_voices(self):
        log, head = _page()
        sd = log.verdict(Q.STEM_DIRECTION, head)
        self.assertEqual((sd.outcome, sd.reason), ("abstained", "stems_disagree"))
        v = log.verdict(Q.ARTICULATION_OWNER, MARK)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, head.to_key())
        self.assertEqual(v.detail["stem_rule"], "stem_side")
        self.assertTrue(v.detail["two_voice"])
        self.assertTrue(v.detail["shared_head"])
        self.assertEqual(v.detail["stem_direction"], "up")

    def test_RED_mark_below_a_shared_head_is_the_lower_voices(self):
        log, head = _page(cls="articAccentBelow")
        v = log.verdict(Q.ARTICULATION_OWNER, MARK)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, head.to_key())
        self.assertEqual(v.detail["stem_direction"], "down")
        self.assertTrue(v.detail["shared_head"])


class TestOneStemIsNotTwoVoices(unittest.TestCase):
    """The decided page with the second stem taken away: one voice, the mark on
    its stem side -- the old abstention stands."""

    def test_only_the_up_stem_mark_above_keeps_abstaining(self):
        log, head = _page(down=False)
        self.assertEqual(log.verdict(Q.STEM_DIRECTION, head).value, "up")
        v = log.verdict(Q.ARTICULATION_OWNER, MARK)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "stem_contradicts_class_side")

    def test_only_the_down_stem_mark_below_keeps_abstaining(self):
        log, head = _page(up=False, cls="articAccentBelow")
        self.assertEqual(log.verdict(Q.STEM_DIRECTION, head).value, "down")
        v = log.verdict(Q.ARTICULATION_OWNER, MARK)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "stem_contradicts_class_side")


if __name__ == "__main__":
    unittest.main()
