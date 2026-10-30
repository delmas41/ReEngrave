"""ROADMAP 2.239 (`OMR_SPLIT_JOINS`, default OFF): the stroke map cuts a fused piece at its joins (head|stem, head|head, head|ledger,
head|arc), every part keeps a `joined_to` link and no ink is lost; the page-wide barline claim leaves a whole left-edge mark's ink to the bracket.
Synthetic cells of KNOWN geometry; each control below can FAIL (a notch cut-off no scan can reach leaves the stack whole)."""
import os
import types
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import gather as G
from tools.omr.staged import head_ink as HI
from tools.omr.staged import stroke_map as SM
from tools.omr.staged.record import Q

SP = 100
LINES = [300 + SP * i for i in range(5)]


def _blank(w=1400, h=1100):
    img = np.full((h, w), 255, np.uint8)
    raw = img.copy()
    for y in LINES:
        raw[y - 3:y + 4, :] = 0
    return img, raw


def _oval(img, cx, cy, rx=48, ry=55, p=4):
    """A head: a full (super-)ellipse, as a scanned black head is fuller than an ellipse where two of them touch."""
    yy, xx = np.ogrid[:img.shape[0], :img.shape[1]]
    img[np.abs((xx - cx) / float(rx)) ** p + np.abs((yy - cy) / float(ry)) ** p <= 1.0] = 0


def _chord():
    """Two black heads a third apart (centres 1 sp apart, touching) on one up-stem at their right edge."""
    img, raw = _blank()
    _oval(img, 300, 650)
    _oval(img, 300, 550)
    img[200:650, 330:347] = 0                        # stem 0.17 sp wide at the heads' right edge, 3.5 sp above the lower head's centre
    return img, raw


def _total(res):
    return sum(int(m.sum()) for m, _x, _y in res.masks)


class SplitChord(unittest.TestCase):
    def setUp(self):
        self.img, self.raw = _chord()

    def test_off_is_one_vertical_and_byte_identical_to_the_default(self):
        off = SM.map_strokes(self.img, SP, LINES, self.raw, split_joins=False)
        with mock.patch.dict(os.environ, {SM.SPLIT_JOINS_ENV: ""}):
            dflt = SM.map_strokes(self.img, SP, LINES, self.raw)
        self.assertEqual([(s.kind, s.box) for s in off.strokes], [(s.kind, s.box) for s in dflt.strokes])
        big = max(off.strokes, key=lambda s: s.area_sp2)
        self.assertEqual(big.kind, "vertical")          # the cause: the stack and the stem are ONE vertical stroke
        self.assertGreater(big.area_sp2, 1.5)
        self.assertTrue(all(not s.joined_to for s in off.strokes))

    def test_on_cuts_stem_and_two_heads_with_links_and_loses_no_ink(self):
        off = SM.map_strokes(self.img, SP, LINES, self.raw, split_joins=False)
        on = SM.map_strokes(self.img, SP, LINES, self.raw, split_joins=True)
        self.assertEqual(_total(on), _total(off))       # every pixel of the fused piece is in exactly one part
        stems = [s for s in on.strokes if s.kind == "vertical"]
        heads = [s for s in on.strokes if s.kind == "blob" and s.area_sp2 > 0.5]
        self.assertEqual(len(stems), 1, [(s.kind, s.box, s.area_sp2) for s in on.strokes])
        self.assertLess(stems[0].thickness_sp, 0.4)
        self.assertEqual(len(heads), 2, [(s.kind, s.box, s.area_sp2) for s in on.strokes])
        for h in heads:
            self.assertLessEqual(h.box[3], SM.HEAD_HEIGHT_CAP_SPACES * SP)
            self.assertTrue(h.joined_to)
        si = on.strokes.index(stems[0])
        self.assertTrue(any(j == si for h in heads for j, _how in h.joined_to))
        self.assertTrue(any(how.startswith("stem|") for _j, how in stems[0].joined_to))

    def test_flag_env_turns_it_on(self):
        with mock.patch.dict(os.environ, {SM.SPLIT_JOINS_ENV: "1"}):
            res = SM.map_strokes(self.img, SP, LINES, self.raw)
        self.assertTrue(any(s.joined_to for s in res.strokes))

    def test_control_a_notch_no_scan_reaches_leaves_the_stack_whole(self):
        with mock.patch.object(SM, "STACK_NOTCH_SPACES", 5.0), mock.patch.object(SM, "WAIST_SHARE_MAX", 0.0):
            res = SM.map_strokes(self.img, SP, LINES, self.raw, split_joins=True)
        heads = [s for s in res.strokes if s.kind == "blob" and s.area_sp2 > 0.5]
        self.assertEqual(len(heads), 1)                 # the stem still comes off; the two heads stay one part
        self.assertGreater(heads[0].box[3], SM.HEAD_HEIGHT_CAP_SPACES * SP)
        self.assertGreaterEqual(res.split_refused.get("stack_no_waist", 0), 1)


class SplitOthers(unittest.TestCase):
    def test_head_on_a_ledger_rung(self):
        img, raw = _blank()
        img[194:206, 400:650] = 0                       # a rung 2.5 sp long above the staff
        _oval(img, 525, 200, rx=62, ry=50, p=2)         # a head 1.24 sp wide: its middle rows pass the rung's horizontal opening
        off = SM.map_strokes(img, SP, LINES, raw, split_joins=False)
        on = SM.map_strokes(img, SP, LINES, raw, split_joins=True)
        self.assertEqual(_total(on), _total(off))
        stubs = [s for s in on.strokes if s.kind == "horizontal"]
        heads = [s for s in on.strokes if s.kind == "blob"]
        # Sean 2026-10-30 (tiles 6, 9): the head on a rung is ONE part, all of the oval (its tips too); the rung is cut off only where it
        # sticks out, and the stubs are ledger strokes, not blobs
        self.assertEqual(len(heads), 1, [(s.kind, s.box, s.area_sp2, s.joined_to) for s in on.strokes])
        self.assertGreater(heads[0].box[3], 0.9 * SP)                    # the whole oval's height, not a slice
        self.assertEqual(len(stubs), 2)
        for st in stubs:
            self.assertLess(st.thickness_sp, 0.25)
            self.assertTrue(any(how == "ledger|head" for _j, how in st.joined_to))

    def test_a_clef_box_keeps_its_ink_whole(self):
        img, raw = _chord()
        on = SM.map_strokes(img, SP, LINES, raw, split_joins=True, keep_whole=[(200, 150, 400, 750)])
        off = SM.map_strokes(img, SP, LINES, raw, split_joins=False)
        self.assertEqual([(s.kind, s.box) for s in on.strokes], [(s.kind, s.box) for s in off.strokes])
        self.assertGreaterEqual(on.split_refused.get("inside_clef_key_meter", 0), 1)

    def test_head_with_a_tie_leaving_it(self):
        img, raw = _blank()
        _oval(img, 300, 450, ry=50)
        xs = np.arange(340, 640)
        for x in xs:                                    # a slur 0.15 sp thick bowing away from the head's right side
            y = int(470 + 200 * np.sin(np.pi * (x - 340) / (640 - 340)))
            img[y:y + 15, x] = 0
        off = SM.map_strokes(img, SP, LINES, raw, split_joins=False)
        on = SM.map_strokes(img, SP, LINES, raw, split_joins=True)
        self.assertEqual(_total(on), _total(off))
        kinds = sorted(s.kind for s in on.strokes if s.area_sp2 > 0.3)
        self.assertEqual(kinds, ["blob", "curve"], [(s.kind, s.box, s.area_sp2) for s in on.strokes])
        self.assertTrue(any(how == "arc|head" for s in on.strokes for _j, how in s.joined_to))

    def test_a_bracket_line_and_a_barline_stay_whole(self):
        img, raw = _blank()
        img[100:1000, 100:160] = 0                      # a bracket's thick line, 0.6 sp wide, 9 sp tall
        img[100:1000, 400:412] = 0                      # a barline
        off = SM.map_strokes(img, SP, LINES, raw, split_joins=False)
        on = SM.map_strokes(img, SP, LINES, raw, split_joins=True)
        self.assertEqual([(s.kind, s.box) for s in on.strokes], [(s.kind, s.box) for s in off.strokes])

    def test_head_caps_are_head_inks(self):
        self.assertEqual(SM.HEAD_HEIGHT_CAP_SPACES, HI.MAX_HEIGHT_SPACES_V2)
        self.assertEqual(SM.HEAD_WIDTH_CAP_SPACES, HI.MAX_WIDTH_SPACES)


class StrokeRowsCarryTheJoin(unittest.TestCase):
    def test_rows_file_joined_to_only_with_the_flag(self):
        img, raw = _chord()
        c = types.SimpleNamespace(page_index=0, staff_index=0, measure_index=0, image_no_staff=img, binary=raw,
                                  staff_line_ys_canonical=LINES, upscale_factor=1.0, bbox_page_px=(0, 0, 1400, 1100))
        for word, want in (("", False), ("1", True)):
            log = G.Log()
            with mock.patch.dict(os.environ, {SM.SPLIT_JOINS_ENV: word, G.STROKE_MAP_ENV: "1"}), \
                    mock.patch.object(G, "_cell_grid", lambda _c: (LINES[0], SP / 2.0)):
                G.gather_stroke_map(log, [c], {0: (0, 0)})
            rows = [r for r in log.all_rows() if r.quantity == Q.STROKE]
            self.assertTrue(rows)
            self.assertEqual(any("joined_to" in (r.detail or {}) for r in rows), want)


class BarlineClaimLeavesBracketInk(unittest.TestCase):
    def _run(self, word):
        st = types.SimpleNamespace(staff_index=0, line_spacing_px=20.0, top_y=100.0, bottom_y=180.0)
        pws = types.SimpleNamespace(page=types.SimpleNamespace(page_index=0), staves=[st], staged_page_wide=True,
                                    barlines=[types.SimpleNamespace(system_index=0, x=105.0), types.SimpleNamespace(system_index=0, x=400.0)],
                                    system_structure={0: {"left_edge": {"marks": [{"kind": "bracket", "box": [96, 90, 112, 400]}]}}})
        cells = [types.SimpleNamespace(staff_index=0, system_index=0, measure_index=0, bbox_page_px=(100, 60, 410, 220))]
        log = G.Log()
        with mock.patch.dict(os.environ, {SM.SPLIT_JOINS_ENV: word, "OMR_BARLINE_SYSTEM_COLUMNS": "1"}):
            G.gather_barline_claim(log, pws, cells, {0: (0, 0)})
        return sorted(int(r.detail["barline_x"]) for r in log.all_rows() if r.quantity == Q.CLAIMED_AREA
                      and type(r).__name__ != "Abstention")

    def test_off_claims_the_bracket_column_on_flag_leaves_it(self):
        self.assertEqual(self._run(""), [105, 400])
        self.assertEqual(self._run("1"), [400])


if __name__ == "__main__":
    unittest.main()
