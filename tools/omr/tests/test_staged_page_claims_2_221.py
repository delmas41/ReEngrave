"""ROADMAP 2.221 m1 / m1b: words, dynamics, brackets and braces claim their ink FIRST and PAGE-WIDE -- `gather.gather_page_claims`
(flags `OMR_CLAIM_WORDS_FIRST`, `OMR_CLAIM_BRACKETS_FIRST`, default ON), `claims.spell_letter_runs` / `claims.left_edge_claims`, and the
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
    img[202:216, 311:327] = 0                          # a metronome note's head, right of the word (tempo tests)
    img[198:220, 327:329] = 0                          # and its stem
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


def _word_row(log, text="dolce", bbox=WORD_BOX, gi=9000, category="expression"):
    return log.observe(R.glyph(0, 0, 0, 0, gi), Q.DIRECTION_WORD, text, reader=READERS.SURYA, frame="page", category=category,
                       bbox_page_px=list(bbox))


def _gather(log, env, boxes, **kw):
    _PWS.page.binary = _page()
    with mock.patch.dict(os.environ, env):
        G.gather_page_claims(log, _PWS(), CELLS, LOCAL, _dets(boxes), **kw)
    return [r for r in log.rows(Q.CLAIMED_AREA, R.system(0, 0)) if r.detail.get("owner") in ("word", "bracket")]


def _verdict(env, k, box, stem=None, word=WORD_BOX, category="expression"):
    log = Log()
    _staff_space(log, SP)
    g = _box(log, k, 0, box)
    _word_row(log, bbox=word, category=category)
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
    def test_both_default_on_deny_list_and_need_the_register(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMR_CLAIM_WORDS_FIRST", None)
            os.environ.pop("OMR_CLAIM_BRACKETS_FIRST", None)
            os.environ.pop("OMR_CLAIMED_REGISTER", None)
            self.assertTrue(CL.words_first_enabled())
            self.assertTrue(CL.brackets_first_enabled())
        with mock.patch.dict(os.environ, {"OMR_CLAIM_WORDS_FIRST": "0", "OMR_CLAIM_BRACKETS_FIRST": "off"}):
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


class TestLeftEdgeClaims(unittest.TestCase):
    def _m(self, kind, **kw):
        base = dict(kind=kind, box=[94, 90, 98, 380], staff_indices=[0, 1], hook_sp=0.9, bend_sp=0.0, width_sp=0.6)
        base.update(kw)
        return base

    def test_a_bracket_is_READ_by_its_shape_and_a_brace_needs_the_detector_as_second_witness(self):
        got = CL.left_edge_claims([self._m("bracket"), self._m("brace", box=[94, 400, 98, 700]), self._m("brace", box=[94, 800, 98, 900])],
                                  [([90, 395, 100, 705], "brace")])
        self.assertEqual([(a["kind"], a["standing"], a["witness"]) for a in got],
                         [("bracket", "READ", None), ("brace", "READ", "brace"), ("brace", "GUESSED", None)])

    def test_CONTROL_a_mark_of_no_kind_is_still_claimed_but_never_READ(self):
        got = CL.left_edge_claims([self._m(None)], [])
        self.assertEqual((got[0]["kind"], got[0]["standing"], got[0]["area"]), (None, "GUESSED", [94.0, 90.0, 98.0, 380.0]))


class TestMetronomeAndLabels(unittest.TestCase):
    def test_a_metronome_note_and_its_tail_are_part_of_the_tempo_mark(self):
        img = np.full((200, 700), 255, np.uint8)
        img[100:110, 400:412] = 0                         # the note head
        img[80:110, 411:413] = 0                          # its stem
        img[100:102, 440:470] = 0                         # the `=`
        img[98:112, 480:520] = 0                          # `108`
        mm = CL.metronome_mark([100.0, 90.0, 380.0, 112.0], [[400.0, 98.0, 413.0, 112.0]], img, SP)
        self.assertEqual(mm["note_box"], [400.0, 98.0, 413.0, 112.0])
        self.assertGreaterEqual(mm["box"][2], 520.0)
        self.assertEqual(mm["box"][0], 100.0)

    def test_CONTROL_no_note_right_of_the_word_or_a_note_on_another_line_is_no_metronome(self):
        img = np.full((200, 700), 255, np.uint8)
        self.assertIsNone(CL.metronome_mark([100.0, 90.0, 380.0, 112.0], [], img, SP))
        self.assertIsNone(CL.metronome_mark([100.0, 90.0, 380.0, 112.0], [[400.0, 160.0, 413.0, 174.0]], img, SP))
        self.assertIsNone(CL.metronome_mark([100.0, 90.0, 380.0, 112.0], [[100.0, 95.0, 113.0, 109.0]], img, SP))   # LEFT of the word

    def test_an_instrument_name_is_the_text_sized_ink_of_its_strip_and_a_brace_is_not(self):
        img = np.full((300, 400), 255, np.uint8)
        img[100:114, 20:30] = 0
        img[100:114, 40:60] = 0
        img[20:280, 90:96] = 0                            # a brace: taller than text
        self.assertEqual(CL.margin_label_box(img, [0, 0, 100, 300], SP), [20.0, 100.0, 60.0, 114.0])
        self.assertIsNone(CL.margin_label_box(img, [85, 0, 100, 300], SP))
        self.assertEqual(CL.margin_label_box(img, [0, 0, 100, 300], SP, avoid=[[15, 95, 65, 120]]), None)

    def test_heading_text_joins_into_blocks_and_skips_what_is_claimed(self):
        img = np.full((300, 600), 255, np.uint8)
        for x in range(100, 300, 24):
            img[50:80, x:x + 14] = 0
        img[200:220, 400:420] = 0
        blocks = CL.heading_blocks(img, [0, 0, 600, 300], SP, avoid=[[390, 190, 430, 230]])
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0][:2], [100.0, 50.0])

    def test_a_heading_needs_two_letters_a_speck_a_stem_tip_or_one_curved_stroke_is_not_text(self):
        img = np.full((300, 600), 255, np.uint8)
        img[50:68, 250:254] = 0                           # a stem tip: one thin speck
        for x in range(100, 140):                         # a slur: one long, curved, wide stroke
            img[200 + (x - 120) ** 2 // 60, x] = 0
        img[200:204, 300:560] = 0                         # a long flat stroke
        self.assertEqual(CL.heading_blocks(img, [0, 0, 600, 300], SP), [])
        img[100:130, 20:34] = 0                           # two letters on a line: a heading
        img[100:130, 44:58] = 0
        img[96:99, 62:65] = 0                             # an i-dot beside them joins; it never starts a block
        got = CL.heading_blocks(img, [0, 0, 600, 300], SP)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][:2], [20.0, 96.0])

    def test_a_heading_never_takes_ink_along_a_traced_arc_and_sizes_a_letter_by_the_pages_read_text(self):
        img = np.full((300, 600), 255, np.uint8)
        img[100:130, 20:34] = 0
        img[100:130, 44:58] = 0
        trace = {x: (95.0, 135.0) for x in range(10, 70)}
        self.assertEqual(CL.heading_blocks(img, [0, 0, 600, 300], SP, arc_traces=[trace]), [])
        self.assertTrue(CL.on_traces([20, 100, 34, 130], [trace]))
        self.assertFalse(CL.on_traces([300, 100, 314, 130], [trace]))
        self.assertEqual(len(CL.heading_blocks(img, [0, 0, 600, 300], SP, letter_height=30.0)), 1)
        self.assertEqual(CL.heading_blocks(img, [0, 0, 600, 300], SP, letter_height=200.0), [])    # the page's text is far taller: these are specks

    def test_the_lexicon_splits_a_metronome_tail_only_for_a_tempo_word_and_only_in_the_staged_scope(self):
        from tools.omr import direction_lexicon as DL
        on = DL.scope_for(None, (), tempo_marks=True)
        h = DL.lookup("Allegro con brio. d = 108.", scope=on)
        self.assertEqual((h.text, h.category, h.metronome), ("Allegro con brio.", "tempo", "d = 108."))
        self.assertIsNone(DL.lookup("Allegro con brio. d = 108.", scope=DL.scope_for(None, ())))     # flag off: refused as before
        self.assertIsNone(DL.lookup("Allegro con brio. d = 108."))                                    # LEGACY: unchanged
        self.assertIsNone(DL.lookup("dolce = 108", scope=on))                                         # not a tempo word
        self.assertIsNone(DL.lookup("Fl. 12", scope=on))


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

    def test_brackets_come_from_the_page_wide_passs_whole_marks_and_nothing_is_scanned_again(self):
        mark = dict(kind="bracket", box=[94, 90, 98, 380], staff_indices=[0, 1], hook_sp=0.9, bend_sp=0.0, width_sp=0.6, height_sp=18.0)
        log = Log()
        g = _box(log, 0, 0, BRACKET_HEAD)
        _PWS.system_structure = {0: {"columns": [], "left_edge": {"marks": [mark]}}}
        try:
            with mock.patch("tools.omr.bracket_reader.strokes_at_left_edge", side_effect=AssertionError("scanned twice")):
                rows = _gather(log, BRACKETS, [(0, BRACKET_HEAD)])
        finally:
            del _PWS.system_structure
        self.assertEqual([(r.detail["owner"], r.detail["source"], r.detail["kind"], r.detail["standing"]) for r in rows],
                         [("bracket", "left_edge_mark", "bracket", "READ")])
        self.assertGreaterEqual(rows[0].detail["boxes_inside"][g.to_key()]["ink_share_inside"], 0.5)

    def test_a_tempo_word_claims_its_metronome_note_and_the_note_is_refused_even_with_a_stem(self):
        log = Log()
        g = _box(log, 0, 0, (310, 200, 14, 18))
        log.observe(R.glyph(0, 0, 0, 0, 9000), Q.DIRECTION_WORD, "Allegro", reader=READERS.SURYA, frame="page", category="tempo",
                    bbox_page_px=list(WORD_BOX))
        dets = _dets([(0, (310, 200, 14, 18))])
        pg = _page()
        pg[196:218, 322:324] = 0                                 # the note's own stem
        pg[205:208, 340:360] = 0                                 # `=`
        _PWS.page.binary = pg
        with mock.patch.dict(os.environ, WORDS):
            G.gather_page_claims(log, _PWS(), CELLS, LOCAL, dets)
        rows = [r for r in log.rows(Q.CLAIMED_AREA, R.system(0, 0)) if r.detail.get("owner") == "word"]
        self.assertEqual(len(rows), 1)
        self.assertGreaterEqual(rows[0].value[2], 360.0)
        self.assertEqual(rows[0].detail["metronome_note"], [310.0, 200.0, 324.0, 218.0])
        self.assertGreaterEqual(rows[0].detail["boxes_inside"][g.to_key()]["ink_share_inside"], 0.5)

    def test_a_printed_instrument_name_claims_its_box_and_a_label_without_ink_claims_nothing(self):
        log = Log()
        log.observe(R.staff(0, 0, 0), Q.MARGIN_LABEL, "Fl.", reader=READERS.TEXT_LAYER, frame="margin", bbox_page_px=[20, 100, 60, 114])
        log.observe(R.staff(0, 0, 1), Q.MARGIN_LABEL, "Ob.", reader=READERS.TEXT_LAYER, frame="margin")
        rows = _gather(log, WORDS, [])
        self.assertEqual([(r.detail["source"], r.value) for r in rows if r.detail["source"] == "margin_label"], [("margin_label", [20.0, 100.0, 60.0, 114.0])])
        cen = [r for r in log.refusals(Q.CLAIMED_AREA, R.page(0)) if (r.detail or {}).get("why") == "page_claim_census"]
        self.assertEqual(cen[0].detail["census"]["word:margin_label:no_ink_found"], 1)

    def test_a_detector_brace_box_at_the_left_edge_claims_once_and_one_right_of_the_staff_start_does_not(self):
        log = Log()
        dets = {R.cell(0, 0, 0, 0).to_key(): [_Det("brace", 70 - 60, 90 - 50, 20, 290)],
                R.cell(0, 0, 1, 0).to_key(): [_Det("brace", 71 - 60, 92 - 250, 20, 288), _Det("brace", 300 - 60, 92 - 250, 20, 288)]}
        _PWS.page.binary = _page()
        with mock.patch.dict(os.environ, BRACKETS):
            G.gather_page_claims(log, _PWS(), CELLS, LOCAL, dets)
        rows = [r for r in log.rows(Q.CLAIMED_AREA, R.system(0, 0)) if r.detail.get("owner") == "bracket"]
        self.assertEqual([(r.detail["source"], r.detail["kind"]) for r in rows], [("detector_box", "brace")])

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
        mark = dict(kind="bracket", box=[94, 90, 98, 380], staff_indices=[0, 1], hook_sp=0.9, bend_sp=0.0, width_sp=0.6, height_sp=18.0)
        with mock.patch.object(_PWS, "system_structure", {0: {"columns": [], "left_edge": {"marks": [mark]}}}, create=True):
            v = _verdict(BRACKETS, 0, BRACKET_HEAD)
            self.assertEqual((v.value, v.reason), (True, "claimed_by:bracket"))
            self.assertNotEqual(_verdict(OFF, 0, BRACKET_HEAD).reason, "claimed_by:bracket")

    def test_CONTROL_the_word_flag_does_not_touch_a_bracket_box_and_the_reverse(self):
        self.assertNotEqual(_verdict(WORDS, 0, BRACKET_HEAD).reason, "claimed_by:bracket")
        self.assertNotEqual(_verdict(BRACKETS, 0, WORD_HEAD).reason, "claimed_by:word")

    def test_a_head_a_stem_stands_on_under_a_word_is_narrowed_never_refused(self):
        v = _verdict(WORDS, 0, WORD_HEAD, stem=(222 - 60, 160 - 50, 4, 60))
        self.assertEqual((v.outcome, v.reason), ("narrowed", "claim_narrowed:word"))

    def test_a_tempo_marks_metronome_note_is_refused_stem_and_all_but_an_expression_words_stemmed_head_is_narrowed(self):
        note = (310, 200, 20, 18)
        stem = (328 - 60, 198 - 50, 2, 22)
        v = _verdict(WORDS, 0, note, stem=stem, category="tempo")
        self.assertEqual((v.value, v.reason), (True, "claimed_by:word"))
        v = _verdict(WORDS, 0, note, stem=stem, category="expression")
        self.assertNotEqual(v.reason, "claimed_by:word")                     # CONTROL: no metronome claim, the rule does not fire

    def test_a_lone_dynamic_letter_claims_its_own_box_GUESSED_and_refuses_no_stemmed_head(self):
        box = (600, 200, 612, 218)
        log = Log()
        log.observe(R.glyph(0, 0, 0, 1, 5), Q.DYNAMIC_LETTER, "dynamicF", reader=READERS.DETECTOR, frame="page", letter="f", bbox_page_px=list(box))
        rows = _gather(log, WORDS, [])
        self.assertEqual([(r.detail["owner"], r.detail["source"], r.detail["text"], r.detail["standing"], r.value) for r in rows],
                         [("word", "dynamic_letters", "f", "GUESSED", [600.0, 200.0, 612.0, 218.0])])
        # a stemmed head standing on it is not refused (GUESSED refuses nothing)
        log = Log()
        _staff_space(log, SP)
        g = _box(log, 1, 0, (597, 200, 20, 18))
        log.observe(R.glyph(0, 0, 0, 1, 5), Q.DYNAMIC_LETTER, "dynamicF", reader=READERS.DETECTOR, frame="page", letter="f", bbox_page_px=list(box))
        log.observe(R.cell(0, 0, 0, 1), Q.STEM, (610 - 400, 160 - 50, 4, 60), reader=READERS.CV_INK, frame="cell:1", x0=210, x1=214, y_center=0)
        _gather(log, WORDS, [(1, (597, 200, 20, 18))])
        with mock.patch.dict(os.environ, WORDS):
            adjudicate.run(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertFalse(str(v.reason).startswith(("claimed_by:word", "claim_narrowed:word")))

    def test_CONTROL_a_lone_letter_on_an_accepted_words_ink_or_inside_the_staff_claims_nothing(self):
        log = Log()
        _word_row(log)
        log.observe(R.glyph(0, 0, 0, 0, 5), Q.DYNAMIC_LETTER, "dynamicP", reader=READERS.DETECTOR, frame="page", letter="p",
                    bbox_page_px=[210, 200, 222, 218])                               # a letter of "dolce"
        log.observe(R.glyph(0, 0, 0, 0, 6), Q.DYNAMIC_LETTER, "dynamicF", reader=READERS.DETECTOR, frame="page", letter="f",
                    bbox_page_px=[500, 110, 512, 128])                               # on the staff lines
        rows = _gather(log, WORDS, [])
        self.assertEqual([r.detail["source"] for r in rows], ["direction_word"])

    def test_CONTROL_a_lone_letter_is_not_filed_with_the_flag_off(self):
        log = Log()
        log.observe(R.glyph(0, 0, 0, 1, 5), Q.DYNAMIC_LETTER, "dynamicF", reader=READERS.DETECTOR, frame="page", letter="f",
                    bbox_page_px=[600, 200, 612, 218])
        self.assertEqual(_gather(log, OFF, []), [])

    def test_CONTROL_a_head_in_the_staff_is_never_touched(self):
        v = _verdict(dict(WORDS, OMR_CLAIM_BRACKETS_FIRST="1"), 0, FREE_HEAD)
        self.assertFalse(str(v.reason).startswith(("claimed_by:word", "claimed_by:bracket", "claim_narrowed:word", "claim_narrowed:bracket")))


if __name__ == "__main__":
    unittest.main()
