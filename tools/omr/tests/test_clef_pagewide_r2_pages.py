"""ROADMAP 2.251 round 2 -- Sean's round-1 tiles as real-page twins (needs the library's .pdf renders: slow tier).

* tile 5 (Litolff p6 s0 staff 5): a header G clef is NOT a C clef (its tail below the staff);
* tile 10 (Litolff p16 s0 staff 3): the F claim is the clef's own ink, never the quarter rest standing left of it;
* tile 11 (Brahms p5 s1 staff 3): a real F clef whose dots touch Breitkopf's thick lines and a stem IS read, bass;
* the failing twin (Brahms p25 s0 staff 3): a false `clefF` box over a half note and a barline is still refused.
"""
import gzip
import json
import os
import pathlib
import unittest

import numpy as np
import pytest

pytestmark = pytest.mark.slow

ROOT = pathlib.Path(__file__).resolve().parents[3]
LIB = ROOT / "library"
PDF = {"litolff": "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
CM = {"litolff": "_shared-records/cell-maps/55d95838e0709b92-dpi600", "brahms": "_shared-records/cell-maps/be40c09fbd9f55f0-dpi600"}


def _page(plate, pg):
    from tools.omr.preprocessing import render_page
    return np.asarray(render_page(str(LIB / PDF[plate]), pg, dpi=600).rgb).mean(axis=2) < 128


def _staff(plate, pg, sys_i, local):
    d = json.load(gzip.open(LIB / CM[plate] / "pages" / ("p%03d.json.gz" % pg)))
    st = sorted([t for t in d["staves"] if t["system_index"] == sys_i], key=lambda t: t["line_ys"][0])[local]
    ly = [float(v) for v in st["line_ys"]]
    return st, ly, (ly[4] - ly[0]) / 4.0


@unittest.skipUnless((LIB / PDF["litolff"]).exists() and (LIB / PDF["brahms"]).exists(), "needs the score library")
class SeansRound1Tiles(unittest.TestCase):
    def test_tile5_header_g_clef_is_not_a_c_clef(self):
        from tools.omr.staged import clef_pagewide as CP
        ink = _page("litolff", 6)
        st, ly, sp = _staff("litolff", 6, 0, 5)
        got = [c for c in CP.c_bars(ink, ly, sp, st["x_start"], st["x_start"] + 120) if c["passed"]]
        self.assertEqual(got, [])

    def test_tile10_f_claim_leaves_the_rest_out(self):
        from tools.omr.staged import clef_pagewide as CP
        ink = _page("litolff", 16)
        _st, ly, sp = _staff("litolff", 16, 0, 3)
        box = [926.175, 825.985, 980.8275, 874.18]            # the detector's clefF box: it also holds the quarter rest's right half
        got = CP.read_box("clefF", box, ink, CP.local_lines(ink, ly, sp, box[0]), sp)
        self.assertTrue(got["passed"])
        self.assertEqual(got["kind"], "bass")
        self.assertGreater(CP.f_claim_area(got, box, sp)[0], 940.0)

    def test_tile11_brahms_f_clef_is_read(self):
        from tools.omr.staged import clef_pagewide as CP
        ink = _page("brahms", 5)
        _st, ly, sp = _staff("brahms", 5, 1, 3)
        box = [1004.7, 4726.6, 1079.0, 4813.7]
        got = CP.read_box("clefF", box, ink, CP.local_lines(ink, ly, sp, box[0]), sp)
        self.assertTrue(got["passed"], got)
        self.assertEqual(got["kind"], "bass")

    def test_failing_twin_brahms_p25_false_f_box(self):
        from tools.omr.staged import clef_pagewide as CP
        ink = _page("brahms", 25)
        obs = LIB / "_shared-records/lane-report-slices-20261029-night/brahms/observations.jsonl"
        if not obs.exists():
            self.skipTest("needs the brahms lane-report slice")
        box = None
        with open(obs) as f:
            for line in f:
                if '"glyph/25/0/3/1/' in line and '"glyph_box"' in line and '"clefF' in line:
                    box = json.loads(line)["detail"]["bbox_page_px"]
                    break
        self.assertIsNotNone(box)
        _st, ly, sp = _staff("brahms", 25, 0, 3)
        got = CP.read_box("clefF", box, ink, CP.local_lines(ink, ly, sp, box[0]), sp)
        self.assertFalse(got["passed"], got)


if __name__ == "__main__":
    unittest.main()
