"""ROADMAP 2.68 (Sean, 2026-10-09): a dynamic marking is anchored to ONE NOTE.

Sean: *"Hairpins and dynamic markings will often cross many bars. Can we make
dynamics system specific rather than cell specific?"* / *"They will still need a
single point to start or end - connected to a note."*  And the rule, asked on the
Litolff `p cresc. f` whose `f` is printed on the barline: *"If it is on a note,
it starts on the note. If it's between notes, it impacts the next one coming up.
It's meant to give the musician a heads up."*

So: a mark whose ink stands AT a note's x on its own staff anchors to that note;
a mark BETWEEN two notes anchors to the NEXT onset on its staff -- across a
barline, whatever cell detected the box. The bar is DERIVED from the anchored
note. Nothing following in the system -> abstain and say so.

"At a note" is measured on the page, from the boxes' own x extents (a position in
page pixels is local by construction, CLAUDE.md §10); every case has its positive
control the other way.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import text as T
from tools.omr.staged.record import Log, Outcome, Q, READERS

STAFF = R.staff(0, 0, 0)
OTHER = R.staff(0, 0, 1)


def _col(x0, x1, key="n", cell=0, carrier="notehead"):
    return T.OnsetColumn(x0=x0, x1=x1, keys=(key,), cell=cell, carrier=carrier)


class TestThePureRule(unittest.TestCase):
    COLS = [_col(100, 120, "a", 0), _col(200, 220, "b", 0), _col(300, 320, "c", 1)]

    def test_a_mark_on_a_note_starts_on_that_note(self):
        got = T.anchor_for_extent(205, 235, self.COLS)
        self.assertEqual((got.relation, got.column.keys), ("at_note", ("b",)))

    def test_a_mark_between_two_notes_takes_the_next_one(self):
        """The positive control the other way: the same mark moved into the gap
        between `b` and `c` anchors to `c`, not to the nearer-by-distance `b`."""
        got = T.anchor_for_extent(225, 245, self.COLS)
        self.assertEqual((got.relation, got.column.keys), ("next_onset", ("c",)))

    def test_nearest_is_not_the_rule(self):
        """A mark 5 px after `b` and 75 px before `c`: nearest would say `b`."""
        got = T.anchor_for_extent(225, 245, self.COLS)
        self.assertNotEqual(got.column.keys, ("b",))

    def test_a_mark_on_a_barline_goes_to_the_first_note_of_the_next_bar(self):
        """Litolff `p cresc. f`: the `f` at the barline. The columns carry their
        own cells; the mark carries none."""
        cols = [_col(100, 120, "last_of_bar0", 0), _col(300, 320, "first_of_bar1", 1)]
        got = T.anchor_for_extent(200, 225, cols)
        self.assertEqual(got.column.keys, ("first_of_bar1",))
        self.assertEqual(got.column.cell, 1)

    def test_a_touch_below_the_overlap_floor_is_between_not_at(self):
        """The floor is a quarter of the head's width: 2 px of a 20 px head is a
        graze, and the mark is read as standing between."""
        got = T.anchor_for_extent(218, 240, self.COLS)
        self.assertEqual(got.relation, "next_onset")
        self.assertEqual(got.column.keys, ("c",))

    def test_a_graze_on_the_following_head_still_means_that_head(self):
        got = T.anchor_for_extent(205, 302, [_col(100, 120, "a"), _col(300, 320, "c")])
        self.assertEqual(got.column.keys, ("c",))

    def test_two_notes_equally_under_the_mark_abstain(self):
        """A wide mark over two heads equally: both are plausible, so neither is
        chosen (rule 8)."""
        cols = [_col(100, 120, "a"), _col(125, 145, "b")]
        got = T.anchor_for_extent(105, 140, cols)
        self.assertIsNone(got.column)
        self.assertEqual(got.why, "equally_plausible")

    def test_a_wide_mark_is_anchored_to_the_head_it_is_centred_on(self):
        """An `ff` under a beamed group overlaps three heads (Litolff cello,
        the case that abstained `equally_plausible` before): a dynamic is set
        centred on its note, so the head under the mark's own centre is the
        anchor. The control is the next test: centred on NO head, it abstains."""
        cols = [_col(100, 120, "a"), _col(130, 150, "b"), _col(160, 180, "c")]
        got = T.anchor_for_extent(105, 175, cols)       # centre 140, over b
        self.assertEqual((got.relation, got.column.keys), ("at_note", ("b",)))

    def test_a_wide_mark_centred_on_no_head_and_overlapping_two_equally_abstains(self):
        cols = [_col(100, 120, "a"), _col(125, 145, "b")]
        got = T.anchor_for_extent(105, 140, cols)       # centre 122.5, between
        self.assertIsNone(got.column)
        self.assertEqual(got.why, "equally_plausible")

    def test_the_clearly_larger_overlap_wins(self):
        cols = [_col(100, 120, "a"), _col(125, 145, "b")]
        got = T.anchor_for_extent(112, 148, cols)
        self.assertEqual(got.column.keys, ("b",))

    def test_nothing_following_abstains_and_says_so(self):
        got = T.anchor_for_extent(330, 350, self.COLS)
        self.assertIsNone(got.column)
        self.assertEqual(got.why, "no_following_note_in_system")

    def test_a_rest_is_an_onset(self):
        cols = [_col(100, 120, "n", 0), _col(300, 340, "r", 1, "rest")]
        got = T.anchor_for_extent(200, 220, cols)
        self.assertEqual(got.column.carrier, "rest")

    def test_no_columns_at_all_abstains(self):
        got = T.anchor_for_extent(10, 20, [])
        self.assertIsNone(got.column)
        self.assertEqual(got.why, "no_following_note_in_system")


def _head(log, staff, cell, gi, x, *, w=20.0, y=100.0, h=20.0, category="notehead"):
    g = R.glyph(0, 0, staff, cell, gi)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine" if category == "notehead" else "restWhole",
                                 x, y, w, h),
                reader=READERS.DETECTOR, frame=f"cell:{cell}", score=0.9,
                category=category, bbox_page_px=[x, y, x + w, y + h],
                x_center_page=x + w / 2.0, y_center_page=y + h / 2.0)
    return g


def _letter(log, staff, cell, gi, letter, x0, x1, sp=10.0):
    g = R.glyph(0, 0, staff, cell, gi)
    log.observe(g, Q.DYNAMIC_LETTER, "dynamic" + letter.upper(),
                reader=READERS.DETECTOR, frame=G.FRAME_PAGE, score=0.8,
                letter=letter, cell_frame=f"cell:{cell}",
                bbox_page_px=[x0, 150.0, x1, 175.0],
                x_center_page=(x0 + x1) / 2.0, y_center_page=162.0,
                staff_bottom_line_page=140.0, staff_spacing_px=sp,
                band_offset_spaces=2.0, in_hairpin_band=True)
    return g


def _decide(log):
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.DYNAMIC_ANCHOR, STAFF)


class TestTheDecision(unittest.TestCase):

    def test_the_bar_comes_from_the_note_not_from_the_cell_that_detected_the_box(self):
        """An `f` detected in cell 0 (the padded cell reaches it) but printed
        between the last note of bar 0 and the first of bar 1: the anchor is bar
        1's note and the verdict says cell 1."""
        log = Log()
        _head(log, 0, 0, 0, 100)
        first_of_next = _head(log, 0, 1, 0, 300)
        _letter(log, 0, 0, 5, "f", 200, 225)
        v = _decide(log)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        m = v.value[0]
        self.assertEqual(m["text"], "f")
        self.assertEqual(m["anchor"], first_of_next.to_key())
        self.assertEqual(m["anchor_cell"], 1)
        self.assertEqual(m["relation"], "next_onset")
        self.assertEqual(m["detected_in_cell"], 0)

    def test_a_mark_on_a_note_anchors_to_it(self):
        log = Log()
        _head(log, 0, 0, 0, 100)
        on = _head(log, 0, 0, 1, 200)
        _head(log, 0, 0, 2, 300)
        _letter(log, 0, 0, 5, "p", 202, 228)
        v = _decide(log)
        self.assertEqual(v.value[0]["anchor"], on.to_key())
        self.assertEqual(v.value[0]["relation"], "at_note")

    def test_a_note_another_staff_owns_is_not_an_anchor(self):
        """The nearest onset to the right belongs to the staff below; this
        staff's own next note is farther and is the anchor."""
        log = Log()
        _head(log, 1, 0, 0, 230)
        own = _head(log, 0, 0, 0, 300)
        _letter(log, 0, 0, 5, "f", 150, 175)
        v = _decide(log)
        self.assertEqual(v.value[0]["anchor"], own.to_key())

    def test_a_mark_with_nothing_after_it_is_counted_not_guessed(self):
        log = Log()
        _head(log, 0, 0, 0, 100)
        _letter(log, 0, 0, 5, "f", 400, 425)
        v = _decide(log)
        m = v.value[0]
        self.assertIsNone(m["anchor"])
        self.assertEqual(m["why"], "no_following_note_in_system")
        self.assertEqual(v.detail["marks_without_a_following_note"], 1)

    def test_a_chord_is_one_column(self):
        """Three heads of one chord at one x are one onset, so a mark between
        the chord before and it is not 'equally plausible' among them."""
        log = Log()
        _head(log, 0, 0, 0, 100)
        for gi, y in ((1, 100.0), (2, 90.0), (3, 80.0)):
            _head(log, 0, 0, gi, 300, y=y)
        _letter(log, 0, 0, 5, "p", 180, 200)
        v = _decide(log)
        self.assertIsNotNone(v.value[0]["anchor"])
        self.assertEqual(v.value[0]["n_heads_in_column"], 3)

    def test_the_two_halves_of_an_f_cut_by_the_barline_are_one_mark(self):
        """Litolff p2 staff 3: the `f` printed ON the barline is cut by it; the
        bar before detects a 12 px piece, the bar after a 27 px piece. Each cell
        spelled its own `f` -- two marks for one letter. RED before: two."""
        log = Log()
        _head(log, 0, 1, 0, 100)
        into = _head(log, 0, 2, 0, 830)
        _letter(log, 0, 1, 5, "f", 762, 774, sp=15.0)
        _letter(log, 0, 2, 5, "f", 774, 801, sp=15.0)
        v = _decide(log)
        self.assertEqual(len(v.value), 1)
        self.assertEqual(v.value[0]["anchor"], into.to_key())
        self.assertEqual(v.detail["letter_halves_joined_across_a_barline"], 1)

    def test_a_printed_ff_across_a_barline_stays_two_marks(self):
        """The control that can fail: two FULL letters either side of the
        barline are two letters -- their union is wider than any one letter."""
        log = Log()
        _head(log, 0, 1, 0, 100)
        _head(log, 0, 2, 0, 400)
        _letter(log, 0, 1, 5, "f", 750, 774, sp=15.0)       # 24 px
        _letter(log, 0, 2, 5, "f", 774, 798, sp=15.0)
        v = _decide(log)
        self.assertEqual(len(v.value), 2)

    def test_a_staff_with_no_dynamic_files_an_empty_list(self):
        log = Log()
        _head(log, 0, 0, 0, 100)
        log.abstain(R.cell(0, 0, 0, 0), Q.DYNAMIC_LETTER, reader=READERS.DETECTOR,
                    frame="cell:0", reason="no_glyph_of_this_kind")
        v = _decide(log)
        self.assertEqual(v.value, [])


if __name__ == "__main__":
    unittest.main()
