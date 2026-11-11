"""ROADMAP 2.301 -- a dynamic holds its own ink only, a word holds its own letters. CONTROLS FROM THE REAL PIXELS AND ROWS of Sean's 2.296 r1 tiles (fixture
`data_dynamic_own_ink_2_301.npz`, cut by `benchmarks/dynamics-not-words-2026-11/make_fixture_2_301.py` from the saved gathers and the master cell map): each case is a crop
of the page's raster at its real page position plus the real direction-word row, the real detector dynamic letters and the real detector boxes of the crop.

* tiles 2 and 4 (Brahms p14 `p dim.`, `piu p`): the detector boxed ONE `p` as both a `dynamicP` and a `dynamicF`; the dynamic's claim named its letter `fp` (the twins' letters
  joined) while its own marking says `p`. The claim row now carries the token its slot spells. FAILS on main.
* tile 8 (Brahms p0 `f legato`): the detector boxed the `g` of `legato` as a `dynamicF`; the stroke owner gives a page-wide word claim only strokes WHOLLY inside it (+1 px) and the
  `g`'s stroke box (1750.1, 2529.3, 1794.1, 2585.5) lies 0.5 px past the word's box +1, so the `g` was settled as a dynamic. With `OMR_WORD_OWNS_ITS_INK` a word claim holds it. FAILS OFF.
* tile 7 (Brahms p14 `p dim`): the CONTROL that a naive slack would fail: a flat's stem (detector `accidentalFlat`) stands against the word and its stroke box
  (4861.1, 3547, 4864.4, 3591.6) lies 2.6 px past the word's box; a padded word box took it. It must stay the flat's.
* tile 3 (Litolff p8 `sempre piu p`): the word's claim of `piu` and the claim of `sempre` are two pieces of ONE marking; no claim reaches past the marking's own box.
"""
from __future__ import annotations

import json
import os
import pathlib
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import claims as CL
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests.test_staged_duration import _staff_space

DATA = pathlib.Path(__file__).with_name("data_dynamic_own_ink_2_301.npz")
_NZ = np.load(DATA, allow_pickle=False)
META = json.loads(str(_NZ["meta"]))
BASE = {"OMR_CLAIMED_REGISTER": "1", "OMR_CLAIM_WORDS_FIRST": "1", "OMR_CLAIM_BRACKETS_FIRST": "0", "OMR_PAGE_LEDGER_OWNS": "1", "OMR_DYNAMIC_OWN_CLAIM": "1"}
ON = dict(BASE, OMR_WORD_OWNS_ITS_INK="1")
OFF = dict(BASE, OMR_WORD_OWNS_ITS_INK="0")
PAD = 400                                    # white margin above and below the crop, where the two synthetic staves stand


class _Det:
    def __init__(self, name, x, y, w, h):
        self.smufl_name, self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical = name, x, y, w, h
        self.confidence, self.category = 0.9, ""


class _Cell:
    def __init__(self, staff, k, bbox):
        self.staff_index, self.measure_index, self.page_index, self.bbox_page_px, self.upscale_factor = staff, k, 0, bbox, 1.0


class _Staff:
    def __init__(self, i, lines, sp):
        self.staff_index, self.system_index, self.line_ys = i, 0, lines
        self.top_y, self.bottom_y, self.line_spacing_px, self.x_start = int(lines[0]), int(lines[-1]), sp, 0


def _case(name):
    """The case's page canvas (crop at (0, PAD), everything else white) and its rows, all in the canvas's coordinates."""
    m = META[name]
    x0, y0, x1, y1 = m["crop"]
    sp = float(m["spacing"])
    ink = np.unpackbits(_NZ[name + "__ink"], axis=1)[:, :x1 - x0].astype(bool)
    h, w = ink.shape
    img = np.full((h + 2 * PAD, w), 255, np.uint8)
    img[PAD:PAD + h][ink] = 0
    sh = lambda b: [float(b[0]) - x0, float(b[1]) - y0 + PAD, float(b[2]) - x0, float(b[3]) - y0 + PAD]
    top = [20.0 + sp * i for i in range(5)]
    bot = [PAD + h + 40.0 + sp * i for i in range(5)]
    pws = type("PWS", (), {})()
    pws.page = type("P", (), {"page_index": 0, "binary": img})()
    pws.staves = [_Staff(0, top, sp), _Staff(1, bot, sp)]
    cells = [_Cell(0, 0, (0, 0, w, PAD + h // 2)), _Cell(1, 0, (0, PAD + h // 2, w, h + 2 * PAD))]
    log = Log()
    _staff_space(log, sp)
    dets, gi_of = [], {}
    for d in m["dets"]:
        b = sh(d["box"])
        gi_of[d["key"]] = len(dets)
        dets.append(_Det(d["cls"], b[0], b[1], b[2] - b[0], b[3] - b[1]))
    keys = []
    for lt in m["letters"]:
        gi = gi_of.get(lt["key"])
        if gi is None:
            gi = len(dets)
            b = sh(lt["box"])
            dets.append(_Det("dynamic" + lt["letter"].upper(), b[0], b[1], b[2] - b[0], b[3] - b[1]))
        g = R.glyph(0, 0, 0, 0, gi)
        log.observe(g, Q.DYNAMIC_LETTER, "dynamic" + lt["letter"].upper(), reader=READERS.DETECTOR, frame="cell:0", letter=lt["letter"],
                    bbox_page_px=sh(lt["box"]), staff_spacing_px=sp)
        keys.append(g.to_key())
    wd = m["word"]
    log.observe(R.glyph(0, 0, 0, 0, 90000), Q.DIRECTION_WORD, wd["text"], reader=READERS.SURYA, frame="page", category=wd.get("category") or "expression",
                bbox_page_px=sh(wd["box"]), dynamics=wd.get("dynamics") or [], includes_dynamic_glyphs=keys)
    return log, pws, cells, {R.cell(0, 0, 0, 0).to_key(): dets}, sh, sp


def _claims(name, env):
    log, pws, cells, det, sh, sp = _case(name)
    local = {0: (0, 0), 1: (0, 1)}
    with mock.patch.dict(os.environ, env):
        G.gather_page_claims(log, pws, cells, local, det)
    rows = [r for r in log.rows(Q.CLAIMED_AREA, R.system(0, 0)) if r.detail.get("owner") == "word" and r.detail.get("unit") == "area"]
    return rows, sh


def _wholly_inside(stroke, rect):
    return rect[0] - 1 <= stroke[0] and stroke[2] <= rect[2] + 1 and rect[1] - 1 <= stroke[1] and stroke[3] <= rect[3] + 1


class TestDynamicLabelIsItsOwnSlot(unittest.TestCase):
    def test_tiles_2_and_4_the_dynamic_of_a_twin_boxed_p_is_called_p_never_fp(self):
        for name, token in (("t2_brahms_p14_p_dim", "p"), ("t4_brahms_p14_piu_p", "p")):
            rows, _sh = _claims(name, ON)
            dyn = [r for r in rows if r.detail.get("source") == "dynamic_letters" and r.detail.get("compound_of")]
            self.assertEqual(len(dyn), 1, name)
            self.assertEqual(dyn[0].detail.get("dynamic_token"), token, name)
            self.assertEqual(dyn[0].detail.get("detector_letter"), token, name)          # FAILS on main: 'fp'
            self.assertIn("f", dyn[0].detail.get("detector_letters"), name)              # the detector's own twin letters stay on the row, honestly
            self.assertIsNone(dyn[0].detail.get("text"), name)

    def test_CONTROL_the_twins_really_are_boxed_as_both_letters(self):
        # the fault needs the twin: one slot holding a dynamicP and a dynamicF
        for name in ("t2_brahms_p14_p_dim", "t4_brahms_p14_piu_p"):
            m = META[name]
            got = CL.compound_dynamic_slots(m["word"]["text"], m["word"]["dynamics"], [(lt["box"], lt["letter"], lt["key"]) for lt in m["letters"]])
            self.assertIsNone(got["why"], name)
            self.assertTrue(any(set(s["letters"]) >= {"p", "f"} for s in got["slots"]), name)


class TestWordOwnsItsLetters(unittest.TestCase):
    G_STROKE = (1750.1, 2529.3, 1794.1, 2585.5)        # the stroke map's page box of the `g` of `legato` (Brahms p0, the record's stroke 375046)

    def _g(self, env):
        rows, sh = _claims("t8_brahms_p0_f_legato", env)
        s = sh(self.G_STROKE)
        return [r for r in rows if r.detail.get("source") == "direction_word" and _wholly_inside(s, r.value)]

    def test_tile_8_ON_a_word_claim_holds_the_g_of_legato_whole(self):
        self.assertTrue(self._g(ON))

    def test_CONTROL_OFF_nothing_holds_it_so_the_dynamic_box_on_the_g_settles_it(self):
        self.assertFalse(self._g(OFF))                                         # main's behaviour: the g is not wholly inside any word claim

    def test_tile_8_the_dynamic_still_owns_only_its_f(self):
        rows, sh = _claims("t8_brahms_p0_f_legato", ON)
        dyn = [r for r in rows if r.detail.get("source") == "dynamic_letters" and r.detail.get("compound_of")]
        self.assertEqual(len(dyn), 1)
        self.assertLess(dyn[0].value[2], sh([1700, 0, 1700, 0])[0])            # it ends before the `l` of legato
        self.assertFalse(_wholly_inside(sh(self.G_STROKE), dyn[0].value))

    def test_tile_7_CONTROL_a_flat_stem_against_the_word_stays_the_flats(self):
        stem = (4861.1, 3547.0, 4864.4, 3591.6)           # cell 13's vertical stroke 375045: the detector's accidentalFlat stands on it
        for env in (ON, OFF):
            rows, sh = _claims("t7_brahms_p14_p_dim_flat", env)
            s = sh(stem)
            self.assertFalse([r for r in rows if _wholly_inside(s, r.value)], env.get("OMR_WORD_OWNS_ITS_INK"))

    def test_tile_7_CONTROL_a_blind_pad_takes_the_stem(self):
        # the control that can fail: the rule without its avoid list pads the word's box 3 px and the flat's stem falls inside it
        rows, sh = _claims("t7_brahms_p14_p_dim_flat", OFF)
        word = [r for r in rows if r.detail.get("source") == "direction_word"]
        self.assertTrue(word)
        padded = [word[0].value[0] - 3.0, word[0].value[1] - 3.0, word[0].value[2] + 3.0, word[0].value[3] + 3.0]
        self.assertTrue(_wholly_inside(sh((4861.1, 3547.0, 4864.4, 3591.6)), padded))

    def test_tile_3_the_word_of_sempre_piu_p_holds_only_its_own_box(self):
        for env in (ON, OFF):
            rows, sh = _claims("t3_litolff_p8_sempre_piu_p", env)
            word = [r for r in rows if r.detail.get("source") == "direction_word"]
            box = sh(META["t3_litolff_p8_sempre_piu_p"]["word"]["box"])
            self.assertGreaterEqual(len(word), 2)                                  # `sempre` and `piu` are two pieces of ONE marking (the tile boxed one of them)
            self.assertEqual({r.detail.get("owner_row") for r in word}, {word[0].detail.get("owner_row")})
            for r in word:
                self.assertGreaterEqual(r.value[0], box[0] - 3.0)
                self.assertLessEqual(r.value[2], box[2] + 3.0)
                # the accent of `più` (the dot of the i, the grave of the u) stands above the OCR box: the word's own ink, at most half a space past it (+ slack)
                self.assertGreaterEqual(r.value[1], box[1] - 0.7 * 15.75)
                self.assertLessEqual(r.value[3], box[3] + 3.0)


class TestEdgeInkBoxesPure(unittest.TestCase):
    def test_a_letter_standing_on_the_edge_gets_its_padded_box_and_a_letter_inside_gets_none(self):
        img = np.full((200, 300), 255, np.uint8)
        img[100:140, 100:112] = 0                    # a letter ending exactly on the box's bottom edge
        img[100:120, 150:160] = 0                    # a letter well inside
        got = CL.edge_ink_boxes(img, [90.0, 90.0, 200.0, 140.0], 32.0, [])
        self.assertEqual(len(got), 1)
        self.assertGreater(got[0][3], 140.0)
        self.assertEqual(got[0][1], 100.0 - 0.1 * 32.0)

    def test_CONTROL_ink_another_mark_holds_is_never_taken(self):
        img = np.full((200, 300), 255, np.uint8)
        img[100:140, 100:112] = 0
        self.assertEqual(CL.edge_ink_boxes(img, [90.0, 90.0, 200.0, 140.0], 32.0, [[95.0, 95.0, 120.0, 130.0]]), [])

    def test_CONTROL_a_staff_line_under_the_box_is_not_a_letter(self):
        img = np.full((200, 300), 255, np.uint8)
        img[139:142, 0:300] = 0
        self.assertEqual(CL.edge_ink_boxes(img, [90.0, 90.0, 200.0, 140.0], 32.0, []), [])

    def test_the_flag_is_off_unless_asked(self):
        with mock.patch.dict(os.environ, {"OMR_CLAIMED_REGISTER": "1", "OMR_CLAIM_WORDS_FIRST": "1", "OMR_PAGE_LEDGER_OWNS": "1"}):
            os.environ.pop("OMR_WORD_OWNS_ITS_INK", None)
            self.assertFalse(CL.word_ink_enabled())
            os.environ["OMR_WORD_OWNS_ITS_INK"] = "1"
            self.assertTrue(CL.word_ink_enabled())


if __name__ == "__main__":
    unittest.main()
