"""ROADMAP 2.85: repeat barlines and 1st/2nd endings, numbered the print's way.

Evidence: Breitkopf 317803 pdf p10 system 1 (`out/print/bar-drift/
brahms_p10_s1.png`) prints a 2-bar 1st ending and a 2nd ending; the print's
own bar numbers (188 -> 194) show the 2nd ending REUSES the 1st ending's
numbers (Sean, 2026-10-11). STAGED counted straight through: +2 to every
later bar.

Each reader has a positive control and a refusal case in the SAME class (a
hooked stroke that is not a bracket; a dot column that is not a repeat), so
no test passes by refusing everything. The EXPORT tests were run RED against
the unrepaired tree (origin/main 26cb57c6): the bar numbers came out
1,2,3,4,5,6 and no `<ending>`/`<repeat>` was written.
"""
from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

import numpy as np

from tools.omr import repeat_dots as RD
from tools.omr import volta_bracket as VB
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import export as SX
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS

from tools.omr.tests.test_staged_export import _one_staff_page, _vrd

SP = 20          # staff space, px
TOP = 300        # top staff line y


def _page(w=1200, h=500):
    return np.full((h, w), 255, dtype=np.uint8)


def _staff(img, x0=100, x1=1100, top=TOP):
    ys = [top + i * SP for i in range(5)]
    for y in ys:
        img[y:y + 2, x0:x1] = 0
    return ys


def _bracket(img, x0, x1, y, hook_l=2.8, hook_r=0.0, thick=6):
    img[y:y + thick, x0:x1] = 0
    if hook_l:
        img[y:y + int(hook_l * SP), x0:x0 + 4] = 0
    if hook_r:
        img[y:y + int(hook_r * SP), x1 - 4:x1] = 0


# ─────────────────────────────────────────────────────────────────────────────
# 1. The CV readers
# ─────────────────────────────────────────────────────────────────────────────


class TestFindBrackets(unittest.TestCase):

    def test_a_hooked_stroke_above_the_staff_IS_a_candidate(self):
        img = _page()
        ys = _staff(img)
        _bracket(img, 300, 700, TOP - 6 * SP, hook_l=2.8, hook_r=2.7)
        found = VB.find_brackets(img, ys, 100, 1100)
        self.assertEqual(len(found), 1)
        b = found[0]
        self.assertLessEqual(abs(b.x0 - 300), 2)
        self.assertGreaterEqual(b.left_hook, VB.MIN_HOOK_SPACES)
        self.assertGreaterEqual(b.right_hook, VB.MIN_HOOK_SPACES)

    def test_an_open_bracket_has_no_right_hook(self):
        img = _page()
        ys = _staff(img)
        _bracket(img, 300, 700, TOP - 6 * SP, hook_l=2.8, hook_r=0)
        b = VB.find_brackets(img, ys, 100, 1100)[0]
        self.assertLess(b.right_hook, VB.MIN_HOOK_SPACES)

    def test_REFUSAL_a_beam_whose_stems_run_into_the_staff(self):
        """The census's whole false-positive population: a horizontal stroke
        with verticals that reach the staff -- stems, not hooks."""
        img = _page()
        ys = _staff(img)
        y = TOP - 4 * SP
        img[y:y + 6, 300:700] = 0
        for x in (300, 696):
            img[y:TOP + 2 * SP, x:x + 4] = 0
        self.assertEqual(VB.find_brackets(img, ys, 100, 1100), [])

    def test_REFUSAL_a_flat_stroke_with_no_hook(self):
        img = _page()
        ys = _staff(img)
        _bracket(img, 300, 700, TOP - 6 * SP, hook_l=0, hook_r=0)
        self.assertEqual(VB.find_brackets(img, ys, 100, 1100), [])

    def test_REFUSAL_a_short_hooked_stroke(self):
        img = _page()
        ys = _staff(img)
        _bracket(img, 300, 300 + 4 * SP, TOP - 6 * SP, hook_l=2.8)
        self.assertEqual(VB.find_brackets(img, ys, 100, 1100), [])


def _dot(binary, x, y, r=5):
    yy, xx = np.ogrid[:binary.shape[0], :binary.shape[1]]
    binary[(yy - y) ** 2 + (xx - x) ** 2 <= r * r] = 1


class TestRepeatDots(unittest.TestCase):

    def _staff_binary(self):
        b = np.zeros((500, 1200), dtype=np.uint8)
        ys = [TOP + i * SP for i in range(5)]
        for y in ys:
            b[y:y + 2, 100:1100] = 1
        return b, ys

    def test_two_dots_left_of_a_barline_are_found(self):
        b, ys = self._staff_binary()
        _dot(b, 580, (ys[1] + ys[2]) // 2 + 1)
        _dot(b, 580, (ys[2] + ys[3]) // 2 + 1)
        self.assertIsNotNone(RD.find_pair(b, ys, 600, "left"))
        self.assertIsNone(RD.find_pair(b, ys, 600, "right"))

    def test_REFUSAL_one_dot_is_not_a_repeat(self):
        b, ys = self._staff_binary()
        _dot(b, 580, (ys[1] + ys[2]) // 2 + 1)
        self.assertIsNone(RD.find_pair(b, ys, 600, "left"))

    def test_REFUSAL_two_dots_not_one_above_the_other(self):
        b, ys = self._staff_binary()
        _dot(b, 560, (ys[1] + ys[2]) // 2 + 1)
        _dot(b, 590, (ys[2] + ys[3]) // 2 + 1)
        self.assertIsNone(RD.find_pair(b, ys, 600, "left"))


# ─────────────────────────────────────────────────────────────────────────────
# 2. ADJUDICATE
# ─────────────────────────────────────────────────────────────────────────────

SYS = R.system(0, 0)


def _cells(log, edges):
    """Staff-0 cell boxes from barline x's."""
    for i, (a, b) in enumerate(zip(edges, edges[1:])):
        log.observe(R.cell(0, 0, 0, i), Q.CELL_BOX, [float(a), 0.0, float(b),
                    100.0], reader=READERS.GEOMETRY, frame=G.frame_cell(i))


def _br(log, k, x0, x1, left=2.8, right=0.0):
    log.observe(SYS, Q.VOLTA_BRACKET,
                {"x0": x0, "x1": x1, "y": 10, "thickness": 9,
                 "left_hook": left, "right_hook": right},
                reader=READERS.CV_VOLTA, frame=G.FRAME_VOLTA, bracket=k,
                space=27.5)


def _num(log, k, text, reader=READERS.SURYA):
    log.observe(SYS, Q.VOLTA_NUMERAL, text, reader=reader,
                frame=G.FRAME_VOLTA_NUMERAL, bracket=k)


#: Brahms p10 system 1's own barlines and brackets.
EDGES = [630, 1551, 2146, 2584, 3442, 3957, 4481, 4963, 5502]


class TestEndings(unittest.TestCase):

    def _decide(self, log):
        log.freeze()
        adjudicate.run(log, order=(Q.ENDINGS,))
        return log.verdict(Q.ENDINGS, SYS)

    def _brahms(self, n1="1.", n2="2."):
        log = Log()
        _cells(log, EDGES)
        _br(log, 0, 1558, 2590, right=2.73)
        _br(log, 1, 2601, 3442, right=0.29)
        if n1 is not None:
            _num(log, 0, n1)
        if n2 is not None:
            _num(log, 1, n2)
        return log

    def test_brahms_p10_DECIDES_the_two_endings(self):
        v = self._decide(self._brahms())
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(
            [(e["number"], e["first_cell"], e["last_cell"], e["closed"])
             for e in v.value],
            [(1, 1, 2, True), (2, 3, 3, False)])

    def test_the_verdict_RECORDS_the_rows_it_used(self):
        """Both brackets, both numerals and the cell boxes at each end --
        and nothing it did not read."""
        log = self._brahms()
        v = self._decide(log)
        used = set(v.used)
        brackets = {r.id for r in log.rows(Q.VOLTA_BRACKET, SYS)}
        numerals = {r.id for r in log.rows(Q.VOLTA_NUMERAL, SYS)}
        self.assertTrue(brackets <= used)
        self.assertTrue(numerals <= used)
        self.assertEqual(v.detail["refused"], [])

    def test_REFUSAL_a_numeral_misread_as_4_never_becomes_a_1st_ending(self):
        """Tesseract's measured misread of the bold Breitkopf "1"."""
        v = self._decide(self._brahms(n1="4."))
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_first_and_second_ending")

    def test_REFUSAL_an_unread_numeral_is_not_numbered_by_position(self):
        v = self._decide(self._brahms(n1=None))
        self.assertIs(v.outcome, Outcome.ABSTAINED)

    def test_REFUSAL_two_readers_disagreeing_abstain(self):
        log = self._brahms()
        _num(log, 0, "4.", reader=READERS.TESSERACT)
        v = self._decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)

    def test_REFUSAL_a_span_not_at_barlines(self):
        log = Log()
        _cells(log, EDGES)
        _br(log, 0, 1800, 2590)
        _br(log, 1, 2601, 3442)
        _num(log, 0, "1.")
        _num(log, 1, "2.")
        v = self._decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)

    def test_REFUSAL_endings_not_adjacent(self):
        log = Log()
        _cells(log, EDGES)
        _br(log, 0, 1558, 2146)
        _br(log, 1, 2601, 3442)
        _num(log, 0, "1.")
        _num(log, 1, "2.")
        v = self._decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "endings_not_adjacent")

    def test_no_bracket_abstains(self):
        log = Log()
        _cells(log, EDGES)
        log.abstain(SYS, Q.VOLTA_BRACKET, reader=READERS.CV_VOLTA,
                    frame=G.FRAME_VOLTA, reason=ABSTAIN.NO_INK)
        v = self._decide(log)
        self.assertEqual(v.reason, "no_bracket")


class TestRepeatBarlines(unittest.TestCase):

    def _decide(self, staves_with_dots, n_staves=14, edge="end"):
        log = Log()
        log.observe(SYS, Q.SYSTEM_STAFF_COUNT, n_staves,
                    reader=READERS.GEOMETRY, frame=G.FRAME_SYSTEM)
        for st in range(staves_with_dots):
            log.observe(SYS, Q.REPEAT_DOTS, edge,
                        reader=READERS.CV_REPEAT_DOTS,
                        frame=G.FRAME_REPEAT_DOTS, staff=st, cell=2)
        log.freeze()
        adjudicate.run(log, order=(Q.REPEAT_BARLINE,))
        return log.verdict(Q.REPEAT_BARLINE, SYS)

    def test_brahms_p10_eleven_of_fourteen_staves_is_a_backward_repeat(self):
        v = self._decide(11)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value[0]["direction"], "backward")
        self.assertEqual(v.value[0]["cell"], 2)
        self.assertEqual(len(v.used), 11)
        self.assertEqual(v.detail["n_staves"], 14)

    def test_dots_right_of_the_barline_are_a_forward_repeat(self):
        v = self._decide(11, edge="start")
        self.assertEqual(v.value[0]["direction"], "forward")

    def test_REFUSAL_two_staves_of_fourteen_is_not_a_repeat(self):
        v = self._decide(2)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "too_few_staves")
        self.assertEqual(v.detail["edges"], [{"cell": 2, "edge": "end",
                                              "staves": 2}])


# ─────────────────────────────────────────────────────────────────────────────
# 3. EXPORT: the print's numbering, and the marks
# ─────────────────────────────────────────────────────────────────────────────

ENDINGS_VALUE = [
    {"number": 1, "first_cell": 1, "last_cell": 2, "closed": True},
    {"number": 2, "first_cell": 3, "last_cell": 3, "closed": False}]


def _page_with(endings=True, repeat=True, outcome="decided"):
    page = _one_staff_page(notes=[], n_measures=6,
                           meter={"numerator": 2, "denominator": 4})
    v = page["record"]["verdicts"]
    if endings:
        v.append(_vrd(950, "system/0/0", "endings", ENDINGS_VALUE,
                      outcome=outcome))
    if repeat:
        v.append(_vrd(951, "system/0/0", "repeat_barline",
                      [{"cell": 2, "edge": "end", "direction": "backward",
                        "staves": 11}]))
    return page


class TestExportNumbersThePrintsWay(unittest.TestCase):

    def test_the_2nd_ending_reuses_the_1st_endings_numbers(self):
        xml, rep = SX.to_musicxml(_page_with())
        nums = [m.get("number") for m in ET.fromstring(xml).iter("measure")]
        self.assertEqual(nums, ["1", "2", "3", "2", "3", "4"])
        self.assertEqual(rep["measure_numbering"]["endings"]["rewound_bars"], 2)

    def test_the_endings_and_the_repeat_are_written(self):
        xml, _ = SX.to_musicxml(_page_with())
        ms = list(ET.fromstring(xml).iter("measure"))
        left = ms[1].find("barline[@location='left']/ending")
        self.assertEqual((left.get("number"), left.get("type")), ("1", "start"))
        right = ms[2].find("barline[@location='right']")
        self.assertEqual(right.find("bar-style").text, "light-heavy")
        self.assertEqual(right.find("ending").get("type"), "stop")
        self.assertEqual(right.find("repeat").get("direction"), "backward")
        # child order: ending before repeat
        tags = [c.tag for c in right]
        self.assertLess(tags.index("ending"), tags.index("repeat"))
        two = ms[3].find("barline[@location='left']/ending")
        self.assertEqual((two.get("number"), two.get("type")), ("2", "start"))
        stop2 = ms[3].find("barline[@location='right']/ending")
        self.assertEqual(stop2.get("type"), "discontinue")

    def test_CONTROL_no_endings_counts_straight_through(self):
        xml, rep = SX.to_musicxml(_page_with(endings=False, repeat=False))
        nums = [m.get("number") for m in ET.fromstring(xml).iter("measure")]
        self.assertEqual(nums, ["1", "2", "3", "4", "5", "6"])
        self.assertEqual(len(list(ET.fromstring(xml).iter("barline"))), 0)

    def test_REFUSAL_an_abstained_endings_verdict_renumbers_nothing(self):
        xml, _ = SX.to_musicxml(_page_with(outcome="abstained", repeat=False))
        nums = [m.get("number") for m in ET.fromstring(xml).iter("measure")]
        self.assertEqual(nums, ["1", "2", "3", "4", "5", "6"])

    def test_the_accounting_still_balances(self):
        _xml, rep = SX.to_musicxml(_page_with())
        self.assertEqual(rep["status_census"]["unaccounted"], [])


class TestThePrintedNumberCheckSeesTheRewind(unittest.TestCase):

    def test_a_system_after_the_endings_is_compared_on_the_rewound_number(self):
        """Brahms p11 s0 prints 194: 188 is p10 s1's first bar, 8 bars on
        that system (1 + 2 first-ending + 5), so a straight count says 196."""

        class _Rec:
            def verdict(self, q, sub):
                return {(Q.ENDINGS, "system/10/1"): {
                            "outcome": "decided", "value": [
                                {"number": 1, "first_cell": 1,
                                 "last_cell": 2, "closed": True},
                                {"number": 2, "first_cell": 3,
                                 "last_cell": 3, "closed": False}]},
                        (Q.PRINTED_BAR_NUMBER, "system/11/0"): {
                            "outcome": "decided", "value": 194},
                        }.get((q, sub))

        numbering = {"scheme": "document", "systems": [
            {"system": "10/1", "page": 10, "system_index": 1, "bars": 8,
             "offset": 187},
            {"system": "11/0", "page": 11, "system_index": 0, "bars": 11,
             "offset": 195}]}
        plan = SX._ending_plan(_Rec(), numbering)
        rep = SX._printed_bar_number_check(_Rec(), numbering, plan)
        row = [r for r in rep["systems"] if r["system"] == "11/0"][0]
        self.assertEqual(row["file_number"], 194)
        self.assertEqual(row["state"], "agree")


if __name__ == "__main__":
    unittest.main()
