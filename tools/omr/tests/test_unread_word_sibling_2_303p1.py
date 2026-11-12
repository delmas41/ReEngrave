"""ROADMAP 2.303 PART 1 (flag `OMR_UNREAD_WORD_SIBLING`, default OFF) -- a text line the lexicon refused, a sibling staff's READ word at the same x-extent, and the letters the detector boxed inside.

CONTROLS FROM THE REAL ROWS (fixture `data_unread_word_sibling_2_303p1.json`, cut by `benchmarks/dynamics-not-words-2026-11/make_fixture_2_303p1.py` from the saved gather of Litolff p8, the
20261029-night record): Sean's 2.301 r1 tile 4 ("it boxes MP, but it's actually a part of the word sempre. So that should be a word"). The print: `sempre piu p` on staves 0-3 (a barline cuts the
word; the lexicon refused those readings) and READ on staff 8. The false `mp` is written at P2 (staff 2) bar 12 with the flag OFF; ON it is not, and the line is written as `sempre piu p`, GUESSED.
Real controls that must not change: the lone `ff` Sean judged a dynamic (2.301 r1 tile 3, Litolff p8 system 1 staff 4, an unread candidate window lies over it) and the lone `pp` of staff 8 bar 17
(an unread window of its own, two letter boxes). Each test that must fail OFF says so.
"""
from __future__ import annotations

import json
import os
import pathlib
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q

ROWS = json.loads(pathlib.Path(__file__).with_name("data_unread_word_sibling_2_303p1.json").read_text())
FLAG = "OMR_UNREAD_WORD_SIBLING"


def _log():
    log = Log()
    for r in ROWS:
        sub = R.Subject.from_key(r["subject"])
        d = dict(r.get("detail") or {})
        if r["_kind"] == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"], frame=r["frame"], score=r.get("score"), **d)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"], frame=r["frame"], reason=r["reason"], **d)
    log.freeze()
    adjudicate.run(log)
    return log


def _decided(flag):
    with mock.patch.dict(os.environ, {FLAG: flag}):
        return _log()


def _dyn(log, staff, cell, system=0, page=8):
    v = log.verdict(Q.DYNAMIC, R.cell(page, system, staff, cell))
    return None if v is None else v.value


def _dir_detail(log, staff, cell, page=8):
    v = log.verdict(Q.DIRECTION, R.cell(page, 0, staff, cell))
    return {} if v is None else (v.detail or {})


class TestUnreadWordSibling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.off = _decided("0")
        cls.on = _decided("1")

    def test_flag_default_is_off(self):
        from tools.omr.staged.adjudicators import text as T
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG, None)
            self.assertFalse(T.unread_word_sibling_enabled())

    def test_p2_bar12_the_false_mp_is_written_OFF_and_not_ON(self):
        off = _dyn(self.off, 2, 11)
        self.assertTrue(off and "mp" in " ".join(map(str, off)), "CONTROL: main writes the `mp` of sempre as a dynamic here (%r); the test would pass vacuously otherwise" % (off,))   # FAILS OFF
        on = _dyn(self.on, 2, 11)
        self.assertFalse(on and "mp" in " ".join(map(str, on)), on)

    def test_p2_bar12_the_line_is_its_siblings_word_guessed(self):
        self.assertFalse(_dir_detail(self.off, 2, 11).get("guessed_words"))
        g = _dir_detail(self.on, 2, 11).get("guessed_words")
        self.assertTrue(g and g[0]["text"] == "sempre più", g)
        self.assertEqual(g[0]["witness"]["staff"], R.cell(8, 0, 8, 12).at(R.Kind.STAFF).to_key())      # staff 8's READ word, another ink
        self.assertEqual(g[0]["guess_candidates"], [{"value": "sempre più", "support": None}])

    def test_fault2_p2_bar12_no_stray_dyn_and_no_pp(self):
        # round 2, fault 2: with the lexicon-refused line witnessed, every letter but the sibling's dynamic token is the word's. the round-1 ON arm left a blue `dyn.` (the twin box of the first `m`, one
        # printed letter judged by the wrong box: now one group) and a `pp` (the `p` and `i-u` of `piu`, boxed as two letters 0.9 spaces apart); the real final `p` (bar 14) stays its own dynamic.
        off11, on11 = _dyn(self.off, 2, 11), _dyn(self.on, 2, 11)
        self.assertEqual(off11, ["mp"], "CONTROL: OFF writes the false mp over sempre")
        self.assertEqual(on11, [])
        self.assertIsNone(_dyn(self.off, 2, 12), "CONTROL: OFF leaves the letters of piu an unspellable run (written `dyn.`), not an empty bar")
        self.assertEqual(_dyn(self.on, 2, 12), [])
        self.assertEqual(_dyn(self.on, 2, 13), ["p"])

    def test_fault1_brahms_p0_staff10_the_f_keeps_its_ink_and_one_word_is_guessed(self):
        # round 2, fault 1: OFF writes `ff` (the f of `f espr. e legato` plus the m, p of `espr.` spelled `fmp`, a guess); the neighbouring staves read `espr. e legato` and `f espr. e legato`
        # (one marking: the leading f is a dynamic token). ON: the f is its own dynamic, the rest is the word, written `espr. e legato` blue.
        self.assertEqual(_dyn(self.off, 10, 0, page=0), ["ff"])
        self.assertEqual(_dyn(self.on, 10, 0, page=0), ["f"])
        g = _dir_detail(self.on, 10, 0, page=0).get("guessed_words")
        self.assertTrue(g and g[0]["text"] == "espr. e legato", g)
        self.assertFalse(_dir_detail(self.on, 10, 0, page=0).get("unread_lines"))

    def test_the_word_is_written_without_its_dynamic_token(self):
        # CONVENTION (DECISIONS 2026-10-08: the dynamic stays the dynamic reader's, the word is read separately, `Q.MARKING` joins them): the sibling's `sempre piu p` is written `sempre piu`
        g = _dir_detail(self.on, 3, 11).get("guessed_words")
        self.assertTrue(g and "p" not in g[0]["text"].split(), g)

    def test_p3_bar12_same(self):
        self.assertTrue(_dir_detail(self.on, 3, 11).get("guessed_words"))

    def test_the_read_staff_is_untouched(self):
        # staff 8 holds the READ word: nothing guessed or marked there, its dynamics identical
        self.assertFalse(_dir_detail(self.on, 8, 12).get("guessed_words"))
        self.assertFalse(_dir_detail(self.on, 8, 12).get("unread_lines"))
        for cell in (12, 13, 14):
            self.assertEqual(_dyn(self.off, 8, cell), _dyn(self.on, 8, cell), cell)

    def test_CONTROL_the_lone_ff_Sean_judged_stays_a_dynamic(self):
        # Litolff p8 system 1 staff 4 bar 12 (2.301 r1 tile 3, "a double f (ff) dynamic"): an unread candidate window lies over it
        off, on = _dyn(self.off, 4, 12, system=1), _dyn(self.on, 4, 12, system=1)
        self.assertTrue(off and "ff" in off, "CONTROL: the real ff is written OFF (%r)" % (off,))
        self.assertEqual(off, on)

    def test_CONTROL_the_lone_pp_of_staff_8_stays_a_dynamic(self):
        # staff 8 bar 17: a `pp` in a 60 px unread window of its own (two letter boxes): a lone dynamic, never an unread text line
        off, on = _dyn(self.off, 8, 16), _dyn(self.on, 8, 16)
        self.assertTrue(off, off)
        self.assertEqual(off, on)
        self.assertFalse(_dir_detail(self.on, 8, 16).get("unread_lines"))

    def test_without_a_sibling_the_line_is_unread_and_marked_never_guessed(self):
        # take staff 8's READ word away: no sibling reads the marking, so the lines stay UNREAD (marked) and no word is invented, no mp written
        rows = [r for r in ROWS if not (r["quantity"] == "direction_word" and r["_kind"] == "obs" and r["subject"].startswith("glyph/8/0/8/"))]
        with mock.patch.dict(os.environ, {FLAG: "1"}):
            log = Log()
            for r in rows:
                sub = R.Subject.from_key(r["subject"])
                d = dict(r.get("detail") or {})
                if r["_kind"] == "obs":
                    log.observe(sub, r["quantity"], r["value"], reader=r["reader"], frame=r["frame"], score=r.get("score"), **d)
                else:
                    log.abstain(sub, r["quantity"], reader=r["reader"], frame=r["frame"], reason=r["reason"], **d)
            log.freeze()
            adjudicate.run(log)
        det = _dir_detail(log, 2, 11)
        self.assertFalse(det.get("guessed_words"))
        self.assertTrue(det.get("unread_lines"), det)
        v = _dyn(log, 2, 11)
        self.assertFalse(v and "mp" in " ".join(map(str, v)), v)


class TestExportOfTheTwoMarks(unittest.TestCase):
    def test_guessed_word_is_blue_with_its_candidates_and_never_plain(self):
        from tools.omr.staged import export as SX
        payload = json.dumps({"text": "sempre più p", "guess": {"rule": "unread_word_sibling", "candidates": [{"value": "sempre più p", "support": None}]}})
        xml = SX._direction_xml("words_guess", payload, "  ")
        self.assertIn('<words color="#1F6FEB">sempre più p</words>', xml)
        self.assertIn("reengrave:guessed", xml)
        self.assertNotIn("<words>", xml)

    def test_unread_line_is_red(self):
        from tools.omr.staged import export as SX
        self.assertIn('<words color="#D00000">unread text</words>', SX._direction_xml("words_unread", SX.UNREAD_TEXT_LINE_WORD, "  "))


if __name__ == "__main__":
    unittest.main()
