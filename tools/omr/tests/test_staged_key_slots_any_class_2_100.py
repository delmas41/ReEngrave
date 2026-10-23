"""ROADMAP 2.100, Sean's answers on the first tiles (2026-10-12): *"Three and
thirteen are time signatures. All the rest are key accidentals."*

* tiles 1 6 7 8 9 11 -- a `flag8thUp`, `timeSig2`/`timeSig4`/`timeSig1` and an
  `arpeggiato` standing in the key slots are KEY ACCIDENTALS: refused as what
  the detector called them; a `timeSig` in its own staff's key slots is no
  meter statement.
* tiles 3 and 13 -- a `rest8th` on the 8 of a 6/8 and a `restQuarter` on a
  whole 2/4 stack are TIME SIGNATURES: refused as rests.

⚠️ RUN RED FIRST against 88619a03: the flag / arpeggiato / tie verdicts read
`value=False`, the rest in the meter column read `reason="rest"`, and the meter
rows were all kept. Every refusal has a positive control in the same class: a
flag after the key stays a flag, a rest AFTER the time signature stays a rest,
a time signature after the key stays a meter statement.

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import key_slots as K
from tools.omr.staged.record import Log, Q, READERS

SPACE = 89.75
CLEF = ("clefG", 243, 402, 267, 641)
FLATS = [("keyFlat", 541, 590, 105, 270), ("keyFlat", 650, 540, 105, 270)]


def _staff(log, staff, boxes, *, page_x0=700.0):
    """One header cell, every box filed as GATHER files it, with the page box
    (1 canonical px = 1/5.79 page px, as on Litolff)."""
    log.observe(R.cell(1, 0, staff, 0), Q.CELL_STAFF_SPACE, SPACE,
                reader=READERS.GEOMETRY, frame="cell:0")
    out = []
    for gi, box in enumerate(boxes):
        g = R.glyph(1, 0, staff, 0, gi)
        k = 15.5 / SPACE
        page = [page_x0 + box[1] * k, 1100.0 + staff * 200 + box[2] * k,
                page_x0 + (box[1] + box[3]) * k,
                1100.0 + staff * 200 + (box[2] + box[4]) * k]
        log.observe(g, Q.GLYPH_BOX, tuple(box), reader=READERS.DETECTOR,
                    frame="cell:0", score=0.5, category="x",
                    bbox_page_px=page)
        cls = box[0]
        if cls.startswith("rest"):
            log.observe(g, Q.REST, cls, reader=READERS.DETECTOR,
                        frame="cell:0", score=0.5, category="rest")
        if cls.startswith("flag"):
            log.observe(g, Q.FLAG, cls, reader=READERS.DETECTOR,
                        frame="cell:0", score=0.5, category="flag")
        out.append(g)
    return out


def _run(log, *qs):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=tuple(qs))


_PIN = mock.patch.dict(os.environ, {"OMR_KEY_SIGNATURE_CLAIM": "0"})


def setUpModule():
    # pinned OFF: this file tests the five `in_a_key_signature_slot` gates, which the 2.183 key claim (default ON, Sean 2026-10-23) subsumes
    _PIN.start()


def tearDownModule():
    _PIN.stop()


class TestAnyClassInTheKeySlots(unittest.TestCase):

    def test_a_flag_in_the_key_slots_is_refused(self):
        log = Log()
        g = _staff(log, 0, [CLEF, *FLATS, ("flag8thUp", 640, 585, 102, 239)])
        _run(log, Q.FLAG_IS_NOT_A_FLAG)
        v = log.verdict(Q.FLAG_IS_NOT_A_FLAG, g[3])
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "in_a_key_signature_slot")

    def test_an_arpeggiato_in_the_key_slots_is_refused(self):
        log = Log()
        g = _staff(log, 0, [CLEF, *FLATS, ("arpeggiato", 640, 560, 116, 269)])
        _run(log, Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO)
        v = log.verdict(Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO, g[3])
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "in_a_key_signature_slot")

    def test_a_flag_after_the_key_stays_a_flag(self):
        """⚠️ Control: a flag 2.5 spaces past the last flat."""
        log = Log()
        g = _staff(log, 0, [CLEF, *FLATS, ("flag8thUp", 1100, 585, 102, 239)])
        _run(log, Q.FLAG_IS_NOT_A_FLAG)
        v = log.verdict(Q.FLAG_IS_NOT_A_FLAG, g[3])
        self.assertIs(v.value, False)

    def test_structure_is_not_refused(self):
        """A staff box spans the header and is no accidental."""
        self.assertFalse(K.is_refusable_class("staff"))
        self.assertFalse(K.is_refusable_class("ledgerLine"))
        self.assertTrue(K.is_refusable_class("timeSig4"))
        self.assertTrue(K.is_refusable_class("tie"))


class TestATimeSignatureInTheKeySlotsIsNoMeterStatement(unittest.TestCase):

    def _rows(self, log, staff, cls, x):
        return [type("R", (), dict(
            value=cls, frame="cell:0", detail={"x": x, "cell": 0},
            subject=R.staff(1, 0, staff)))()]

    class _EV:
        def __init__(self, log):
            self.log = log

        def rows(self, q, scope=None, subject=None):
            return self.log.rows(q, subject, scope=scope)

    def test_a_digit_in_the_key_slots_is_dropped(self):
        log = Log()
        _staff(log, 0, [CLEF, *FLATS, ("timeSig4", 640, 694, 126, 273)])
        ev = self._EV(log)
        kept, dropped = K.meter_rows_outside_key_slots(
            ev, self._rows(log, 0, "timeSig4", 640))
        self.assertEqual((len(kept), dropped), (0, 1))

    def test_a_digit_after_the_key_is_kept(self):
        """⚠️ Control: the printed meter, 3 spaces past the last flat."""
        log = Log()
        _staff(log, 0, [CLEF, *FLATS, ("timeSig4", 1000, 694, 126, 273)])
        ev = self._EV(log)
        kept, dropped = K.meter_rows_outside_key_slots(
            ev, self._rows(log, 0, "timeSig4", 1000))
        self.assertEqual((len(kept), dropped), (1, 0))


class TestARestOnTheMetersDigits(unittest.TestCase):
    """Litolff p1 s0: staves 1 and 7 print the 2/4 as `timeSig2`/`timeSig4`
    boxes at page x 819-848; staff 8's own copy is boxed `restQuarter`."""

    def setUp(self):
        # pinned OFF: this tests the retired 18-space meter_column rule (2.177 ON no longer consults it)
        p = mock.patch.dict(os.environ, {"OMR_METER_OBJECT": "0"})
        p.start()
        self.addCleanup(p.stop)

    def _system(self, rest):
        log = Log()
        _staff(log, 1, [CLEF, *FLATS, ("timeSig2", 1002, 353, 157, 211),
                        ("timeSig4", 998, 406, 165, 328)])
        g = _staff(log, 8, [CLEF, *FLATS, rest])
        _run(log, Q.REST_IS_NOT_A_REST)
        return log, g[3]

    def test_a_restQuarter_on_the_digits_column_is_a_meter_digit(self):
        log, g = self._system(("restQuarter", 997, 577, 169, 365))
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_is_a_meter_digit")

    def test_a_rest_after_the_time_signature_stays_a_rest(self):
        """⚠️ THE CONTROL THAT CAN FAIL: 3 spaces right of the digits."""
        log, g = self._system(("rest8th", 1500, 585, 102, 239))
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_no_sibling_digits_no_column_no_refusal(self):
        log = Log()
        g = _staff(log, 8, [CLEF, *FLATS, ("restQuarter", 997, 577, 169, 365)])
        _run(log, Q.REST_IS_NOT_A_REST)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, g[3]).value, False)

    def test_a_digit_that_is_a_key_flat_is_not_the_column(self):
        """A sibling `timeSig4` standing in ITS OWN key slots is a flat; it
        must not define a meter column that swallows a real rest."""
        log = Log()
        _staff(log, 1, [CLEF, *FLATS, ("timeSig4", 640, 694, 126, 273)])
        g = _staff(log, 8, [CLEF, *FLATS, ("rest8th", 1100, 585, 102, 239)],
                   page_x0=630.0)
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g[3])
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")


if __name__ == "__main__":
    unittest.main()
