"""ROADMAP 2.198 step 2: `Q.GLYPH_STROKES` (each detector box -> the strokes it covers), the register's `ink` claims, `claims.covering`'s
`ink` branch, and the slimmed `Q.STROKE` rows. A synthetic cell of KNOWN geometry; every control can fail."""
import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import claims as CL
from tools.omr.staged import gather as G
from tools.omr.staged import record as RC
from tools.omr.staged import stroke_map as SM
from tools.omr.staged.record import Q, READERS
from tools.omr.tests.test_stroke_map_2_195 import LINES, SP, _build

ENV = G.STROKE_MAP_ENV


class _Det:
    def __init__(self, name, x, y, w, h):
        self.smufl_name, self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical = name, x, y, w, h


class _Cell:
    page_index, system_index, staff_index, measure_index = 0, 0, 0, 0
    staff_line_ys_canonical = LINES
    upscale_factor = 2.0
    bbox_page_px = (10, 20, 710, 520)

    def __init__(self):
        self.image_no_staff, self.binary = _build()


def _strokes():
    img, raw = _build()
    return SM.map_strokes(img, SP, LINES, raw)


def _at(res, kind, near):
    c = [i for i, s in enumerate(res.strokes) if s.kind == kind and abs(s.box[0] - near[0]) < 80 and abs(s.box[1] - near[1]) < 80]
    assert len(c) == 1, (kind, near)
    return c[0]


class StrokesInBox(unittest.TestCase):
    def setUp(self):
        self.res = _strokes()
        self.stem = _at(self.res, "vertical", (200, 350))
        self.beam = _at(self.res, "horizontal", (600, 340))
        self.rung = _at(self.res, "horizontal", (700, 800))

    def test_a_box_on_the_beam_covers_the_beam_and_nothing_else(self):
        got = dict(SM.strokes_in_box(self.res, (590, 330, 1010, 400)))
        self.assertGreaterEqual(got[self.beam], 0.95)
        self.assertEqual(set(got) - {self.beam}, set())

    def test_a_box_over_empty_paper_covers_nothing_and_says_so(self):
        self.assertEqual(SM.strokes_in_box(self.res, (1100, 100, 1300, 250)), [])

    def test_CONTROL_a_box_moved_off_the_beam_loses_it(self):
        self.assertNotIn(self.beam, dict(SM.strokes_in_box(self.res, (590, 600, 1010, 680))))

    def test_a_box_across_half_a_stroke_reports_the_half(self):
        got = dict(SM.strokes_in_box(self.res, (600, 330, 800, 400)))        # the left half of the 400 px beam
        self.assertAlmostEqual(got[self.beam], 0.5, delta=0.08)
        self.assertLess(got[self.beam] - 0.5, 0.08)

    def test_the_cut_is_the_registers_one_cut(self):
        self.assertEqual(SM.COVER_SHARE_MIN, CL.INSIDE_SHARE_MIN)


class GlyphStrokesRows(unittest.TestCase):
    def _run(self, word):
        c = _Cell()
        dets = {G.R.cell(0, 0, 0, 0).to_key(): [_Det("beam", 590, 330, 420, 70), _Det("rest", 1100, 100, 200, 150),
                                                  _Det("stem", 190, 340, 40, 370)]}
        log = G.Log()
        with mock.patch.dict(os.environ, {ENV: word}):
            cache = G.gather_stroke_map(log, [c], {0: (0, 0)})
            G.gather_glyph_strokes(log, [c], {0: (0, 0)}, dets, cache)
        return log, cache

    def test_off_files_nothing_and_returns_nothing(self):
        log, cache = self._run("0")
        self.assertEqual(cache, {})
        self.assertEqual([r for r in log.all_rows() if r.quantity in (Q.STROKE, Q.GLYPH_STROKES)], [])

    def test_on_files_one_row_per_box_with_empty_lists_kept(self):
        log, cache = self._run("1")
        rows = sorted((r for r in log.all_rows() if r.quantity == Q.GLYPH_STROKES), key=lambda r: r.subject.to_key())
        self.assertEqual(len(rows), 3)
        by = {r.subject.to_key().rsplit("/", 1)[1]: r for r in rows}
        res = cache[(0, 0, 0, 0)]
        beam_i = _at(res, "horizontal", (600, 340))
        self.assertEqual(by["0"].value, [beam_i])                     # the beam box stands on the beam
        self.assertEqual(by["1"].value, [])                           # the rest box on empty paper: an empty list is a fact
        self.assertEqual(len(by["2"].detail["shares"]), len(by["2"].value))
        self.assertIn(_at(res, "vertical", (200, 350)), by["2"].value)

    def test_a_cell_with_no_strokes_abstains_per_box_never_an_empty_list(self):
        c = _Cell()
        c.image_no_staff = np.full((1000, 1400), 255, np.uint8)
        log = G.Log()
        with mock.patch.dict(os.environ, {ENV: "1"}):
            cache = G.gather_stroke_map(log, [c], {0: (0, 0)})
            G.gather_glyph_strokes(log, [c], {0: (0, 0)}, {G.R.cell(0, 0, 0, 0).to_key(): [_Det("beam", 590, 330, 420, 70)]}, cache)
        gs = [r for r in log.all_rows() if r.quantity == Q.GLYPH_STROKES]
        self.assertEqual([type(r).__name__ for r in gs], ["Abstention"])           # one abstention, no observation (no empty list)
        self.assertEqual(gs[0].reason, "no_ink")

    def test_the_slimmed_rows_keep_what_the_plan_names_and_drop_the_rest(self):
        log, _ = self._run("1")
        rows = [r for r in log.all_rows() if r.quantity == Q.STROKE]
        self.assertTrue(rows)
        for r in rows:
            for gone in ("area_sp2", "component_n_strokes", "staff_lines_left", "staff_lines_right"):
                self.assertNotIn(gone, r.detail)
            for kept in ("stroke_box", "length_spaces", "angle_deg", "thickness_spaces", "thickness_spread_spaces", "fill", "ends",
                         "end_steps_from_top", "touches", "component", "staff_space_local_px"):
                self.assertIn(kept, r.detail)
            self.assertEqual(len(r.detail["ends"]), 4)
            self.assertEqual("profile_sixteenths" in r.detail, r.value != "blob")
        self.assertEqual(sum(1 for r in rows if "cell_n_below_floor" in r.detail), 1)       # the cell fact is said once


class StrokesAreNotWalked(unittest.TestCase):
    """The measured cost of making strokes glyph subjects: every EVALUATE rule 'skipped' each of them (+11.9 MB on 2 Litolff pages)."""

    def test_log_subjects_lists_marks_not_strokes(self):
        log = G.Log()
        mark, stroke = G.R.glyph(0, 0, 0, 0, 7), G.R.glyph(0, 0, 0, 0, RC.STROKE_GLYPH_BASE + 3)
        log.observe(mark, Q.GLYPH_BOX, "noteheadBlack", reader=READERS.DETECTOR, frame="cell:0")
        log.observe(stroke, Q.STROKE, "blob", reader=READERS.CV_STROKE, frame="cell:0")
        keys = [s.to_key() for s in log.subjects(RC.Kind.GLYPH)]
        self.assertEqual(keys, [mark.to_key()])
        self.assertEqual(len(log.subjects(RC.Kind.CELL)), 1)                           # the cell is listed as ever
        self.assertEqual(len(log.rows(Q.STROKE, stroke)), 1)                           # and the stroke row is still readable

    def test_CONTROL_a_mark_numbered_just_below_the_base_is_still_listed(self):
        log = G.Log()
        m = G.R.glyph(0, 0, 0, 0, RC.STROKE_GLYPH_BASE - 1)
        log.observe(m, Q.GLYPH_BOX, "noteheadBlack", reader=READERS.DETECTOR, frame="cell:0")
        self.assertEqual([s.to_key() for s in log.subjects(RC.Kind.GLYPH)], [m.to_key()])
        h = G.R.glyph(0, 0, 0, 0, RC.HUMAN_GLYPH_BASE_FLOOR)                            # a human box (400,000) is a mark
        log.observe(h, Q.GLYPH_BOX, "noteheadBlack", reader=READERS.DETECTOR, frame="cell:0")
        self.assertIn(h.to_key(), [s.to_key() for s in log.subjects(RC.Kind.GLYPH)])

    def test_the_two_bases_agree_with_the_human_base(self):
        from tools.omr.staged.review import human_evidence as HE
        self.assertEqual(RC.HUMAN_GLYPH_BASE_FLOOR, HE.HUMAN_GLYPH_BASE)
        self.assertEqual(G._STROKE_GLYPH_BASE, RC.STROKE_GLYPH_BASE)
        self.assertLess(RC.STROKE_GLYPH_BASE, RC.HUMAN_GLYPH_BASE_FLOOR)


class _Row:
    def __init__(self, value, **d):
        self.value, self.detail, self.id = value, d, "obs"


class InkBranch(unittest.TestCase):
    def test_ink_claims_are_ignored_without_box_strokes(self):
        rows = [_Row([1, 2], owner="clef", unit="ink", cell=0, owner_glyph="own")]
        self.assertEqual(CL.covering(rows, "b"), [])                     # every existing caller reads what it read

    def test_a_box_on_the_claims_strokes_is_held_and_a_neighbour_is_not(self):
        rows = [_Row([1, 2], owner="clef", unit="ink", cell=0, owner_glyph="own")]
        got = CL.covering(rows, "b", box_strokes=[1, 2], cell=0)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][1]["stroke_share"], 1.0)
        self.assertEqual(CL.covering(rows, "c", box_strokes=[7, 8], cell=0), [])          # CONTROL: other strokes, not held
        self.assertEqual(CL.covering(rows, "d", box_strokes=[1, 7, 8], cell=0), [])        # a third shared is below the cut
        self.assertEqual(len(CL.covering(rows, "e", box_strokes=[1, 2, 7], cell=0)), 1)    # two of three is above it
        self.assertEqual(CL.covering(rows, "b", box_strokes=[1, 2], cell=1), [])           # another cell's ordinals are not these
        self.assertEqual(CL.covering(rows, "own", box_strokes=[1, 2], cell=0), [])         # the owner box is never its own held box

    def test_area_claims_still_work_beside_ink_claims(self):
        rows = [_Row([0, 0, 1, 1], owner="clef", unit="area", boxes_inside={"a": {"named": True}}),
                _Row([1], owner="clef", unit="ink", cell=0, owner_glyph="own")]
        self.assertEqual([r.detail["unit"] for r, _ in CL.covering(rows, "a", box_strokes=[1], cell=0)], ["area", "ink"])


class RegisterInkRows(unittest.TestCase):
    def test_a_clef_box_files_an_ink_claim_beside_its_area_claim(self):
        from tools.omr.tests.test_staged_claims_register_2_181 import _Cell as RC_, _Det as RD, _PWS, _page, ON as REG_ON
        img = _page()
        img[84:184, 150:176] = 0                       # the clef's ink
        _PWS.page.binary = img
        cell = RC_(0, (100, 50, 400, 250))
        dets = {G.R.cell(0, 0, 0, 0).to_key(): [RD("clefG", 50, 34, 26, 100)]}
        # a stroke map for the cell: one blob exactly under the clef box
        res = SM.CellStrokes([], 0, 1.0, 16.0, True)
        res.masks = [(np.ones((100, 26), bool), 50, 34)]
        res.strokes = [None]
        log = G.Log()
        gs = G.R.glyph(0, 0, 0, 0, 0)
        log.observe(gs, Q.GLYPH_BOX, "clefG", reader=READERS.DETECTOR, frame=G.frame_cell(0))
        log.observe(gs, Q.GLYPH_STROKES, [0], reader=READERS.CV_GLYPH_STROKES, frame=G.frame_cell(0), shares=[1.0])
        with mock.patch.dict(os.environ, REG_ON):
            G.gather_claimed_register(log, _PWS(), [cell], {0: (0, 0)}, dets, stroke_cells={(0, 0, 0, 0): res})
        claims = list(log.rows(Q.CLAIMED_AREA, G.R.staff(0, 0, 0)))
        units = sorted(r.detail["unit"] for r in claims if r.detail["owner"] == "clef")
        self.assertEqual(units, ["area", "ink"])
        ink = [r for r in claims if r.detail["unit"] == "ink"][0]
        self.assertEqual(ink.value, [0])
        self.assertEqual(ink.detail["owner_glyph"], gs.to_key())
        # CONTROL: no stroke map -> no ink row at all (flag off behaves as before)
        log2 = G.Log()
        log2.observe(gs, Q.GLYPH_BOX, "clefG", reader=READERS.DETECTOR, frame=G.frame_cell(0))
        with mock.patch.dict(os.environ, REG_ON):
            G.gather_claimed_register(log2, _PWS(), [cell], {0: (0, 0)}, dets)
        self.assertEqual([r.detail["unit"] for r in log2.rows(Q.CLAIMED_AREA, G.R.staff(0, 0, 0)) if r.detail["owner"] == "clef"], ["area"])


if __name__ == "__main__":
    unittest.main()
