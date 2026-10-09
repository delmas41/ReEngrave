"""A notehead box lying ON a detected dynamic letter's box is that letter's
ink, not a note (Sean 2026-10-09, `out/print/2.73-review` tile 10: *"Not a
note - dynamic p"*). STAGED, ADJUDICATE: `notehead_precision.
_on_a_dynamic_letter_refusal`, reason `on_a_dynamic_letter`.

The measured shape (Litolff Beethoven 5, pdf page 3 `glyph/2/0/2/1/12`): the
bowl of a printed `p` (of `p cresc.`) boxed as `noteheadBlackInSpace`; the
detector's OWN `dynamicP` box for that `p` sits in the NEXT staff's cell
(`glyph/2/0/3/1/6`), so the letter search reads the adjacent staves' same-index
cells, not only the head's own.

RED FIRST: against the tree before `_on_a_dynamic_letter_refusal` existed
every refusal test below decided `value=False, reason="notehead"`; the
controls passed (as they must on a tree that refuses nothing), which is why
each control sits beside a positive test of the SAME class and geometry.

THE CONTROLS THAT CAN FAIL: a head merely beside/touching a letter stays; a
head ON a letter box that carries a real note's stem (>= 3 staff spaces; a
letter's own stroke is shorter) stays; a head inside a letter box that is not
letter-sized (it holds other ink) stays.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_notehead_precision import (
    CELL, SPACING, _cell_geometry, _verdict)

#: page px per canonical px: SPACING (100 canonical) = 15.75 page px, the
#: Litolff staff space at 600 dpi.
S = 0.1575
SP_PAGE = SPACING * S


def _head(log, gi, page_box, *, cls="noteheadBlackInSpace", conf=0.36):
    """A notehead whose canonical box is its page box rescaled by 1/S (x,y are
    the top-left corner, as every `Q.GLYPH_BOX` is)."""
    x0, y0, x1, y1 = page_box
    g = R.glyph(CELL.page, CELL.system, CELL.staff, CELL.cell, gi)
    xc, yc = (x0 - 500.0) / S, (y0 - 1000.0) / S
    wc, hc = (x1 - x0) / S, (y1 - y0) / S
    log.observe(g, Q.GLYPH_BOX, (cls, xc, yc, wc, hc),
                reader=READERS.DETECTOR, frame="cell:0", score=conf,
                category="notehead", bbox_page_px=list(page_box))
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR,
                frame="cell:0", score=conf)
    log.observe(g, Q.GLYPH_CONF, conf, reader=READERS.DETECTOR,
                frame="cell:0", score=conf)
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 4.0, reader=READERS.GEOMETRY,
                frame="cell:0")
    return g


def _letter(log, gi, page_box, *, staff=0, cls="dynamicP", with_box=True):
    g = R.glyph(CELL.page, CELL.system, staff, CELL.cell, gi)
    kw = {"bbox_page_px": list(page_box)} if with_box else {}
    log.observe(g, Q.DYNAMIC_LETTER, cls, reader=READERS.DETECTOR,
                frame="page", score=0.59, **kw)
    return g


def _stem(log, page_box):
    """A CV stem row in the head's cell, canonical `[x, y, w, h]`."""
    x0, y0, x1, y1 = page_box
    log.observe(CELL, Q.STEM, [(x0 - 500.0) / S, (y0 - 1000.0) / S,
                               (x1 - x0) / S, (y1 - y0) / S],
                reader=READERS.CV_LINES, frame="cell:0")


def _run(log):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    return log


# tile 10's own numbers (page px), shifted into the fixture cell
HEAD = [650.08, 1068.17, 668.98, 1095.10]          # 1.2 x 1.7 spaces
LETTER = [635.59, 1075.08, 664.72, 1106.10]         # 1.85 x 1.97 spaces


class TestAHeadOnALetterIsTheLettersInk(unittest.TestCase):

    def test_the_geometry_is_the_measured_one(self):
        """The fixture is tile 10's, not a convenient one."""
        ix = min(HEAD[2], LETTER[2]) - max(HEAD[0], LETTER[0])
        iy = min(HEAD[3], LETTER[3]) - max(HEAD[1], LETTER[1])
        frac = ix * iy / ((HEAD[2] - HEAD[0]) * (HEAD[3] - HEAD[1]))
        self.assertAlmostEqual(frac, 0.58, delta=0.02)

    def test_a_head_on_the_letter_of_its_own_cell_is_refused(self):
        log = Log()
        _cell_geometry(log)
        h = _head(log, 0, HEAD)
        L = _letter(log, 1, LETTER, staff=0)
        v = _verdict(_run(log), h)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "on_a_dynamic_letter")
        self.assertEqual(v.detail.get("dynamic_letter"), L.to_key())

    def test_a_head_on_the_letter_filed_in_the_next_staffs_cell_is_refused(self):
        """Tile 10 exactly: the detector filed the `p` under the staff BELOW
        (`glyph/2/0/3/1/6`), the head under the one above."""
        for staff in (1,):
            log = Log()
            _cell_geometry(log)
            h = _head(log, 0, HEAD)
            _letter(log, 1, LETTER, staff=staff)
            v = _verdict(_run(log), h)
            self.assertIs(v.value, True)
            self.assertEqual(v.reason, "on_a_dynamic_letter")

    def test_the_letters_own_short_stroke_is_not_a_stem(self):
        """The `p`'s descender and an `f`'s stem read as CV stems 2.2-2.5
        spaces long on Litolff; that is the letter, not a note's stem."""
        log = Log()
        _cell_geometry(log)
        h = _head(log, 0, HEAD)
        _letter(log, 1, LETTER)
        _stem(log, [HEAD[0] - 3.0, HEAD[1], HEAD[0] + 1.0,
                    HEAD[1] + 2.4 * SP_PAGE])
        v = _verdict(_run(log), h)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "on_a_dynamic_letter")


class TestControlsThatCanFail(unittest.TestCase):

    def test_a_head_beside_a_letter_stays(self):
        log = Log()
        _cell_geometry(log)
        h = _head(log, 0, [LETTER[2] + 4.0, HEAD[1], LETTER[2] + 4.0 + 18.9,
                           HEAD[3]])
        _letter(log, 1, LETTER)
        v = _verdict(_run(log), h)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")

    def test_a_head_touching_a_letter_stays(self):
        """Sean: a head that touches a dynamic letter is a note. Overlap, not
        contact, is the test: here 3 px of 19 (about 10 percent of the head)."""
        log = Log()
        _cell_geometry(log)
        h = _head(log, 0, [LETTER[2] - 2.0, HEAD[1], LETTER[2] - 2.0 + 18.9,
                           HEAD[3]])
        _letter(log, 1, LETTER)
        v = _verdict(_run(log), h)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")

    def test_a_head_on_a_letter_with_a_real_stem_stays(self):
        """Litolff `glyph/2/1/8/6/7`: a beamed head under an `sf`, its stem
        7 spaces long."""
        log = Log()
        _cell_geometry(log)
        h = _head(log, 0, HEAD)
        _letter(log, 1, LETTER)
        _stem(log, [HEAD[2] - 2.0, HEAD[1] - 6.0 * SP_PAGE, HEAD[2] + 2.0,
                    HEAD[3]])
        v = _verdict(_run(log), h)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")
        self.assertTrue(v.detail.get("dynamic_letter_signal"),
                        "the overlap stays on the record where it spares")

    def test_a_head_inside_a_box_that_is_not_letter_sized_stays(self):
        """Litolff `glyph/2/1/9/10/1`: the `dynamicF` box is 6 spaces tall (an
        `f` plus the note under it); lying in it says nothing about the head."""
        log = Log()
        _cell_geometry(log)
        h = _head(log, 0, HEAD)
        _letter(log, 1, [LETTER[0], HEAD[1] - 2.0 * SP_PAGE, LETTER[2] + 10.0,
                         HEAD[1] + 4.0 * SP_PAGE])
        v = _verdict(_run(log), h)
        self.assertIs(v.value, False)

    def test_an_f_box_narrower_than_any_f_spares_the_head(self):
        """Brahms `glyph/1/0/7/0/13`: a beam's tail boxed `dynamicF`, 1.49
        spaces wide, over a real head. Positive control in the SAME geometry:
        the same box as a `dynamicP` (a `p` is legitimately that narrow)
        refuses."""
        narrow = [HEAD[0] - 2.0, HEAD[1] - 2.0, HEAD[0] - 2.0 + 1.49 * SP_PAGE,
                  HEAD[3] + 2.0]
        log = Log()
        _cell_geometry(log)
        h = _head(log, 0, HEAD)
        _letter(log, 1, narrow, cls="dynamicF")
        v = _verdict(_run(log), h)
        self.assertIs(v.value, False)
        self.assertEqual(
            v.detail["dynamic_letter_signal"]["spared"],
            "letter_box_too_narrow_for_an_f")
        log = Log()
        _cell_geometry(log)
        h = _head(log, 0, HEAD)
        _letter(log, 1, narrow, cls="dynamicP")
        v = _verdict(_run(log), h)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "on_a_dynamic_letter")

    def test_a_letter_with_no_page_box_decides_nothing(self):
        log = Log()
        _cell_geometry(log)
        h = _head(log, 0, HEAD)
        _letter(log, 1, LETTER, with_box=False)
        v = _verdict(_run(log), h)
        self.assertIs(v.value, False)

    def test_a_head_with_no_letter_anywhere_is_unchanged(self):
        log = Log()
        _cell_geometry(log)
        h = _head(log, 0, HEAD)
        v = _verdict(_run(log), h)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")

    def test_the_reason_is_declared(self):
        self.assertIn("on_a_dynamic_letter", adjudicate.REGISTRY[
            Q.NOTEHEAD_IS_NOT_A_NOTEHEAD].reasons)


if __name__ == "__main__":
    unittest.main()
