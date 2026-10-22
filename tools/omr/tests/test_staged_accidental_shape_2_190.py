"""ROADMAP 2.190 -- the accidental SHAPE check (flag `OMR_ACCIDENTAL_SHAPE`, default OFF), on top of 2.186's merge.

Every test that says the shape CHOOSES has a twin that says it must not (an unclear shape, a shape the detector did not offer, a single class,
the flag OFF), and the shape reader has a control that fails when its windows are broken."""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import accidental_shape as AS
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests import test_staged_accidental as TA

ONE = "OMR_ONE_INK_ONE_MARK"
SHAPE = "OMR_ACCIDENTAL_SHAPE"
H, W = 60, 24


def _blank():
    return np.zeros((H, W), bool)


def flat():
    a = _blank()
    a[:, 2:6] = True                       # one tall stem on the left, to the bottom
    a[36:40, 6:20] = True                  # the bowl: top bar, right side, bottom bar
    a[36:60, 16:20] = True
    a[56:60, 6:20] = True
    return a


def natural():
    a = _blank()
    a[0:40, 2:6] = True                    # left stem: up, stops above the bottom
    a[20:60, 18:22] = True                 # right stem: starts below the top, runs down
    a[20:24, 2:22] = True                  # the two slanted bars (drawn level)
    a[36:40, 2:22] = True
    return a


def sharp():
    a = _blank()
    a[:, 3:7] = True                       # two verticals, both full height
    a[:, 17:21] = True
    a[20:24, 0:24] = True                  # two bars crossing both, extending past both
    a[36:40, 0:24] = True
    return a


def img_of(ink, pad=6):
    img = np.full((H + 2 * pad, W + 2 * pad), 255, np.uint8)
    img[pad:pad + H, pad:pad + W][ink] = 0
    return img, (pad, pad, W, H)


def shape_of(ink):
    img, box = img_of(ink)
    return AS.classify(AS.measure(img, box))["shape"]


class TestShapeReader(unittest.TestCase):

    def test_the_three_shapes_read_as_themselves(self):
        self.assertEqual(shape_of(flat()), "flat")
        self.assertEqual(shape_of(natural()), "natural")
        self.assertEqual(shape_of(sharp()), "sharp")

    def test_CONTROL_a_flipped_natural_is_not_a_natural(self):
        """A natural turned upside down has its left stem at the BOTTOM-left and a stem at the top-right: an arrangement no printed accidental
        has -> unclear/other, never `natural`. Fails if the corners were read the wrong way round."""
        self.assertNotEqual(shape_of(natural()[::-1]), "natural")

    def test_CONTROL_broken_windows_cannot_tell_a_natural_from_a_sharp(self):
        """Make both windows cover the whole glyph: every shape fills both -> the test above (natural vs sharp) must then fail to hold."""
        with mock.patch.object(AS, "WINDOW_W", 1.0), mock.patch.object(AS, "WINDOW_H", 1.0):
            self.assertNotEqual(shape_of(natural()), "natural")

    def test_a_speck_or_blank_box_is_unread_not_a_shape(self):
        img = np.full((40, 40), 255, np.uint8)
        self.assertEqual(AS.classify(AS.measure(img, (5, 5, 20, 20)))["shape"], "unread")
        img[10:12, 10:12] = 0
        self.assertEqual(AS.classify(AS.measure(img, (5, 5, 20, 20)))["shape"], "unread")

    def test_a_corner_between_the_zones_is_unclear(self):
        self.assertEqual(AS.classify({"bl": 0.4, "tr": 0.02})["shape"], "unclear")
        self.assertEqual(AS.classify({"bl": 0.9, "tr": 0.02})["shape"], "flat")

    def test_it_never_reads_a_raster_with_the_dust_of_a_neighbour(self):
        ink = natural()
        img, box = img_of(ink)
        img[6:9, 6 + 16:6 + 23] = 0          # a small mote in the top right corner, under 8% of the ink
        self.assertEqual(AS.classify(AS.measure(img, box))["shape"], "natural")


class TestChoose(unittest.TestCase):
    N = {"shape": "natural"}

    def test_a_clear_shape_that_names_an_offered_class_is_picked(self):
        self.assertEqual(AS.choose(["accidentalFlat", "accidentalNatural"], self.N)["pick"], "accidentalNatural")

    def test_never_a_class_the_detector_did_not_offer(self):
        r = AS.choose(["accidentalFlat", "accidentalSharp"], self.N)
        self.assertIsNone(r["pick"])
        self.assertEqual(r["why"], "shape_not_offered")

    def test_unclear_unread_and_one_class_pick_nothing(self):
        self.assertEqual(AS.choose(["accidentalFlat", "accidentalNatural"], {"shape": "unclear"})["why"], "unclear")
        self.assertEqual(AS.choose(["accidentalFlat", "accidentalNatural"], {"shape": "unread"})["why"], "unread")
        self.assertEqual(AS.choose(["accidentalFlat"], self.N)["why"], "unambiguous")

    def test_double_sharp_among_the_candidates_is_never_picked(self):
        self.assertEqual(AS.choose(["accidentalSharp", "accidentalDoubleSharp"], {"shape": "sharp"})["pick"], "accidentalSharp")
        self.assertIsNone(AS.choose(["accidentalDoubleFlat", "accidentalDoubleSharp"], {"shape": "sharp"})["pick"])


def _merged(shape, winner="accidentalFlat", rival="accidentalNatural", single=False, flag_shape=True, flag_one=True):
    """One merged accidental glyph (winner flat 0.8, rival natural 0.6) with a head to its right and a filed shape; returns (log, glyph)."""
    log = Log()
    TA._cell_unit(log)
    g = R.glyph(0, 0, 0, 0, 0)
    y0 = 4 * TA.HALF - TA.SPACE
    log.observe(g, Q.GLYPH_BOX, (winner, 88.0, y0, 12.0, TA.SPACE * 2), reader=READERS.DETECTOR, frame="cell:0", score=0.8, category="accidental")
    alt = {"accidentalFlat": "b", "accidentalNatural": "n", "accidentalSharp": "#"}
    extra = {}
    if not single:
        extra["one_ink"] = {"rivals": [{"class": rival, "conf": 0.6}], "margin": 0.2, "winner": {"class": winner, "conf": 0.8}, "iou_min": 0.5}
        extra["position_by_class"] = {winner: {"alteration": alt[winner], "position": 4.0, "anchor_fraction": 0.5},
                                      rival: {"alteration": alt[rival], "position": 5.0, "anchor_fraction": 0.5}}
    log.observe(g, Q.ACCIDENTAL_STAFF_POSITION, 4.0, reader=READERS.GEOMETRY, frame="cell:0", alteration=alt[winner], detector_class=winner,
                anchor_fraction=0.5, box_centre_position=4.0, residual=0.0, rounded=4, x0=88.0, x1=100.0, y0=y0, y1=y0 + 2 * TA.SPACE,
                confidence=0.8, shape=shape, **extra)
    TA._head(log, 1, 106.0, 4.0)
    TA._head(log, 2, 106.0, 5.0, w=TA.HEAD_W)   # a second head one step away: ambiguity unless the position moved with the class
    env = {ONE: "1" if flag_one else "0", SHAPE: "1" if flag_shape else "0"}
    with mock.patch.dict(os.environ, env):
        TA._decide(log)
    return log, g


NAT = {"bl": 0.0, "tr": 0.0, "shape": "natural"}
FLAT = {"bl": 0.8, "tr": 0.0, "shape": "flat"}
SHARP = {"bl": 0.8, "tr": 0.8, "shape": "sharp"}
UNCL = {"bl": 0.28, "tr": 0.0, "shape": "unclear"}


class TestChoiceAmongCandidates(unittest.TestCase):

    def _ow(self, *a, **k):
        log, g = _merged(*a, **k)
        return log.verdict(Q.ACCIDENTAL_OWNER, g)

    def test_a_natural_shape_over_a_flat_winner_writes_the_natural(self):
        v = self._ow(NAT)
        self.assertEqual(v.detail["alteration"], "n")
        self.assertEqual(v.detail["detector_class"], "accidentalNatural")
        oi = v.detail["one_ink"]
        self.assertEqual(oi["winner"]["class"], "accidentalNatural")
        self.assertEqual(oi["chosen_by"], "shape")
        self.assertIn("accidentalFlat", [r["class"] for r in oi["rivals"]])      # both candidates stay
        self.assertEqual(v.detail["shape_check"]["switched_from"], "accidentalFlat")

    def test_TWIN_flag_off_the_flat_stays(self):
        v = self._ow(NAT, flag_shape=False)
        self.assertEqual(v.detail["alteration"], "b")
        self.assertNotIn("shape_check", v.detail)

    def test_TWIN_an_unclear_shape_leaves_the_confidence_winner_and_both_candidates(self):
        v = self._ow(UNCL)
        self.assertEqual(v.detail["alteration"], "b")
        self.assertEqual({r["class"] for r in v.detail["one_ink"]["rivals"]}, {"accidentalNatural"})
        self.assertEqual(v.detail["shape_check"]["why"], "unclear")

    def test_TWIN_a_shape_the_detector_did_not_offer_is_never_invented(self):
        v = self._ow(SHARP)
        self.assertEqual(v.detail["alteration"], "b")
        self.assertEqual(v.detail["shape_check"]["why"], "shape_not_offered")

    def test_a_shape_that_agrees_with_the_winner_changes_nothing(self):
        v = self._ow(FLAT)
        self.assertEqual(v.detail["alteration"], "b")
        self.assertTrue(v.detail["shape_check"]["agrees_with_winner"])
        self.assertNotIn("chosen_by", v.detail["one_ink"])

    def test_TWIN_a_single_class_is_recorded_never_moved(self):
        v = self._ow(NAT, single=True)
        self.assertEqual(v.detail["alteration"], "b")
        self.assertEqual(v.detail["shape_check"]["why"], "unambiguous")

    def test_the_position_follows_the_chosen_class(self):
        """The natural anchors one step lower (position 5.0 here) than the flat (4.0): the owner is the head at 5.0, not the one at 4.0."""
        log, g = _merged(NAT)
        v = log.verdict(Q.ACCIDENTAL_OWNER, g)
        self.assertEqual(v.outcome, "decided")
        self.assertAlmostEqual(v.detail["accidental_position"], 5.0, places=2)

    def test_it_is_always_written_guessed_never_read(self):
        from tools.omr.staged import one_ink as OI
        self.assertIsNone(AS.SHAPE_READ)
        self.assertFalse(AS.reads_shape(9.9))
        self.assertFalse(OI.reads(0.5))


class TestLaneReportReplayOfAGatheredRecord(unittest.TestCase):
    """The lane report may replay ADJUDICATE..EXPORT of a record gathered with the GATHER-side flags on, for both arms, ONLY when told so."""

    def test_refused_without_the_option_allowed_with_it(self):
        from tools.omr.staged import lane_report as L
        orig = L.flag_homes
        L.flag_homes = lambda f, root=None: ["staged/gather.py"]
        try:
            with self.assertRaises(SystemExit):
                L.decide_from("adjudicate", [("OMR_X", "0", "1")], False)
            mode, notes = L.decide_from("adjudicate", [("OMR_X", "0", "1")], False, replay_gathered=True)
            self.assertEqual(mode, "adjudicate")
            self.assertTrue(any("REPLAY OF A RECORD GATHERED" in n for n in notes))
            with self.assertRaises(SystemExit):
                L.decide_from("gather", [("OMR_X", "0", "1")], False, replay_gathered=True)
        finally:
            L.flag_homes = orig


if __name__ == "__main__":
    unittest.main()
