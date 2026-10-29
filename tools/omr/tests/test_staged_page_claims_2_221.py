"""ROADMAP 2.221 m1 / m1b: words, dynamics, brackets and braces claim their ink FIRST and PAGE-WIDE -- `gather.gather_page_claims`
(flags `OMR_CLAIM_WORDS_FIRST`, `OMR_CLAIM_BRACKETS_FIRST`, default OFF), `claims.spell_letter_runs` / `claims.bracket_areas`, and the
one consult `claimed_by`.

CAUSE (Sean 2026-10-28): heads take ink first because nobody wrote down who owns a word's letters or a bracket's rule before the head
box was drawn; the old pair rules refuse most of the damage afterwards. Sean 2026-10-29: words and dynamics are claimed "system or page
wide not based on individual measures", and with no new reading pass. Every CONTROL here passes with the rule absent or present, so a
rule that refuses everything cannot pass.
"""
from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate, adjudicators            # noqa: F401
from tools.omr.staged import claims as CL
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged import stroke_owner as SO
from tools.omr.staged.adjudicators import stroke_owner as ASO
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests.test_staged_duration import _staff_space

SP = 16.0
WORDS = {"OMR_CLAIMED_REGISTER": "1", "OMR_CLAIM_WORDS_FIRST": "1", "OMR_CLAIM_BRACKETS_FIRST": "0"}
BRACKETS = {"OMR_CLAIMED_REGISTER": "1", "OMR_CLAIM_WORDS_FIRST": "0", "OMR_CLAIM_BRACKETS_FIRST": "1"}
OFF = {"OMR_CLAIMED_REGISTER": "1", "OMR_CLAIM_WORDS_FIRST": "0", "OMR_CLAIM_BRACKETS_FIRST": "0"}
L0 = [100.0 + SP * i for i in range(5)]
L1 = [300.0 + SP * i for i in range(5)]
DYN = frozenset({"p", "pp", "f", "ff", "sf", "mf"})


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


# two bars on each staff: a barline at x 400
CELLS = [_Cell(0, 0, (60, 50, 400, 250)), _Cell(0, 1, (400, 50, 880, 250)),
         _Cell(1, 0, (60, 250, 400, 450)), _Cell(1, 1, (400, 250, 880, 450))]
LOCAL = {0: (0, 0), 1: (0, 1)}
WORD_BOX = (195.0, 198.0, 305.0, 220.0)          # "dolce" between the staves, in bar 0
SPREAD_BOX = (350.0, 198.0, 470.0, 220.0)        # "cresc." across the barline at x 400


def _page():
    img = np.full((520, 900), 255, np.uint8)
    for ly in L0 + L1:
        img[int(ly) - 1:int(ly) + 2, 100:880] = 0
    img[90:380, 94:98] = 0                             # a bracket rule: left of the staff start, crossing the gap
    for x in list(range(200, 300, 12)) + list(range(355, 470, 12)):   # two words' letters between the staves
        img[200:218, x:x + 7] = 0
    return img


def _box(log, k, gi, box, cls="noteheadBlackOnLine"):
    g = R.glyph(0, 0, 0, k, gi)
    x0 = 60 if k == 0 else 400
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame=f"cell:{k}", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (cls, box[0] - x0, box[1] - 50, box[2], box[3]), reader=READERS.DETECTOR, frame=f"cell:{k}", score=0.9,
                category="notehead", bbox_page_px=[box[0], box[1], box[0] + box[2], box[1] + box[3]])
    log.observe(g, Q.GLYPH_CONF, 0.9, reader=READERS.DETECTOR, frame=f"cell:{k}")
    return g


def _dets(boxes):
    """`{cell key: [det]}` for head boxes `(k, (x, y, w, h))` in page px on staff 0."""
    out = {}
    for k, (x, y, w, h) in boxes:
        x0 = 60 if k == 0 else 400
        out.setdefault(R.cell(0, 0, 0, k).to_key(), []).append(_Det("noteheadBlackOnLine", x - x0, y - 50, w, h))
    return out


def _word_row(log, text="dolce", bbox=WORD_BOX, gi=9000):
    return log.observe(R.glyph(0, 0, 0, 0, gi), Q.DIRECTION_WORD, text, reader=READERS.SURYA, frame="page", category="expression",
                       bbox_page_px=list(bbox))


def _gather(log, env, boxes, **kw):
    _PWS.page.binary = _page()
    with mock.patch.dict(os.environ, env):
        G.gather_page_claims(log, _PWS(), CELLS, LOCAL, _dets(boxes), **kw)
    return [r for r in log.rows(Q.CLAIMED_AREA, R.system(0, 0)) if r.detail.get("owner") in ("word", "bracket")]


def _verdict(env, k, box, stem=None, word=WORD_BOX):
    log = Log()
    _staff_space(log, SP)
    g = _box(log, k, 0, box)
    _word_row(log, bbox=word)
    if stem is not None:
        log.observe(R.cell(0, 0, 0, k), Q.STEM, stem, reader=READERS.CV_INK, frame=f"cell:{k}", x0=stem[0], x1=stem[0] + stem[2],
                    y_center=0)
    _gather(log, env, [(k, box)])
    with mock.patch.dict(os.environ, env):
        adjudicate.run(log)
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)


WORD_HEAD = (205, 200, 20, 18)          # a head-sized box standing on the word's letters (between the staves)
SPREAD_HEAD = (415, 200, 20, 18)        # a head-sized box on the spread word's letters, in BAR 1
FREE_HEAD = (205, 128, 20, 16)          # a head in the staff, nowhere near any word
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
        self.assertIn(CL.OWNER_BRACKET, CL.OWNERS)


class TestSpellLetterRuns(unittest.TestCase):
    def test_two_f_boxes_side_by_side_are_one_ff(self):
        runs = CL.spell_letter_runs([((100, 10, 112, 30), "f", "a"), ((114, 10, 126, 30), "f", "b")], SP, DYN)
        self.assertEqual([(r["text"], r["read"]) for r in runs], [("ff", True)])

    def test_CONTROL_a_lone_letter_is_not_read(self):
        runs = CL.spell_letter_runs([((100, 10, 112, 30), "f", "a")], SP, DYN)
        self.assertEqual([(r["read"], r["why"]) for r in runs], [(False, "lone_letter")])

    def test_CONTROL_letters_far_apart_are_two_lone_letters(self):
        runs = CL.spell_letter_runs([((100, 10, 112, 30), "f", "a"), ((200, 10, 212, 30), "f", "b")], SP, DYN)
        self.assertEqual([r["read"] for r in runs], [False, False])

    def test_a_twin_naming_another_letter_leaves_the_run_unspelled(self):
        runs = CL.spell_letter_runs([((100, 10, 112, 30), "f", "a"), ((100, 10, 112, 30), "p", "t"), ((114, 10, 126, 30), "f", "b")],
                                    SP, DYN)
        self.assertEqual([(r["read"], r["why"]) for r in runs], [(False, "twin_letters_disagree")])

    def test_a_twin_naming_the_same_letter_folds(self):
        runs = CL.spell_letter_runs([((100, 10, 112, 30), "f", "a"), ((101, 10, 112, 30), "f", "t"), ((114, 10, 126, 30), "f", "b")],
                                    SP, DYN)
        self.assertEqual([(r["text"], r["read"], len(r["rows"])) for r in runs], [("ff", True, 3)])

    def test_CONTROL_a_spelling_outside_the_vocabulary_is_not_read(self):
        runs = CL.spell_letter_runs([((100, 10, 112, 30), "p", "a"), ((114, 10, 126, 30), "f", "b")], SP, DYN)
        self.assertEqual([(r["read"], r["why"]) for r in runs], [(False, "not_a_dynamic")])


class TestBracketAreas(unittest.TestCase):
    def _s(self, **kw):
        base = dict(x_left=94, x_right=97, x_centre=95.5, thickness_px=4, thickness_spacings=0.25, y_top=90, y_bot=379,
                    height_spacings=18.0, straightness=0.99, offset_spacings=-0.3, n_columns=4)
        base.update(kw)
        return SimpleNamespace(**base)

    def test_a_tall_rule_left_of_the_staff_start_is_claimed_as_a_rule_and_a_curved_one_as_a_brace(self):
        got = CL.bracket_areas([self._s(), self._s(straightness=0.3, thickness_spacings=0.9)], lambda s: s.straightness > 0.9)
        self.assertEqual([a["kind"] for a in got], ["rule", "brace"])

    def test_CONTROL_a_stroke_right_of_the_staff_start_or_short_is_not_claimed(self):
        self.assertEqual(CL.bracket_areas([self._s(offset_spacings=2.0), self._s(height_spacings=2.5)], lambda s: True), [])


class TestGather(unittest.TestCase):
    def test_a_read_word_is_ONE_claim_on_its_system_holding_the_box_on_it(self):
        log = Log()
        g = _box(log, 0, 0, WORD_HEAD)
        _word_row(log)
        rows = _gather(log, WORDS, [(0, WORD_HEAD)])
        self.assertEqual([r.detail["owner"] for r in rows], ["word"])
        self.assertEqual((rows[0].detail["standing"], rows[0].detail["scope"], rows[0].detail["cell"]), ("READ", "system", None))
        self.assertGreaterEqual(rows[0].detail["boxes_inside"][g.to_key()]["ink_share_inside"], 0.5)

    def test_a_word_across_a_barline_is_one_claim_holding_boxes_in_both_bars(self):
        log = Log()
        _word_row(log, "cresc.", SPREAD_BOX)
        rows = _gather(log, WORDS, [(0, (365, 200, 20, 18)), (1, SPREAD_HEAD)])
        self.assertEqual(len(rows), 1)
        inside = rows[0].detail["boxes_inside"]
        self.assertIn(R.glyph(0, 0, 0, 0, 0).to_key(), inside)
        self.assertIn(R.glyph(0, 0, 0, 1, 0).to_key(), inside)

    def test_flag_off_files_nothing(self):
        log = Log()
        _word_row(log)
        self.assertEqual(_gather(log, OFF, [(0, WORD_HEAD)]), [])

    def test_CONTROL_a_word_on_the_staff_lines_is_not_claimed_here(self):
        log = Log()
        _word_row(log, bbox=(195.0, 96.0, 305.0, 170.0))            # inside staff 0's line band: milestone 4's
        self.assertEqual(_gather(log, WORDS, [(0, WORD_HEAD)]), [])

    def test_CONTROL_a_word_the_lexicon_refused_claims_nothing(self):
        log = Log()
        log.abstain(R.glyph(0, 0, 0, 0, 9000), Q.DIRECTION_WORD, reader=READERS.SURYA, frame="page", reason="no_reading",
                    bbox_page_px=list(WORD_BOX))
        self.assertEqual(_gather(log, WORDS, [(0, WORD_HEAD)]), [])

    def test_a_dynamic_spelled_from_two_detector_letters_claims_and_leaves_its_own_letter_boxes_out(self):
        log = Log()
        for gi, x in ((5, 200), (6, 214)):
            log.observe(R.glyph(0, 0, 0, 0, gi), Q.DYNAMIC_LETTER, "dynamicF", reader=READERS.DETECTOR, frame="page", letter="f",
                        bbox_page_px=[x, 200, x + 12, 218])
        rows = _gather(log, WORDS, [(0, WORD_HEAD)])
        self.assertEqual([(r.detail["owner"], r.detail["source"], r.detail["text"]) for r in rows], [("word", "dynamic_letters", "ff")])

    def test_brackets_come_from_the_page_wide_pass_strokes_given_and_nothing_is_scanned_again(self):
        stk = SimpleNamespace(x_left=94, x_right=97, x_centre=95.5, thickness_px=4, thickness_spacings=0.25, y_top=90, y_bot=379,
                              height_spacings=18.0, straightness=0.99, offset_spacings=-0.3, n_columns=4)
        log = Log()
        g = _box(log, 0, 0, BRACKET_HEAD)
        with mock.patch("tools.omr.bracket_reader.strokes_at_left_edge", side_effect=AssertionError("scanned twice")):
            rows = _gather(log, BRACKETS, [(0, BRACKET_HEAD)], edge_strokes={0: [stk]})
        self.assertEqual([r.detail["owner"] for r in rows], ["bracket"])
        self.assertGreaterEqual(rows[0].detail["boxes_inside"][g.to_key()]["ink_share_inside"], 0.5)

    def test_a_bracket_rule_read_by_the_left_edge_scan_files_a_claim(self):
        log = Log()
        g = _box(log, 0, 0, BRACKET_HEAD)
        rows = _gather(log, BRACKETS, [(0, BRACKET_HEAD)])
        self.assertTrue(rows)
        self.assertEqual(rows[0].detail["owner"], "bracket")
        self.assertGreaterEqual(rows[0].detail["boxes_inside"][g.to_key()]["ink_share_inside"], 0.5)

    def test_CONTROL_a_head_in_the_staff_is_in_no_claim(self):
        log = Log()
        g = _box(log, 0, 0, FREE_HEAD)
        _word_row(log)
        rows = _gather(log, dict(WORDS, OMR_CLAIM_BRACKETS_FIRST="1"), [(0, FREE_HEAD)])
        self.assertTrue(rows)
        self.assertTrue(all(g.to_key() not in (r.detail.get("boxes_inside") or {}) for r in rows))

    def test_the_page_census_row_says_what_was_claimed(self):
        log = Log()
        _word_row(log)
        _gather(log, WORDS, [(0, WORD_HEAD)])
        cen = [r for r in log.refusals(Q.CLAIMED_AREA, R.page(0)) if (r.detail or {}).get("why") == "page_claim_census"]
        self.assertEqual(cen[0].detail["census"], {"word:direction_word:claimed": 1})


class TestStrokeTier(unittest.TestCase):
    def test_a_page_wide_claim_owns_only_strokes_wholly_inside_it(self):
        class _Ev:
            def __init__(self, rows):
                self._rows = rows

            def rows(self, *_a, **_k):
                return self._rows
        row = SimpleNamespace(id="w", value=[195.0, 198.0, 305.0, 220.0],
                              detail={"owner": "word", "unit": "area", "standing": "READ", "scope": "system", "cell": None})
        page = {0: (200.0, 200.0, 207.0, 218.0), 1: (222.0, 160.0, 226.0, 219.0)}     # a letter; a stem crossing the word's box
        got = ASO._areas(_Ev([row]), SimpleNamespace(cell=3), page)
        self.assertEqual([c.covers for c in got], [(0,)])


class TestEndToEnd(unittest.TestCase):
    def test_a_box_on_a_read_words_ink_is_refused_with_the_flag_on(self):
        v = _verdict(WORDS, 0, WORD_HEAD)
        self.assertEqual((v.value, v.reason), (True, "claimed_by:word"))

    def test_a_box_in_the_next_bar_under_a_spread_word_is_refused_too(self):
        v = _verdict(WORDS, 1, SPREAD_HEAD, word=SPREAD_BOX)
        self.assertEqual((v.value, v.reason), (True, "claimed_by:word"))

    def test_FAILS_WITHOUT_THE_FIX_the_same_box_is_not_refused_as_a_word_with_the_flag_off(self):
        self.assertNotEqual(_verdict(OFF, 0, WORD_HEAD).reason, "claimed_by:word")

    def test_a_box_on_a_bracket_rule_is_refused_with_the_flag_on(self):
        v = _verdict(BRACKETS, 0, BRACKET_HEAD)
        self.assertEqual((v.value, v.reason), (True, "claimed_by:bracket"))
        self.assertNotEqual(_verdict(OFF, 0, BRACKET_HEAD).reason, "claimed_by:bracket")

    def test_CONTROL_the_word_flag_does_not_touch_a_bracket_box_and_the_reverse(self):
        self.assertNotEqual(_verdict(WORDS, 0, BRACKET_HEAD).reason, "claimed_by:bracket")
        self.assertNotEqual(_verdict(BRACKETS, 0, WORD_HEAD).reason, "claimed_by:word")

    def test_a_head_a_stem_stands_on_under_a_word_is_narrowed_never_refused(self):
        v = _verdict(WORDS, 0, WORD_HEAD, stem=(222 - 60, 160 - 50, 4, 60))
        self.assertEqual((v.outcome, v.reason), ("narrowed", "claim_narrowed:word"))

    def test_CONTROL_a_head_in_the_staff_is_never_touched(self):
        v = _verdict(dict(WORDS, OMR_CLAIM_BRACKETS_FIRST="1"), 0, FREE_HEAD)
        self.assertFalse(str(v.reason).startswith(("claimed_by:word", "claimed_by:bracket", "claim_narrowed:word", "claim_narrowed:bracket")))


if __name__ == "__main__":
    unittest.main()
