"""ROADMAP 2.315 -- a bar that prints only a whole rest is READ (flag `OMR_WHOLE_REST_SEARCH_OWN_BAR`, default ON since 2026-11-17; the OFF twins below say `=0`).

THE RULE, in a musician's words: a bar that holds nothing of its own but a whole rest -- a block hanging from a line, a little over a space and a
half wide, well under a space tall -- is a whole-bar rest, written GUESSED (blue) where any other box stands in the bar. NEVER over a note: a head
(a space tall or more), a flag's piece (narrower), a stem, a word's or a barline's ink is not the rest; and never beside a refusal that may be a
real note of this bar (rule 8: "cannot tell" is not "silence").

CONTROLS ARE REAL MARKS (rule 7; Sean 2026-11-10 after 2.288 r3): `benchmarks/whole-rests-2026-11/real_cells/*.npz` are the staff-erased rasters of real
bars (Sean's 2.311 set-b tiles 8 and 12, and bars of the frozen sample), `rests-claim-first-2026-11/real_cases/` the stroke maps round Sean's answered rest
tiles. Each control was run where it fails first: with the flag OFF the real tile-12 bar is never searched and the real 0.87 sp rests are turned down.
"""
from __future__ import annotations

import json
import os
import pathlib
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import export as SX
from tools.omr.staged import gather
from tools.omr.staged.record import Log, Q, cell as R_cell
from tools.omr.tests import real_rest_cases as RC

HERE = pathlib.Path(__file__).resolve().parents[3] / "benchmarks" / "whole-rests-2026-11"
CELLS = json.load(open(HERE / "real_cells.json"))
FLAG = gather.WHOLE_REST_SEARCH_OWN_BAR_ENV


class _Det:
    def __init__(self, smufl_name):
        self.smufl_name = smufl_name


class _RealCell:
    """What `gather_empty_bar_rest_search` reads off a measure cell, from a dumped real bar."""

    def __init__(self, cid):
        z = np.load(HERE / "real_cells" / (cid + ".npz"))
        shape = tuple(int(v) for v in z["shape"])
        ink = np.unpackbits(z["ink"], axis=1)[:, :shape[1]].astype(bool)
        self.image_no_staff = np.where(ink, 0, 255).astype(np.uint8)
        self.staff_line_ys_canonical = [float(v) for v in z["lines"]]
        self.page_index, self.staff_index, self.measure_index = 0, 0, 0


def _search(cid, flag, detections=None):
    log = Log()
    c = _RealCell(cid)
    with mock.patch.dict(os.environ, {FLAG: "1" if flag else "0"}):
        gather.gather_empty_bar_rest_search(log, [c], {0: (0, 0)}, detections or {})
    return log.rows(Q.EMPTY_BAR_REST_SEARCH, R_cell(0, 0, 0, 0))


def _one_foreign_box():
    return {R_cell(0, 0, 0, 0).to_key(): [_Det("noteheadBlackInSpace")]}


class TestTheFlag(unittest.TestCase):
    def test_default_on_and_the_words_that_turn_it_off(self):
        env = {k: v for k, v in os.environ.items() if k != FLAG}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertTrue(gather.whole_rest_search_own_bar_enabled())
            self.assertTrue(SX.whole_rest_search_own_bar_enabled())
        for v in ("0", "false", "no", "off", "OFF"):
            with mock.patch.dict(os.environ, {FLAG: v}):
                self.assertFalse(gather.whole_rest_search_own_bar_enabled(), v)
                self.assertFalse(SX.whole_rest_search_own_bar_enabled(), v)
        for v in ("1", "true", "yes", "on"):
            with mock.patch.dict(os.environ, {FLAG: v}):
                self.assertTrue(gather.whole_rest_search_own_bar_enabled())
                self.assertTrue(SX.whole_rest_search_own_bar_enabled())


class TestSeansTwoTiles(unittest.TestCase):
    """Set b tiles 8 and 12: bars that hold NOTHING but a whole rest (his words). The cell of each holds one box that is not the bar's."""

    def test_the_search_never_looked_in_a_bar_whose_cell_holds_a_box(self):
        for cid in ("b-tile12", "b-tile8"):
            self.assertEqual(_search(cid, flag=False, detections=_one_foreign_box()), (), cid)   # fails where it fails: no row at all

    def test_with_the_flag_the_real_whole_rest_is_found_in_the_middle_of_the_bar(self):
        for cid in ("b-tile12", "b-tile8"):
            rows = _search(cid, flag=True, detections=_one_foreign_box())
            self.assertEqual(len(rows), 1, cid)
            self.assertIs(rows[0].value, True, cid)
            self.assertEqual(rows[0].detail["witness"], "middle", cid)
            self.assertLessEqual(rows[0].detail["height_spaces"], 0.92, cid)


class TestTheShapeIsTheInkRule(unittest.TestCase):
    """Real whole rests the detector-box numbers turn down (0.87 sp tall, aspect 1.56-1.62): found by the ink rule."""

    REAL_RESTS = ("lit-8-0-1-4", "lit-6-0-1-5", "bra-8-1-0-5")

    def test_the_box_numbers_turn_them_down(self):
        for cid in self.REAL_RESTS:
            rows = _search(cid, flag=False)
            self.assertEqual(len(rows), 1, cid)
            self.assertIs(rows[0].value, False, cid)
            self.assertEqual(rows[0].detail.get("reason"), "not_rest_shaped_or_positioned", cid)

    def test_the_ink_rule_finds_them(self):
        for cid in self.REAL_RESTS:
            rows = _search(cid, flag=True)
            self.assertEqual(len(rows), 1, cid)
            self.assertIs(rows[0].value, True, cid)

    def test_a_real_bar_of_notes_is_not_a_rest(self):
        """Bars of real notes the detector never boxed (our look): a head is a space tall or more, a half note is hollow -- nothing hangs as a rest."""
        for cid, m in CELLS.items():
            if m["is_whole_rest_bar"]:
                continue
            rows = _search(cid, flag=True)
            self.assertEqual(len(rows), 1, cid)
            self.assertIs(rows[0].value, False, cid)


class TestSeansRealMarksAtTheShapeTest(unittest.TestCase):
    """The 2.288 real cases (page strokes and pixels round Sean's answered rest tiles): the ink rule on the stroke a box stands on."""

    def _dims(self, cid):
        c = RC.load(cid)
        pm, bx, sp = c["page_map"], c["box"], c["page_map"].sp
        sel = []
        for s in pm.strokes:
            if s.box[0] < -1e5:
                continue
            b = (s.box[0], s.box[1], s.box[0] + s.box[2], s.box[1] + s.box[3])
            ix, iy = max(0, min(bx[2], b[2]) - max(bx[0], b[0])), max(0, min(bx[3], b[3]) - max(bx[1], b[1]))
            if (b[2] - b[0]) * (b[3] - b[1]) > 0 and ix * iy / ((b[2] - b[0]) * (b[3] - b[1])) > 0.5:
                sel.append(s)
        if not sel:
            return None
        h = (max(s.box[1] + s.box[3] for s in sel) - min(s.box[1] for s in sel)) / sp
        w = (max(s.box[0] + s.box[2] for s in sel) - min(s.box[0] for s in sel)) / sp
        return h, w

    def test_his_whole_rests_pass_and_the_box_numbers_missed_two_of_them(self):
        from tools.omr.staged.adjudicators import rhythm as RH
        cases = {c["id"]: c for c in json.load(open(RC.CASES_JSON))}
        passed, box_missed = [], []
        for cid, c in cases.items():
            if not c["sean"].startswith("whole rest"):
                continue
            d = self._dims(cid)
            if d is None:
                continue
            h, w = d
            self.assertTrue(gather._whole_rest_ink_shaped(h, w), (cid, h, w))
            passed.append(cid)
            if not RH._rest_shaped(h, w / h):
                box_missed.append(cid)
        self.assertGreaterEqual(len(passed), 8)
        self.assertEqual(sorted(box_missed), ["r3-06", "r3-12"])      # the control fails where it should: his real rests the old numbers refuse

    def test_his_heads_flags_text_and_strokes_are_not_rests(self):
        cases = {c["id"]: c for c in json.load(open(RC.CASES_JSON))}
        n = 0
        for cid, c in cases.items():
            if c["is_rest"] or not c["cls"].startswith(("restWhole", "restHalf", "rest8th", "rest16th", "restQuarter", "control")):
                continue
            d = self._dims(cid)
            if d is None:
                continue
            self.assertFalse(gather._whole_rest_ink_shaped(*d), (cid, c["sean"], d))
            n += 1
        self.assertGreaterEqual(n, 6)


class _Rec:
    """The three questions `_place_found_whole_rests` asks of a record."""

    def __init__(self, sub_cell, boxes, page_boxes=None, lines=None, staff=None):
        self.sub_cell = sub_cell
        self._boxes = boxes
        self._page_boxes = page_boxes or {}
        self._lines = lines
        self._staff = staff
        self.__dict__["_x"] = 1

    def obs_of(self, q):
        if q == Q.EMPTY_BAR_REST_SEARCH:
            return [{"subject": self.sub_cell, "detail": {"ink_bbox_canonical": [10, 20, 40, 32], "bbox_page_px": [100, 200, 130, 212]}}]
        if q == Q.GLYPH_BOX:
            return [dict({"subject": s, "value": [cls, 0, 0, 10, 10]},
                         **({"detail": {"bbox_page_px": self._page_boxes[s]}} if s in self._page_boxes else {}))
                    for s, cls in self._boxes.items()]
        return []

    def obs(self, q, key):
        if q == Q.GLYPH_BOX:
            return [o for o in self.obs_of(Q.GLYPH_BOX) if o["subject"] == key]
        if q == Q.STAFF_LINES and self._lines is not None and key == self._staff:
            return [{"subject": key, "value": self._lines}]
        return []

    def verdict(self, q, subject):
        return {"outcome": "decided", "value": True, "reason": "whole_rest_found_by_search"}


class TestExportWritesOnlyWhereNothingIsTheBarsOwn(unittest.TestCase):
    SUB = "cell/8/0/0/5"

    def _write(self, flag, boxes, fates):
        rec = _Rec(self.SUB, boxes)
        run = SX.StaffRun(key="staff/8/0/0", page=8, system=0, staff=0, n_measures=8)
        with mock.patch.dict(os.environ, {FLAG: "1" if flag else "0"}):
            SX._place_found_whole_rests(rec, {"staff/8/0/0": run}, None, {}, fates)
        return run.cells.get(5)

    def test_a_foreign_head_alone_leaves_the_rest_written_blue(self):
        boxes = {"glyph/8/0/0/5/0": "noteheadBlackOnLine"}
        cell = self._write(True, boxes, {"glyph/8/0/0/5/0": "owned_by_another_staff"})
        self.assertIsNotNone(cell)
        det = cell.detections[0]
        self.assertEqual(det["class"], "restWhole")
        self.assertIsNotNone(det["guess"])                      # another box stands in the bar: GUESSED, never READ

    def test_a_barline_boxs_ink_is_not_the_bars_own_either(self):
        boxes = {"glyph/8/0/0/5/0": "noteheadBlackInSpace"}
        self.assertIsNotNone(self._write(True, boxes, {"glyph/8/0/0/5/0": "not_a_notehead:claimed_by:barline"}))

    def test_a_refusal_that_may_be_a_real_note_keeps_the_bar_unread(self):
        """Rule 8: `too_narrow` / `clipped_fragment` / a narrowed value may be this bar's own note -- no whole rest beside it."""
        for fate in ("not_a_notehead:too_narrow", "not_a_notehead:clipped_fragment", "duration_narrowed", None):
            boxes = {"glyph/8/0/0/5/0": "noteheadBlackOnLine"}
            self.assertIsNone(self._write(True, boxes, {"glyph/8/0/0/5/0": fate} if fate else {}), fate)

    def test_with_the_flag_off_the_old_behaviour_is_unchanged(self):
        boxes = {"glyph/8/0/0/5/0": "noteheadBlackOnLine"}
        self.assertIsNotNone(self._write(False, boxes, {"glyph/8/0/0/5/0": "not_a_notehead:too_narrow"}))


class TestLitolffP1M51(unittest.TestCase):
    """The 2.315 fix, from the REAL bar (Litolff page 4, system 0, staff 0, bar 2 = P1 m51: a real whole rest, blue with the flag off, dropped by the
    first 2.315 build). Numbers read off the lane's saved record: the staff lines, and the one head-classed box in the bar -- a refused
    `clipped_fragment` of a note of the NEXT staff, cut off at this bar's cell edge, 3.7 spaces below the staff, its ledger line on the far side."""
    SUB = "cell/4/0/0/2"
    HEAD = "glyph/4/0/0/2/3"
    LINES = [414.0, 429.0, 445.0, 461.0, 476.0]
    FRAG = [796.705, 533.97, 816.39, 538.0]
    LEDGERS = {"glyph/4/0/0/2/0": [779.5, 456.005, 817.785, 460.345], "glyph/4/0/0/2/2": [792.675, 471.04, 807.245, 474.45]}   # inside the staff band

    def _write(self, frag=None, extra=None, fixed=True):
        boxes = {self.HEAD: "noteheadBlackInSpace", **{k: "ledgerLine" for k in self.LEDGERS}}
        pages = {self.HEAD: frag or self.FRAG, **self.LEDGERS}
        for k, (cls, b) in (extra or {}).items():
            boxes[k], pages[k] = cls, b
        rec = _Rec(self.SUB, boxes, pages, self.LINES, "staff/4/0/0")
        run = SX.StaffRun(key="staff/4/0/0", page=4, system=0, staff=0, n_measures=15)
        fates = {self.HEAD: "not_a_notehead:clipped_fragment"}
        with mock.patch.dict(os.environ, {FLAG: "1"}):
            if fixed:
                SX._place_found_whole_rests(rec, {"staff/4/0/0": run}, None, {}, fates)
            else:    # the build before the fix: every clipped piece may be this bar's own note
                with mock.patch.object(SX, "_clipped_piece_of_the_next_staff", lambda *a, **k: False):
                    SX._place_found_whole_rests(rec, {"staff/4/0/0": run}, None, {}, fates)
        return run.cells.get(2)

    def test_fails_before_the_fix(self):
        self.assertIsNone(self._write(fixed=False))

    def test_the_rest_is_written_blue_after_it(self):
        cell = self._write()
        self.assertIsNotNone(cell)
        self.assertIsNotNone(cell.detections[0]["guess"])        # another box stands in the bar: GUESSED, never READ

    def test_a_clipped_piece_within_three_spaces_of_the_staff_is_still_possibly_a_note(self):
        near = [796.705, 476.0 + 2.0 * 15.5, 816.39, 476.0 + 2.0 * 15.5 + 4.0]
        self.assertIsNone(self._write(frag=near))

    def test_a_ledger_line_between_the_piece_and_the_staff_keeps_the_bar_unread(self):
        self.assertIsNone(self._write(extra={"glyph/4/0/0/2/9": ("ledgerLine", [790.0, 500.0, 815.0, 503.0])}))

    def test_another_refusal_beside_it_still_keeps_the_bar_unread(self):
        self.assertIsNone(self._write(extra={"glyph/4/0/0/2/8": ("noteheadBlackInSpace", [790.0, 440.0, 805.0, 452.0])}))


if __name__ == "__main__":
    unittest.main()
