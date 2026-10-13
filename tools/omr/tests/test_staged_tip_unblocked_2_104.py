"""ROADMAP 2.104 -- a flag the tip reader abstained `occupied` on is read by its own shape.

Sean, 2026-10-13 (2.97 round-3 tile 3, and his hand-truth `q1009` on Brahms pdf 0): a printed eighth flag our reader did not see,
so the head stayed `quarter | eighth`. The tip reader's SHAPE test was never run there: a detection box (a mid-bar `clefF` the
detector drew round the stem and its flag, a `ledgerLine`, a dynamic, an arpeggio) covered the ink, so `_observe_stem_tip_ink`
filed `occupied` and stopped. `OMR_TIP_UNBLOCKED` (default ON) reads the shape once more with the boxes set aside and files ONLY a flag-shaped
reading; every other outcome leaves the abstention exactly as it was (rule 8).

RUN RED FIRST against the unrepaired reader (`gather.py` as of 2ebc61d9): the ON tests fail there (the tip stays `occupied`); the
OFF test and the controls (a beam that runs on, a wedge with no arm, a clean stem, an uncovered tip) pass on both -- a refusal test with
no positive control passes by refusing everything.
NO TEST ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md 6c).
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q

SP = 20.0
STEM_X0, STEM_X1 = 190.0, 194.0
TOP_Y, BOTTOM_Y = 100.0, 300.0
SUB = R.cell(0, 0, 0, 0)
STEM_BOX = (STEM_X0, TOP_Y, STEM_X1 - STEM_X0, BOTTOM_Y - TOP_Y)


class FakeCell:
    def __init__(self, img):
        self.image_no_staff = img


def _paper():
    return np.full((400, 400), 255, dtype=np.uint8)


def _draw(img, x0, y0, x1, y1):
    img[int(round(y0)):int(round(y1)), int(round(x0)):int(round(x1))] = 0


def _up_stem_with_flag(img):
    _draw(img, STEM_X0, TOP_Y, STEM_X1, BOTTOM_Y)
    _draw(img, STEM_X1, TOP_Y, STEM_X1 + 14, TOP_Y + 12)
    _draw(img, STEM_X1 + 11, TOP_Y + 12, STEM_X1 + 16, TOP_Y + 50)


# a box the detector drew over the stem's tip and its flag (a false `clefF`: it wraps the stem and the ink hanging from it)
OVER_FLAG = (STEM_X0 - 2.0, TOP_Y - 2.0, STEM_X1 + 30.0, TOP_Y + 60.0)


def _top_rows(log):
    log.freeze()
    obs = [r for r in log.rows(Q.STEM_TIP_INK, SUB) if r.detail.get("end") == "top"]
    ab = [a for a in log.refusals(Q.STEM_TIP_INK, SUB) if a.detail.get("end") == "top"]
    return obs, ab


def _observe(img, blockers, env):
    log = Log()
    with mock.patch.dict(os.environ, env, clear=False):
        gather._observe_stem_tip_ink(log, SUB, "cell:0", FakeCell(img), "obs:stem-1", STEM_BOX, list(blockers), SP)
    return _top_rows(log)


class TestAFlagUnderABoxIsReadByItsShape(unittest.TestCase):

    def test_ON_a_flag_under_a_covering_box_is_found(self):
        """⚠️ THE FAULT: the flag is plainly there and a box that is not a flag makes the tip occupied."""
        img = _paper()
        _up_stem_with_flag(img)
        obs, ab = _observe(img, [OVER_FLAG], {"OMR_TIP_UNBLOCKED": "1"})
        self.assertEqual(len(obs), 1, (obs, ab))
        self.assertIs(obs[0].value, True)
        self.assertEqual(obs[0].detail.get("witness"), "shape_unblocked")
        self.assertIsNotNone(obs[0].detail.get("hooks"), obs[0].detail)    # the 2.69 hook count rides on it
        self.assertEqual(ab, [])

    def test_DEFAULT_unset_or_a_typo_is_ON(self):
        img = _paper()
        _up_stem_with_flag(img)
        for env in ({"OMR_TIP_UNBLOCKED": "tru"}, {"OMR_TIP_UNBLOCKED": "1"}):
            obs, _ = _observe(img, [OVER_FLAG], env)
            self.assertEqual(len(obs), 1, env)
        with mock.patch.dict(os.environ, clear=False):
            os.environ.pop("OMR_TIP_UNBLOCKED", None)
            self.assertTrue(gather.tip_unblocked_enabled())

    def test_OFF_the_same_tip_is_still_occupied(self):
        """An explicit off-word (default is ON since 2026-10-13) restores the shipped reader."""
        img = _paper()
        _up_stem_with_flag(img)
        for env in ({"OMR_TIP_UNBLOCKED": "0"}, {"OMR_TIP_UNBLOCKED": "off"}, {"OMR_TIP_UNBLOCKED": ""}):
            obs, ab = _observe(img, [OVER_FLAG], env)
            self.assertEqual(obs, [], env)
            self.assertEqual([a.reason for a in ab], [ABSTAIN.OCCUPIED], env)


class TestWhatTheUnblockedReadingMustNotDo(unittest.TestCase):
    """Positive controls: the same switch ON, and every one of these must keep its abstention."""

    ON = {"OMR_TIP_UNBLOCKED": "1"}

    def test_a_beam_that_runs_on_from_the_tip_stays_occupied(self):
        img = _paper()
        _draw(img, STEM_X0, TOP_Y, STEM_X1, BOTTOM_Y)
        _draw(img, STEM_X1, TOP_Y, STEM_X1 + 90, TOP_Y + 12)       # a 4.5-space bar to the next stem
        beam_box = (STEM_X1, TOP_Y - 2.0, STEM_X1 + 92.0, TOP_Y + 14.0)
        obs, ab = _observe(img, [beam_box], self.ON)
        self.assertEqual(obs, [])
        self.assertEqual([a.reason for a in ab], [ABSTAIN.OCCUPIED])

    def test_a_wedge_with_no_arm_stays_occupied(self):
        img = _paper()
        _draw(img, STEM_X0, TOP_Y, STEM_X1, BOTTOM_Y)
        _draw(img, STEM_X1, TOP_Y, STEM_X1 + 12, TOP_Y + 6)
        box = (STEM_X1, TOP_Y - 2.0, STEM_X1 + 14.0, TOP_Y + 8.0)
        obs, ab = _observe(img, [box], self.ON)
        self.assertEqual(obs, [])
        self.assertEqual(len(ab), 1)

    def test_a_clean_stem_is_found_FALSE_not_a_flag(self):
        """Nothing hangs from the tip: a positive 'no flag'. The switch never touches it."""
        img = _paper()
        _draw(img, STEM_X0, TOP_Y, STEM_X1, BOTTOM_Y)
        obs, ab = _observe(img, [OVER_FLAG], self.ON)
        self.assertEqual(len(obs), 1)
        self.assertIs(obs[0].value, False)
        self.assertNotEqual(obs[0].detail.get("witness"), "shape_unblocked")

    def test_an_uncovered_flag_is_read_by_the_ordinary_path(self):
        img = _paper()
        _up_stem_with_flag(img)
        obs, ab = _observe(img, [], self.ON)
        self.assertEqual(len(obs), 1)
        self.assertIs(obs[0].value, True)
        self.assertEqual(obs[0].detail.get("witness"), "shape")


if __name__ == "__main__":
    unittest.main()
