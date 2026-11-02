"""ROADMAP 2.251 carry -- the F clef with NO detector box, as real-page twins (needs the library's .pdf renders: slow tier).

The reader (`clef_pagewide.f_nobox`): a dot pair straddling the F line AND the page's own F body (a read F clef of the same page,
`f_templates`) where those dots put it. READ at `F_TEMPLATE_READ_SCORE`, else a clef-shaped CANDIDATE that stops a carry.
* Litolff bar 38 (p2 s1 bassoon): a bass clef with no box (heads boxed on it) IS read, bass.
* Litolff bar 115 (p5 s0 bassoon): a bass clef with a head through its body is a candidate, not read.
* Litolff bar 110 / 114 (C clefs): their bowls, cut by the lines, pass as an F dot pair -- never read as an F clef.
* confusables, never read: a head with a flat beside it (p13 s1 bassoon), heads and an accidental (p13 s1 staff 1), a beamed chord
  (p4 s1 staff 9).
"""
import gzip
import json
import pathlib
import unittest

import numpy as np
import pytest

pytestmark = pytest.mark.slow

ROOT = pathlib.Path(__file__).resolve().parents[3]
LIB = ROOT / "library"
PDF = "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
CM = "_shared-records/cell-maps/55d95838e0709b92-dpi600"
#: the detector's clef-sized `clefF` boxes of each page (20261031-night record), the reader's templates
F_BOXES = {
    2: [(0, 3, [362.8, 843.0, 411.4, 899.8]), (0, 6, [361.4, 1284.9, 409.8, 1340.4]), (0, 10, [363.6, 1880.8, 411.6, 1936.2]),
        (1, 6, [362.2, 2946.3, 410.3, 3002.4]), (1, 10, [363.9, 3528.3, 404.9, 3583.4])],
    4: [(0, 3, [373.7, 854.4, 427.7, 911.9]), (0, 9, [1976.9, 1749.3, 2031.1, 1804.3]), (0, 10, [380.4, 1900.8, 430.8, 1957.9]),
        (1, 3, [375.0, 2582.6, 428.5, 2639.5]), (1, 3, [1677.8, 2577.4, 1724.6, 2631.1])],
    5: [(0, 3, [379.3, 996.0, 423.6, 1050.2]), (0, 3, [2375.8, 995.1, 2448.1, 1044.7]), (0, 8, [383.6, 1882.0, 432.3, 1938.1])],
    13: [(0, 3, [366.8, 906.9, 412.1, 964.0]), (0, 10, [368.3, 1831.3, 420.6, 1882.7]), (1, 3, [380.5, 2576.2, 429.4, 2632.3]),
         (1, 6, [381.1, 2981.0, 430.0, 3038.6]), (1, 10, [385.5, 3533.9, 432.2, 3586.0])],
}


def _page(pg):
    from tools.omr.preprocessing import render_page
    return np.asarray(render_page(str(LIB / PDF), pg, dpi=600).binary) == 0      # the ink GATHER reads


def _staves(pg):
    d = json.load(gzip.open(LIB / CM / "pages" / ("p%03d.json.gz" % pg)))
    out = {}
    for s in sorted({t["system_index"] for t in d["staves"]}):
        for li, t in enumerate(sorted([t for t in d["staves"] if t["system_index"] == s], key=lambda t: t["line_ys"][0])):
            ly = [float(v) for v in t["line_ys"]]
            out[(s, li)] = (ly, (ly[4] - ly[0]) / 4.0, t)
    return out


def _read(pg, s, li, x0, x1):
    from tools.omr.staged import clef_pagewide as CP
    ink, st = _page(pg), _staves(pg)
    per = [(st[(bs, bl)][0], st[(bs, bl)][1], [b]) for bs, bl, b in F_BOXES[pg]]
    tps = CP.f_templates(ink, per)
    ly, sp, _t = st[(s, li)]
    return CP.f_nobox(ink, ly, sp, x0, x1, tps)


@unittest.skipUnless((LIB / PDF).exists() and (LIB / CM).exists(), "needs the score library and the Litolff cell map")
class NoBoxBassClef(unittest.TestCase):
    def test_bar38_bass_clef_with_no_box_is_read(self):
        got = [g for g in _read(2, 1, 3, 940, 1040) if g["read"]]
        self.assertEqual(len(got), 1, got)
        self.assertTrue(990 <= got[0]["pair"]["x_left"] <= 1020)

    def test_bar115_head_through_the_body_is_a_candidate_not_read(self):
        got = [g for g in _read(5, 0, 3, 840, 920)]
        self.assertTrue(got, "the bar-115 bass clef must at least stop a carry")
        self.assertFalse(any(g["read"] for g in got), got)

    def test_c_clef_bowls_are_not_read_as_an_f_clef(self):
        for pg, s, x0, x1 in ((4, 1, 2150, 2200), (5, 0, 690, 730)):
            self.assertFalse(any(g["read"] for g in _read(pg, s, 3, x0, x1)), (pg, s))

    def test_confusables_are_not_read(self):
        for pg, s, li, x in ((13, 1, 3, 2214), (13, 1, 1, 988), (4, 1, 9, 1658)):
            self.assertFalse(any(g["read"] for g in _read(pg, s, li, x - 60, x + 60)), (pg, s, li, x))

    def _scan(self, pg, s, li, x0, x1):
        from tools.omr.staged import clef_pagewide as CP
        ink, st = _page(pg), _staves(pg)
        tps = CP.f_templates(ink, [(st[(bs, bl)][0], st[(bs, bl)][1], [b]) for bs, bl, b in F_BOXES[pg]])
        ly, sp, _t = st[(s, li)]
        return [r for r in CP.f_body_scan(ink, ly, sp, x0, x1, tps) if r["match"]["score"] >= CP.F_BODY_SCAN_CANDIDATE_SCORE]

    def test_bar111_dots_fused_body_alone_is_a_candidate(self):
        # round 2: the bar-111 bass clef's dots are fused with the heads beside them (no pair); its body alone stops the carry
        got = self._scan(4, 1, 3, 2200, 2700)
        self.assertTrue(any(2300 <= r["x"] <= 2370 for r in got), got)

    def test_bar111_candidate_stands_after_the_eighth_printed_before_the_clef(self):
        # Sean's carry r2 tile 2: an eighth note (head box 2314-2338, centre 2326) is printed BEFORE the bar-111 bass clef and its head
        # overlaps the clef's body. The candidate (filed at the body's left edge, `gather_clef_pagewide`) must stand right of that head, so
        # the eighth keeps the clef in force before it, and left of the first head after the clef (2380)
        got = [r for r in self._scan(4, 1, 3, 2200, 2700) if 2300 <= r["x"] <= 2380]
        self.assertTrue(got)
        x = max(got, key=lambda r: r["match"]["score"])["x"]
        self.assertTrue(2326 < x < 2380, x)
        from tools.omr.staged import clef_pagewide as CP

        class Row:
            def __init__(self, x, **d):
                self.value, self.detail = [x, 0, x + 40, 50], d
        ch = CP.changes_of([Row(2167, source=CP.SOURCE, change=True, kind="tenor")])
        cands = CP.candidates_of([Row(0, source=CP.SOURCE, candidate=True, x_page=x, family="F")])
        self.assertEqual(CP.clef_in_force(2326, ch, cands, "bass")[0], "tenor")   # the eighth: tenor, carried
        self.assertIsNone(CP.clef_in_force(2390, ch, cands, "bass")[0])          # after the clef: unread, never tenor

    def test_body_scan_finds_nothing_where_no_clef_stands(self):
        # the bassoon after the bar-390 bass clef on p13 s1 (heads, a flat, rests): the highest no-clef body scores on Litolff (<= 0.55)
        self.assertEqual(self._scan(13, 1, 3, 1540, 1720), [])


if __name__ == "__main__":
    unittest.main()
