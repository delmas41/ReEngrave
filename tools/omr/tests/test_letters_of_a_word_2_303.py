"""ROADMAP 2.303 -- letters printed inside a READ word are the word's, never a dynamic (flag `OMR_LETTERS_ARE_THE_WORD`, default OFF). CONTROLS FROM THE REAL PIXELS AND ROWS (fixture
`data_letters_of_a_word_2_303.npz`, cut by `benchmarks/dynamics-not-words-2026-11/make_fixture_2_303.py` from real page gathers): each case is a crop of the page's raster at its real page
position plus the real direction-word row, the real detector dynamic letters with the neighbour ink the CV reader measured beside each, and the real detector boxes of the crop.

* Litolff p8 `sempre piu p` and `sempre A` (Sean 2026-11-11, 2.301 r1 tile 4: "it boxes MP, but it's actually a part of the word sempre"): the detector's `m`+`p` / `p`+`p` of `sempre` were
  spelled `pp` / `ppp` and filed as READ dynamics over the word's own ink. FAIL with the flag OFF, pass ON.
* Brahms p14 `dolce sempre` (`mp`), Brahms p0 `f espr. e legato` (`fz` / `fp` over the letters of `legato`): same fault, other plate.
* The controls that must NOT change: the real final `p` of `sempre piu p` (its own dynamic claim, from the 2.296 split); the real `f` of `f espr. e legato`; the `PiU p` run that holds the real
  `p` of the marking (a run standing on a dynamic token's stretch is a dynamic or cannot be told).
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
from tools.omr.tests.test_dynamic_own_ink_2_301 import PAD, _Cell, _Det, _Staff
from tools.omr.tests.test_staged_duration import _staff_space

DATA = pathlib.Path(__file__).with_name("data_letters_of_a_word_2_303.npz")
_NZ = np.load(DATA, allow_pickle=False)
META = json.loads(str(_NZ["meta"]))
BASE = {"OMR_CLAIMED_REGISTER": "1", "OMR_CLAIM_WORDS_FIRST": "1", "OMR_CLAIM_BRACKETS_FIRST": "0", "OMR_PAGE_LEDGER_OWNS": "1", "OMR_DYNAMIC_OWN_CLAIM": "1", "OMR_WORD_OWNS_ITS_INK": "1"}
ON = dict(BASE, OMR_LETTERS_ARE_THE_WORD="1")
OFF = dict(BASE, OMR_LETTERS_ARE_THE_WORD="0")


def _case(name):
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
    dets, gi_of, key_of = [], {}, {}
    for d in m["dets"]:
        b = sh(d["box"])
        gi_of[d["key"]] = len(dets)
        dets.append(_Det(d["cls"], b[0], b[1], b[2] - b[0], b[3] - b[1]))
    for lt in m["letters"]:
        gi = gi_of.get(lt["key"])
        if gi is None:
            gi = len(dets)
            b = sh(lt["box"])
            dets.append(_Det("dynamic" + lt["letter"].upper(), b[0], b[1], b[2] - b[0], b[3] - b[1]))
        g = R.glyph(0, 0, 0, 0, gi)
        key_of[lt["key"]] = g.to_key()
        log.observe(g, Q.DYNAMIC_LETTER, "dynamic" + lt["letter"].upper(), reader=READERS.DETECTOR, frame="cell:0", letter=lt["letter"], bbox_page_px=sh(lt["box"]), staff_spacing_px=sp)
        log.observe(g, Q.DYNAMIC_LETTER_NEIGHBOURS, {"left": lt["left"], "right": lt["right"], "left_spaces": lt["left_spaces"], "right_spaces": lt["right_spaces"]},
                    reader=READERS.CV_LETTER_NEIGHBOURS, frame="page")
    for k, wd in enumerate(m["words"]):
        log.observe(R.glyph(0, 0, 0, 0, 90000 + k), Q.DIRECTION_WORD, wd["text"], reader=READERS.SURYA, frame="page", category=wd.get("category") or "expression", bbox_page_px=sh(wd["box"]),
                    dynamics=wd.get("dynamics") or [], includes_dynamic_glyphs=[key_of[x] for x in wd["includes"] if x in key_of])
    return log, pws, cells, {R.cell(0, 0, 0, 0).to_key(): dets}, sh


def _dyn(name, env):
    """The page-wide DYNAMIC claims (source `dynamic_letters`) of the case, as (text or letter, box in page px) -- and the split ones apart."""
    log, pws, cells, det, sh = _case(name)
    with mock.patch.dict(os.environ, env):
        G.gather_page_claims(log, pws, cells, {0: (0, 0), 1: (0, 1)}, det)
    x0, y0 = META[name]["crop"][:2]
    out = []
    for r in log.rows(Q.CLAIMED_AREA, R.system(0, 0)):
        d = r.detail
        if d.get("owner") == "word" and d.get("unit") == "area" and d.get("source") == "dynamic_letters":
            b = r.value
            out.append(dict(text=d.get("text") or d.get("detector_letter"), compound=bool(d.get("compound_of")), box=[b[0] + x0, b[1] + y0 - PAD, b[2] + x0, b[3] + y0 - PAD]))
    return out


def _centre_in(box, word):
    cx = (box[0] + box[2]) / 2.0
    return word[0] <= cx <= word[2]


def _word_dynamics(name, env):
    """The dynamic claims NOT split from the marking (`compound_of`) whose centre lies inside the READ word's box."""
    wb = META[name]["word_box"]
    return [c for c in _dyn(name, env) if not c["compound"] and _centre_in(c["box"], wb)]


class TestLettersOfTheWordRealCases(unittest.TestCase):
    def test_litolff_p8_sempre_piu_p_the_pp_of_sempre_is_the_words(self):
        off = _word_dynamics("l8_sempre_piu_p", OFF)
        self.assertTrue(off, "CONTROL: main files a dynamic over the letters of `sempre piu`; the test would pass vacuously otherwise")      # FAILS OFF
        self.assertEqual(_word_dynamics("l8_sempre_piu_p", ON), [])

    def test_litolff_p8_sempre_A_the_pp_and_ppp_are_the_words(self):
        off = _word_dynamics("l8_sempre_A", OFF)
        self.assertTrue(off, "CONTROL")
        self.assertEqual(_word_dynamics("l8_sempre_A", ON), [])

    def test_brahms_p14_dolce_sempre_the_mp_is_the_words(self):
        self.assertTrue(_word_dynamics("b14_dolce_sempre", OFF), "CONTROL")
        self.assertEqual(_word_dynamics("b14_dolce_sempre", ON), [])

    def test_brahms_p0_legato_fz_and_fp_are_letters_of_legato(self):
        off = [c for c in _dyn("b0_f_espr_e_legato", OFF) if not c["compound"] and c["box"][0] > META["b0_f_espr_e_legato"]["word_box"][0] + 100]
        self.assertTrue(off, "CONTROL")
        on = [c for c in _dyn("b0_f_espr_e_legato", ON) if not c["compound"] and c["box"][0] > META["b0_f_espr_e_legato"]["word_box"][0] + 100]
        self.assertEqual(on, [])

    def test_where_the_word_was_refused_nothing_changes(self):
        # Sean's 2.301 r1 tile 4 itself (Litolff p8, the `mp` of `sempre` at 1547.8-1587.3 x 788.4-839.1): the OCR candidate there was REFUSED by the lexicon, so no READ word holds
        # the letters and the rule must change nothing (a refusal never becomes an answer, CLAUDE rule 8). The dynamic claim stays, ON and OFF alike.
        off, on = _dyn("l8_sempre_unread", OFF), _dyn("l8_sempre_unread", ON)
        self.assertTrue(any(c["text"] == "mp" and abs(c["box"][0] - 1547.8) < 3 for c in off))
        self.assertEqual(sorted((c["text"], round(c["box"][0]), round(c["box"][1])) for c in off), sorted((c["text"], round(c["box"][0]), round(c["box"][1])) for c in on))

    def test_the_real_dynamics_are_never_taken(self):
        # the final `p` of `sempre piu p` (its own claim from the 2.296 split) and the real `f` of `f espr. e legato`: the same claims OFF and ON
        for name in ("l8_sempre_piu_p", "b0_f_espr_e_legato"):
            wb = META[name]["word_box"]
            dyn_off = [c for c in _dyn(name, OFF) if c["compound"]]
            dyn_on = [c for c in _dyn(name, ON) if c["compound"]]
            self.assertTrue(dyn_off, name)
            self.assertEqual(sorted(round(v) for c in dyn_off for v in c["box"]), sorted(round(v) for c in dyn_on for v in c["box"]), name)
        # `PiU p`: the run holds the real final p (it stands on the trailing dynamic token's stretch): unchanged
        self.assertEqual(sorted((round(c["box"][0]), round(c["box"][2])) for c in _dyn("b14_piu_p", OFF)),
                         sorted((round(c["box"][0]), round(c["box"][2])) for c in _dyn("b14_piu_p", ON)))

    def test_the_flag_is_off_by_default(self):
        with mock.patch.dict(os.environ, BASE, clear=False):
            os.environ.pop("OMR_LETTERS_ARE_THE_WORD", None)
            self.assertFalse(CL.letters_are_the_word_enabled())
        with mock.patch.dict(os.environ, ON):
            self.assertTrue(CL.letters_are_the_word_enabled())


class TestLettersOfTheWordPure(unittest.TestCase):
    WORD = [100.0, 0.0, 340.0, 40.0]            # `sempre piu p`: 12 characters, 20 px each; the dynamic `p` stands at 320-340

    def test_letters_of_sempre_are_the_words_with_ink_beside_them(self):
        self.assertEqual(CL.letters_of_the_word([[160.0, 5.0, 200.0, 35.0]], self.WORD, "sempre piu p", True), "letters_of_a_word")

    def test_CONTROL_no_ink_beside_them_cannot_tell(self):
        self.assertIsNone(CL.letters_of_the_word([[160.0, 5.0, 200.0, 35.0]], self.WORD, "sempre piu p", False))

    def test_CONTROL_the_trailing_dynamic_token_stays_a_dynamic(self):
        self.assertIsNone(CL.letters_of_the_word([[318.0, 5.0, 340.0, 35.0]], self.WORD, "sempre piu p", True))
        self.assertIsNone(CL.letters_of_the_word([[300.0, 5.0, 340.0, 35.0]], self.WORD, "sempre piu p", True))      # a run reaching into its stretch: cannot tell

    def test_CONTROL_the_leading_dynamic_token_stays_a_dynamic(self):
        self.assertIsNone(CL.letters_of_the_word([[100.0, 5.0, 122.0, 35.0]], [100.0, 0.0, 340.0, 40.0], "p dolce sempre", True))

    def test_CONTROL_a_text_that_is_only_a_dynamic_is_no_word(self):
        self.assertIsNone(CL.letters_of_the_word([[160.0, 5.0, 200.0, 35.0]], self.WORD, "pp", True))

    def test_CONTROL_letters_outside_the_word_box_are_not_its_letters(self):
        self.assertIsNone(CL.letters_of_the_word([[400.0, 5.0, 440.0, 35.0]], self.WORD, "sempre piu p", True))


if __name__ == "__main__":
    unittest.main()
