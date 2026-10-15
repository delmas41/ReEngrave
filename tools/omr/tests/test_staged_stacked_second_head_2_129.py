"""ROADMAP 2.129 -- a second head of a chord of THIRDS, kept where the ink is two heads tall.

Brahms 20261013-night, pdf 0, Sean's every-head truth (`data/hand-truth/pages/imslp317803/0.json`):
5 of the 7 boxes refused `stacked_head_duplicate` on that page are the second head of two touching heads one
staff space apart (a chord of thirds on one side of one stem). The stack fit read k=1 for all five: its slots
scored 1.00 / 1.00 / 0.86 (the middle slot saturates on the blob; the lower head lost its centre to staff-line
removal) so the pair's mean fell 0.068 under the lone best and the mean gate refused it. The other two refusals
are right: one head boxed twice (dy 0) and a box on no head (ink blob 0.7 spaces).

Layers: A `gather.stacked_blob_height_spaces` (pure); B `gather.fit_stacked_head_count` with the blob witness;
C `gather.gather_stacked_head_fit` behind `OMR_STACKED_SECOND_HEAD` (default OFF, byte-identical when off);
D the refusal that says how close it came. The painted twin: two heads at -1.1 / +1.02 half-steps with the
lower one cut across its centre (the staff line removed) -- the shape that reads k=1 on the shipped path.

NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""
from __future__ import annotations

import os
import types
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.staged.record import Q, READERS, State, Log
from tools.omr.tests.test_staged_notehead_recentre import _fill_ellipse, _paper
from tools.omr.tests.test_staged_stacked_head_fit import (
    SPACING, _cell, _detection, _stem_row)

HALF = SPACING / 2.0
TOP = 100.0
OBS_TWIN = [-1.1, 1.02]


def _twin_ink(positions=(-1.1, 1.02), cut=True, h=400, w=200):
    """Two touching heads a third apart; the lower one cut across its centre for 6 rows over the right half --
    the staff-line removal that dropped the real twin's lower slot to 0.86."""
    img = _paper(h=h, w=w)
    cx = w / 2.0
    for p in positions:
        _fill_ellipse(img, cx, TOP + p * HALF, 1.3 * SPACING, 1.1 * SPACING)
    if cut:
        y = int(TOP + positions[-1] * HALF)
        img[y:y + 6, int(cx):int(cx + 0.65 * SPACING)] = 255
    return img, cx


def _one_head_ink(p=0.0, h=400, w=200):
    img = _paper(h=h, w=w)
    cx = w / 2.0
    _fill_ellipse(img, cx, TOP + p * HALF, 1.3 * SPACING, 1.1 * SPACING)
    return img, cx


def _blob_fn(img, cx):
    return lambda pos: gather.stacked_blob_height_spaces(
        img, cx, TOP + (pos[0] + pos[1]) / 2.0 * HALF, SPACING)


class TestBlobHeightPure(unittest.TestCase):
    def test_one_head_is_about_one_space_two_touching_heads_about_two(self):
        one, cx = _one_head_ink()
        two, cx2 = _twin_ink(cut=False)
        h1 = gather.stacked_blob_height_spaces(one, cx, TOP, SPACING)
        h2 = gather.stacked_blob_height_spaces(two, cx2, TOP, SPACING)
        self.assertLess(h1, 1.35)
        self.assertGreater(h2, 1.8)

    def test_a_cut_across_the_lower_head_is_bridged(self):
        two, cx = _twin_ink(cut=True)
        self.assertGreater(gather.stacked_blob_height_spaces(two, cx, TOP, SPACING), 1.8)

    def test_two_heads_a_gap_apart_are_not_one_blob(self):
        img, cx = _twin_ink(positions=(-2.0, 2.0), cut=False)     # two spaces apart: blank between
        self.assertLess(gather.stacked_blob_height_spaces(img, cx, TOP, SPACING), 1.35)

    def test_blank_paper_is_zero_and_off_raster_is_none(self):
        img = _paper(h=400, w=200)
        self.assertEqual(gather.stacked_blob_height_spaces(img, 100.0, TOP, SPACING), 0.0)
        self.assertIsNone(gather.stacked_blob_height_spaces(img, 100.0, 5000.0, SPACING))


class TestFitWithTheBlobWitness(unittest.TestCase):
    def _fit(self, img, cx, observed, blob=True, n_boxes=2):
        return gather.fit_stacked_head_count(
            img, cx, list(range(-3, 4)), TOP, HALF, SPACING, n_boxes, observed=observed,
            **({"blob_height_fn": _blob_fn(img, cx)} if blob else {}))

    def test_the_shipped_path_reads_the_twin_as_one_head(self):
        """The failure, pinned: with no blob witness the twin is k=1 (this is every OFF run)."""
        img, cx = _twin_ink()
        fit = self._fit(img, cx, OBS_TWIN, blob=False)
        self.assertEqual(fit["k"], 1)
        self.assertIsNone(fit["margin"])

    def test_two_touching_heads_tall_are_two_heads(self):
        img, cx = _twin_ink()
        fit = self._fit(img, cx, OBS_TWIN)
        self.assertEqual(fit["k"], 2)
        self.assertEqual(fit["positions"], (-1, 1))
        self.assertEqual(fit["second_head_by"], "blob_height")
        self.assertFalse(fit["ambiguous"])
        self.assertGreater(fit["margin"], 0.0)

    def test_one_head_boxed_twice_stays_one_head(self):
        """A true duplicate: both boxes on ONE head (0.1 half-step apart)."""
        img, cx = _one_head_ink(p=1.0)
        fit = self._fit(img, cx, [0.95, 1.05])
        self.assertEqual(fit["k"], 1)
        self.assertIsNone(fit["second_head_by"])

    def test_a_box_on_no_head_stays_refused_and_says_how_close_it_came(self):
        """One head, a second box a space away over blank paper under the same stem: the pair's slots both hold
        enough ink to be examined, the blob is one head tall, so k=1 AND the near-miss is recorded."""
        img, cx = _one_head_ink(p=0.0)
        fit = self._fit(img, cx, [-1.0, 1.0])
        self.assertEqual(fit["k"], 1)
        self.assertIsNone(fit["second_head_by"])
        nm = fit["near_miss"]
        self.assertIsNotNone(nm)
        self.assertLess(nm["blob_spaces"], nm["needed_spaces"])
        self.assertEqual(nm["positions"], [-1, 1])

    def test_a_slot_with_no_detector_box_is_never_added(self):
        """The fit may not add a head the detector never boxed: both boxes sit at one slot."""
        img, cx = _twin_ink()
        fit = self._fit(img, cx, [-1.05, -1.0])
        self.assertEqual(fit["k"], 1)

    def test_the_blob_witness_is_not_asked_when_the_mean_test_passes(self):
        img = _paper(h=400, w=200)
        cx = 100.0
        for p in (-1, 1):
            _fill_ellipse(img, cx, TOP + p * HALF, 1.3 * SPACING, 1.1 * SPACING)
        asked = []
        fit = gather.fit_stacked_head_count(
            img, cx, list(range(-3, 4)), TOP, HALF, SPACING, 2, observed=[-1.0, 1.0],
            blob_height_fn=lambda pos: asked.append(pos) or 9.0)
        self.assertEqual(fit["k"], 2)
        self.assertIsNone(fit["second_head_by"])
        self.assertEqual(asked, [])


class TestGatherBehindTheFlag(unittest.TestCase):
    def _run(self, img, dets, stem):
        cell = _cell(img)
        sub = R.cell(0, 0, 0, 0)
        log = Log()
        _stem_row(log, sub, x_c=stem[0], y_c=stem[1], w_c=stem[2], h_c=stem[3])
        gather.gather_stacked_head_fit(log, [cell], {0: (0, 0)}, {sub.to_key(): dets})
        return log

    def _dets(self, cx, observed):
        return [_detection("noteheadBlackInSpace", cx, TOP + p * HALF) for p in observed]

    def test_off_by_default_the_twin_is_k1_and_unchanged(self):
        img, cx = _twin_ink()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMR_STACKED_SECOND_HEAD", None)
            log = self._run(img, self._dets(cx, OBS_TWIN), (cx - 22.0, 40.0, 20.0, 260.0))
        for gi in range(2):
            row = log.rows(Q.STACKED_HEAD_FIT, R.glyph(0, 0, 0, 0, gi))[0]
            self.assertEqual(row.value[0], 1)
            self.assertNotIn("near_miss", row.detail or {})

    def test_on_the_twin_is_two_heads_each_box_its_own_slot(self):
        img, cx = _twin_ink()
        with mock.patch.dict(os.environ, {"OMR_STACKED_SECOND_HEAD": "1"}):
            log = self._run(img, self._dets(cx, OBS_TWIN), (cx - 22.0, 40.0, 20.0, 260.0))
        rows = [log.rows(Q.STACKED_HEAD_FIT, R.glyph(0, 0, 0, 0, gi))[0] for gi in range(2)]
        self.assertEqual([r.value[0] for r in rows], [2, 2])
        self.assertEqual({r.value[1] for r in rows}, {0, 1})
        self.assertEqual(rows[0].detail["second_head_by"], "blob_height")

    def test_on_a_duplicate_box_is_still_one_head(self):
        img, cx = _one_head_ink(p=1.0)
        with mock.patch.dict(os.environ, {"OMR_STACKED_SECOND_HEAD": "1"}):
            log = self._run(img, self._dets(cx, [0.95, 1.05]), (cx - 22.0, 40.0, 20.0, 260.0))
        rows = [log.rows(Q.STACKED_HEAD_FIT, R.glyph(0, 0, 0, 0, gi))[0] for gi in range(2)]
        self.assertEqual([r.value[0] for r in rows], [1, 1])


class TestTheRefusalRecordsTheNearMiss(unittest.TestCase):
    def test_a_refused_box_carries_the_near_miss_of_its_group(self):
        img, cx = _one_head_ink(p=0.0)
        dets = [_detection("noteheadBlackInSpace", cx, TOP + p * HALF) for p in (-1.0, 1.0)]
        cell = _cell(img)
        sub = R.cell(0, 0, 0, 0)
        with mock.patch.dict(os.environ, {"OMR_STACKED_SECOND_HEAD": "1"}):
            log = Log()
            _stem_row(log, sub, x_c=cx - 22.0, y_c=40.0, w_c=20.0, h_c=260.0)
            gather.gather_stacked_head_fit(log, [cell], {0: (0, 0)}, {sub.to_key(): dets})
        row = log.rows(Q.STACKED_HEAD_FIT, R.glyph(0, 0, 0, 0, 0))[0]
        self.assertEqual(row.value[0], 1)
        self.assertIn("near_miss", row.detail)
        self.assertLess(row.detail["near_miss"]["blob_spaces"], row.detail["near_miss"]["needed_spaces"])
