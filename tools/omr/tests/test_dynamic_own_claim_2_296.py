"""ROADMAP 2.296 -- a printed dynamic is claimed as a DYNAMIC, never as the first letters of the word printed beside it (flag `OMR_DYNAMIC_OWN_CLAIM`,
default OFF). `claims.compound_dynamic_slots` (pure) and `gather.gather_page_claims` (the word's claim stops at the dynamic's ink, the dynamic claims
its own, READ).

The boxes in the pure tests are the REAL rows of Brahms p0 / p14 and Litolff p8 (the cases Sean's page pass and tiles name): 'f legato' (the f is Sean's
dynamic; the detector also boxed the `l` of `legato` as a `dynamicP`, which spelled a false `fp`), 'p dolce' (one ink boxed as both `dynamicF` and
`dynamicP`), 'piu p' (the `p` of `piu` is the word's), 'sempre piu p'. Every CONTROL here fails with the rule absent."""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import claims as CL
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests.test_staged_page_claims_2_221 import CELLS, L0, LOCAL, SP, _Det, _PWS, _page, _staff_space

ON = {"OMR_CLAIMED_REGISTER": "1", "OMR_CLAIM_WORDS_FIRST": "1", "OMR_CLAIM_BRACKETS_FIRST": "0", "OMR_PAGE_LEDGER_OWNS": "1",
      "OMR_DYNAMIC_OWN_CLAIM": "1"}
OFF = dict(ON, OMR_DYNAMIC_OWN_CLAIM="0")


class TestFlag(unittest.TestCase):
    def test_default_off_and_needs_the_words_pass(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMR_DYNAMIC_OWN_CLAIM", None)
            self.assertFalse(CL.dynamic_own_enabled())
        with mock.patch.dict(os.environ, {"OMR_DYNAMIC_OWN_CLAIM": "1", "OMR_CLAIMED_REGISTER": "1", "OMR_CLAIM_WORDS_FIRST": "1"}):
            self.assertTrue(CL.dynamic_own_enabled())
        with mock.patch.dict(os.environ, {"OMR_DYNAMIC_OWN_CLAIM": "1", "OMR_CLAIM_WORDS_FIRST": "0"}):
            self.assertFalse(CL.dynamic_own_enabled())


class TestCompoundSlots(unittest.TestCase):
    """Real rows. `letters` = `(page box, letter, row id)` the word row `includes_dynamic_glyphs`."""

    def test_f_legato_brahms_p0_the_f_is_the_dynamic_and_the_l_boxed_as_p_is_the_words(self):
        # Brahms p0 obs:028457 'F legato' (word box x 1699..1903): the f at 1625..1689 is Sean's dynamic; the `dynamicP` at 1699..1726 sits on the `l`
        got = CL.compound_dynamic_slots("F legato", ["f"], [((1625, 2932, 1689, 2998), "f", "a"), ((1699, 2941, 1726, 2998), "p", "b")])
        self.assertIsNone(got["why"])
        self.assertEqual([(s["letters"], s["rows"]) for s in got["slots"]], [(["f"], ["a"])])
        self.assertEqual(got["rows"], ["a", "b"])           # both are the marking's, so neither is spelled `fp` by the lone-letter loop

    def test_CONTROL_the_old_spelling_joins_the_two_into_a_false_fp(self):
        runs = CL.spell_letter_runs([((1625, 2932, 1689, 2998), "f", "a"), ((1699, 2941, 1726, 2998), "p", "b")], 32.0, {"f", "p", "fp"})
        self.assertEqual([(r["text"], r["read"]) for r in runs], [("fp", True)])

    def test_p_dolce_brahms_p14_one_ink_boxed_as_f_and_as_p_is_the_p(self):
        got = CL.compound_dynamic_slots("p dolce", ["p"], [((1207, 4605, 1254, 4658), "f", "a"), ((1207, 4605, 1255, 4658), "p", "b"),
                                                          ((1219, 4605, 1267, 4641), "p", "c")])
        self.assertIsNone(got["why"])
        self.assertEqual([(s["letters"], sorted(s["rows"])) for s in got["slots"]][0][0], ["f", "p"])

    def test_piu_p_the_p_of_piu_is_the_words_and_the_rightmost_slot_is_the_dynamic(self):
        got = CL.compound_dynamic_slots("piu p", ["p"], [((5251, 6144, 5302, 6192), "p", "a"), ((5335, 6144, 5356, 6178), "m", "b"),
                                                       ((5383, 6148, 5440, 6197), "p", "c"), ((5383, 6147, 5436, 6197), "f", "d")])
        self.assertIsNone(got["why"])
        self.assertEqual([s["box"][0] for s in got["slots"]], [5383.0])
        self.assertEqual(sorted(got["slots"][0]["rows"]), ["c", "d"])

    def test_p_cresc_f_a_dynamic_at_each_end(self):
        got = CL.compound_dynamic_slots("p cresc. f", ["p", "f"], [((622, 1374, 671, 1402), "p", "a"), ((776, 1364, 824, 1402), "f", "b")])
        self.assertIsNone(got["why"])
        self.assertEqual([s["text"] for s in got["slots"]], ["p", "f"])

    def test_ff_is_two_slots_and_a_one_slot_ff_is_not_split(self):
        two = CL.compound_dynamic_slots("ff dolce", ["ff"], [((100, 10, 130, 40), "f", "a"), ((135, 10, 165, 40), "f", "b")])
        self.assertEqual([s["rows"] for s in two["slots"]], [["a"], ["b"]])
        one = CL.compound_dynamic_slots("ff dolce", ["ff"], [((100, 10, 190, 40), "f", "a")])
        self.assertEqual((one["slots"], one["why"]), ([], "fewer_letters_than_the_token"))

    def test_CONTROLS_nothing_is_split_on_a_guess(self):
        self.assertEqual(CL.compound_dynamic_slots("a p dolce", ["p"], [((1, 1, 9, 9), "p", "a")])["why"], "dynamic_token_in_the_middle")
        self.assertEqual(CL.compound_dynamic_slots("p", ["p"], [((1, 1, 9, 9), "p", "a")])["why"], "text_is_all_dynamic")
        self.assertEqual(CL.compound_dynamic_slots("f legato", ["f"], [((1, 1, 9, 9), "p", "a")])["why"], "letters_do_not_spell_the_token")
        self.assertEqual(CL.compound_dynamic_slots("f legato", ["f"], [])["why"], "fewer_letters_than_the_token")
        self.assertEqual(CL.compound_dynamic_slots("legato", [], [((1, 1, 9, 9), "f", "a")])["why"], "no_dynamic_token")


class TestGrowToInk(unittest.TestCase):
    def test_a_descender_past_the_tight_detector_box_is_the_dynamics_own_ink(self):
        # Litolff p8 `sempre piu p`: the detector's box ends at 1607, the p's stem at 1613 (6 px = 0.4 sp)
        img = np.full((200, 200), 255, np.uint8)
        img[50:60, 100:112] = 0                      # the bowl, inside the box
        img[60:66, 103:106] = 0                      # the descender, past it
        img[50:66, 140:150] = 0                      # another letter, far off: not touched
        got = CL.grow_to_ink(img, [99.0, 49.0, 113.0, 61.0], SP)
        self.assertEqual(got, [99.0, 49.0, 113.0, 66.0])

    def test_CONTROL_growth_never_runs_more_than_half_a_space_past_a_side(self):
        img = np.full((200, 200), 255, np.uint8)
        img[50:61, 100:112] = 0
        img[61:100, 103:106] = 0                     # a long stem running on down: only its first 0.5 sp is taken
        got = CL.grow_to_ink(img, [99.0, 49.0, 113.0, 61.0], SP)
        self.assertEqual(got[3], 61.0 + 0.5 * SP)


WORD = (222.0, 198.0, 330.0, 220.0)          # "f legato", between the staves; the `f` is ink 222..236, `legato` 252..330
F_LETTER = (221.0, 199.0, 237.0, 216.0)     # the detector's dynamicF on the f: TIGHT, the ink runs to y 218
P_LETTER = (252.0, 198.0, 264.0, 220.0)     # a dynamicP the detector drew on the `l` of legato


def _marking_page():
    img = np.full((520, 900), 255, np.uint8)
    for ly in L0 + [300.0 + SP * i for i in range(5)]:
        img[int(ly) - 1:int(ly) + 2, 100:880] = 0
    img[200:218, 224:236] = 0                          # the f
    for x in range(254, 330, 12):                      # legato
        img[200:218, x:x + 7] = 0
    return img


def _log_with_marking(text="f legato"):
    log = Log()
    _staff_space(log, SP)
    keys = []
    for gi, (box, letter) in enumerate(((F_LETTER, "f"), (P_LETTER, "p")), start=1):
        g = R.glyph(0, 0, 0, 0, gi)
        log.observe(g, Q.DYNAMIC_LETTER, f"dynamic{letter.upper()}", reader=READERS.DETECTOR, frame="cell:0", letter=letter,
                    bbox_page_px=list(box), staff_spacing_px=SP)
        keys.append(g.to_key())
    log.observe(R.glyph(0, 0, 0, 0, 9000), Q.DIRECTION_WORD, text, reader=READERS.SURYA, frame="page", category="expression",
                bbox_page_px=list(WORD), dynamics=["f"], includes_dynamic_glyphs=keys)
    return log


def _claims(env, log):
    _PWS.page.binary = _marking_page()
    with mock.patch.dict(os.environ, env):
        G.gather_page_claims(log, _PWS(), CELLS, LOCAL, {}, )
    return [r for r in log.rows(Q.CLAIMED_AREA, R.system(0, 0)) if r.detail.get("owner") == "word" and r.detail.get("unit") == "area"]


class TestMarkingSplitInGather(unittest.TestCase):
    def test_ON_the_word_stops_at_the_dynamic_and_the_dynamic_claims_its_own_ink(self):
        rows = _claims(ON, _log_with_marking())
        dyn = [r for r in rows if r.detail.get("category") == "dynamic"]
        wrd = [r for r in rows if r.detail.get("source") == "direction_word"]
        self.assertEqual(len(dyn), 1)
        self.assertEqual(dyn[0].detail.get("compound_of") is not None, True)
        self.assertLessEqual(dyn[0].value[2], 240.0)                     # the f only
        self.assertEqual(dyn[0].detail.get("standing"), "READ")
        self.assertTrue(wrd)
        self.assertGreaterEqual(min(r.value[0] for r in wrd), 240.0)     # the word owns none of the f's ink
        self.assertEqual(dyn[0].detail.get("detector_letter"), "f")
        self.assertGreaterEqual(dyn[0].value[3], 218.0)                  # its ink, not the detector's tight box (a stroke past the box would be nobody's)

    def test_CONTROL_OFF_the_word_covers_the_f_and_no_dynamic_claim_stands_on_it(self):
        rows = _claims(OFF, _log_with_marking())
        wrd = [r for r in rows if r.detail.get("source") == "direction_word"]
        self.assertEqual(len(wrd), 1)
        self.assertLessEqual(wrd[0].value[0], 224.0)                     # the word's area holds the f
        self.assertFalse([r for r in rows if r.detail.get("category") == "dynamic" and r.detail.get("compound_of")])

    def test_ON_the_l_boxed_as_p_is_not_spelled_into_a_dynamic(self):
        rows = _claims(ON, _log_with_marking())
        self.assertFalse([r for r in rows if r.detail.get("source") == "dynamic_letters" and r.detail.get("text") == "fp"])
        self.assertEqual([r.detail.get("detector_letter") for r in rows if r.detail.get("source") == "dynamic_letters"], ["f"])

    def test_ON_a_marking_the_split_cannot_place_stays_one_word_claim(self):
        log = _log_with_marking(text="legato f legato")          # a dynamic in the middle: no guess
        rows = _claims(ON, log)
        self.assertFalse([r for r in rows if r.detail.get("compound_of")])
        self.assertTrue([r for r in rows if r.detail.get("source") == "direction_word"])


if __name__ == "__main__":
    unittest.main()
