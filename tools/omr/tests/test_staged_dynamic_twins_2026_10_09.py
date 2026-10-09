"""ROADMAP 2.68 (Sean, 2026-10-09): *"Across an entire score many dynamic
markings could ... get double boxed. I saw a lot of double boxing when I was
hand-labelling a dynamic F."* ONE PRINTED LETTER BOXED TWICE IS ONE LETTER.

The same principle as `rest_is_a_duplicate_box` and `gather._same_ink_boxes`:
one ink, one mark. Two dynamic-letter boxes overlapping by at least half of the
smaller one are the SAME ink; two letters printed side by side (`ff`, `fp`,
`sf`) are DISTINCT ink and stay a run -- that is the control beside every case
here.

Which letter the ink is comes from evidence, in this order: every box agrees
-> that letter; they disagree -> the ink's own HEIGHT in staff spaces (an `f`
rises above the x-height and falls below it, a `p` only falls: measured on
Sean's 12 hand-labelled `f` boxes, Brahms 317803 pdf 0, 2.4 to 2.6 spaces; a
`p` 1.4 to 2.1); height between the two bands, or none measured -> the letter
is PRESENT and its identity ABSTAINS (rule 8). The detector's own score is NOT
evidence for the identity: on Brahms p1 it ranks the `f` twin above the
printed `p` on 5 of the 12 same-ink pairs.
"""
from __future__ import annotations

import unittest

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

CELL = R.cell(0, 0, 0, 0)


def _letter(log, gi, letter, x0, x1, *, score=0.8, ink_h=None, cell=0,
            y0=100.0, y1=125.0, sp=10.0):
    extra = {} if ink_h is None else {"ink_height_spaces": ink_h}
    return log.observe(
        R.glyph(0, 0, 0, cell, gi), Q.DYNAMIC_LETTER, "dynamic" + letter.upper(),
        reader=READERS.DETECTOR, frame=G.FRAME_PAGE, score=score,
        letter=letter, cell_frame="cell:%d" % cell,
        bbox_page_px=[x0, y0, x1, y1],
        x_center_page=(x0 + x1) / 2.0, y_center_page=(y0 + y1) / 2.0,
        staff_bottom_line_page=90.0, staff_spacing_px=sp,
        band_offset_spaces=1.0, in_hairpin_band=True, **extra)


def _run(log):
    log.freeze()
    adjudicate.run(log)
    return log


class TestOneInkIsOneLetter(unittest.TestCase):

    def test_one_p_boxed_as_p_and_as_f_is_one_letter_not_fp(self):
        """Brahms p1 `cell/1/0/9/1`: the printed `p` carries a `dynamicP` and a
        `dynamicF` box on the same ink (the `f` twin scores LOWER there but is
        higher on 5 of 12 pairs, so the score cannot decide). The ink is 1.9
        spaces tall -- a `p`. RED before: the run spelled `fp`."""
        log = Log()
        _letter(log, 0, "p", 100, 125, score=0.74, ink_h=1.9)
        _letter(log, 1, "f", 100, 124, score=0.56, ink_h=1.9)
        _run(log)
        v = log.verdict(Q.DYNAMIC, CELL)
        self.assertEqual(v.value, ["p"])
        self.assertEqual(v.detail["letters_same_ink_collapsed"], 1)

    def test_the_f_twin_scoring_higher_does_not_make_a_p_an_f(self):
        """The same ink, the detector ranking the WRONG class first (Brahms p1
        tiles 6 and 7: `f` 0.83 over the printed `p`). Ink height decides."""
        log = Log()
        _letter(log, 0, "f", 100, 125, score=0.83, ink_h=1.85)
        _letter(log, 1, "p", 100, 125, score=0.50, ink_h=1.85)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL).value, ["p"])

    def test_one_f_boxed_as_f_and_as_p_is_an_f_when_the_ink_is_tall(self):
        """The positive control the other way: a tall ink is an `f` whichever
        box the detector ranked first."""
        log = Log()
        _letter(log, 0, "p", 100, 125, score=0.9, ink_h=2.6)
        _letter(log, 1, "f", 100, 125, score=0.4, ink_h=2.6)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL).value, ["f"])

    def test_height_between_the_bands_abstains_the_identity_not_the_letter(self):
        """Rule 8. 2.25 spaces is neither a `p` (<= 2.1) nor an `f` (>= 2.4):
        the letter is PRESENT, its identity is not read, and nothing is guessed
        -- not `fp`, not either letter. The decision narrows to what the
        lexicon still allows."""
        log = Log()
        _letter(log, 0, "p", 100, 125, score=0.9, ink_h=2.25)
        _letter(log, 1, "f", 100, 125, score=0.4, ink_h=2.25)
        _run(log)
        v = log.verdict(Q.DYNAMIC, CELL)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        got = {c.value for c in v.candidates}
        self.assertEqual(got, {"f", "p"})
        self.assertNotIn("fp", got)

    def test_no_ink_measure_and_disagreeing_boxes_abstains_the_identity(self):
        """An older record has no `ink_height_spaces`; the detector's score is
        not a witness (it is wrong on 5 of 12), so the identity abstains."""
        log = Log()
        _letter(log, 0, "p", 100, 125, score=0.9)
        _letter(log, 1, "f", 100, 125, score=0.4)
        _run(log)
        v = log.verdict(Q.DYNAMIC, CELL)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual({c.value for c in v.candidates}, {"f", "p"})

    def test_one_f_boxed_three_times_as_f_is_one_f(self):
        """Brahms p0 tile 40: `ff` for one printed `f` (two same-class boxes,
        the second the lower half of the first). RED before: `ff`."""
        log = Log()
        _letter(log, 0, "f", 2091, 2112, y0=6129, y1=6278, sp=32.0)
        _letter(log, 1, "f", 2091, 2112, y0=6156, y1=6258, sp=32.0)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL).value, ["f"])

    def test_three_p_boxes_on_one_ink_are_one_p(self):
        """Litolff-shaped: three overlapping `p` boxes (the second and third
        parts of the first). RED before: `ppp`, a real dynamic that is not
        there."""
        log = Log()
        _letter(log, 0, "p", 3147, 3195, y0=684, y1=737, sp=20.0)
        _letter(log, 1, "p", 3147, 3177, y0=684, y1=737, sp=20.0)
        _letter(log, 2, "p", 3149, 3195, y0=685, y1=721, sp=20.0)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL).value, ["p"])

    def test_the_s_of_a_printed_sf_tucked_inside_the_f_box_is_still_a_letter(self):
        """THE CONTROL THAT CAN FAIL. Litolff p2: a 14 x 26 px `dynamicS` box
        lies wholly inside the 42 x 48 px `f` box -- by the half-of-the-smaller
        rule that is 'the same ink', and a first version of this lane collapsed
        37 printed `sf` to `f` on it. On the print (`out/print/2.68-dynamic-twins`)
        the `s` is a SEPARATE letter tucked under the `f`'s hook. Boxes of
        different classes are one ink only where they are comparable boxes."""
        log = Log()
        _letter(log, 0, "f", 1375, 1417, y0=2337, y1=2385, score=0.82, ink_h=2.7, sp=15.0)
        _letter(log, 1, "s", 1373, 1387, y0=2354, y1=2380, score=0.66, ink_h=2.7, sp=15.0)
        _run(log)
        v = log.verdict(Q.DYNAMIC, CELL)
        self.assertEqual(v.value, ["sf"])
        self.assertEqual(v.detail["letters_same_ink_collapsed"], 0)

    def test_twins_do_not_chain_an_s_into_an_f_through_a_big_s_box(self):
        """Litolff p2 sf (11 came out `f`): the small `s` box is a twin of a
        BIG `s` box (the same ink boxed larger, on the staff beneath), and the
        big `s` box is comparable to the `f`'s -- so s~s' and s'~f chained the
        printed `s` into the `f`. A group is a clique: every member is the same
        ink as every other. RED against the chained groups."""
        log = Log()
        _letter(log, 0, "s", 1373, 1387, y0=2354, y1=2380, score=0.66, ink_h=2.7, sp=15.0)
        _letter(log, 1, "s", 1376, 1416, y0=2338, y1=2384, score=0.30, ink_h=2.7, sp=15.0)
        _letter(log, 2, "f", 1375, 1417, y0=2337, y1=2385, score=0.82, ink_h=2.7, sp=15.0)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL).value, ["sf"])

    def test_an_s_box_the_size_of_the_f_box_is_the_same_ink(self):
        """The positive control the other way: an `s` box that covers the whole
        letter (0.95 of the larger, a real pair on Litolff) is one ink, and a
        2.7-space ink is an `f`."""
        log = Log()
        _letter(log, 0, "f", 1375, 1417, y0=2337, y1=2385, score=0.82, ink_h=2.7, sp=15.0)
        _letter(log, 1, "s", 1376, 1416, y0=2338, y1=2384, score=0.30, ink_h=2.7, sp=15.0)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL).value, ["f"])

    # -- the controls: distinct ink side by side stays a run ----------------

    def test_ff_two_letters_side_by_side_stay_ff(self):
        """Two `f` boxes of two printed letters, clear of each other."""
        log = Log()
        _letter(log, 0, "f", 100, 124, ink_h=2.5)
        _letter(log, 1, "f", 130, 154, ink_h=2.5)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL).value, ["ff"])

    def test_the_interlocked_ff_of_litolff_stays_ff(self):
        """THE CONTROL THAT CAN FAIL (Sean, Litolff p2 tile 2: `ff`). The two
        `f` of the printed `ff` are interlocked and their boxes overlap by HALF
        the smaller (41 x 48 px at [898, 915] and 39 x 48 at [915, 954], staff
        spacing 15). By the overlap rule alone they are 'the same ink', and a
        first version of this lane collapsed 43 Litolff `ff` to `f`. What tells
        them apart is how much ink the pair can HOLD: the union is 3.7 spaces
        wide and no one letter is wider than 2.9."""
        log = Log()
        _letter(log, 0, "f", 898, 939, y0=2991, y1=3039, ink_h=3.2, sp=15.0)
        _letter(log, 1, "f", 915, 954, y0=2992, y1=3040, ink_h=3.2, sp=15.0)
        _run(log)
        v = log.verdict(Q.DYNAMIC, CELL)
        self.assertEqual(v.value, ["ff"])
        self.assertEqual(v.detail["letters_same_ink_collapsed"], 0)

    def test_an_f_boxed_twice_at_one_x_is_one_f_but_a_sliver_is_nobodys_twin(self):
        """A box split in two vertically (one `f`, the same x) is one letter. A
        3 px sliver of a box (under 0.8 spaces tall) is nobody's twin: it is
        not a letter at all and is left to the rest of the chain."""
        log = Log()
        _letter(log, 0, "f", 100, 122, y0=100, y1=148, ink_h=2.5)
        _letter(log, 1, "f", 100, 122, y0=100, y1=124, ink_h=2.5)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL).value, ["f"])

    def test_fp_side_by_side_stays_fp(self):
        log = Log()
        _letter(log, 0, "f", 100, 124, ink_h=2.5)
        _letter(log, 1, "p", 122, 146, ink_h=1.9)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL).value, ["fp"])

    def test_sf_side_by_side_stays_sf(self):
        log = Log()
        _letter(log, 0, "s", 100, 114, y0=110, y1=125)
        _letter(log, 1, "f", 116, 140, ink_h=2.5)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL).value, ["sf"])

    def test_two_agreeing_boxes_need_no_ink_measure(self):
        """No shape evidence is asked where nothing disagrees."""
        log = Log()
        _letter(log, 0, "f", 100, 125)
        _letter(log, 1, "f", 101, 124)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL).value, ["f"])

    def test_a_lexicon_can_settle_what_the_ink_cannot(self):
        """`s` then a twin {f, p} slot whose identity abstains: `sf` is a
        dynamic and `sp` is not, so the run spells `sf` -- deduced from the
        lexicon, labelled as such, and `fp`'s twin ambiguity is still never
        guessed alone."""
        log = Log()
        _letter(log, 0, "s", 100, 114, y0=110, y1=125)
        _letter(log, 1, "f", 116, 140, score=0.5)
        _letter(log, 2, "p", 116, 140, score=0.5)
        _run(log)
        v = log.verdict(Q.DYNAMIC, CELL)
        self.assertEqual(v.value, ["sf"])
        self.assertEqual(v.detail["words"][0]["identity"], "lexicon")


class TestTheInkMeasure(unittest.TestCase):
    """GATHER's `letter_ink_extent`: the tallest piece of ink inside a box, in
    staff spaces, with staff lines and barlines taken out."""

    SP = 10.0

    def _page(self):
        return np.zeros((200, 200), np.uint8)

    def test_a_tall_glyph_reads_tall_and_a_short_one_short(self):
        page = self._page()
        page[60:86, 100:104] = 255      # an f-ish stroke, 2.6 spaces
        page[100:119, 100:104] = 255    # a p-ish stroke, 1.9 spaces
        tall = G.letter_ink_extent(page, (95, 55, 110, 90), self.SP)
        short = G.letter_ink_extent(page, (95, 95, 110, 125), self.SP)
        self.assertAlmostEqual(tall["height_spaces"], 2.6, delta=0.15)
        self.assertAlmostEqual(short["height_spaces"], 1.9, delta=0.15)

    def test_a_staff_line_through_the_box_is_not_part_of_the_letter(self):
        page = self._page()
        page[70:90, 100:104] = 255      # a 2.0-space stroke
        page[80:82, 20:180] = 255       # a staff line across it
        got = G.letter_ink_extent(page, (95, 60, 110, 100), self.SP)
        self.assertAlmostEqual(got["height_spaces"], 2.0, delta=0.25)

    def test_a_box_holding_only_a_staff_line_measures_nothing(self):
        """The control that can fail: no letter ink, only a line."""
        page = self._page()
        page[80:82, 20:180] = 255
        self.assertIsNone(G.letter_ink_extent(page, (95, 60, 110, 100), self.SP))


if __name__ == "__main__":
    unittest.main()
