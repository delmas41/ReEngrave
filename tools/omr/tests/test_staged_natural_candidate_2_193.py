"""ROADMAP 2.193 -- the sub-floor NATURAL as a candidate (flag `OMR_NATURAL_CANDIDATE`, default ON), for an ink that already holds a flat/sharp box.

Every test that says the natural IS chosen has a twin that says it must not: flag OFF, shape not natural, score under the lower bound, an ink
with no accidental box at all, a natural the detector already offered."""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr import natural_candidate as NC
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests import test_staged_accidental as TA

ONE, SHAPE, NATC = "OMR_ONE_INK_ONE_MARK", "OMR_ACCIDENTAL_SHAPE", "OMR_NATURAL_CANDIDATE"
NAT = {"bl": 0.0, "tr": 0.0, "shape": "natural"}
FLAT = {"bl": 0.8, "tr": 0.0, "shape": "flat"}
UNCL = {"bl": 0.28, "tr": 0.0, "shape": "unclear"}


def _ink(shape, cls="accidentalSharp", nat_conf=0.12, flag=True, rival=None):
    """One accidental glyph the detector drew as `cls` (conf 0.8), a head at the sharp's position and another one step lower (where a natural anchors)."""
    log = Log()
    TA._cell_unit(log)
    g = R.glyph(0, 0, 0, 0, 0)
    y0 = 4 * TA.HALF - TA.SPACE
    log.observe(g, Q.GLYPH_BOX, (cls, 88.0, y0, 12.0, TA.SPACE * 2), reader=READERS.DETECTOR, frame="cell:0", score=0.8, category="accidental")
    extra = {}
    if nat_conf is not None:
        extra["natural_candidate"] = {"conf": nat_conf, "alteration": "natural", "anchor_fraction": 0.5, "position": 5.0}
    if rival:
        extra["one_ink"] = {"rivals": [{"class": rival, "conf": 0.5}], "margin": 0.3, "winner": {"class": cls, "conf": 0.8}, "iou_min": 0.5}
        extra["position_by_class"] = {cls: {"alteration": "#", "position": 4.0, "anchor_fraction": 0.5},
                                      rival: {"alteration": "natural" if rival == "accidentalNatural" else "b", "position": 5.0, "anchor_fraction": 0.5}}
    log.observe(g, Q.ACCIDENTAL_STAFF_POSITION, 4.0, reader=READERS.GEOMETRY, frame="cell:0", alteration="#", detector_class=cls,
                anchor_fraction=0.5, box_centre_position=4.0, residual=0.0, rounded=4, x0=88.0, x1=100.0, y0=y0, y1=y0 + 2 * TA.SPACE,
                confidence=0.8, shape=shape, **extra)
    TA._head(log, 1, 106.0, 4.0)
    TA._head(log, 2, 106.0, 5.0, w=TA.HEAD_W)
    env = {ONE: "1", SHAPE: "1", NATC: "1" if flag else "0"}
    with mock.patch.dict(os.environ, env):
        TA._decide(log)
    return log.verdict(Q.ACCIDENTAL_OWNER, g)


class TestNaturalAsCandidate(unittest.TestCase):

    def test_a_natural_shape_with_a_sub_floor_natural_score_writes_the_natural_guessed(self):
        v = _ink(NAT)
        self.assertEqual(v.detail["alteration"], "natural")
        self.assertEqual(v.detail["detector_class"], "accidentalNatural")
        oi = v.detail["one_ink"]
        self.assertEqual(oi["winner"]["class"], "accidentalNatural")
        self.assertEqual(oi["chosen_by"], "shape")
        self.assertIn("accidentalSharp", [r["class"] for r in oi["rivals"]])          # both candidates stay, with their scores
        self.assertAlmostEqual(oi["winner"]["conf"], 0.12)
        self.assertAlmostEqual(v.detail["accidental_position"], 5.0, places=2)         # the position follows the class

    def test_it_also_works_inside_a_2_186_merge(self):
        v = _ink(NAT, cls="accidentalFlat", rival="accidentalSharp")
        self.assertEqual(v.detail["alteration"], "natural")
        self.assertEqual({r["class"] for r in v.detail["one_ink"]["rivals"]}, {"accidentalFlat", "accidentalSharp"})

    def test_TWIN_flag_off_the_sharp_stays(self):
        v = _ink(NAT, flag=False)
        self.assertEqual(v.detail["alteration"], "#")
        self.assertEqual(v.detail["shape_check"]["why"], "unambiguous")

    def test_TWIN_a_flat_shape_never_takes_the_natural(self):
        v = _ink(FLAT, cls="accidentalFlat")
        self.assertNotEqual(v.detail["alteration"], "natural")

    def test_TWIN_an_unclear_shape_never_takes_the_natural(self):
        v = _ink(UNCL)
        self.assertEqual(v.detail["alteration"], "#")
        self.assertNotIn("one_ink", v.detail)                                           # a candidate not chosen leaves no trace on the mark

    def test_TWIN_a_score_under_the_lower_bound_is_not_a_candidate(self):
        v = _ink(NAT, nat_conf=NC.LOWER_BOUND - 0.01)
        self.assertEqual(v.detail["alteration"], "#")

    def test_TWIN_no_natural_score_no_natural(self):
        v = _ink(NAT, nat_conf=None)
        self.assertEqual(v.detail["alteration"], "#")

    def test_TWIN_a_natural_the_detector_already_offered_is_not_doubled(self):
        v = _ink(NAT, cls="accidentalFlat", rival="accidentalNatural", nat_conf=0.1)
        rivals = [r["class"] for r in v.detail["one_ink"]["rivals"]]
        self.assertEqual(rivals.count("accidentalNatural") + (v.detail["one_ink"]["winner"]["class"] == "accidentalNatural"), 1)

    def test_default_is_on(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(NATC, None)
            self.assertTrue(NC.enabled())
        for off in ("0", "false", "no", "off"):
            with mock.patch.dict(os.environ, {NATC: off}):
                self.assertFalse(NC.enabled())


class TestDetectorSide(unittest.TestCase):

    def _det(self, name, box, cat="accidental"):
        from tools.omr.template_matcher import SymbolDetection
        x, y, w, h = box
        return SymbolDetection(cell=None, smufl_name=name, category=cat, x_canonical=x, y_canonical=y, width_canonical=w, height_canonical=h, confidence=0.8)

    def _attach(self, dets, nscore, nbox_xywh):
        from tools.omr import detector_cache as DC
        from tools.omr.yolo_detector import YoloDetector
        aux = dict(arrays={"nidx0": np.arange(len(nscore), dtype=np.int32), "nbox0": np.array(nbox_xywh, np.float32),
                           "nscore0": np.array(nscore, np.float32)}, img_shape=[100, 100], floor=0.05)
        with mock.patch.object(DC, "last_aux", return_value=aux):
            return YoloDetector._attach_natural_scores(dets, (100, 100, 3))

    def test_the_score_is_taken_from_the_anchor_over_the_same_ink_and_only_there(self):
        d = self._det("accidentalSharp", (40, 40, 10, 20))
        out = self._attach([d], [0.31, 0.9], [[45, 50, 10, 20], [10, 10, 10, 20]])    # the second anchor is elsewhere: ignored even at 0.9
        self.assertAlmostEqual(out[0].natural_score, 0.31, places=3)

    def test_TWIN_no_anchor_over_the_ink_no_score(self):
        d = self._det("accidentalSharp", (40, 40, 10, 20))
        out = self._attach([d], [0.9], [[10, 10, 10, 20]])
        self.assertIsNone(out[0].natural_score)

    def test_TWIN_only_accidental_boxes_flat_or_sharp_get_one(self):
        ds = [self._det("noteheadBlack", (40, 40, 10, 20), "notehead"), self._det("keyFlat", (40, 40, 10, 20)),
              self._det("accidentalNatural", (40, 40, 10, 20))]
        out = self._attach(ds, [0.5], [[45, 50, 10, 20]])
        self.assertTrue(all(o.natural_score is None for o in out))

    def test_the_aux_arrays_keep_an_anchor_whose_best_class_is_another_class(self):
        import torch
        from tools.omr import detector_cache as DC
        pred = torch.zeros((1, 4 + 3, 4))
        pred[0, 4 + 0, 0] = 0.9           # anchor 0: class 0 wins
        pred[0, 4 + 2, 0] = 0.3           # ... natural (class 2) also scores 0.3 there
        pred[0, 4 + 2, 1] = 0.07          # anchor 1: only a faint natural
        a = DC._aux_arrays(pred, 2, 0.05)
        self.assertEqual(sorted(a["nidx0"].tolist()), [0, 1])
        c, _ = DC._candidates(pred, 0.25)
        self.assertEqual(c["idx0"].tolist(), [0])                                       # the standard candidates never held the natural
        self.assertEqual(DC._aux_arrays(pred, 2, 0.5)["nidx0"].tolist(), [])


if __name__ == "__main__":
    unittest.main()
