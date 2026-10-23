"""ROADMAP 2.183 (plan 2026-10-20 §7 step 3): the KEY SIGNATURE as an area claim in the register -- owner `key_signature`, flag
`OMR_KEY_SIGNATURE_CLAIM` (default OFF; needs `OMR_CLAIMED_REGISTER`). It subsumes the five 2.100 `in_a_key_signature_slot` gates (notehead,
rest, flag, arpeggiato, arc) and owns the cancelling naturals at a key change (Sean 2026-10-20).

Every CONTROL passes with the rule absent or present, so a rule that refuses everything cannot pass. The fixtures are the REAL numbers of
Litolff p1 s0 staff 0 (`test_staged_key_slots_2_100`): cell staff space 89.75, clef box, three `keyFlat` boxes.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate, adjudicators            # noqa: F401
from tools.omr.staged import claims as CL
from tools.omr.staged import export as E
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import key_slots as K
from tools.omr.staged.record import Log, Q, READERS

SPACE = 89.75
CLEF = ("clefG", 243, 402, 267, 641)
FLATS = [("keyFlat", 541, 590, 105, 270), ("keyFlat", 650, 540, 105, 270), ("keyFlat", 747, 585, 102, 239)]
THIRD = FLATS[2]

OFF = {"OMR_KEY_SIGNATURE_CLAIM": "0", "OMR_CLAIMED_REGISTER": "1"}
ON = {"OMR_KEY_SIGNATURE_CLAIM": "1", "OMR_CLAIMED_REGISTER": "1"}
LINES = [700.0 + SPACE * i for i in range(5)]


class TestFlag(unittest.TestCase):
    def test_default_on_and_needs_the_register(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMR_KEY_SIGNATURE_CLAIM", None)
            os.environ.pop("OMR_CLAIMED_REGISTER", None)
            self.assertTrue(CL.key_enabled())
            self.assertTrue(CL.key_active())
        with mock.patch.dict(os.environ, ON):
            self.assertTrue(CL.key_active())
        with mock.patch.dict(os.environ, {"OMR_KEY_SIGNATURE_CLAIM": "1", "OMR_CLAIMED_REGISTER": "0"}):
            self.assertTrue(CL.key_enabled())
            self.assertFalse(CL.key_active())                       # the claim lives in the register
        with mock.patch.dict(os.environ, {"OMR_KEY_SIGNATURE_CLAIM": "0"}):
            self.assertFalse(CL.key_enabled())


def _kb(cls, x, y=400.0, w=105.0, h=270.0, i=0):
    return K.KeyBox("g%d" % i, cls, x, y, w, h)


class TestCancellingNaturals(unittest.TestCase):
    """Sean 2026-10-20: "Canceling accidentals should be considered key signature" -- the naturals printed before the new key's flats."""

    def _boxes(self, nat_cls):
        clef = K.KeyBox("clef", "clefG", 243, 402, 267, 641)
        nats = [_kb(nat_cls, 541 + 110 * i, i=i) for i in range(3)]              # three cancelling naturals, one slot apart
        flats = [_kb("keyFlat", 541 + 110 * (3 + i), i=3 + i) for i in range(2)]
        return [clef] + nats + flats

    def test_the_standard_window_misses_a_run_that_opens_with_naturals_boxed_as_in_bar_accidentals(self):
        boxes = self._boxes("accidentalNatural")
        self.assertIsNone(K.key_slot_window(boxes, SPACE))                        # the first KEY box stands > 2 sp from the clef
        w = K.claim_window(boxes, SPACE)
        self.assertIsNotNone(w)
        self.assertEqual(w.slots, 5)
        self.assertEqual(w.members, ("g0", "g1", "g2", "g3", "g4"))              # the naturals ARE the run
        self.assertEqual(w.lo, 243 + 267)                                        # from the clef's right edge

    def test_a_rest_boxed_on_a_cancelling_natural_stands_in_the_run(self):
        boxes = self._boxes("accidentalNatural")
        w = K.claim_window(boxes, SPACE)
        rest = K.KeyBox("r", "rest8th", 650, 585, 102, 239)                       # on the second natural
        self.assertTrue(K.stands_in_the_window(w, rest))

    def test_CONTROL_naturals_after_the_new_key_are_a_notes_not_the_signatures(self):
        boxes = self._boxes("accidentalNatural") + [_kb("accidentalNatural", 541 + 110 * 5, i=9)]
        w = K.claim_window(boxes, SPACE)
        self.assertNotIn("g9", w.members)

    def test_CONTROL_no_clef_no_cancelling_run(self):
        self.assertIsNone(K.window_with_cancels([b for b in self._boxes("accidentalNatural") if b.cls != "clefG"], SPACE))

    def test_CONTROL_naturals_only_is_the_standard_windows_own(self):
        clef = K.KeyBox("clef", "clefG", 243, 402, 267, 641)
        boxes = [clef] + [_kb("keyNatural", 541 + 110 * i, i=i) for i in range(2)]
        self.assertIsNone(K.window_with_cancels(boxes, SPACE))
        self.assertIsNotNone(K.key_slot_window(boxes, SPACE))

    def test_CONTROL_a_standard_run_is_unchanged(self):
        clef = K.KeyBox("clef", "clefG", 243, 402, 267, 641)
        boxes = [clef] + [_kb("keyFlat", 541 + 110 * i, i=i) for i in range(3)]
        self.assertEqual(K.claim_window(boxes, SPACE), K.key_slot_window(boxes, SPACE))

    def test_stand_margin_is_positive_inside_and_none_outside(self):
        boxes = [K.KeyBox("clef", "clefG", 243, 402, 267, 641)] + [_kb("keyFlat", 541 + 110 * i, i=i) for i in range(3)]
        w = K.key_slot_window(boxes, SPACE)
        inside = K.KeyBox("r", "rest8th", 600, 585, 102, 239)
        after = K.KeyBox("r2", "rest8th", 960, 585, 102, 239)
        self.assertGreater(K.stand_margin_spaces(w, inside, SPACE), 0)
        self.assertIsNone(K.stand_margin_spaces(w, after, SPACE))


class _Det:
    def __init__(self, name, x, y, w, h, conf=0.9):
        self.smufl_name, self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical = name, x, y, w, h
        self.confidence, self.category = conf, ""


class _Cell:
    def __init__(self, k, bbox, staff=0):
        self.staff_index, self.measure_index, self.page_index, self.bbox_page_px, self.upscale_factor = staff, k, 1, bbox, 1.0


class _Staff:
    def __init__(self, staff_index=0):
        self.staff_index, self.system_index, self.line_ys = staff_index, 0, LINES


class _PWS:
    class page:
        page_index = 1
    staves = [_Staff()]


def _raster(boxes):
    img = np.full((1800, 2600), 255, np.uint8)
    for cls, x, y, w, h in boxes:
        img[int(y):int(y + h), int(x):int(x + w)] = 0
    return img


def _fx(boxes, *, env=ON):
    """One header cell (cell 0, page frame == canonical) holding `boxes`; the GLYPH_BOX rows as GATHER files them, the claim rows from
    the REAL `gather_key_signature_claim` (ON) -- so the consult is tested on rows the pipeline would file."""
    log = Log()
    cell_box = (0.0, 0.0, 2600.0, 1800.0)
    log.observe(R.cell(1, 0, 0, 0), Q.CELL_STAFF_SPACE, SPACE, reader=READERS.GEOMETRY, frame="cell:0")
    gids, dets = [], []
    for gi, box in enumerate(boxes):
        g = R.glyph(1, 0, 0, 0, gi)
        log.observe(g, Q.GLYPH_BOX, tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.5, category="x",
                    bbox_page_px=[box[1], box[2], box[1] + box[3], box[2] + box[4]])
        cls = box[0]
        if cls.startswith("rest"):
            log.observe(g, Q.REST, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.5, category="rest")
        if cls.startswith("notehead"):
            log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.5, category="notehead")
        if cls.startswith("flag"):
            log.observe(g, Q.FLAG, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.5, category="flag")
        log.observe(g, Q.GLYPH_CONF, 0.9, reader=READERS.DETECTOR, frame="cell:0")
        gids.append(g)
        dets.append(_Det(*box))
    pws = _PWS()
    pws.page.binary = _raster(boxes)
    with mock.patch.dict(os.environ, env):
        G.gather_key_signature_claim(log, pws, [_Cell(0, cell_box)], {0: (0, 0)}, {R.cell(1, 0, 0, 0).to_key(): dets})
    return log, gids


def _decide(log, env, *qs):
    log.freeze()
    adjudicate._ensure_decisions()
    with mock.patch.dict(os.environ, env):
        adjudicate.run(log, order=tuple(qs))


def _key_rows(log):
    return [r for r in log.rows(Q.CLAIMED_AREA, R.staff(1, 0, 0)) if r.detail["owner"] == "key_signature"]


class TestGather(unittest.TestCase):
    def test_files_one_key_run_claim_with_the_boxes_that_stand_in_it(self):
        log, g = _fx([CLEF, *FLATS, ("rest8th", *THIRD[1:]), ("rest8th", 960, 585, 102, 239)])
        rows = _key_rows(log)
        self.assertEqual(len(rows), 1)
        d = rows[0].detail
        self.assertEqual((d["unit"], d["standing"], d["slots"], d["cell"]), ("area", "READ", 3, 0))
        self.assertEqual(len(d["members"]), 3)
        self.assertTrue(d["boxes_inside"][g[4].to_key()]["named"])               # the rest on the third flat
        self.assertNotIn(g[5].to_key(), d["boxes_inside"])                        # CONTROL: the rest after the signature is not claimed
        self.assertGreater(d["boxes_inside"][g[4].to_key()]["stand_margin_spaces"], 0)
        self.assertGreater(rows[0].value[2], rows[0].value[0])

    def test_flag_off_files_nothing(self):
        log, _ = _fx([CLEF, *FLATS], env=OFF)
        self.assertEqual(_key_rows(log), [])

    def test_register_off_files_nothing(self):
        log, _ = _fx([CLEF, *FLATS], env={"OMR_KEY_SIGNATURE_CLAIM": "1", "OMR_CLAIMED_REGISTER": "0"})
        self.assertEqual(list(log.rows(Q.CLAIMED_AREA, R.staff(1, 0, 0))), [])

    def test_a_c_major_header_files_no_claim(self):
        log, _ = _fx([CLEF, ("rest8th", 520, 585, 102, 239)])
        self.assertEqual(list(log.rows(Q.CLAIMED_AREA, R.staff(1, 0, 0))), [])

    def test_a_key_change_in_a_later_cell_is_never_read_even_with_a_witness_staff(self):
        log = Log()
        cells = [_Cell(0, (0.0, 0.0, 1300.0, 1800.0)), _Cell(3, (1300.0, 0.0, 2600.0, 1800.0))]
        boxes3 = [("keyFlat", 100, 590, 105, 270), ("keyFlat", 210, 540, 105, 270)]
        dets = {R.cell(1, 0, 0, 3).to_key(): [_Det(*b) for b in boxes3]}
        pws = _PWS()
        pws.page.binary = _raster([(b[0], 1300 + b[1], b[2], b[3], b[4]) for b in boxes3])
        with mock.patch.dict(os.environ, ON):
            G.gather_key_signature_claim(log, pws, cells, {0: (0, 0)}, dets)
        self.assertEqual([(r.detail["cell"], r.detail["standing"]) for r in _key_rows(log)], [(3, "NARROWED")])
        # a second staff drawing the same window at the same x is recorded, and still does not make it READ
        log2 = Log()
        pws2 = _PWS()
        pws2.staves = [_Staff(0), _Staff(1)]
        pws2.page.binary = pws.page.binary
        cells2 = cells + [_Cell(3, (1300.0, 0.0, 2600.0, 1800.0), staff=1)]
        dets2 = dict(dets)
        dets2[R.cell(1, 0, 1, 3).to_key()] = [_Det(*b) for b in boxes3]
        with mock.patch.dict(os.environ, ON):
            G.gather_key_signature_claim(log2, pws2, cells2, {0: (0, 0), 1: (0, 1)}, dets2)
        rows2 = [r for sub in (R.staff(1, 0, 0), R.staff(1, 0, 1)) for r in log2.rows(Q.CLAIMED_AREA, sub) if r.detail["owner"] == "key_signature"]
        self.assertEqual({r.detail["standing"] for r in rows2}, {"NARROWED"})
        self.assertTrue(all(r.detail["witness_staves"] for r in rows2))


class TestParityWithTheFiveGates(unittest.TestCase):
    """The claim refuses exactly the boxes the 2.100 gates refuse (flag OFF vs ON), for each of the five families."""

    def _rest(self, boxes, idx, env):
        log, g = _fx(boxes, env=env)
        _decide(log, env, Q.REST_IS_NOT_A_REST)
        return log.verdict(Q.REST_IS_NOT_A_REST, g[idx])

    def test_a_rest_on_the_third_flat_off_and_on(self):
        boxes = [CLEF, *FLATS, ("rest8th", *THIRD[1:])]
        off, on = self._rest(boxes, 4, OFF), self._rest(boxes, 4, ON)
        self.assertEqual((off.value, off.reason), (True, "rest_in_a_key_signature_slot"))
        self.assertEqual((on.value, on.reason), (True, "claimed_by:key_signature"))
        self.assertGreater(on.margin, 0)

    def test_a_rest_between_two_flats_off_and_on(self):
        boxes = [CLEF, FLATS[0], ("keyFlat", 700, 590, 102, 270), ("rest8th", 620, 585, 102, 239)]
        self.assertEqual(self._rest(boxes, 3, OFF).value, True)
        self.assertEqual(self._rest(boxes, 3, ON).reason, "claimed_by:key_signature")

    def test_a_rest_before_the_first_flat_off_and_on(self):
        boxes = [CLEF, ("rest8th", 520, 585, 102, 239), FLATS[1]]
        self.assertEqual(self._rest(boxes, 1, OFF).value, True)
        self.assertEqual(self._rest(boxes, 1, ON).reason, "claimed_by:key_signature")

    def test_CONTROL_a_real_rest_after_the_last_flat_stays_a_rest_both_ways(self):
        boxes = [CLEF, *FLATS, ("rest8th", 960, 585, 102, 239)]
        for env in (OFF, ON):
            v = self._rest(boxes, 4, env)
            self.assertEqual((v.value, v.reason), (False, "rest"), env)

    def test_a_notehead_on_a_flats_bowl_off_and_on(self):
        boxes = [CLEF, *FLATS, ("noteheadBlackOnLine", 760, 700, 90, 80)]
        for env, reason in ((OFF, "notehead_in_a_key_signature_slot"), (ON, "claimed_by:key_signature")):
            log, g = _fx(boxes, env=env)
            _decide(log, env, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD)
            v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g[4])
            self.assertEqual((v.value, v.reason), (True, reason))

    def test_CONTROL_a_note_after_the_signature_stays_a_note_both_ways(self):
        boxes = [CLEF, *FLATS, ("noteheadBlackOnLine", 1000, 700, 90, 80)]
        for env in (OFF, ON):
            log, g = _fx(boxes, env=env)
            _decide(log, env, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD)
            v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g[4])
            self.assertEqual((v.value, v.reason), (False, "notehead"), env)

    def test_a_flag_and_an_arpeggiato_in_the_slots_off_and_on(self):
        for cls, q in (("flag8thUp", Q.FLAG_IS_NOT_A_FLAG), ("arpeggiato", Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO)):
            boxes = [CLEF, *FLATS, (cls, 640, 585, 102, 239)]
            for env, reason in ((OFF, "in_a_key_signature_slot"), (ON, "claimed_by:key_signature")):
                log, g = _fx(boxes, env=env)
                _decide(log, env, q)
                v = log.verdict(q, g[4])
                self.assertEqual((v.value, v.reason), (True, reason), (cls, env))

    def test_CONTROL_a_flag_after_the_key_stays_a_flag_both_ways(self):
        boxes = [CLEF, *FLATS, ("flag8thUp", 1100, 585, 102, 239)]
        for env in (OFF, ON):
            log, g = _fx(boxes, env=env)
            _decide(log, env, Q.FLAG_IS_NOT_A_FLAG)
            self.assertIs(log.verdict(Q.FLAG_IS_NOT_A_FLAG, g[4]).value, False, env)


class TestConsult(unittest.TestCase):
    def _claim_fx(self, entry, standing="READ", cls="noteheadBlackOnLine"):
        log = Log()
        log.observe(R.cell(1, 0, 0, 0), Q.CELL_STAFF_SPACE, SPACE, reader=READERS.GEOMETRY, frame="cell:0")
        g = R.glyph(1, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.5, category="notehead")
        log.observe(g, Q.GLYPH_BOX, (cls, 700, 700, 90, 80), reader=READERS.DETECTOR, frame="cell:0", score=0.5, category="x",
                    bbox_page_px=[700, 700, 790, 780])
        log.observe(R.staff(1, 0, 0), Q.CLAIMED_AREA, [0.0, 0.0, 100.0, 100.0], reader=READERS.CV_KEY_SIGNATURE_CLAIM, frame="cell:0",
                    cell=0, owner="key_signature", owner_row=None, unit="area", standing=standing, boxes_inside={g.to_key(): entry})
        return log, g

    def _v(self, log, g):
        _decide(log, ON, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD)
        return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)

    def test_a_named_box_is_refused_even_with_a_stem_on_it(self):
        log, g = self._claim_fx({"named": True, "stand_margin_spaces": 0.4, "ink_share_inside": 1.0})
        log.observe(R.cell(1, 0, 0, 0), Q.STEM, (760, 600, 4, 200), reader=READERS.CV_INK, frame="cell:0", x0=760, x1=764, y_center=740)
        v = self._v(log, g)
        self.assertEqual((v.outcome, v.reason), ("decided", "claimed_by:key_signature"))

    def test_ink_inside_the_run_but_not_standing_in_it_only_narrows(self):
        """Sean 2.181's rule: where the claim cannot say the box STANDS in the run, it NARROWS (blue), never refuses."""
        log, g = self._claim_fx({"ink_share_inside": 0.8})
        v = self._v(log, g)
        self.assertEqual((v.outcome, v.reason), ("narrowed", "claim_narrowed:key_signature"))
        self.assertEqual(v.candidates[0].value, False)                           # the note first: written, blue
        rec = E.Record({"record": log.to_json()})
        self.assertEqual(E.claim_guess_of(rec, g.to_key())["rule"], "claim_narrowed:key_signature")

    def test_a_key_change_one_staff_alone_drew_narrows_even_a_standing_box(self):
        log, g = self._claim_fx({"named": True, "stand_margin_spaces": 0.4}, standing="NARROWED")
        v = self._v(log, g)
        self.assertEqual((v.outcome, v.reason), ("narrowed", "claim_narrowed:key_signature"))

    def test_CONTROL_under_the_cut_nothing(self):
        log, g = self._claim_fx({"ink_share_inside": 0.3})
        v = self._v(log, g)
        self.assertEqual((v.value, v.reason), (False, "notehead"))


if __name__ == "__main__":
    unittest.main()
