"""ROADMAP 2.239 (`OMR_SPLIT_JOINS`, default ON since 2026-10-30): the stroke map cuts a fused piece at its joins (head|stem, head|head, head|ledger,
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


def _canvas(res):
    out = np.zeros((200, 300), bool)   # the reduced frame of a 1400 x 1100 cell at SP 100
    for m, x, y in res.masks:
        out[y:y + m.shape[0], x:x + m.shape[1]] |= m
    return out


def _total(res):
    return sum(int(m.sum()) for m, _x, _y in res.masks)


class SplitChord(unittest.TestCase):
    def setUp(self):
        self.img, self.raw = _chord()

    def test_off_is_one_vertical_and_byte_identical_to_the_flag_off(self):
        off = SM.map_strokes(self.img, SP, LINES, self.raw, split_joins=False)
        with mock.patch.dict(os.environ, {SM.SPLIT_JOINS_ENV: "0"}):
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

    def test_tile_9_a_rung_at_the_heads_top_is_not_a_second_head(self):
        """Sean 2026-10-30, round-1 tile 9 ("gets a part of a head but mostly the ledger line next to it"): a head below the staff on a
        stem, a rung crossing its top -- the stack cut must not take the rung + the head's top as a 'head'; the head stays one part."""
        img, raw = _blank()
        _oval(img, 300, 900, rx=55, ry=50, p=2.5)
        img[300:880, 248:264] = 0                       # a stem at the head's left, up to the staff
        img[843:855, 215:390] = 0                       # a rung through the head's top rows, sticking out both sides
        on = SM.map_strokes(img, SP, LINES, raw, split_joins=True)
        heads = [s for s in on.strokes if s.kind == "blob" and s.area_sp2 > 0.3]
        self.assertEqual(len(heads), 1, [(s.kind, s.box, s.area_sp2, s.joined_to) for s in on.strokes])
        self.assertGreaterEqual(heads[0].box[3], 0.8 * SP)          # the oval below the rung row, never a sliver

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


class Round3TouchingMarksAndClefs(unittest.TestCase):
    """2.239 round 3 (Sean's round-2 tiles 1 "part of a ledger line and a flat", 7 "tip cut of a G clef"). CAUSE: the cuts above read a
    change of width inside ONE mark; two marks that touch have none. And the openings cut a clef into pieces (flag OFF too)."""

    def _flat_on_rung(self):
        img, raw = _blank()
        img[894:906, 300:650] = 0                       # a rung below the staff, through a head and running left under the flat
        _oval(img, 525, 900, rx=62, ry=50, p=2)
        img[700:960, 200:212] = 0                       # the flat's stem
        for y in range(880, 960):                       # its bowl, the bottom row resting on the rung, closing at x=300
            half = int(50 * np.sqrt(max(0.0, 1 - ((y - 920) / 40.0) ** 2)))
            img[y, 205 + 0:205 + 2 * half] = 0 if half else img[y, 205:206]
        return img, raw

    def test_a_flat_touching_a_ledger_stub_is_cut_at_the_boxes(self):
        img, raw = self._flat_on_rung()
        boxes = [["accidental", 190, 690, 302, 970], ["head", 460, 845, 590, 955], ["ledger", 300, 885, 650, 915]]
        r2 = SM.map_strokes(img, SP, LINES, raw, split_joins=True)
        r3 = SM.map_strokes(img, SP, LINES, raw, split_joins=True, touch_boxes=boxes)
        self.assertTrue((_canvas(r3) == _canvas(r2)).all())             # the same ink, every pixel
        cut = [s for s in r3.strokes if any(how.startswith("accidental|") for _j, how in s.joined_to)]
        self.assertEqual(len(cut), 2, [(s.kind, s.box, s.joined_to) for s in r3.strokes])
        acc_side = min(cut, key=lambda s: s.box[0])
        led_side = max(cut, key=lambda s: s.box[0])
        self.assertLessEqual(acc_side.box[0] + acc_side.box[2], 310)          # the flat's ink stops at the flat box's edge
        self.assertGreaterEqual(led_side.box[0], 295)                         # the stub starts there
        self.assertGreaterEqual(r3.split_refused.get("touch_cut", 0), 1)

    def test_no_accidental_box_or_one_box_leaves_it_as_round_2(self):
        img, raw = self._flat_on_rung()
        r2 = SM.map_strokes(img, SP, LINES, raw, split_joins=True)
        for boxes in ([["head", 460, 845, 590, 955], ["ledger", 300, 885, 650, 915]],       # the detector missed the flat
                      [["accidental", 150, 650, 700, 990], ["head", 460, 845, 590, 955]]):  # one box over both marks: cannot tell
            r3 = SM.map_strokes(img, SP, LINES, raw, split_joins=True, touch_boxes=boxes)
            self.assertEqual([(s.kind, s.box) for s in r3.strokes], [(s.kind, s.box) for s in r2.strokes])

    def test_boxes_that_overlap_on_the_ink_leave_it_whole_with_the_reason(self):
        m = np.zeros((10, 100), bool)
        m[3:7, :] = True                                # one piece of ink, 100 px long, in the reduced frame
        refused = {}
        parts = SM._cut_touching(m, 0, 0, 16.0, [("accidental", (0, 0, 60, 10)), ("ledger", (40, 0, 100, 10))], refused)
        self.assertEqual([j for _k, _p, j in parts], ["accidental|ledger"] * 2)
        other, acc = parts[0][1], parts[1][1]
        self.assertEqual(int(other.sum()) + int(acc.sum()), int(m.sum()))
        self.assertTrue(acc[3:7, :40].all())            # each box's own ink stays on its side
        self.assertTrue(other[3:7, 60:].all())
        refused = {}
        self.assertIsNone(SM._cut_touching(m, 0, 0, 16.0, [("accidental", (0, 0, 80, 10)), ("ledger", (20, 0, 100, 10))], refused))
        self.assertEqual(refused.get("touch_boxes_undecided"), 1)          # 60% of the ink in both boxes: the boxes cannot tell

    def _g_clef(self):
        """A clef-like shape the openings cut up: a tall spine, a bowl crossing it, a ball at the tail, the tail leaving the box."""
        img, raw = _blank()
        img[300:850, 300:318] = 0                       # the spine
        yy, xx = np.ogrid[:img.shape[0], :img.shape[1]]
        ring = np.abs(np.hypot(xx - 310, yy - 600) - 110) <= 9
        img[ring] = 0                                   # the bowl around the spine
        img[np.hypot(xx - 250, yy - 860) <= 32] = 0     # the ball
        img[850:870, 250:318] = 0                       # the tail joining spine and ball
        img[230:300, 318:330] = 0                       # the top curl's tip, above the detector's box (inside a G clef's 7.024 sp)
        return img, raw

    def test_a_clef_the_openings_cut_up_is_one_stroke(self):
        img, raw = self._g_clef()
        box = [180, 300, 440, 900]                      # the detector's box: 6 sp tall, the clef's tip outside it
        old = SM.map_strokes(img, SP, LINES, raw, split_joins=True, keep_whole=[box])
        new = SM.map_strokes(img, SP, LINES, raw, split_joins=True, keep_whole=[box + ["clef:G"]])
        self.assertGreater(len(old.strokes), 2)          # the cause: the openings cut the clef up, keep-whole never joined it
        self.assertEqual(len(new.strokes), 1, [(s.kind, s.box) for s in new.strokes])
        self.assertEqual(int(_canvas(new).sum()), int(_canvas(old).sum()))   # the same ink (an opening's crossing is counted once)
        self.assertLess(new.strokes[0].box[1], 300)     # its tip above the box came with it
        self.assertGreaterEqual(new.split_refused.get("clef_pieces_joined", 0), 2)

    def test_f_clef_dots_join_and_a_barline_touching_the_clef_does_not(self):
        img, raw = self._g_clef()
        img[400:412, 400:412] = 0                       # two dots inside the box, clear of the clef (an F clef's dots)
        img[480:492, 400:412] = 0
        img[0:1100, 180:192] = 0                        # a barline the bowl does not reach, and ...
        img[598:604, 192:200] = 0                       # ... a hair joining it to the bowl: one ink component, mostly outside the box
        box = [182, 300, 440, 900, "clef:G"]
        new = SM.map_strokes(img, SP, LINES, raw, split_joins=True, keep_whole=[box])
        big = [s for s in new.strokes if s.box[3] > 9 * SP]
        self.assertEqual(len(big), 1)                   # the barline stays its own stroke
        clef = [s for s in new.strokes if s is not big[0] and s.area_sp2 > 0.3]
        self.assertEqual(len(clef), 1, [(s.kind, s.box, s.area_sp2) for s in new.strokes])
        self.assertGreaterEqual(clef[0].box[0] + clef[0].box[2], 412)          # the dots are in it

    def test_ink_beyond_the_clefs_size_is_not_the_clef(self):
        img, raw = self._g_clef()
        img[0:562, 400:412] = 0                         # a line touching the bowl and running 5 sp above the box: a stem, not the clef
        new = SM.map_strokes(img, SP, LINES, raw, split_joins=True, keep_whole=[[180, 300, 440, 900, "clef:G"]])
        line = [s for s in new.strokes if s.box[1] == 0]
        self.assertEqual(len(line), 1, [(s.kind, s.box) for s in new.strokes])        # that line is its own stroke
        clef = max(new.strokes, key=lambda s: s.area_sp2)
        self.assertIsNot(clef, line[0])
        self.assertGreater(clef.box[1], 150)            # the clef stroke stops within the clef's size
        self.assertEqual(SM.clef_family("clefCAlto"), "C")
        self.assertEqual(SM.clef_family("gClef"), "G")
        self.assertIsNone(SM.clef_family("keyFlat"))


class StrokeRowsCarryTheJoin(unittest.TestCase):
    def test_rows_file_joined_to_only_with_the_flag(self):
        img, raw = _chord()
        c = types.SimpleNamespace(page_index=0, staff_index=0, measure_index=0, image_no_staff=img, binary=raw,
                                  staff_line_ys_canonical=LINES, upscale_factor=1.0, bbox_page_px=(0, 0, 1400, 1100))
        for word, want in (("0", False), ("", True)):
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
        self.assertEqual(self._run("0"), [105, 400])
        self.assertEqual(self._run(""), [400])


class ClefAreaGrowsToItsInk(unittest.TestCase):
    """Sean 2026-10-30: "make sure the box is big enough to claim all the ink and it should be based off of shape and size"."""

    def test_the_clef_claim_grows_to_its_joined_stroke_within_the_clefs_size(self):
        img, raw = Round3TouchingMarksAndClefs()._g_clef()
        img[0:562, 400:412] = 0                         # a stem touching the bowl, far above: never the clef's
        res = SM.map_strokes(img, SP, LINES, raw, split_joins=True, keep_whole=[[180, 300, 440, 900, "clef:G"]])
        cell = types.SimpleNamespace(upscale_factor=1.0, bbox_page_px=(0, 0, 1400, 1100))
        box = [180.0, 300.0, 440.0, 900.0]
        with mock.patch.dict(os.environ, {SM.SPLIT_JOINS_ENV: "1"}):
            area, grown = G._clef_area_by_ink(list(box), "G", cell, res, float(SP))
            self.assertEqual(grown, box)
            self.assertLess(area[1], 300)               # the curl's tip above the box is claimed now ...
            self.assertGreater(area[1], 150)            # ... the stem above the clef's size is not
        with mock.patch.dict(os.environ, {SM.SPLIT_JOINS_ENV: "0"}):
            self.assertEqual(G._clef_area_by_ink(list(box), "G", cell, res, float(SP)), (box, None))


class LeftEdgeReadOnce(unittest.TestCase):
    """The 2.239 left-side edge test lives in the ONE page-wide pass (Sean 2026-10-29: no second scan), STAGED pages only."""

    def test_the_left_side_test_is_staged_only_and_follows_the_flag(self):
        from tools.omr import measure_extractor as ME
        staged = types.SimpleNamespace(staged_page_wide=True)
        legacy = types.SimpleNamespace()                       # a LEGACY caller never sets staged_page_wide
        for word, want in (("0", False), ("1", True), ("", True)):
            with mock.patch.dict(os.environ, {SM.SPLIT_JOINS_ENV: word}):
                self.assertEqual(ME._left_edge_by_left(staged), want)
                self.assertFalse(ME._left_edge_by_left(legacy))
                self.assertFalse(ME._left_edge_by_left(None))

    def test_a_legacy_page_reads_the_old_left_edge_with_the_flag_on(self):
        from tools.omr import measure_extractor as ME
        seen = []
        with mock.patch.dict(os.environ, {SM.SPLIT_JOINS_ENV: "1"}), \
                mock.patch.object(ME, "_left_edge_read", side_effect=lambda *a, **k: seen.append(k.get("edge_by_left")) or {"marks": []}):
            ME._left_edge_read(None, [], edge_by_left=ME._left_edge_by_left(types.SimpleNamespace()))
            ME._left_edge_read(None, [], edge_by_left=ME._left_edge_by_left(types.SimpleNamespace(staged_page_wide=True)))
        self.assertEqual(seen, [False, True])

    def test_gather_scans_nothing_it_reads_the_pass(self):
        from tools.omr import measure_extractor as ME
        pws = types.SimpleNamespace(page=types.SimpleNamespace(binary=np.zeros((10, 10), np.uint8)), staves=[],
                                    system_structure={0: {"left_edge": {"marks": [{"kind": "bracket"}]}}})
        with mock.patch.dict(os.environ, {SM.SPLIT_JOINS_ENV: "1"}), \
                mock.patch.object(ME, "_left_edge_read", side_effect=AssertionError("scanned twice")):
            self.assertEqual(G._left_edge_marks(pws, 0), [{"kind": "bracket"}])


if __name__ == "__main__":
    unittest.main()
