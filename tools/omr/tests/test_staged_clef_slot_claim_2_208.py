"""ROADMAP 2.208: the clef claims its own ink on every staff -- `gather.gather_clef_slot_claim`, flag `OMR_CLEF_SLOT_CLAIM` (default OFF).

CAUSE (2.205 tile 5, Litolff p4 staff 8): a staff whose clef nothing located and the detector never boxed (a clef carried from other
systems) files no clef claim, so the detector's head on the clef's body stands unopposed. The slot between the system's clef offset and
the key claim is that clef's. Every CONTROL passes with the rule absent or present, so a rule that refuses everything cannot pass.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate, adjudicators            # noqa: F401
from tools.omr.staged import claims as CL
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests.test_staged_duration import _staff_space

SP = 16.0
ON = {"OMR_CLAIMED_REGISTER": "1", "OMR_CLEF_SLOT_CLAIM": "1"}
OFF = {"OMR_CLAIMED_REGISTER": "1", "OMR_CLEF_SLOT_CLAIM": "0"}
L0 = [100.0 + SP * i for i in range(5)]           # staff 0 (shows its clef)
L1 = [300.0 + SP * i for i in range(5)]           # staff 1 (clef carried: nothing located, nothing boxed)


class _Det:
    def __init__(self, name, x, y, w, h, conf=0.9):
        self.smufl_name, self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical = name, x, y, w, h
        self.confidence, self.category = conf, ""


class _Cell:
    def __init__(self, staff, k, bbox):
        self.staff_index, self.measure_index, self.page_index, self.bbox_page_px, self.upscale_factor = staff, k, 0, bbox, 1.0


class _Staff:
    def __init__(self, i, lines):
        self.staff_index, self.system_index, self.line_ys = i, 0, lines


class _PWS:
    class page:
        page_index = 0
    staves = [_Staff(0, L0), _Staff(1, L1)]


def _page():
    img = np.full((520, 900), 255, np.uint8)
    for ly in L0 + L1:
        img[int(ly) - 1:int(ly) + 2, 100:880] = 0
    img[60:420, 100:106] = 0                       # the system barline
    img[84:184, 150:176] = 0                       # staff 0's clef (the detector boxed it: clefG)
    img[284:384, 150:176] = 0                      # staff 1's clef ink: nobody boxed it
    img[330:350, 156:172] = 0                      # a head-sized blob on its body (what the detector drew a head on)
    img[304:320, 250:268] = 0                      # a key flat, further on
    return img


CELLS = [_Cell(0, 0, (100, 50, 400, 250)), _Cell(1, 0, (100, 250, 400, 450))]


def _dets(extra_key=True):
    d = {R.cell(0, 0, 0, 0).to_key(): [_Det("clefG", 50, 34, 26, 100)],
         R.cell(0, 0, 1, 0).to_key(): [_Det("noteheadBlackOnLine", 56, 80, 18, 18)]}      # the false head on staff 1's clef
    return d


def _gather(env, key_lo=None):
    img = _page()
    _PWS.page.binary = img
    log = Log()
    with mock.patch.dict(os.environ, env):
        G.gather_claimed_register(log, _PWS(), CELLS, {0: (0, 0), 1: (0, 1)}, _dets())
        if key_lo is not None:                      # the key claim of staff 1 (gather_key_signature_claim files this shape)
            log.observe(R.staff(0, 0, 1), Q.CLAIMED_AREA, [key_lo, 270.0, key_lo + 40.0, 400.0], reader=READERS.CV_KEY_SIGNATURE_CLAIM,
                        frame="cell:0", cell=0, owner="key_signature", owner_row=None, unit="area", standing="READ", boxes_inside={})
        G.gather_clef_slot_claim(log, _PWS(), CELLS, {0: (0, 0), 1: (0, 1)}, _dets())
    return log


def _slot_rows(log, staff):
    return [r for r in log.rows(Q.CLAIMED_AREA, R.staff(0, 0, staff))
            if r.detail.get("owner") == "clef" and r.detail.get("source") == "clef_slot"]


class TestPure(unittest.TestCase):
    def test_flag_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMR_CLEF_SLOT_CLAIM", None)
            self.assertFalse(CL.clef_slot_enabled())
        with mock.patch.dict(os.environ, ON):
            self.assertTrue(CL.clef_slot_enabled())
        with mock.patch.dict(os.environ, {"OMR_CLAIMED_REGISTER": "0", "OMR_CLEF_SLOT_CLAIM": "1"}):
            self.assertFalse(CL.clef_slot_enabled())                  # needs the register

    def test_slot_runs_from_the_offset_to_the_key_and_never_past_the_widest_sibling_clef(self):
        self.assertEqual(CL.clef_slot(150.0, 230.0, 180.0, L1, SP), [150.0, 236.0, 192.0, 428.0])
        self.assertEqual(CL.clef_slot(150.0, 400.0, 180.0, L1, SP)[2], 192.0)      # the key claim far on: the sibling cap holds
        self.assertEqual(CL.clef_slot(150.0, None, 180.0, L1, SP)[2], 192.0)       # no key claim: the cap alone

    def test_CONTROL_a_slot_narrower_than_a_space_is_none(self):
        self.assertIsNone(CL.clef_slot(150.0, 160.0, 180.0, L1, SP))


class TestGather(unittest.TestCase):
    def test_a_staff_with_no_clef_claim_gets_the_slot_claim_and_one_with_its_own_does_not(self):
        log = _gather(ON, key_lo=230.0)
        self.assertEqual(_slot_rows(log, 0), [])                                   # staff 0 shows its clef: no slot claim
        rows = _slot_rows(log, 1)
        self.assertEqual([r.detail["unit"] for r in rows], ["area"])
        r = rows[0]
        self.assertEqual(r.detail["standing"], "READ")
        self.assertLessEqual(r.value[2], 230.0)                                    # never past the key claim
        head = R.glyph(0, 0, 1, 0, 0).to_key()
        self.assertGreaterEqual(r.detail["boxes_inside"][head]["ink_share_inside"], 0.5)

    def test_flag_off_files_no_slot_claim(self):
        self.assertEqual(_slot_rows(_gather(OFF, key_lo=230.0), 1), [])

    def test_CONTROL_no_sibling_clef_files_nothing_and_says_so(self):
        # a system with no clef on any staff: the column abstained, so there is no clef offset and no slot to draw
        log = Log()
        _PWS.page.binary = _page()
        with mock.patch.dict(os.environ, ON):
            G.gather_clef_slot_claim(log, _PWS(), CELLS, {0: (0, 0), 1: (0, 1)}, {})
        self.assertEqual(_slot_rows(log, 0) + _slot_rows(log, 1), [])


def _box(log, gi, box, cls):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.9, category="notehead",
                bbox_page_px=[box[0], box[1], box[0] + box[2], box[1] + box[3]])
    log.observe(g, Q.GLYPH_CONF, 0.9, reader=READERS.DETECTOR, frame="cell:0")
    return g


class TestEndToEnd(unittest.TestCase):
    """The failure this lane exists for, through GATHER's claim and ADJUDICATE's consult. The false head stands IN the slot
    (page px 152..172); `stem` is a `Q.STEM` row (cell canonical = page px here) that touches it."""
    def _verdict(self, env, stem=None):
        log = Log()
        _staff_space(log, SP)
        g = _box(log, 0, (152, 300, 20, 16), "noteheadBlackOnLine")
        slot = _slot_rows(_gather(env, key_lo=230.0), 1)
        if slot:       # the REAL claim gather drew; its measured entry for the false head re-keyed onto this log's head
            entry = slot[0].detail["boxes_inside"][R.glyph(0, 0, 1, 0, 0).to_key()]
            log.observe(R.staff(0, 0, 0), Q.CLAIMED_AREA, slot[0].value, reader=READERS.CV_CLEF_SLOT_CLAIM, frame="cell:0", cell=0,
                        owner="clef", owner_row=None, owner_glyph=None, unit="area", standing="READ", source="clef_slot",
                        boxes_inside={g.to_key(): entry})
        if stem is not None:
            log.observe(R.cell(0, 0, 0, 0), Q.STEM, stem, reader=READERS.CV_INK, frame="cell:0", x0=stem[0], x1=stem[0] + stem[2], y_center=0)
        with mock.patch.dict(os.environ, env):
            adjudicate.run(log)
        return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)

    def test_the_head_on_a_carried_clefs_ink_is_refused_with_the_flag_on(self):
        v = self._verdict(ON)
        self.assertEqual((v.value, v.reason), (True, "claimed_by:clef"))

    def test_FAILS_WITHOUT_THE_FIX_the_same_head_stands_with_the_flag_off(self):
        v = self._verdict(OFF)
        self.assertNotEqual(v.reason, "claimed_by:clef")

    def test_a_stem_the_line_finder_drew_on_the_clefs_own_ink_does_not_make_the_head_a_note(self):
        # Litolff p4 staff 8: the finder's "stem" touching the head was the clef's curl, itself inside the slot
        v = self._verdict(ON, stem=(162, 290, 4, 60))
        self.assertEqual((v.value, v.reason), (True, "claimed_by:clef"))

    def test_CONTROL_a_stem_standing_outside_the_slot_still_makes_it_a_note(self):
        # a stem whose centre is right of the slot (x 190 > 188): not the clef's; a stemmed head is never refused by a clef claim
        v = self._verdict(ON, stem=(170, 290, 40, 60))
        self.assertEqual((v.outcome, v.value), ("decided", False))

    def test_CONTROL_a_stem_inside_a_DETECTOR_clef_claim_still_counts_as_a_stem(self):
        # only the slot claim reads a stem in its area as its own ink: every older clef claim consults exactly as before
        log = Log()
        _staff_space(log, SP)
        g = _box(log, 0, (152, 300, 20, 16), "noteheadBlackOnLine")
        log.observe(R.staff(0, 0, 0), Q.CLAIMED_AREA, [140.0, 236.0, 188.0, 428.0], reader=READERS.CV_CLAIMED_REGISTER, frame="cell:0",
                    cell=0, owner="clef", owner_row=None, owner_glyph=None, unit="area", standing="READ", source="detector",
                    boxes_inside={g.to_key(): {"ink_share_inside": 0.95}})
        log.observe(R.cell(0, 0, 0, 0), Q.STEM, (162, 290, 4, 60), reader=READERS.CV_INK, frame="cell:0", x0=162, x1=166, y_center=0)
        with mock.patch.dict(os.environ, ON):
            adjudicate.run(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertEqual((v.outcome, v.value), ("decided", False))


if __name__ == "__main__":
    unittest.main()
