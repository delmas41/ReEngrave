"""ROADMAP 2.80 -- a bar short by a MISSED REST is not a note one beam short.

`reconcile_duration` lands a short bar by lengthening ONE note where exactly
one re-reading fits. A rest the detector never boxed makes a bar short in the
same way, and the "fix" writes the wrong music that the bar-sum control cannot
see (Brahms 1/i Breitkopf Contrabass bar 13: an eighth stretched to a quarter;
the print has a second eighth rest the detector boxed as a narrow notehead
and ADJUDICATE refused). The re-reading now stands only where the bar's
staff-sized ink (`Q.CELL_INK_PIECES`) is wholly explained by standing glyphs.

Tests named `*_RED` fail on the tree without the witness. The positive
controls (a bar whose ink is explained still lands; a bar too LONG still
lands, because a missed rest cannot overfill a bar) pass on both sides.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import consequences
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict

CELL = R.cell(0, 0, 1, 3)
SPACE = 20.0          # page px per staff space in these fixtures


import pytest as _pytest_2_162


@_pytest_2_162.fixture(autouse=True)
def _bar_may_move_decided_notes_2_162(monkeypatch):
    """ROADMAP 2.162 landed ON: the bar never moves a DECIDED note. This file pins the older bar-move behaviour."""
    monkeypatch.setenv("OMR_NARROWED_BAR_LENGTH_UNKNOWN", "0")


def _v(log, sub, q, outcome, value, reason="t", detail=None):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome,
        value=value, decider="test", reason=reason, detail=detail or {}))


def _dur(beats, levels):
    return {"beats": beats, "written": beats, "dots": 0,
            "beam_levels": levels}


def _note(log, g, beats, levels=0):
    sub = R.glyph(0, 0, 1, 3, g)
    _v(log, sub, Q.DURATION, Outcome.DECIDED, _dur(beats, levels),
       reason="head_and_marks")
    return sub


def _events(log, n):
    _v(log, CELL, Q.EVENT, Outcome.DECIDED,
       {"events": [{"glyphs": [g]} for g in range(n)]})


def _meter(log, num=2, den=4):
    return _v(log, R.system(0, 0), Q.METER, Outcome.DECIDED,
              {"numerator": num, "denominator": den, "raw": f"{num}/{den}"})


def ink(log, *pieces, cell=CELL):
    """File `Q.CELL_INK_PIECES` for a cell: each piece `(x0, y0, x1, y1)` in
    page px (20 px to the space)."""
    log.observe(cell, Q.CELL_INK_PIECES, len(pieces),
                reader=READERS.CV_INK_PIECES, frame="cell",
                pieces=[[*p, 0.5] for p in pieces],
                cell_staff_space_px=SPACE * 3.0, staff_space_page_px=SPACE)


def clear_ink(log, cell=CELL):
    """The bar was READ and holds no ink nobody explains."""
    ink(log, cell=cell)


def box(log, g, x0, y0, x1, y1, name="rest8th"):
    sub = R.glyph(0, 0, 1, 3, g)
    log.observe(sub, Q.GLYPH_BOX, [name, 0, 0, 0, 0],
                reader=READERS.DETECTOR, frame="cell",
                bbox_page_px=[x0, y0, x1, y1])
    return sub


def _fire(log, meter):
    return consequences.reconcile_duration(log, CELL, meter)


def _short_bar(log):
    """1.0 + 0.5 (an eighth) in 2/4: short by an eighth. ONE landing: the
    eighth one beam shorter-flagged, i.e. a quarter."""
    _note(log, 0, 1.0)
    e = _note(log, 1, 0.5, levels=1)
    _events(log, 2)
    return e


class TestTheWitness(unittest.TestCase):

    def test_ink_nobody_explains_refuses_the_lengthening_RED(self):
        """The Contrabass-13 shape: a piece of ink in the bar that no
        standing glyph covers -- the rest explanation is not refuted."""
        log = Log()
        e = _short_bar(log)
        ink(log, (400, 100, 414, 140))                 # 0.7 x 2.0 spaces
        self.assertEqual(_fire(log, _meter(log)), [])
        self.assertEqual(log.verdict(Q.DURATION, e).value["beats"], 0.5)

    def test_a_box_DECIDED_not_a_notehead_does_not_explain_its_ink_RED(self):
        """The narrow 'notehead' over the second eighth rest (refused
        `too_narrow`) is exactly the ink that is NOT explained."""
        log = Log()
        e = _short_bar(log)
        g = box(log, 5, 395, 95, 420, 145, name="noteheadBlackInSpace")
        _v(log, g, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Outcome.DECIDED, True,
           reason="too_narrow")
        ink(log, (400, 100, 414, 140))
        self.assertEqual(_fire(log, _meter(log)), [])
        self.assertEqual(log.verdict(Q.DURATION, e).value["beats"], 0.5)

    def test_a_bar_with_no_ink_reading_is_refused_RED(self):
        """Rule 8: 'unread' is not 'clear'."""
        log = Log()
        e = _short_bar(log)
        self.assertEqual(_fire(log, _meter(log)), [])
        self.assertEqual(log.verdict(Q.DURATION, e).value["beats"], 0.5)

    # ── positive controls: the re-reading is still right where it is ─────
    def test_a_bar_whose_ink_is_explained_still_lands(self):
        log = Log()
        e = _short_bar(log)
        box(log, 5, 395, 95, 420, 145)                 # a kept rest box
        ink(log, (400, 100, 414, 140))
        out = _fire(log, _meter(log))
        self.assertEqual(len(out), 1)
        now = log.verdict(Q.DURATION, e)
        self.assertEqual(now.value["beats"], 1.0)
        self.assertTrue(now.detail.get("missed_rest_refuted_by_ink"))

    def test_a_bar_with_only_a_stem_or_crumb_left_still_lands(self):
        log = Log()
        e = _short_bar(log)
        ink(log, (400, 100, 404, 180))                 # 0.2 sp wide: a stem
        self.assertEqual(len(_fire(log, _meter(log))), 1)
        self.assertEqual(log.verdict(Q.DURATION, e).value["beats"], 1.0)

    def test_a_clear_bar_lands(self):
        log = Log()
        e = _short_bar(log)
        clear_ink(log)
        self.assertEqual(len(_fire(log, _meter(log))), 1)
        self.assertEqual(log.verdict(Q.DURATION, e).value["beats"], 1.0)

    def test_a_box_DECIDED_a_whole_rest_explains_its_ink(self):
        log = Log()
        _short_bar(log)
        g = box(log, 5, 395, 95, 420, 145, name="noteheadBlackInSpace")
        _v(log, g, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Outcome.DECIDED, True,
           reason="ink_is_a_whole_rest")
        _v(log, g, Q.NOTEHEAD_IS_A_WHOLE_REST, Outcome.DECIDED, True,
           reason="shape_and_position_agree")
        ink(log, (400, 100, 414, 140))
        self.assertEqual(len(_fire(log, _meter(log))), 1)

    def test_a_SHORTENING_needs_no_witness(self):
        """A missed rest cannot make a bar too long. 1.0 + 2.0 in 2/4 is a
        beat over and the only landing is the half note read one level
        shorter -- it lands with ink unexplained AND no reading at all."""
        log = Log()
        _note(log, 0, 1.0)
        e = _note(log, 1, 2.0)
        _events(log, 2)
        ink(log, (400, 100, 414, 140))
        out = _fire(log, _meter(log))
        self.assertEqual(len(out), 1)
        self.assertEqual(log.verdict(Q.DURATION, e).value["beats"], 1.0)
        log2 = Log()
        _note(log2, 0, 1.0)
        e2 = _note(log2, 1, 2.0)
        _events(log2, 2)                      # no ink row at all
        self.assertEqual(len(_fire(log2, _meter(log2))), 1)


if __name__ == "__main__":
    unittest.main()
