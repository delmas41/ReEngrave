"""ROADMAP 2.161 (STAGED GATHER `gather.head_stem_bridge` + ADJUDICATE `rhythm.adjudicate_duration` first step), flag
`OMR_HEAD_STEM_BRIDGE`, default OFF.

Sean 2026-10-17: "I'm not sure why it doesn't see simple half notes" / "Yes to both" (go after the box and stem readers).
Measured on the 20261016-night records: of 2.159's real-note Litolff heads with no stem touching the detector box, the
biggest single cause is a stem the stem finder FOUND standing 0.13-0.27 sp beside a box that stops short of the head's stem
side. The head's own ink bridging that gap makes it the head's stem at 2.148's first step. Each positive has a control that
differs only in the evidence (CLAUDE.md rule 7); the real-raster pair is crop 22 of `litolff-unread-35` and a black head on
the same page with a stem the same distance away across WHITE."""
from __future__ import annotations

import os
import pathlib
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import READERS, Log, Outcome, Q
from tools.omr.staged import record as R
from tools.omr.line_detection import _binary_ink
from tools.omr.tests.test_staged_bare_stem_2_81 import CELL, _stem, _two_staff
from tools.omr.tests.test_staged_head_fill_first_2_148 import _run

FLAG = rhythm.HEAD_STEM_BRIDGE_ENV
DATA = pathlib.Path(__file__).with_name("data_head_stem_bridge_2_161.npz")
HOLLOW_WINDOWS = {"best": 0.8, "best_window": "ring", "windows": {"center": 0.3, "ring": 0.8}}


# ─────────────────────────────────────────────────────────────────────────────
# GATHER: the ruler
# ─────────────────────────────────────────────────────────────────────────────


def _page(gap_ink: bool, *, sp=16, stem_x=40):
    """255 paper / 0 ink. A head box at x 46..66 (y 50..66); a stem at `stem_x` (4 wide, y 20..90); the head's ink runs
    left out of its box to the stem when `gap_ink`."""
    img = np.full((120, 120), 255, np.uint8)
    img[50:66, 46:66] = 0
    img[20:90, stem_x:stem_x + 4] = 0
    if gap_ink:
        img[56:62, stem_x + 4:46] = 0
    return _binary_ink(img), (46.0, 50.0, 20.0, 16.0), [(float(stem_x), 20.0, 4.0, 70.0)]


class TestTheRuler(unittest.TestCase):

    def test_head_ink_running_into_a_stem_beside_the_box_is_read(self):
        ink, box, stems = _page(True)
        r = G.head_stem_bridge(ink, box, stems, 16.0)
        self.assertIsNotNone(r)
        self.assertEqual(r["side"], "left")
        self.assertEqual(r["bridge_rows"], 6)
        self.assertEqual(r["bridged_box"], [44.0, 50.0, 22.0, 16.0])
        self.assertTrue(r["stem_below"] and r["stem_above"])

    def test_control_white_between_head_and_stem_is_not_a_bridge(self):
        ink, box, stems = _page(False)
        self.assertIsNone(G.head_stem_bridge(ink, box, stems, 16.0))

    def test_a_stem_touching_the_box_is_not_this_readers(self):
        ink, box, stems = _page(True, stem_x=44)
        self.assertIsNone(G.head_stem_bridge(ink, box, stems, 16.0))

    def test_another_heads_box_in_the_gap_makes_the_ink_its_own(self):
        ink, box, stems = _page(True)
        self.assertIsNone(G.head_stem_bridge(ink, box, stems, 16.0,
                                             [("noteheadBlackOnLine", (42.0, 52.0, 6.0, 10.0))]))

    def test_a_head_and_gap_wider_than_one_head_is_not_read(self):
        """box 20 px + gap 12 px = 2.0 sp > 1.9 sp (2.148's head-sized ceiling)."""
        img = np.full((120, 120), 255, np.uint8)
        img[50:66, 46:66] = 0
        img[20:90, 30:34] = 0
        img[56:62, 34:46] = 0
        self.assertIsNone(G.head_stem_bridge(_binary_ink(img), (46.0, 50.0, 20.0, 16.0), [(30.0, 20.0, 4.0, 70.0)], 16.0))

    def test_the_ceiling_is_2_148s_own(self):
        self.assertEqual(G.STEM_BRIDGE_MAX_HEAD_WIDTH_SPACES, rhythm.HEAD_BOX_MAX_WIDTH_SPACES)

    @unittest.skipUnless(DATA.exists(), "fixture")
    def test_real_litolff_crop_22_is_bridged(self):
        d = np.load(DATA)
        r = G.head_stem_bridge(_binary_ink(d["pos_img"]), tuple(d["pos_head"]), [tuple(s) for s in d["pos_stems"]], 100.0)
        self.assertIsNotNone(r)
        self.assertEqual(r["side"], "left")
        self.assertAlmostEqual(r["gap_sp"], 0.25)
        self.assertTrue(r["stem_below"])

    @unittest.skipUnless(DATA.exists(), "fixture")
    def test_control_real_litolff_black_head_with_a_white_gap_to_a_stem(self):
        d = np.load(DATA)
        self.assertIsNone(G.head_stem_bridge(_binary_ink(d["neg_img"]), tuple(d["neg_head"]),
                                             [tuple(s) for s in d["neg_stems"]], 100.0))


class TestTheGatherFilesIt(unittest.TestCase):
    """`gather_notehead_ink` files the reading in `Q.NOTEHEAD_INK.detail.stem_bridge` for a head no stem touches."""

    def _gather(self, gap_ink):
        img = np.full((120, 120), 255, np.uint8)
        img[50:66, 46:66] = 0
        img[20:90, 40:44] = 0
        if gap_ink:
            img[56:62, 44:46] = 0
        cell = SimpleNamespace(page_index=0, staff_index=0, measure_index=0, binary=img.copy(), image_no_staff=img.copy(),
                               staff_line_ys_canonical=[34.0, 50.0, 66.0, 82.0, 98.0])
        det = SimpleNamespace(smufl_name="noteheadBlackInSpace", x_canonical=46, y_canonical=50, width_canonical=20,
                              height_canonical=16, x_center=56.0, y_center=58.0)
        log = Log()
        log.observe(R.cell(0, 0, 0, 0), Q.STEM, (40, 20, 4, 70), reader=READERS.CV_LINES, frame="cell:0")
        with mock.patch.dict(os.environ, {"OMR_RECENTRE_PART_BOXED": "0"}):
            G.gather_notehead_ink(log, [cell], {0: (0, 0)}, {R.cell(0, 0, 0, 0).to_key(): [det]})
        rows = log.rows(Q.NOTEHEAD_INK, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(len(rows), 1)
        return rows[0].detail.get("stem_bridge")

    def test_filed(self):
        sb = self._gather(True)
        self.assertIsNotNone(sb)
        self.assertEqual(sb["stem_box"], [40.0, 20.0, 4.0, 70.0])
        self.assertIn("interior_white_bridged", sb)

    def test_control_not_filed_across_white(self):
        self.assertIsNone(self._gather(False))


# ─────────────────────────────────────────────────────────────────────────────
# ADJUDICATE: 2.148's first step
# ─────────────────────────────────────────────────────────────────────────────

#: `_two_staff`'s head is (100, 90, 20, 16) at space 16: head-sized. The stem stands 4 px (0.25 sp) to its left, y 60..110.
STEM = (92, 60, 4, 50)


def _bridged(log, *, share=0.4, side="left", below=True, above=True, stem=STEM, file_stem=True, bridge=True,
             narrow=False, bridged_share=0.4, window_hollow=True):
    g = _two_staff(log)
    if file_stem:
        _stem(log, x=stem[0], y=stem[1], w=stem[2], h=stem[3])
    if narrow:   # 16 px = 1.0 sp wide (< 1.1): not head-sized; the box extended to the stem is 1.25 sp
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 104, 90, 16, 16), reader=READERS.DETECTOR, frame="cell:0",
                    score=0.9, bbox_page_px=[1104, 990, 1120, 1006])
    extra = {}
    if bridge:
        hx = 104 if narrow else 100
        extra["stem_bridge"] = {"side": side, "gap_sp": round((hx - 96) / 16.0, 3), "bridge_rows": 6, "rows_read": 16,
                                "stem_box": [float(v) for v in stem], "stem_below": below, "stem_above": above,
                                "bridged_box": [96.0, 90.0, float(hx + (16 if narrow else 20) - 96), 16.0],
                                "interior_white_bridged": {"rows_share": bridged_share, "hole_share": 0.0, "rows_read": 8,
                                                           "box": [96, 90, 24, 16]}}
    log.observe(g, Q.NOTEHEAD_INK, 1.0, reader=READERS.CV_NOTEHEAD_INK, frame="cell:0",
                ink_raw=(HOLLOW_WINDOWS if window_hollow
                         else {"best": 1.0, "best_window": "center", "windows": {"center": 1.0, "ring": 0.8}}),
                interior_white={"rows_share": share, "hole_share": 0.0, "rows_read": 8, "box": [100, 90, 20, 16]},
                **extra)
    return g


def _decide(log, g, on=True):
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        _run(log)
    return log.verdict(Q.DURATION, g)


def _written(v):
    return (v.value or {}).get("written")


class TestTheBridgedStemIsTheHeadsOwn(unittest.TestCase):

    def test_a_hollow_head_whose_ink_runs_into_a_stem_is_a_half(self):
        log = Log()
        g = _bridged(log)
        v = _decide(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(_written(v), 2.0)
        hf = v.detail["head_fill_first"]
        self.assertEqual(hf["settled"], "half_on_a_stem")
        self.assertEqual(hf["stem_bridge"]["side"], "left")

    def test_control_flag_off_no_half_at_the_first_step(self):
        log = Log()
        g = _bridged(log)
        v = _decide(log, g, on=False)
        self.assertNotEqual((v.detail.get("head_fill_first") or {}).get("settled"), "half_on_a_stem")

    def test_control_no_bridge_reading_is_the_flag_off_verdict(self):
        on, off = Log(), Log()
        g1, g2 = _bridged(on, bridge=False), _bridged(off, bridge=False)
        v1, v2 = _decide(on, g1), _decide(off, g2, on=False)
        self.assertEqual((v1.outcome, v1.reason, v1.value), (v2.outcome, v2.reason, v2.value))

    def test_control_a_black_head_is_never_made_a_half(self):
        log = Log()
        g = _bridged(log, share=0.0)
        v = _decide(log, g)
        self.assertNotEqual(_written(v), 2.0)

    def test_control_a_left_stem_that_does_not_run_below_is_the_wrong_side(self):
        """Stems up -> right, down -> left: a stem at the head's LEFT that only runs ABOVE it is not its stem."""
        log = Log()
        g = _bridged(log, below=False, above=True)
        self.assertNotEqual(_decide(log, g).detail["head_fill_first"].get("settled"), "half_on_a_stem")

    def test_control_the_stem_must_still_be_on_the_record(self):
        log = Log()
        g = _bridged(log, file_stem=False)
        self.assertNotEqual(_decide(log, g).detail["head_fill_first"].get("settled"), "half_on_a_stem")


class TestTheNarrowBoxExtendedToItsStem(unittest.TestCase):

    def test_a_narrow_box_read_hollow_on_the_box_extended_to_its_stem_is_a_half(self):
        log = Log()
        g = _bridged(log, narrow=True, share=0.0)
        v = _decide(log, g)
        self.assertEqual(_written(v), 2.0)
        hf = v.detail["head_fill_first"]
        self.assertTrue(hf["bridged_box"])
        self.assertEqual(hf["detector_box_rows_share"], 0.0)

    def test_control_flag_off_the_narrow_box_is_not_read(self):
        log = Log()
        g = _bridged(log, narrow=True, share=0.0)
        v = _decide(log, g, on=False)
        self.assertTrue(v.detail["head_fill_first"]["not_head_sized"])
        self.assertNotEqual(v.detail["head_fill_first"].get("settled"), "half_on_a_stem")

    def test_control_solid_on_the_extended_box(self):
        log = Log()
        g = _bridged(log, narrow=True, share=0.0, bridged_share=0.03)
        self.assertNotEqual(_written(_decide(log, g)), 2.0)

    def test_control_the_2_23_window_solid(self):
        log = Log()
        g = _bridged(log, narrow=True, share=0.0, window_hollow=False)
        self.assertNotEqual(_written(_decide(log, g)), 2.0)


if __name__ == "__main__":
    unittest.main()
