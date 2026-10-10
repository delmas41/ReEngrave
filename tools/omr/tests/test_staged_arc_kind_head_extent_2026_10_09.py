"""ROADMAP 2.75b -- one HEAD the detector drew in pieces is read at the centre of
its pieces (Sean's litolff_06).

THE FAULT. `litolff_06` (Sean: a TIE) joins a half note ON the fourth line to the
half note across the barline, also ON the fourth line. The detector drew the
first head THREE times -- a whole-head box and its upper and lower HALVES (Sean,
2.73: half notes on lines get split into two smaller boxes) -- and the pipeline
keeps one of them and refuses the other two as duplicates of it. The kept box sat
3-4 px below the head's own centre, so the head read at step 6.6 -> 7 against the
stop head's 5.9 -> 6: "different pitch", a SLUR. The pieces TILE the head: the
centre of their union is the head's, step 6.3 -> 6, and the two heads are one
pitch.

THE CONTROLS (CLAUDE.md §6b -- a refusal needs a positive control in its own
class, or it passes by refusing everything). Only a refused box SMALLER THAN A
HEAD that lies on the kept head is a piece:
  * the same head against a stop head two steps lower is still a SLUR (passes on
    the unrepaired tree too);
  * a refused box the size of a head (a copy of it, offset a few px), a refused
    box beside it, and a refused box that does not overlap it are NOT pieces and
    leave the reading as it was -- each beside a positive control that IS one;
  * with no refusal at all the boxes are three heads, not pieces.

Run RED against the unrepaired tree (`9b347c51`): the extent tests fail there.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict

#: page pixels: a staff space is 10 px, a half-step 5 px; the cell frame is 10x
#: the page (canonical spacing 100), so a head's canonical box is its page box x 10.
TOP = 100.0
CELL_W = 200.0
ORDER = (Q.ARC_IS_NOT_AN_ARC, Q.NOTEHEAD_POSITION, Q.ACCIDENTAL_OWNER,
         Q.ARC_KIND, Q.TIE_PAIR)


def _cells(log, n, staff_i=0):
    for m in range(n):
        log.observe(R.cell(0, 0, staff_i, m), Q.CELL_BOX,
                    [m * CELL_W, 50.0, (m + 1) * CELL_W, 250.0],
                    reader=READERS.GEOMETRY, frame=f"cell:{m}")
        log.observe(R.cell(0, 0, staff_i, m), Q.CELL_STAFF_SPACE, 100.0,
                    reader=READERS.GEOMETRY, frame=f"cell:{m}",
                    half_step=50.0, lines=5)


def _box(log, cell, gi, x, y0, y1, *, w=12.0, staff_i=0):
    """A detector notehead box at page y0..y1 and its geometry position row
    (the cell's grid: step = (centre - TOP) / 5)."""
    g = R.glyph(0, 0, staff_i, cell, gi)
    yc = (y0 + y1) / 2.0
    pos = (yc - TOP) / 5.0
    log.observe(g, Q.GLYPH_BOX,
                ("noteheadHalfOnLine", x * 10.0, y0 * 10.0, w * 10.0,
                 (y1 - y0) * 10.0),
                reader=READERS.DETECTOR, frame=f"cell:{cell}", score=0.9,
                category="notehead", bbox_page_px=[x, y0, x + w, y1])
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, round(pos, 2),
                reader=READERS.GEOMETRY, frame=f"cell:{cell}",
                residual=abs(pos - round(pos)), rounded=int(round(pos)))
    return g


def _arc(log, cell, gi, x0, x1, y0, y1, cls="slur", staff_i=0):
    g = R.glyph(0, 0, staff_i, cell, gi)
    log.observe(g, Q.ARC_BOX, cls, reader=READERS.DETECTOR,
                frame=f"cell:{cell}", score=0.8, x0=x0, x1=x1, y0=y0, y1=y1,
                bbox_page_px=[x0, y0, x1, y1])
    return g


def _decide(log, arc, duplicates=()):
    log.freeze()
    for g in duplicates:
        log.record(Verdict(id=log._next_id("vrd"), subject=g,
                           quantity=Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                           outcome=Outcome.DECIDED, value=True, decider="t",
                           reason="notehead_is_a_duplicate_box"))
    adjudicate.run(log, order=ORDER)
    return log.verdict(Q.ARC_KIND, arc)


def _litolff_06(stop_y0, stop_y1, cls="slur"):
    """Litolff p3 bar 8 -> 9, scaled to a 10 px space (the line the heads sit on
    is step 6, y = 130). The start head is drawn three times: kept (centre
    133.1, step 6.6), upper half (128.1), lower half (134.5); the union
    123.5-138.8 is one head 1.5 spaces tall centred on 131.1 (step 6.2)."""
    log = Log()
    _cells(log, 2)
    kept = _box(log, 0, 0, 40.0, 127.3, 138.8)
    up = _box(log, 0, 1, 40.0, 123.5, 132.7)
    low = _box(log, 0, 2, 40.0, 130.3, 138.6)
    _box(log, 0, 3, 120.0, stop_y0, stop_y1)
    arc = _arc(log, 0, 5, 55.0, 115.0, 142.0, 148.0, cls=cls)
    return log, arc, (up, low)


class TestAHeadDrawnInPiecesIsReadWhole(unittest.TestCase):

    def test_litolff_06_two_heads_on_one_line_are_a_tie(self):
        log, arc, dups = _litolff_06(122.1, 136.7)        # stop head: step 5.9
        v = _decide(log, arc, dups)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "tie")
        rule = v.detail["grammar"]["tie_slur_rule"]
        self.assertEqual(rule["rule"], "two_notes_same_pitch")
        two = rule["two_note"]
        self.assertEqual((two["start_step"], two["stop_step"]), (6, 6))
        self.assertEqual(two["start_extent"]["members"], 3)

    def test_the_control_a_stop_head_two_steps_lower_is_a_slur_before_and_after(self):
        """The same three-box head against a head two steps (10 px) lower: the
        extent must not turn every pair into a tie. Passes on the unrepaired
        tree too -- that is what a control is for."""
        log, arc, dups = _litolff_06(132.7, 147.3)        # stop head: step 8.0
        v = _decide(log, arc, dups)
        self.assertEqual(v.value, "slur")
        two = v.detail["grammar"]["tie_slur_rule"]["two_note"]
        self.assertEqual(two["relation"], "different")
        self.assertEqual(two["stop_step"], 8)

    def test_a_stop_head_one_step_lower_than_the_head_is_a_slur(self):
        """6.2 against 7.2: the extent moves the start head to its true step,
        6, and the stop head (6.9 -> 7) is then a step below it."""
        log, arc, dups = _litolff_06(127.1, 141.7)        # stop head: step 6.9
        v = _decide(log, arc, dups)
        self.assertEqual(v.value, "slur")
        two = v.detail["grammar"]["tie_slur_rule"]["two_note"]
        self.assertEqual(two["relation"], "different")
        self.assertEqual((two["start_step"], two["stop_step"]), (6, 7))

    def test_without_the_refused_pieces_the_kept_box_stands_as_before(self):
        """A control that can fail: with NO refusal on the two other boxes they
        are three heads, not pieces, and the reading is the old one."""
        log, arc, _dups = _litolff_06(122.1, 136.7)
        v = _decide(log, arc, ())                         # nothing refused
        two = v.detail["grammar"]["tie_slur_rule"]["two_note"]
        self.assertNotIn("start_extent", two)


class TestOnlyAPieceOfTheHeadIsUsed(unittest.TestCase):
    """The kept box [118, 128] reads step 4.6 -> 5 against a stop head at 4.0 ->
    4: different, a slur. A refused box that IS a piece of the head ([114, 122],
    a half) moves the head's centre to 121 (step 4.2 -> 4): a tie. Every refused
    box that is NOT a piece must leave it a slur, as before."""

    def _head_and_a_refused_box(self, x, y0, y1, cls="slur"):
        log = Log()
        _cells(log, 2)
        _box(log, 0, 0, 40.0, 118.0, 128.0)               # kept: step 4.6 -> 5
        refused = _box(log, 0, 1, x, y0, y1)
        _box(log, 0, 2, 120.0, 115.0, 125.0)              # stop head: step 4.0
        arc = _arc(log, 0, 5, 55.0, 115.0, 130.0, 136.0, cls=cls)
        return _decide(log, arc, (refused,))

    def test_the_positive_control_a_half_of_the_head_is_a_piece(self):
        v = self._head_and_a_refused_box(40.0, 114.0, 122.0)
        two = v.detail["grammar"]["tie_slur_rule"]["two_note"]
        self.assertEqual((two["start_step"], two["stop_step"]), (4, 4))
        self.assertEqual(two["start_extent"]["members"], 2)
        self.assertEqual(two["start_extent"]["kept_step"], 5)
        self.assertEqual(v.value, "tie")

    def test_a_refused_box_the_size_of_a_head_is_not_a_piece(self):
        """A copy of the head offset by a few px says nothing about where the
        head is: the kept box is read as it always was."""
        v = self._head_and_a_refused_box(40.0, 114.0, 124.0)
        two = v.detail["grammar"]["tie_slur_rule"]["two_note"]
        self.assertNotIn("start_extent", two)
        self.assertEqual((two["start_step"], two["relation"]), (5, "different"))
        self.assertEqual(v.value, "slur")

    def test_a_refused_box_beside_the_head_is_not_a_piece(self):
        v = self._head_and_a_refused_box(48.0, 114.0, 122.0)
        two = v.detail["grammar"]["tie_slur_rule"]["two_note"]
        self.assertNotIn("start_extent", two)
        self.assertEqual(v.value, "slur")

    def test_a_refused_box_that_does_not_overlap_the_head_is_not_a_piece(self):
        """Below the kept box and touching nothing of it: another head's, never
        a piece of this one (it may stand as a chord member of its own)."""
        v = self._head_and_a_refused_box(40.0, 129.0, 137.0)
        two = v.detail["grammar"]["tie_slur_rule"]["two_note"]
        self.assertNotIn("start_extent", two)
        self.assertEqual(v.value, "slur")

    def test_a_piece_of_an_unrefused_box_is_a_head(self):
        """The same half-box with NO refusal on it: nothing says it is a piece."""
        log = Log()
        _cells(log, 2)
        _box(log, 0, 0, 40.0, 118.0, 128.0)
        _box(log, 0, 1, 40.0, 114.0, 122.0)               # not refused
        _box(log, 0, 2, 120.0, 115.0, 125.0)
        arc = _arc(log, 0, 5, 55.0, 115.0, 130.0, 136.0, cls="slur")
        v = _decide(log, arc, ())
        two = v.detail["grammar"]["tie_slur_rule"]["two_note"]
        self.assertNotIn("start_extent", two)

    def test_a_head_the_far_head_reader_placed_is_not_moved_by_its_pieces(self):
        """A ledger-read head's position is the ledgers', never a box's."""
        log = Log()
        _cells(log, 2)
        kept = _box(log, 0, 0, 40.0, 148.0, 158.0)        # far below the staff
        refused = _box(log, 0, 1, 40.0, 144.0, 152.0)
        _box(log, 0, 2, 120.0, 145.0, 155.0)
        for g in (kept,):
            log.observe(g, Q.FAR_HEAD_LEDGER_POSITION, 11.0,
                        reader=READERS.LEDGER_FARHEAD, frame="cell:0",
                        geometry_position=11)
        arc = _arc(log, 0, 5, 55.0, 115.0, 160.0, 166.0, cls="slur")
        v = _decide(log, arc, (refused,))
        two = v.detail["grammar"]["tie_slur_rule"]["two_note"]
        self.assertNotIn("start_extent", two)


if __name__ == "__main__":
    unittest.main()
