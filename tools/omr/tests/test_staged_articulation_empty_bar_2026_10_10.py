"""ROADMAP 2.12m -- a mark between two staves belongs to the staff with notes
when the OTHER staff's bar is empty (STAGED, ADJUDICATE:
`adjudicate_articulation_owner`, reason `other_staff_bar_empty`).

Sean (DECISIONS 2026-10-10): *"when the other system in question has an empty
measure then it has to belong to the one with notes in it"*. The other staff is
the one on the mark's declared side (an `...Above` mark: the staff above).

"EMPTY" IS READ, NEVER DEFAULTED (CLAUDE.md rule 8): no notehead in that bar
is that staff's (a decided `Q.GLYPH_OWNER` naming it, or an undecided head filed
in its cell), AND its own cell holds a `restWhole` -- the measure rest. A bar
where nothing was read, or only a shorter rest, is "cannot tell".

The rule acts only where the decision would otherwise abstain for a STEM
reason (`stem_direction_unread`, `stem_contradicts_class_side`), and gives the
mark to the head that reason was about: the nearest head on the mark's declared
side in its column, alone within the tie tolerance.

Written RED against `7dea977d` (each `RED` test abstained there). Each refusal
is the decided page with ONE fact changed.

FRAME: cell canonical px, larger y is LOWER; staff space 20, heads 20 x 20.
Staff 0 is the upper staff, staff 1 the lower; the mark is in staff 1's cell,
above its head.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS

SPACE = 20.0
HALF = SPACE / 2.0
TOP = 100.0
HEAD_W = HEAD_H = 20.0
HEAD_X = 97.0
MARK = R.glyph(0, 0, 1, 0, 0)
HEAD = R.glyph(0, 0, 1, 0, 1)


def _y_of(pos):
    return TOP + pos * HALF - HEAD_H / 2.0


def _box(log, g, cls, x, y, w, h, category):
    log.observe(g, Q.GLYPH_BOX, (cls, x, y, w, h), reader=READERS.DETECTOR,
                frame="cell:%d" % g.staff, score=0.9, category=category)


def _page(*, upper="restWhole", upper_head=False, stem=None,
          cls="articAccentAbove", second_head=False):
    log = Log()
    for st in (0, 1):
        log.observe(R.cell(0, 0, st, 0), Q.CELL_STAFF_SPACE, SPACE,
                    reader=READERS.GEOMETRY, frame="cell:%d" % st,
                    half_step=HALF, lines=5)
    # the lower staff's head, in the staff at position 2
    hy = _y_of(2.0)
    _box(log, HEAD, "noteheadBlack", HEAD_X, hy, HEAD_W, HEAD_H, "notehead")
    log.observe(HEAD, Q.NOTEHEAD_CLASS, "noteheadBlack",
                reader=READERS.DETECTOR, frame="cell:1", score=0.9)
    log.observe(HEAD, Q.NOTEHEAD_STAFF_POSITION, 2.0, reader=READERS.GEOMETRY,
                frame="cell:1", residual=0.0, rounded=2)
    if second_head:     # a second head level with the first, same column
        g2 = R.glyph(0, 0, 1, 0, 3)
        _box(log, g2, "noteheadBlack", HEAD_X + 2, hy, HEAD_W, HEAD_H, "notehead")
        log.observe(g2, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:1", score=0.9)
    if stem == "up":
        x = HEAD_X + HEAD_W - 3.0
        log.observe(R.cell(0, 0, 1, 0), Q.STEM, (x, hy + HEAD_H / 2 - 3.5 * SPACE,
                                                 3.0, 3.5 * SPACE),
                    reader=READERS.CV_LINES, frame="cell:1", x0=x, x1=x + 3,
                    y_center=hy, image="no_staff", staff_lines_erased=True)
    # the upper staff's bar
    if upper:
        _box(log, R.glyph(0, 0, 0, 0, 0), upper, 300.0, TOP + 2 * HALF, 24.0,
             HALF, "rest")
    if upper_head:
        g = R.glyph(0, 0, 0, 0, 1)
        _box(log, g, "noteheadBlack", 400.0, _y_of(4.0), HEAD_W, HEAD_H, "notehead")
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    # the mark, a space and a half above the head (between the staves)
    mh = 8.0
    my = (hy - 1.5 * SPACE - mh) if cls.endswith("Above") else (hy + HEAD_H + 1.5 * SPACE)
    cx = HEAD_X + HEAD_W / 2.0
    log.observe(MARK, Q.ARTICULATION_MARK, cls, reader=READERS.DETECTOR,
                frame="cell:1", score=0.8, x0=cx - 6, x1=cx + 6, y0=my,
                y1=my + mh, x_center=cx, y_center=my + mh / 2,
                side="above" if cls.endswith("Above") else "below")
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.ARTICULATION_OWNER, MARK)


class TestTheOtherStaffsBarIsEmpty(unittest.TestCase):
    def test_RED_unread_stem_and_an_empty_upper_bar_decides_the_lower_head(self):
        v = _page()
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.reason, "other_staff_bar_empty")
        self.assertEqual(v.value, HEAD.to_key())
        self.assertEqual(v.detail["other_staff"], "staff/0/0/0")
        self.assertEqual(v.detail["was"], "stem_direction_unread")

    def test_RED_a_stem_side_mark_and_an_empty_upper_bar_decides_too(self):
        v = _page(stem="up")
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.reason, "other_staff_bar_empty")
        self.assertEqual(v.detail["was"], "stem_contradicts_class_side")


class TestNotProvenEmptyKeepsAbstaining(unittest.TestCase):
    def test_the_upper_bar_has_a_note(self):
        v = _page(upper_head=True)
        self.assertEqual(v.reason, "stem_direction_unread")
        self.assertEqual(v.detail["other_staff_bar"], "has_notes")

    def test_nothing_read_in_the_upper_bar_is_not_empty(self):
        v = _page(upper=None)
        self.assertEqual(v.reason, "stem_direction_unread")
        self.assertEqual(v.detail["other_staff_bar"], "no_measure_rest")

    def test_a_quarter_rest_is_not_an_empty_bar(self):
        v = _page(upper="restQuarter")
        self.assertEqual(v.reason, "stem_direction_unread")
        self.assertEqual(v.detail["other_staff_bar"], "no_measure_rest")

    def test_a_mark_below_looks_at_the_staff_below_which_does_not_exist(self):
        v = _page(cls="articAccentBelow")
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.detail["other_staff_bar"], "no_measure_rest")

    def test_two_heads_equally_near_stay_undecided(self):
        v = _page(second_head=True)
        self.assertNotEqual(v.outcome, "decided")


if __name__ == "__main__":
    unittest.main()
