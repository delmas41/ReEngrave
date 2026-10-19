"""ROADMAP 2.172 (`OMR_DETECTOR_VIEWS`, default OFF): the detector looks at each symbol family at its own size, steadily.

STAGED GATHER only, a fake detector (no weights, no pdf): the phase median, the family-aware merge and the gather wiring. Controls that can fail:
a one-phase read of a box that only one of three phases found is KEPT with one phase and REFUSED with three; a view box on a same-family production box
is refused; a stronger production box of another family refuses it; a weaker one does not; the production list is never changed; the flag OFF
calls nothing."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import detector_views as DV
from tools.omr.staged import gather
from tools.omr.staged.record import ABSTAIN, Log, Q, READERS, cell as R_cell

LINES = [20.0, 40.0, 60.0, 80.0, 100.0]


# dataclasses.replace needs a dataclass: use the real one
from tools.omr.template_matcher import SymbolDetection   # noqa: E402


def D(name, conf, x, y, w=10, h=10):
    return SymbolDetection(cell=None, smufl_name=name, category="x", x_canonical=x, y_canonical=y,
                           width_canonical=w, height_canonical=h, confidence=conf)


class _Cell:
    def __init__(self):
        self.staff_line_ys_canonical = list(LINES)
        self.page_index, self.staff_index, self.measure_index = 0, 0, 3
        self.bbox_page_px, self.upscale_factor = None, None


class _ViewDetector:
    """detect_view returns, per view size, a scripted list of per-phase detections."""

    def __init__(self, script):
        self.script, self.calls = script, []

    def detect_view(self, cell, staff_space_px, *, shifts, anti_alias, conf_threshold):
        self.calls.append((staff_space_px, len(list(shifts)), anti_alias, conf_threshold))
        per = self.script.get(staff_space_px, [])
        return [list(per[i]) if i < len(per) else [] for i in range(len(list(shifts)))]


class TestPhaseMedian(unittest.TestCase):
    def test_two_of_three_phases_clear_the_floor(self):
        ph = [[D("augmentationDot", 0.40, 10, 10)], [D("augmentationDot", 0.30, 11, 10)], []]
        kept = DV.phase_median(ph, ("dot",))
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["phases"], [0, 1])
        self.assertAlmostEqual(kept[0]["conf"], 0.30)                                  # median of 0.40, 0.30, 0 (a phase with no box is 0)

    def test_one_of_three_does_not_clear_it_but_one_phase_would(self):
        three = [[D("augmentationDot", 0.60, 10, 10)], [], []]
        self.assertEqual(DV.phase_median(three, ("dot",)), [])               # the control: a lone lucky phase is a re-roll
        one = [[D("augmentationDot", 0.60, 10, 10)]]
        self.assertEqual(len(DV.phase_median(one, ("dot",))), 1)

    def test_only_the_views_families_are_taken(self):
        ph = [[D("noteheadBlackInSpace", 0.9, 10, 10), D("restQuarter", 0.9, 80, 10)]] * 3
        self.assertEqual([k["family"] for k in DV.phase_median(ph, ("rest",))], ["rest"])
        self.assertEqual([k["family"] for k in DV.phase_median(ph, ("blackhead",))], ["blackhead"])
        self.assertEqual(DV.phase_median(ph, ("dot",)), [])

    def test_two_boxes_of_one_family_apart_stay_two(self):
        ph = [[D("flag8thUp", 0.5, 10, 10), D("flag8thUp", 0.5, 200, 10)]] * 3
        self.assertEqual(len(DV.phase_median(ph, ("flag",))), 2)

    def test_the_recorded_confidence_is_the_median(self):
        ph = [[D("flag8thUp", 0.9, 10, 10)], [D("flag8thUp", 0.5, 10, 10)], [D("flag8thUp", 0.3, 10, 10)]]
        k = DV.phase_median(ph, ("flag",))[0]
        self.assertAlmostEqual(k["conf"], 0.5)
        self.assertAlmostEqual(k["det"].confidence, 0.5)
        self.assertEqual(k["phase_confs"], [0.9, 0.5, 0.3])


class TestMerge(unittest.TestCase):
    def _cand(self, name, conf, x, y, view="small"):
        fam = DV.family_of(name)
        return dict(det=D(name, conf, x, y), conf=conf, family=fam, **{'class': name}, phases=[0, 1, 2], phase_confs=[conf] * 3, view=view)

    def test_same_family_production_box_refuses_and_nothing_of_production_moves(self):
        prod = [D("augmentationDot", 0.4, 10, 10)]
        before = [(p.smufl_name, p.confidence, p.x_canonical) for p in prod]
        kept, refused = DV.merge_into_production([self._cand("augmentationDot", 0.9, 11, 10)], prod)
        self.assertEqual(kept, [])
        self.assertEqual(refused[0]["why"], "production_same_family")
        self.assertEqual(before, [(p.smufl_name, p.confidence, p.x_canonical) for p in prod])

    def test_an_empty_place_is_filled(self):
        kept, _ = DV.merge_into_production([self._cand("restQuarter", 0.5, 50, 10)], [D("noteheadBlackInSpace", 0.9, 200, 10)])
        self.assertEqual(len(kept), 1)

    def test_stronger_production_box_of_another_family_wins_weaker_does_not(self):
        cand = self._cand("noteheadBlackInSpace", 0.4, 10, 10, view="close")
        kept, refused = DV.merge_into_production([cand], [D("restWhole", 0.7, 10, 10)])
        self.assertEqual((kept, refused[0]["why"]), ([], "production_stronger"))
        kept, refused = DV.merge_into_production([cand], [D("restWhole", 0.3, 10, 10)])      # the lane's "head called a rest" case
        self.assertEqual(len(kept), 1)

    def test_a_black_head_view_box_on_any_production_head_is_refused(self):
        kept, refused = DV.merge_into_production([self._cand("noteheadBlackInSpace", 0.9, 10, 10, view="close")],
                                                 [D("noteheadHalfInSpace", 0.3, 10, 10)])
        self.assertEqual(refused[0]["why"], "production_same_family")

    def test_two_views_on_one_ink_keep_the_stronger(self):
        a = self._cand("restQuarter", 0.5, 10, 10)
        b = self._cand("noteheadBlackInSpace", 0.7, 10, 10, view="close")
        kept, refused = DV.merge_into_production([a, b], [])
        self.assertEqual([k["class"] for k in kept], ["noteheadBlackInSpace"])
        self.assertEqual(refused[0]["why"], "view_stronger")


class TestFlagsAndWiring(unittest.TestCase):
    def test_flag_is_off_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(DV.DETECTOR_VIEWS_ENV, None)
            self.assertFalse(DV.enabled())
        for on in ("1", "true", "yes", "on"):
            with mock.patch.dict(os.environ, {DV.DETECTOR_VIEWS_ENV: on}):
                self.assertTrue(DV.enabled())
        for off in ("0", "", "false", "off", "no"):
            with mock.patch.dict(os.environ, {DV.DETECTOR_VIEWS_ENV: off}):
                self.assertFalse(DV.enabled())

    def test_sub_switches(self):
        with mock.patch.dict(os.environ, {DV.PARTS_ENV: "views,aa"}):
            self.assertEqual(DV.n_phases(), 1)
            self.assertIn("aa", DV.parts())
        with mock.patch.dict(os.environ, {DV.PARTS_ENV: "views,phase"}):
            self.assertEqual(DV.n_phases(), 3)
            self.assertNotIn("aa", DV.parts())
        with mock.patch.dict(os.environ, {DV.WHICH_ENV: "close"}):
            self.assertEqual(DV.active_views(), ["close"])

    def _gather(self, script, existing):
        det = _ViewDetector(script)
        log = Log()
        key = R_cell(0, 0, 0, 3).to_key()
        detections = {key: list(existing)} if existing else {}
        gather.gather_detector_views(log, [_Cell()], {0: (0, 0)}, detections, detector=det)
        return log, detections, det, key

    def test_a_kept_view_box_is_appended_and_carries_its_provenance(self):
        three = [[D("restQuarter", 0.6, 50, 30)]] * 3
        prod = [D("noteheadBlackInSpace", 0.9, 150, 30)]
        with mock.patch.dict(os.environ, {DV.PARTS_ENV: "views,aa,phase"}):
            log, dets, det, key = self._gather({8.0: three}, prod)
        self.assertEqual(len(dets[key]), 2)
        self.assertEqual(dets[key][0].smufl_name, "noteheadBlackInSpace")                   # production is first and untouched
        rows = [o for o in log._obs.values() if o.quantity == Q.GLYPH_BOX and o.reader == READERS.DETECTOR_VIEW]
        self.assertEqual(len(rows), 1)
        d = rows[0].detail
        self.assertEqual((d["view"], d["staff_space_px"], d["anti_alias"], d["phases_found"], d["n_phases"]), ("small", 8.0, True, [0, 1, 2], 3))
        self.assertEqual(rows[0].subject.to_key().split("/")[-1], "1")                         # glyph index after the production box
        self.assertEqual(det.calls[0][0], 8.0)
        self.assertEqual(det.calls[0][3], DV.READ_FLOOR)

    def test_a_refused_near_miss_is_on_the_record_but_a_same_family_repeat_is_not(self):
        script = {8.0: [[D("restQuarter", 0.4, 50, 30), D("augmentationDot", 0.9, 150, 30)]] * 3}
        prod = [D("noteheadBlackInSpace", 0.8, 50, 30), D("augmentationDot", 0.5, 150, 30)]
        log, dets, _, key = self._gather(script, prod)
        self.assertEqual(len(dets[key]), 2)
        ab = [a for a in log._abs.values() if a.reader == READERS.DETECTOR_VIEW]
        self.assertEqual([a.detail.get("why") for a in ab], ["production_stronger"])
        self.assertEqual(ab[0].reason, ABSTAIN.AMBIGUOUS)

    def test_a_detector_without_views_is_skipped_and_a_throwing_one_abstains(self):
        class Old:
            pass
        log = Log()
        gather.gather_detector_views(log, [_Cell()], {0: (0, 0)}, {}, detector=Old())
        self.assertEqual(list(log._abs.values()), [])

        class Boom(_ViewDetector):
            def detect_view(self, *a, **k):
                raise RuntimeError("x")
        log = Log()
        gather.gather_detector_views(log, [_Cell()], {0: (0, 0)}, {}, detector=Boom({}))
        ab = [a for a in log._abs.values() if a.reader == READERS.DETECTOR_VIEW]
        self.assertEqual([a.reason for a in ab], [ABSTAIN.READER_UNAVAILABLE])


if __name__ == "__main__":
    unittest.main()
