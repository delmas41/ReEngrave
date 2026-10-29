"""ROADMAP 2.221 m1 / m1b: a READ word and a bracket rule claim their ink BEFORE the heads -- `gather.gather_word_bracket_claims`
(flags `OMR_CLAIM_WORDS_FIRST`, `OMR_CLAIM_BRACKETS_FIRST`, default OFF) and the one consult `claimed_by`.

CAUSE (Sean 2026-10-28): heads take ink first because nobody wrote down who owns a word's letters or a bracket's rule before the head
box was drawn; the old pair rules refuse most of the damage afterwards. Every CONTROL here passes with the rule absent or present, so a
rule that refuses everything cannot pass.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate, adjudicators            # noqa: F401
from tools.omr.staged import claims as CL
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged import stroke_owner as SO
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests.test_staged_duration import _staff_space

SP = 16.0
WORDS = {"OMR_CLAIMED_REGISTER": "1", "OMR_CLAIM_WORDS_FIRST": "1", "OMR_CLAIM_BRACKETS_FIRST": "0"}
BRACKETS = {"OMR_CLAIMED_REGISTER": "1", "OMR_CLAIM_WORDS_FIRST": "0", "OMR_CLAIM_BRACKETS_FIRST": "1"}
OFF = {"OMR_CLAIMED_REGISTER": "1", "OMR_CLAIM_WORDS_FIRST": "0", "OMR_CLAIM_BRACKETS_FIRST": "0"}
L0 = [100.0 + SP * i for i in range(5)]
L1 = [300.0 + SP * i for i in range(5)]


class _Det:
    def __init__(self, name, x, y, w, h, conf=0.9):
        self.smufl_name, self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical = name, x, y, w, h
        self.confidence, self.category = conf, ""


class _Cell:
    def __init__(self, staff, k, bbox):
        self.staff_index, self.measure_index, self.page_index, self.bbox_page_px, self.upscale_factor = staff, k, 0, bbox, 1.0


class _Staff:
    def __init__(self, i, lines):
        self.staff_index, self.system_index, self.line_ys = i, 0, lines
        self.top_y, self.bottom_y, self.line_spacing_px, self.x_start = int(lines[0]), int(lines[-1]), SP, 100


class _PWS:
    class page:
        page_index = 0
    staves = [_Staff(0, L0), _Staff(1, L1)]


CELLS = [_Cell(0, 0, (60, 50, 400, 250)), _Cell(1, 0, (60, 250, 400, 450))]
LOCAL = {0: (0, 0), 1: (0, 1)}


def _page():
    img = np.full((520, 900), 255, np.uint8)
    for ly in L0 + L1:
        img[int(ly) - 1:int(ly) + 2, 100:880] = 0
    img[90:380, 94:98] = 0                             # a bracket rule: left of the staff start, crossing the gap
    for x in range(200, 300, 12):                      # a word's letters between the two staves
        img[200:218, x:x + 7] = 0
    return img


def _box(log, gi, box, cls="noteheadBlackOnLine"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.9, category="notehead",
                bbox_page_px=[box[0], box[1], box[0] + box[2], box[1] + box[3]])
    log.observe(g, Q.GLYPH_CONF, 0.9, reader=READERS.DETECTOR, frame="cell:0")
    return g


def _dets(x, y, w, h):          # the head box in page px -> the cell's canonical px (cell 0 of staff 0 starts at (60, 50), upscale 1)
    return {R.cell(0, 0, 0, 0).to_key(): [_Det("noteheadBlackOnLine", x - 60, y - 50, w, h)]}


def _word_row(log, text="dolce", bbox=(195.0, 198.0, 305.0, 220.0)):
    g = R.glyph(0, 0, 0, 0, 9000)
    return log.observe(g, Q.DIRECTION_WORD, text, reader=READERS.SURYA, frame="page", category="expression", bbox_page_px=list(bbox))


def _log(box, stem=None):
    log = Log()
    _staff_space(log, SP)
    g = _box(log, 0, box)
    _word_row(log)
    if stem is not None:
        log.observe(R.cell(0, 0, 0, 0), Q.STEM, stem, reader=READERS.CV_INK, frame="cell:0", x0=stem[0], x1=stem[0] + stem[2], y_center=0)
    return log, g


def _claims(log, env, box):
    _PWS.page.binary = _page()
    with mock.patch.dict(os.environ, env):
        G.gather_word_bracket_claims(log, _PWS(), CELLS, LOCAL, _dets(*box))
    return [r for r in log.rows(Q.CLAIMED_AREA, R.staff(0, 0, 0)) if r.detail.get("owner") in ("word", "bracket")]


def _verdict(env, box, stem=None):
    log, g = _log(box, stem)
    _claims(log, env, box)
    with mock.patch.dict(os.environ, env):
        adjudicate.run(log)
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)


WORD_HEAD = (205, 200, 20, 18)          # a head-sized box standing on the word's letters (between the staves)
FREE_HEAD = (205, 128, 20, 16)          # a head in the staff, nowhere near the word
BRACKET_HEAD = (88, 128, 12, 16)        # a box on the bracket rule, left of the staff start


class TestFlags(unittest.TestCase):
    def test_both_default_off_and_need_the_register(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMR_CLAIM_WORDS_FIRST", None)
            os.environ.pop("OMR_CLAIM_BRACKETS_FIRST", None)
            self.assertFalse(CL.words_first_enabled())
            self.assertFalse(CL.brackets_first_enabled())
        with mock.patch.dict(os.environ, WORDS):
            self.assertTrue(CL.words_first_enabled())
            self.assertFalse(CL.brackets_first_enabled())
        with mock.patch.dict(os.environ, {"OMR_CLAIMED_REGISTER": "0", "OMR_CLAIM_WORDS_FIRST": "1"}):
            self.assertFalse(CL.words_first_enabled())

    def test_the_new_owners_are_area_owners_for_the_stroke_tier(self):
        self.assertIn("word", SO.AREA_OWNERS)
        self.assertIn("bracket", SO.AREA_OWNERS)
        self.assertIn(CL.OWNER_WORD, CL.OWNERS)


class TestGather(unittest.TestCase):
    def test_a_read_word_outside_the_staves_files_an_area_claim_that_holds_the_box_on_it(self):
        log, g = _log(WORD_HEAD)
        rows = _claims(log, WORDS, WORD_HEAD)
        self.assertEqual([r.detail["owner"] for r in rows], ["word"])
        self.assertEqual(rows[0].detail["standing"], "READ")
        self.assertGreaterEqual(rows[0].detail["boxes_inside"][g.to_key()]["ink_share_inside"], 0.5)

    def test_flag_off_files_nothing(self):
        log, _g = _log(WORD_HEAD)
        self.assertEqual(_claims(log, OFF, WORD_HEAD), [])

    def test_CONTROL_a_word_on_the_staff_lines_is_not_claimed_here(self):
        log = Log()
        _staff_space(log, SP)
        _box(log, 0, WORD_HEAD)
        _word_row(log, bbox=(195.0, 96.0, 305.0, 170.0))            # inside staff 0's line band: milestone 4's
        _PWS.page.binary = _page()
        with mock.patch.dict(os.environ, WORDS):
            G.gather_word_bracket_claims(log, _PWS(), CELLS, LOCAL, _dets(*WORD_HEAD))
        self.assertEqual([r for r in log.rows(Q.CLAIMED_AREA, R.staff(0, 0, 0)) if r.detail.get("owner") == "word"], [])

    def test_CONTROL_a_word_the_lexicon_refused_claims_nothing(self):
        log = Log()
        _staff_space(log, SP)
        _box(log, 0, WORD_HEAD)
        log.abstain(R.glyph(0, 0, 0, 0, 9000), Q.DIRECTION_WORD, reader=READERS.SURYA, frame="page", reason="no_reading",
                    bbox_page_px=[195.0, 198.0, 305.0, 220.0])
        _PWS.page.binary = _page()
        with mock.patch.dict(os.environ, WORDS):
            G.gather_word_bracket_claims(log, _PWS(), CELLS, LOCAL, _dets(*WORD_HEAD))
        self.assertEqual([r for r in log.rows(Q.CLAIMED_AREA, R.staff(0, 0, 0)) if r.detail.get("owner") == "word"], [])

    def test_a_bracket_rule_at_the_left_edge_files_a_claim_and_a_box_on_a_note_does_not(self):
        log, g = _log(BRACKET_HEAD)
        rows = _claims(log, BRACKETS, BRACKET_HEAD)
        self.assertTrue(rows)
        self.assertEqual(rows[0].detail["owner"], "bracket")
        self.assertGreaterEqual(rows[0].detail["boxes_inside"][g.to_key()]["ink_share_inside"], 0.5)

    def test_CONTROL_a_head_in_the_staff_is_in_no_claim(self):
        log, g = _log(FREE_HEAD)
        rows = _claims(log, dict(WORDS, OMR_CLAIM_BRACKETS_FIRST="1"), FREE_HEAD)
        self.assertTrue(all(g.to_key() not in (r.detail.get("boxes_inside") or {}) for r in rows))


class TestEndToEnd(unittest.TestCase):
    def test_a_box_on_a_read_words_ink_is_refused_with_the_flag_on(self):
        v = _verdict(WORDS, WORD_HEAD)
        self.assertEqual((v.value, v.reason), (True, "claimed_by:word"))

    def test_FAILS_WITHOUT_THE_FIX_the_same_box_is_not_refused_as_a_word_with_the_flag_off(self):
        self.assertNotEqual(_verdict(OFF, WORD_HEAD).reason, "claimed_by:word")

    def test_a_box_on_a_bracket_rule_is_refused_with_the_flag_on(self):
        v = _verdict(BRACKETS, BRACKET_HEAD)
        self.assertEqual((v.value, v.reason), (True, "claimed_by:bracket"))
        self.assertNotEqual(_verdict(OFF, BRACKET_HEAD).reason, "claimed_by:bracket")

    def test_CONTROL_the_word_flag_does_not_touch_a_bracket_box_and_the_reverse(self):
        self.assertNotEqual(_verdict(WORDS, BRACKET_HEAD).reason, "claimed_by:bracket")
        self.assertNotEqual(_verdict(BRACKETS, WORD_HEAD).reason, "claimed_by:word")

    def test_a_head_a_stem_stands_on_under_a_word_is_a_note_narrowed_never_refused(self):
        v = _verdict(WORDS, WORD_HEAD, stem=(222, 160, 4, 60))
        self.assertNotEqual(v.reason, "claimed_by:word")
        self.assertEqual((v.outcome, v.reason), ("narrowed", "claim_narrowed:word"))

    def test_CONTROL_a_head_in_the_staff_is_never_touched(self):
        v = _verdict(dict(WORDS, OMR_CLAIM_BRACKETS_FIRST="1"), FREE_HEAD)
        self.assertFalse(str(v.reason).startswith(("claimed_by:word", "claimed_by:bracket", "claim_narrowed:word", "claim_narrowed:bracket")))


if __name__ == "__main__":
    unittest.main()
