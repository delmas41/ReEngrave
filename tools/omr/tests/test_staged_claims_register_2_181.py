"""ROADMAP 2.181 (plan 2026-10-20 §7 step 2): the claimed-area register -- `Q.CLAIMED_AREA` owners `clef` and `leading_column` (plus
2.177's `meter`), `claims.covering`, and the one consult (`adjudicators/claimed_by.py`). Flag `OMR_CLAIMED_REGISTER`, default OFF.
Every CONTROL passes with the rule absent or present, so a rule that refuses everything cannot pass.
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
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests.test_staged_duration import _staff_space

ON = {"OMR_CLAIMED_REGISTER": "1"}
OFF = {"OMR_CLAIMED_REGISTER": "0"}
SP = 16.0
LINES = [100.0 + SP * i for i in range(5)]


def _page():
    img = np.full((400, 800), 255, np.uint8)
    for ly in LINES:
        img[int(ly) - 1:int(ly) + 2, 100:780] = 0
    img[60:240, 100:106] = 0                           # the system barline, running past the staff both ways
    return img


class TestPure(unittest.TestCase):
    def test_flag_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMR_CLAIMED_REGISTER", None)
            self.assertFalse(CL.enabled())
        with mock.patch.dict(os.environ, ON):
            self.assertTrue(CL.enabled())

    def test_a_box_on_the_barline_is_line_shaped(self):
        t = CL.through_stroke(_page(), (98, 116, 116, 132), SP)
        self.assertTrue(t["through"], t)

    def test_CONTROL_a_head_blob_is_not_line_shaped(self):
        img = _page()
        img[118:130, 120:136] = 0                       # a head-sized blob between the lines, nothing running on
        t = CL.through_stroke(img, (118, 116, 138, 132), SP)
        self.assertFalse(t["through"], t)

    def test_CONTROL_a_stem_is_line_shaped_so_a_stemmed_head_is_never_refused_by_the_column(self):
        # (the consult refuses a column box only where no stem touches it; this pins why the stem test is needed)
        img = _page()
        img[118:130, 120:136] = 0
        img[60:130, 134:136] = 0
        self.assertTrue(CL.through_stroke(img, (118, 116, 138, 132), SP)["through"])

    def test_leading_column_runs_from_left_of_the_staff_to_the_clef(self):
        a = CL.leading_column((100, 50, 400, 250), 140.0, SP)
        self.assertEqual(a, [100 - 2 * SP, 50.0, 140.0, 250.0])
        self.assertIsNone(CL.leading_column((100, 50, 400, 250), 100.0, SP))

    def test_clef_box_standing(self):
        self.assertEqual(CL.clef_box_standing((110, 0, 140, 64), (100, 0, 900, 100), SP), "READ")
        self.assertEqual(CL.clef_box_standing((300, 0, 330, 64), (100, 0, 900, 100), SP), "NARROWED")
        self.assertFalse(CL.is_clef_box("clefG", (0, 0, 20, 20), SP))       # 1.25 sp tall: not clef-sized (2.144)
        self.assertTrue(CL.is_clef_box("clefG", (0, 0, 30, 70), SP))

    def test_covering_lists_named_and_measured_never_below_the_cut(self):
        class Row:
            def __init__(self, d):
                self.detail, self.id = d, "obs"
        rows = [Row({"owner": "clef", "unit": "area", "boxes_inside": {"a": {"named": True}, "b": {"ink_share_inside": 0.49}}}),
                Row({"owner": "leading_column", "unit": "area", "boxes_inside": {"b": {"ink_share_inside": 0.8}}})]
        self.assertEqual([r.detail["owner"] for r, _ in CL.covering(rows, "a")], ["clef"])
        self.assertEqual([r.detail["owner"] for r, _ in CL.covering(rows, "b")], ["leading_column"])
        self.assertEqual(CL.covering(rows, "c"), [])


class _Det:
    def __init__(self, name, x, y, w, h, conf=0.9):
        self.smufl_name, self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical = name, x, y, w, h
        self.confidence, self.category = conf, ""


class _Cell:
    def __init__(self, k, bbox):
        self.staff_index, self.measure_index, self.page_index, self.bbox_page_px, self.upscale_factor = 0, k, 0, bbox, 1.0


class _Staff:
    staff_index, system_index, line_ys = 0, 0, LINES


class _PWS:
    class page:
        page_index = 0
    staves = [_Staff()]


class TestGather(unittest.TestCase):
    def _run(self):
        img = _page()
        img[118:130, 112:128] = 0                       # a blob left of the clef (not line-shaped)
        img[84:184, 150:176] = 0                        # the clef's ink
        img[90:180, 500:520] = 0                        # a mid-bar clef-class box's ink (cell 1)
        _PWS.page.binary = img
        cells = [_Cell(0, (100, 50, 400, 250)), _Cell(1, (400, 50, 780, 250))]
        dets = {R.cell(0, 0, 0, 0).to_key(): [_Det("clefG", 50, 34, 26, 100), _Det("noteheadBlackInSpace", -2, 66, 18, 16),
                                               _Det("noteheadBlackInSpace", 12, 66, 16, 16), _Det("noteheadBlackInSpace", 52, 50, 20, 16)],
                R.cell(0, 0, 0, 1).to_key(): [_Det("clefF", 100, 40, 20, 90), _Det("noteheadBlackInSpace", 102, 60, 16, 16)]}
        log = Log()
        with mock.patch.dict(os.environ, ON):
            G.gather_claimed_register(log, _PWS(), cells, {0: (0, 0)}, dets)
        return log

    def test_files_clef_and_column_claims(self):
        rows = self._run().rows(Q.CLAIMED_AREA, R.staff(0, 0, 0))
        by = {(r.detail["owner"], r.detail["cell"]): r for r in rows}
        self.assertEqual(by[("clef", 0)].detail["standing"], "READ")
        self.assertEqual(by[("clef", 1)].detail["standing"], "NARROWED")    # 100 px = 6.25 sp into its bar: past the 6 sp window (2.144)
        col = by[("leading_column", 0)]
        self.assertTrue(col.detail["prior"])
        self.assertEqual(col.detail["right_edge"], "own_clef")
        inside = col.detail["boxes_inside"]
        self.assertTrue(inside[R.glyph(0, 0, 0, 0, 1).to_key()]["through"]["through"])     # on the barline
        self.assertFalse(inside[R.glyph(0, 0, 0, 0, 2).to_key()]["through"]["through"])    # the blob
        self.assertGreaterEqual(by[("clef", 0)].detail["boxes_inside"][R.glyph(0, 0, 0, 0, 3).to_key()]["ink_share_inside"], 0.5)

    def test_flag_off_files_nothing(self):
        log = Log()
        with mock.patch.dict(os.environ, OFF):
            G.gather_claimed_register(log, _PWS(), [_Cell(0, (100, 50, 400, 250))], {0: (0, 0)}, {})
        self.assertEqual(list(log.rows(Q.CLAIMED_AREA, R.staff(0, 0, 0))), [])


def _box(log, gi, box, cls, cell=0, rest=False, conf=0.9):
    g = R.glyph(0, 0, 0, cell, gi)
    log.observe(g, Q.REST if rest else Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:0", score=conf)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=conf,
                category="rest" if rest else "notehead", bbox_page_px=[box[0], box[1], box[0] + box[2], box[1] + box[3]])
    log.observe(g, Q.GLYPH_CONF, conf, reader=READERS.DETECTOR, frame="cell:0")
    return g


def _claim(log, owner, entries, standing="READ", **extra):
    return log.observe(R.staff(0, 0, 0), Q.CLAIMED_AREA, [0.0, 0.0, 100.0, 100.0], reader=READERS.CV_CLAIMED_REGISTER,
                       frame="cell:0", cell=0, owner=owner, owner_row=None, unit="area", standing=standing, boxes_inside=entries, **extra)


def _v(log, g, env=ON, q=Q.NOTEHEAD_IS_NOT_A_NOTEHEAD):
    with mock.patch.dict(os.environ, env):
        adjudicate.run(log)
    return log.verdict(q, g)


class TestConsult(unittest.TestCase):
    def _fx(self, owner, entry, standing="READ", **extra):
        log = Log()
        _staff_space(log, 100)
        g = _box(log, 0, (300, 120, 130, 100), "noteheadBlackInSpace")
        _claim(log, owner, {g.to_key(): entry}, standing=standing, **extra)
        return log, g

    def test_a_read_clef_refuses(self):
        log, g = self._fx("clef", {"ink_share_inside": 0.9})
        v = _v(log, g)
        self.assertEqual((v.value, v.reason), (True, "claimed_by:clef"))

    def test_a_named_box_is_refused_even_with_a_stem_is_a_clef_parity(self):
        log, g = self._fx("clef", {"named": True})
        log.observe(R.cell(0, 0, 0, 0), Q.STEM, (430, 20, 4, 200), reader=READERS.CV_INK, frame="cell:0", x0=430, x1=434, y_center=75)
        self.assertEqual(_v(log, g).reason, "claimed_by:clef")

    def test_a_narrowed_clef_narrows_and_is_written_blue(self):
        log, g = self._fx("clef", {"ink_share_inside": 0.95}, standing="NARROWED")
        v = _v(log, g)
        self.assertEqual((v.outcome, v.reason), ("narrowed", "claim_narrowed:clef"))
        self.assertEqual(v.candidates[0].value, False)                   # the notehead first: written
        rec = E.Record({"record": log.to_json()})
        self.assertEqual(E.claim_guess_of(rec, g.to_key())["rule"], "claim_narrowed:clef")

    def test_the_detector_scoring_the_head_above_the_clef_narrows(self):
        log, g = self._fx("clef", {"ink_share_inside": 0.95}, owner_glyph=R.glyph(0, 0, 0, 0, 7).to_key())
        log.observe(R.glyph(0, 0, 0, 0, 7), Q.GLYPH_CONF, 0.3, reader=READERS.DETECTOR, frame="cell:0")
        self.assertEqual(_v(log, g).reason, "claim_narrowed:clef")

    def test_the_header_column_refuses_line_ink_and_narrows_other_ink(self):
        for through, want in ((True, ("decided", "claimed_by:leading_column")), (False, ("narrowed", "claim_narrowed:leading_column"))):
            log, g = self._fx("leading_column", {"ink_share_inside": 1.0, "through": {"through": through}}, prior=True)
            v = _v(log, g)
            self.assertEqual((v.outcome, v.reason), want, through)

    def test_CONTROL_a_stemmed_head_in_the_column_is_narrowed_not_refused(self):
        log, g = self._fx("leading_column", {"ink_share_inside": 1.0, "through": {"through": True}}, prior=True)
        log.observe(R.cell(0, 0, 0, 0), Q.STEM, (430, 20, 4, 200), reader=READERS.CV_INK, frame="cell:0", x0=430, x1=434, y_center=75)
        self.assertEqual(_v(log, g).outcome, "narrowed")

    def test_CONTROL_a_stemmed_head_inside_a_clef_box_is_kept(self):
        log, g = self._fx("clef", {"ink_share_inside": 0.95})
        log.observe(R.cell(0, 0, 0, 0), Q.STEM, (430, 20, 4, 200), reader=READERS.CV_INK, frame="cell:0", x0=430, x1=434, y_center=75)
        v = _v(log, g)
        self.assertEqual((v.outcome, v.value), ("decided", False))

    def test_CONTROL_under_the_cut_nothing(self):
        log, g = self._fx("clef", {"ink_share_inside": 0.3})
        self.assertEqual(_v(log, g).value, False)

    def test_the_meter_is_read_through_the_register(self):
        log, g = self._fx("meter", {"ink_share_inside": 0.95})
        self.assertEqual(_v(log, g).reason, "claimed_by:meter")
        log2, g2 = self._fx("meter", {"ink_share_inside": 0.95})
        self.assertEqual(_v(log2, g2, OFF).reason, "inside_the_meter")        # flag OFF: 2.177 unchanged

    def test_a_refusing_owner_outranks_a_narrowing_one(self):
        log = Log()
        _staff_space(log, 100)
        g = _box(log, 0, (300, 120, 130, 100), "noteheadBlackInSpace")
        _claim(log, "leading_column", {g.to_key(): {"ink_share_inside": 1.0, "through": {"through": False}}}, prior=True)
        _claim(log, "clef", {g.to_key(): {"ink_share_inside": 0.8}})
        v = _v(log, g)
        self.assertEqual(v.reason, "claimed_by:clef")
        self.assertEqual(len(v.used), 3)                                    # the box and BOTH claims

    def test_FLAG_OFF_the_old_is_a_clef_rule_still_runs(self):
        log = Log()
        _staff_space(log, 100)
        g = _box(log, 0, (300, 120, 130, 100), "noteheadBlackInSpace")
        log.observe(R.staff(0, 0, 0), Q.CLEF_LOCATED, "alto", reader=READERS.CV_LOCATOR, frame="cell:0", score=0.9,
                    overrode_glyph_subjects=[g.to_key()])
        self.assertEqual(_v(log, g, OFF).reason, "is_a_clef")
        log2 = Log()
        _staff_space(log2, 100)
        g2 = _box(log2, 0, (300, 120, 130, 100), "noteheadBlackInSpace")
        log2.observe(R.staff(0, 0, 0), Q.CLEF_LOCATED, "alto", reader=READERS.CV_LOCATOR, frame="cell:0", score=0.9,
                     overrode_glyph_subjects=[g2.to_key()])
        # flag ON with no register row filed: the old rule is retired, so the box is judged on shape (the gather files the claim)
        self.assertEqual(_v(log2, g2, ON).value, False)


class TestRest(unittest.TestCase):
    def test_a_rest_in_a_read_clef_is_refused_and_one_in_the_column_narrowed(self):
        for owner, entry, want in (("clef", {"ink_share_inside": 0.9}, ("decided", "claimed_by:clef")),
                                   ("leading_column", {"ink_share_inside": 0.9, "through": {"through": False}},
                                    ("narrowed", "claim_narrowed:leading_column"))):
            log = Log()
            _staff_space(log, 100)
            g = _box(log, 0, (300, 100, 60, 100), "restQuarter", rest=True)
            _claim(log, owner, {g.to_key(): entry})
            v = _v(log, g, q=Q.REST_IS_NOT_A_REST)
            self.assertEqual((v.outcome, v.reason), want, owner)

    def test_CONTROL_no_claim_rest_stands(self):
        log = Log()
        _staff_space(log, 100)
        g = _box(log, 0, (300, 100, 60, 100), "restQuarter", rest=True)
        self.assertEqual(_v(log, g, q=Q.REST_IS_NOT_A_REST).value, False)


if __name__ == "__main__":
    unittest.main()
