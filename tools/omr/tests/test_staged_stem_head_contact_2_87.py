"""ROADMAP 2.87, `OMR_STEM_FINDER=head_contact` -- STAGED ADJUDICATE.

CONVENTION (Sean 2026-10-11): *"All stems should be connected to a notehead"*, and
*"Maybe the needs to be connected to a notehead could be used to verify later in the
stages"* -- so GATHER keeps recording every stroke and a LATER stage asks. WHAT WOULD
FALSIFY IT: a real stem whose head the detector never boxed (the verdict would then
refuse a true stem to the consumers); measured on Sean's Brahms page 227 of the 229
strokes that match his stems touch a detected head within 0.3 spaces, the other two
are partial strokes that attach to no head anyway.

`Q.STEM_HEAD_CONTACT` is filed on the CELL (a `Q.STEM` row has no subject of its own):
its value is the list of `Q.STEM` row ids that touch no detected notehead; ABSTAINED
where the cell has no notehead box at all (heads unread: rule 8, nothing is refused).

RED first: against the tree before this commit `Q.STEM_HEAD_CONTACT` does not exist.
Every refusal has a positive control in the same class (a stem that DOES touch a head
is kept), and flag OFF is today's behaviour.
"""
from __future__ import annotations

import unittest

from tools.omr.line_detection import STEM_FINDER_ENV
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_family_refusals import CELL, _box, _page_box_at_step
from tools.omr.tests.test_staged_rest_placement_2_33 import _stem


CROP_H = 300.0           # the cell crop spans canonical y 0..300 (page y 1000..1300, up = 1)


def _crop(log):
    log.observe(CELL, Q.CELL_BOX, [0.0, 1000.0, 1000.0, 1000.0 + CROP_H],
                reader=READERS.GEOMETRY, frame="cell:0")


def _head(log, gi, x, y, w=20.0, h=16.0):
    """A notehead box carrying BOTH frames (page = canonical + (0, 1000)), so the
    cell's own frame, and with it the crop's edge, can be solved from it."""
    return _box(log, gi, "noteheadBlack", quantity=Q.NOTEHEAD_CLASS,
                x_c=x, y_c=y, w_c=w, h_c=h,
                page_box=[x, y + 1000.0, x + w, y + h + 1000.0])


def _stem_row(log, x, y, w=4.0, h=80.0):
    return log.observe(CELL, Q.STEM, (x, y, w, h), reader=READERS.CV_LINES,
                       frame="cell:0")


def _run(log, *quantities):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=tuple(quantities))
    return log


class TestTheVerdict(unittest.TestCase):

    def test_a_stem_on_a_head_meets_and_a_stem_on_none_meets_none(self):
        log = Log()
        _crop(log)
        _head(log, 0, 100, 100)
        on = _stem_row(log, 118, 40)                    # at the head's right edge
        off = _stem_row(log, 400, 40)                   # nowhere near any head
        _run(log, Q.STEM_HEAD_CONTACT)
        v = log.verdict(Q.STEM_HEAD_CONTACT, CELL)
        self.assertIs(v.outcome, Outcome.DECIDED, (v.reason, v.detail))
        self.assertEqual(list(v.value), [off.id])       # the control: the other is NOT listed
        self.assertIn(on.id, v.detail["meets"])

    def test_the_tolerance_is_a_named_width_and_a_wider_gap_fails(self):
        for gap, expect_none in ((3.0, False), (0.6 * 16.0, True)):
            log = Log()
            _crop(log)
            _head(log, 0, 100, 100)
            s = _stem_row(log, 120 + gap, 40)
            _run(log, Q.STEM_HEAD_CONTACT)
            v = log.verdict(Q.STEM_HEAD_CONTACT, CELL)
            self.assertEqual(s.id in list(v.value), expect_none, gap)

    def test_no_head_boxed_in_the_cell_is_an_abstention_not_a_refusal(self):
        log = Log()
        _crop(log)
        _stem_row(log, 118, 40)
        _run(log, Q.STEM_HEAD_CONTACT)
        v = log.verdict(Q.STEM_HEAD_CONTACT, CELL)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_heads_read")

    def test_a_unison_head_keeps_both_its_stems(self):
        """Sean 2026-10-11: two voices on one head -- an up stem at its right and a
        down stem at its left. Both touch the one head, so neither is refused."""
        log = Log()
        _crop(log)
        _head(log, 0, 100, 100)
        up = _stem_row(log, 118, 40, h=68)
        down = _stem_row(log, 100, 108, h=80)
        _run(log, Q.STEM_HEAD_CONTACT)
        v = log.verdict(Q.STEM_HEAD_CONTACT, CELL)
        self.assertEqual(list(v.value), [])
        self.assertEqual(set(v.detail["meets"]), {up.id, down.id})


class TestACutStemIsNotJudged(unittest.TestCase):
    """The cell is padded into the next staff, so a neighbour's beamed group arrives as
    stems running off the crop whose heads are in the OTHER cell. Brahms 317803 p1
    cell/1/0/10/0 (crop b_dur3): refusing four of them turned a beamed eighth into a
    quarter."""

    def test_a_stem_cut_by_the_crop_is_neither_met_nor_refused(self):
        log = Log()
        _crop(log)
        _head(log, 0, 100, 100)
        cut = _stem_row(log, 400, 200, h=100.0)          # runs 200..300, off the crop's bottom
        inside = _stem_row(log, 500, 120, h=80.0)        # 120..200, clear of both edges
        _run(log, Q.STEM_HEAD_CONTACT)
        v = log.verdict(Q.STEM_HEAD_CONTACT, CELL)
        self.assertEqual(list(v.value), [inside.id])     # the control: only the uncut one
        self.assertEqual(v.detail["cut_by_the_crop"], [cut.id])

    def test_no_frame_means_nothing_is_refused(self):
        log = Log()
        _box(log, 0, "noteheadBlack", quantity=Q.NOTEHEAD_CLASS, x_c=100, y_c=100,
             w_c=20, h_c=16)                             # no page frame, no CELL_BOX
        _stem_row(log, 400, 120, h=80.0)
        _run(log, Q.STEM_HEAD_CONTACT)
        v = log.verdict(Q.STEM_HEAD_CONTACT, CELL)
        self.assertEqual(list(v.value), [])
        self.assertFalse(v.detail["crop_bounds_known"])


class TestConsumer(unittest.TestCase):
    """`rest_has_a_stem` (family_precision): a stem that touches no head is not a stem
    the rest can be refused for. A whole rest's default box is (200, 200, 140, 20)."""

    def _world(self, with_head):
        log = Log()
        _crop(log)
        # a head IS read in this cell either way (else the verdict abstains and
        # nothing is refused); it touches the stem only in the control. It goes in
        # FIRST so the cell's frame is solved from its page box.
        _head(log, 2, 240.0 if with_head else 600.0, 284.0 if with_head else 40.0)
        g = _box(log, 0, "restWhole", quantity=Q.REST,
                 page_box=_page_box_at_step(4.0))
        _stem(log, 1, x=250.0, y=190.0, w=5.0, h=100.0)
        return log, g

    def _reason(self, with_head):
        log, g = self._world(with_head)
        _run(log, Q.STEM_HEAD_CONTACT, Q.REST_IS_NOT_A_REST)
        return log.verdict(Q.REST_IS_NOT_A_REST, g).reason

    def test_off_is_today(self, ):
        import os
        os.environ[STEM_FINDER_ENV] = ""
        # head_contact unset: the stem refuses the rest, whether or not a head touches it
        self.assertEqual(self._reason(False), "rest_has_a_stem")
        self.assertEqual(self._reason(True), "rest_has_a_stem")

    def test_on_where_no_head_is_read_at_all_the_rest_is_still_refused(self):
        """Rule 8: heads unread says nothing about the stroke."""
        import os
        os.environ[STEM_FINDER_ENV] = "head_contact"
        try:
            log = Log()
            _crop(log)
            g = _box(log, 0, "restWhole", quantity=Q.REST,
                     page_box=_page_box_at_step(4.0))
            _stem(log, 1, x=250.0, y=190.0, w=5.0, h=100.0)
            _run(log, Q.STEM_HEAD_CONTACT, Q.REST_IS_NOT_A_REST)
            self.assertEqual(log.verdict(Q.REST_IS_NOT_A_REST, g).reason,
                             "rest_has_a_stem")
        finally:
            os.environ[STEM_FINDER_ENV] = ""

    def test_on_a_stem_with_no_head_no_longer_refuses_the_rest(self):
        import os
        os.environ[STEM_FINDER_ENV] = "head_contact"
        try:
            self.assertNotEqual(self._reason(False), "rest_has_a_stem")
            # the positive control in the same class: a stem on a head still refuses
            self.assertEqual(self._reason(True), "rest_has_a_stem")
        finally:
            os.environ[STEM_FINDER_ENV] = ""


if __name__ == "__main__":
    unittest.main()
