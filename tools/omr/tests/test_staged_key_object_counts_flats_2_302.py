"""ROADMAP 2.302 -- the key object counts every printed flat from its stems (flag OMR_KEY_OBJECT_COUNTS_FLATS, default ON, deny-list).

CONTROLS ARE REAL PIXELS (CLAUDE rule 7): the key zones of Sean's 23 judged staff starts (2.292 r1, 2.299 r1), cut from the Litolff / Brahms pages
(`benchmarks/key-object-counts-flats-2026-11/data/real_starts.npz`, built by make_fixtures.py). Each case says how many flats the tree counted BEFORE
2.302 (`off_count`) and what Sean read (`truth_fifths`). The control that can fail: the under-counting staves count 3 only with the flag ON.
"""
import json
import os
import pathlib
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import key_object as KO

HERE = pathlib.Path(__file__).resolve().parents[3] / "benchmarks" / "key-object-counts-flats-2026-11" / "data"
META = json.loads((HERE / "real_starts.json").read_text())
PIX = np.load(HERE / "real_starts.npz")
ENV = KO.ENV_FLATS

#: judged three-flat Litolff starts where the tree counted 2 (a crushed flat lost) or 4-5 (an extra piece: a clef's edge / the first note) before 2.302
UNDER = ["litolff_1_0_10", "litolff_11_1_9"]
EXTRA = ["litolff_2_0_0", "litolff_16_0_1", "litolff_8_1_9"]


def run(key, flag):
    v = META[key]
    with mock.patch.dict(os.environ, {ENV: "1" if flag else "0"}):
        return KO.staff_run(PIX[key], v["lines"], v["spacing"], v["x_start"], v["x_hi"], v["boxes"], clef=v["clef"])


class RealStarts(unittest.TestCase):
    def test_flag_default_on_and_deny_list(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV, None)
            self.assertTrue(KO.counts_flats_enabled())
        for v in ("0", "false", "no", "off", "OFF"):
            with mock.patch.dict(os.environ, {ENV: v}):
                self.assertFalse(KO.counts_flats_enabled(), v)

    def test_off_reproduces_the_tree_before(self):
        for k, v in META.items():
            self.assertEqual(len(run(k, False)["pieces"]), v["off_count"], k)

    def test_control_fails_on_main_and_passes_after(self):
        for k in UNDER + EXTRA:
            self.assertNotEqual(len(run(k, False)["pieces"]), 3, "%s: the control must fail with the flag off" % k)
            self.assertEqual(len(run(k, True)["pieces"]), 3, "%s: three flats printed (Sean), counted 3 with the flag on" % k)

    def test_extra_piece_kept_on_the_record_not_counted(self):
        for k in EXTRA:
            r = run(k, True)
            self.assertTrue(r.get("extra_pieces"), k)
            self.assertEqual(len(r["pieces"]), 3)

    def test_never_over_counts_and_never_lowers(self):
        for k, v in META.items():
            off, on = len(run(k, False)["pieces"]), len(run(k, True)["pieces"])
            if v["truth_fifths"] == -3:
                self.assertLessEqual(on, 3, k)
                if off == 3:
                    self.assertEqual(on, 3, "%s: a right count is never moved" % k)
            self.assertGreaterEqual(on, min(off, 3) if off <= 3 else 0, k)

    def test_no_accidental_starts_stay_none(self):
        for k, v in META.items():
            if v["truth_fifths"] == 0:
                self.assertEqual(len(run(k, True)["pieces"]), 0, k)

    def test_brahms_unchanged(self):
        for k, v in META.items():
            if v["plate"] == "brahms":
                a, b = run(k, False), run(k, True)
                self.assertEqual([p["cx"] for p in a["pieces"]], [p["cx"] for p in b["pieces"]], k)

    def test_clef_unnamed_abstains_when_tables_disagree(self):
        # litolff 2/1/9: only one stroke fits any slot table -> no chain of two, nothing counted by the new reader (the old count stands)
        k = "litolff_2_1_9"
        self.assertEqual(len(run(k, True)["pieces"]), len(run(k, False)["pieces"]))

    def test_one_stroke_is_never_a_key(self):
        v = META["litolff_6_0_4"]
        self.assertEqual(len(run("litolff_6_0_4", True)["pieces"]), 0)
        self.assertEqual(KO.flat_stems_v2(None, [], 10, 0, 10, "treble"), [])


if __name__ == "__main__":
    unittest.main()
