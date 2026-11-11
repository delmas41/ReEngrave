"""ROADMAP 2.256b: the key object counts the flat STEMS the print kept -- flag `OMR_KEY_OBJECT_COUNT` (default ON, deny-list).

CAUSE (benchmarks/key-header-2026-11/FINDINGS.md 2.256b): a crushed scan breaks a flat into a stem and a bowl (or fuses two or three), so the
whole-flat piece test of `key_object.staff_run` counts 1-2 of the three printed flats. Each control can fail: the broken flats are counted 2 slots
short with the flag OFF; a note's stem, a barline, a wide stroke and a missing clef add no slot with the flag ON.
Synthetic rasters: staff space 20 px, treble clef; flat k's stem top stands (e_k - 3.8) steps from the top line (e = 4, 1, 5 for Bb, Eb, Ab).
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import key_object as KO

SP = 20.0
W, H = 600, 300
TOP = 100
LINES = [TOP + SP * j for j in range(5)]
X_START = 80.0
E = {1: 4, 2: 1, 3: 5}                     # treble Bb, Eb, Ab: steps below the top line


def _staff(img):
    for y in LINES:
        img[int(y):int(y) + 2, 20:W - 20] = 0


def _stem(img, slot, x, run_sp=2.6, broken=True):
    top = int(LINES[0] + (E[slot] - 3.8) * SP / 2.0)
    img[top:top + int(run_sp * SP), x:x + 3] = 0
    bot = top + int(run_sp * SP)
    # the bowl stands to the right of the stem's lower end; `broken`: a white gap separates it from the stem (the scan's break)
    bx = x + (7 if broken else 3)
    img[bot - 24:bot - 2, bx:bx + 9] = 0


def raster(slots=(1, 2, 3), *, broken=(2, 3)):
    img = np.full((H, W), 255, np.uint8)
    _staff(img)
    for s in slots:
        _stem(img, s, int(X_START + 8 + 24 * (s - 1)), broken=s in broken)
    return img


def run(img, clef="treble", on=True):
    env = dict({KO.ENV_COUNT: "1"} if on else {KO.ENV_COUNT: "0"}, **{KO.ENV_FLATS: "0"})      # 2.302 is another mechanism: pinned off here
    with mock.patch.dict(os.environ, env):
        return KO.staff_run(img, LINES, SP, X_START, X_START + 11 * SP, (), clef=clef)


class FlatStems(unittest.TestCase):
    def test_broken_flats_are_two_short_with_the_flag_off(self):
        self.assertLess(len(run(raster(), on=False)["pieces"]), 3)                 # the failing control: the bug exists

    def test_all_three_counted_with_the_flag_on(self):
        out = run(raster())
        self.assertEqual(len(out["pieces"]), 3)
        self.assertEqual(out["from_stems"], 3)

    def test_one_and_two_flats_count_one_and_two(self):
        self.assertEqual(len(run(raster(slots=(1,)))["pieces"]), 1)
        self.assertEqual(len(run(raster(slots=(1, 2)))["pieces"]), 2)

    def test_a_note_stem_after_the_flats_adds_no_slot(self):
        img = raster()
        img[int(LINES[0]) - 20:int(LINES[0]) - 20 + 70, int(X_START + 8 + 24 * 4):int(X_START + 8 + 24 * 4) + 3] = 0       # 3.5 sp... a stem past the key
        img[int(LINES[0]) - 30:int(LINES[0]) + 90, int(X_START + 8 + 24 * 5):int(X_START + 8 + 24 * 5) + 3] = 0            # 6 sp: a barline-length stroke
        self.assertEqual(len(run(img)["pieces"]), 3)

    def test_a_stroke_off_the_slot_position_ends_the_run(self):
        img = raster(slots=(1,))
        x = int(X_START + 8 + 24)
        img[int(LINES[0] + 5 * SP / 2.0 * 1.0):int(LINES[0] + 5 * SP / 2.0 * 1.0) + 52, x:x + 3] = 0            # slot 2's stem 4 steps too low
        self.assertEqual(len(run(img)["pieces"]), 1)

    def test_no_clef_reads_no_stems(self):
        self.assertLess(len(run(raster(), clef=None)["pieces"]), 3)

    def test_a_wide_stroke_is_not_a_stem(self):
        img = np.full((H, W), 255, np.uint8)
        _staff(img)
        top = int(LINES[0] + (4 - 3.8) * SP / 2.0)
        img[top:top + 52, int(X_START + 8):int(X_START + 8) + 14] = 0                                            # 0.7 sp wide: a bold stroke
        self.assertEqual(len(run(img)["pieces"]), len(run(img, on=False)["pieces"]))       # the stem reader adds nothing to what the pieces read
        self.assertNotIn("from_stems", run(img))

    def test_the_flag_defaults_on_and_denies(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(KO.ENV_COUNT, None)
            self.assertTrue(KO.count_enabled())
        for v in ("0", "false", "no", "off"):
            with mock.patch.dict(os.environ, {KO.ENV_COUNT: v}):
                self.assertFalse(KO.count_enabled())

    def test_the_stem_pieces_never_lower_a_count(self):
        img = raster(slots=(1, 2, 3), broken=())             # whole flats: the piece chain already counts 3
        off, on = run(img, on=False), run(img)
        self.assertGreaterEqual(len(on["pieces"]), len(off["pieces"]))


if __name__ == "__main__":
    unittest.main()
