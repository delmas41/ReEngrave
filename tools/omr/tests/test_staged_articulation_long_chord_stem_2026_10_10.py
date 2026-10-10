"""ROADMAP 2.12m -- an articulation at the TIP of a long chord stem belongs to
that chord (STAGED, ADJUDICATE: `adjudicate_articulation_owner`).

Sean (DECISIONS 2026-10-10, on the 2.12f round-2 tiles): *"The rule of note
side works well in almost every case - it doesn't when there are multiple voices
and stems going in both directions Or if like in tile 6 the stem is very long
because it has multiple notes and one of the notes is far away from the staff -
then it will go closer to the notes."* Tile 6 (Brahms 1, pdf 23, glyph
23/1/7/9/4): an accent above the staff at the tip of an UP stem whose chord runs
down onto ledger lines below the staff; Sean: owner = that chord. STAGED
abstained there with `stem_contradicts_class_side`.

Case (a) (two voices, stems both ways) was already decided by 2.12f round 2's
`stem_side` rule (tiles 2 and 9 right) and is covered by
`test_staged_articulation_stem_side_2026_10_09.py`. This file is case (b).

THE RULE DECIDES ONLY ON POSITIVE EVIDENCE, all of it read, none of it assumed:
  * the candidate's stem is a read `Q.STEM` row (one, attached the way
    `Q.STEM_DIRECTION` attaches it) and its direction is decided;
  * that stem carries at least TWO heads (a chord), and at least one of them
    stands on a LEDGER position on the notehead side (`Q.NOTEHEAD_STAFF_POSITION`
    >= 9.5 half-steps from the top line for an up stem, <= -1.5 for a down one);
  * the mark is beyond the stem's TIP, its near edge within
    `ARTIC_STEM_TIP_MAX_GAP_SPACES` of it (staff spaces, `Q.CELL_STAFF_SPACE`),
    and its x-centre within one notehead width of the stem.
Anything else keeps the old abstention, `stem_contradicts_class_side`, with the
failed condition named in `detail["long_chord_stem"]`.

FRAME: cell canonical px, larger y is LOWER. Staff space 20 px, so the top line
is y = 0 + TOP and a half-step is 10 px. Heads 20 x 20. Every refusal below is
the decided page with ONE fact changed, so none passes by refusing everything.

Written RED against the tree before 2.12m (the brief called it 2.12g; that id is taken) (every `RED` test failed there: the
mark abstained `stem_contradicts_class_side` on the decided page).
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS

CELL = R.cell(0, 0, 0, 0)
SPACE = 20.0                 # one staff space, canonical px
HALF = SPACE / 2.0
TOP = 100.0                  # y of the top staff line
HEAD_W = HEAD_H = 20.0
HEAD_X = 97.0                # head centre x 107; an up stem stands at its right


def _y_of(pos):
    """Top of a head box whose centre is at staff position `pos`."""
    return TOP + pos * HALF - HEAD_H / 2.0


def _head(log, gi, pos, *, x=HEAD_X, position_read=True):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", x, _y_of(pos), HEAD_W, HEAD_H),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead")
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    if position_read:
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, float(pos),
                    reader=READERS.GEOMETRY, frame="cell:0",
                    residual=0.0, rounded=int(round(pos)))
    return g


def _stem(log, x, y_top, y_bottom, w=3.0):
    h = y_bottom - y_top
    log.observe(CELL, Q.STEM, (x, y_top, w, h), reader=READERS.CV_LINES,
                frame="cell:0", x0=x, x1=x + w, y_center=y_top + h / 2,
                image="no_staff", staff_lines_erased=True)


def _space(log):
    log.observe(CELL, Q.CELL_STAFF_SPACE, SPACE, reader=READERS.GEOMETRY,
                frame="cell:0", half_step=HALF, lines=5)


def _mark(log, gi, cx, y, cls, *, w=12.0, h=8.0):
    g = R.glyph(0, 0, 0, 0, gi)
    x = cx - w / 2.0
    side = "above" if cls.endswith("Above") else "below"
    log.observe(g, Q.ARTICULATION_MARK, cls, reader=READERS.DETECTOR,
                frame="cell:0", score=0.8,
                x0=x, x1=x + w, y0=y, y1=y + h,
                x_center=cx, y_center=y + h / 2.0, side=side)
    return g


def _decide(log, mark):
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.ARTICULATION_OWNER, mark)


MARK = R.glyph(0, 0, 0, 0, 0)


def _up_chord(*, far_pos=16.0, tip_pos=-1.0, gap_spaces=0.3, mark_cx=107.0,
              space=True, chord=True, far_position_read=True,
              cls="articAccentAbove"):
    """Tile 6, drawn: an UP stem standing at the heads' right edge, from the far
    head (on ledgers below the staff) to a tip near the top line; the tip-end
    head sits IN the staff at position 6. The accent hangs just above the tip."""
    log = Log()
    if space:
        _space(log)
    tip_y = TOP + tip_pos * HALF
    near = _head(log, 1, 6.0)
    far = None
    if chord:
        far = _head(log, 2, far_pos, position_read=far_position_read)
        bottom = _y_of(far_pos) + HEAD_H / 2.0
    else:
        bottom = _y_of(6.0) + HEAD_H / 2.0
    _stem(log, HEAD_X + HEAD_W - 3.0, tip_y, bottom)
    mark_h = 8.0
    _mark(log, 0, mark_cx, tip_y - gap_spaces * SPACE - mark_h, cls, h=mark_h)
    return log, near, far


class TestTheLongChordStemTakesTheMarkAtItsTip(unittest.TestCase):
    def test_RED_tile6_up_chord_with_a_ledger_head_decides_the_chord(self):
        log, near, _far = _up_chord()
        v = _decide(log, MARK)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.reason, "stem_tip_of_long_chord")
        # the chord's head at the TIP end: the head the mark stands nearest
        self.assertEqual(v.value, near.to_key())
        self.assertEqual(v.detail["stem_rule"], "long_chord_stem")
        self.assertEqual(v.detail["stem_direction"], "up")
        self.assertEqual(v.detail["suffix_side"], "above")
        self.assertEqual(v.detail["chord_heads"], 2)
        self.assertAlmostEqual(v.detail["far_head_position"], 16.0)
        self.assertAlmostEqual(v.detail["tip_gap_spaces"], 0.3, places=3)

    def test_RED_the_mirror_down_chord_with_a_ledger_head_above(self):
        """Stem DOWN from a chord reaching up onto ledgers above the staff; the
        mark hangs below the stem's tip. Same rule, other side."""
        log = Log()
        _space(log)
        near = _head(log, 1, 2.0)
        _head(log, 2, -8.0)
        tip_y = TOP + 9.0 * HALF
        _stem(log, HEAD_X, _y_of(-8.0) + HEAD_H / 2.0, tip_y)
        _mark(log, 0, 107.0, tip_y + 0.3 * SPACE, "articAccentBelow")
        v = _decide(log, MARK)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.reason, "stem_tip_of_long_chord")
        self.assertEqual(v.value, near.to_key())
        self.assertEqual(v.detail["stem_direction"], "down")

    def test_a_mark_touching_the_tip_still_counts(self):
        """Tile 6's accent touches the stem's end (the tip runs into the mark's
        box): a small overlap is the same mark, as long as its CENTRE is beyond
        the tip."""
        log, near, _ = _up_chord(gap_spaces=-0.15)
        v = _decide(log, MARK)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, near.to_key())

    def test_staccato_centred_on_the_STEM_counts(self):
        """Dorico/LilyPond: a stem-side staccato centres on the stem, not the
        head -- inside both the head's x window and the stem's."""
        log, near, _ = _up_chord(mark_cx=HEAD_X + HEAD_W - 1.5 - 2.0,
                                 cls="articStaccatoAbove")
        v = _decide(log, MARK)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, near.to_key())


class TestNoPositiveEvidenceKeepsAbstaining(unittest.TestCase):
    """Each is the decided page above with ONE fact changed."""

    def _abstains(self, log, why):
        v = _decide(log, MARK)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "stem_contradicts_class_side")
        self.assertEqual(v.detail["long_chord_stem"], why)
        return v

    def test_RED_a_far_mark_the_stem_does_not_reach_stays_abstained(self):
        """Two spaces beyond the tip: no stem reaches the mark."""
        log, _, _ = _up_chord(gap_spaces=2.0)
        self._abstains(log, "mark_not_at_stem_tip")

    def test_a_mark_BELOW_the_tip_is_not_beyond_it(self):
        """The mark's centre inside the stem's own span (down by the head) is
        not at the tip."""
        log, _, _ = _up_chord(gap_spaces=-1.5)
        self._abstains(log, "mark_not_at_stem_tip")

    def test_RED_a_chord_with_NO_ledger_head_is_an_ordinary_stem(self):
        """The low head in the first space below the staff (position 9): no
        ledger, the stem is not long -- the notehead side holds, so the mark
        on the stem side is the readers disagreeing, as before."""
        log, _, _ = _up_chord(far_pos=9.0)
        self._abstains(log, "no_ledger_head_on_stem")

    def test_a_single_head_is_not_a_chord(self):
        log, _, _ = _up_chord(chord=False)
        self._abstains(log, "not_a_chord")

    def test_the_far_heads_position_unread_is_no_evidence(self):
        log, _, _ = _up_chord(far_position_read=False)
        self._abstains(log, "no_ledger_head_on_stem")

    def test_no_staff_space_no_unit_no_decision(self):
        log, _, _ = _up_chord(space=False)
        self._abstains(log, "no_staff_space")

    def test_a_mark_off_the_stem_in_x_is_not_at_its_tip(self):
        """Centre more than a notehead width left of the stem (still inside the
        head's own x window)."""
        log, _, _ = _up_chord(mark_cx=HEAD_X - 3.0)
        self._abstains(log, "mark_not_at_stem_tip")


if __name__ == "__main__":
    unittest.main()
