"""ROADMAP 2.107, Sean 2026-10-13: a dynamic whose letters were seen and not all
read is NEVER written as one of its candidates and never plain.

  *"Sf - sforzando is a very specific dynamic treatment - not a 'usual
  dynamic'. can it just say dyn.? in blue"* and, refining it, *"or even better
  - maybe the closest dynamic we can guess with the info that we have?"*

So: a NARROWED dynamic is INFER-collapsed to the candidate the INK scores
closest (the letter reader's own score for the open letter, never the
document's frequency of a word) where the lead is clear, and written BLUE with
every candidate in a carrier; where the ink favours none, the narrowing stands
and EXPORT writes a blue `dyn.`. A DECIDED dynamic is written plain.

RED on the tree before this change: no `collapse_dynamic_by_ink`, no
`dynamics_guess`, and a narrowed dynamic wrote NOTHING.
"""
from __future__ import annotations

import json
import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import export as SX
from tools.omr.staged import infer as INF
from tools.omr.staged import inferences as INFS
from tools.omr.staged import letter_look as LL
from tools.omr.staged.record import Q
from tools.omr.tests.test_staged_export import QUARTER, _one_staff_page, _vrd

CELL = "cell/0/0/0/0"


def _page_with(dyn_verdict):
    page = _one_staff_page(notes=[("C4", QUARTER)])
    page["record"]["verdicts"].append(dyn_verdict)
    return page


def _narrowed(support):
    v = _vrd(7000, CELL, Q.DYNAMIC, None, outcome="narrowed",
             reason="unspellable",
             candidates=[{"value": w, "support": s} for w, s in support.items()])
    v["decider"] = "adjudicate_dynamic"
    v["detail"] = {"words": [{"text": "?f", "spelled": False, "x_page": 120.0,
                              "completions": sorted(support),
                              "completion_support": dict(support)}]}
    return v


def _directions(xml):
    return ET.fromstring(xml).findall(".//direction")


class TestExport(unittest.TestCase):
    def test_a_narrowed_dynamic_is_a_blue_dyn_carrying_every_candidate_RED(self):
        page = _page_with(_narrowed({"sf": 0.05, "mf": 0.05, "rf": 0.05}))
        xml, rep = SX.to_musicxml(page)
        d = _directions(xml)
        self.assertEqual(len(d), 1)
        words = d[0].find("direction-type/words")
        self.assertEqual((words.text, words.get("color")), ("dyn.", SX.GUESS_COLOR))
        self.assertIsNone(d[0].find("direction-type/dynamics"))
        carrier = d[0].find("direction-type/other-direction").text
        body = json.loads(carrier.split(" ", 1)[1])
        self.assertEqual({c["value"] for c in body["candidates"]},
                         {"sf", "mf", "rf"})
        self.assertIsNone(body["chosen"]["value"])
        self.assertEqual(rep["guessed"]["dynamics"], 1)
        self.assertEqual(rep["written"]["dynamics"], 1)

    def test_an_inked_pick_is_blue_with_its_margin_and_all_candidates_RED(self):
        page = _page_with(_narrowed({"sf": 0.62, "mf": 0.05, "rf": 0.05}))
        prior = page["record"]["verdicts"][-1]
        new = _vrd(7001, CELL, Q.DYNAMIC, "sf", reason="ink_evidence",
                   candidates=prior["candidates"])
        new.update(decider="infer:collapse_dynamic_by_ink", supersedes=prior["id"],
                   basis=[prior["id"]],
                   detail={"inferred": True, "margin": 0.57, "runner_up": "mf",
                           "ink_scores": {"sf": 0.62, "mf": 0.05, "rf": 0.05}})
        page["record"]["verdicts"].append(new)
        xml, rep = SX.to_musicxml(page)
        d = _directions(xml)
        dyn = d[0].find("direction-type/dynamics")
        self.assertEqual(dyn.get("color"), SX.GUESS_COLOR)
        self.assertIsNotNone(dyn.find("sf"))
        body = json.loads(d[0].find("direction-type/other-direction").text
                          .split(" ", 1)[1])
        self.assertEqual(body["chosen"]["value"], "sf")
        self.assertEqual(body["rule"], "collapse_dynamic_by_ink")
        self.assertAlmostEqual(body["margin"], 0.57)
        self.assertEqual(len(body["candidates"]), 3)
        self.assertEqual(rep["guessed"]["by_rule"]["collapse_dynamic_by_ink"], 1)

    def test_a_DECIDED_dynamic_is_written_plain_with_its_letters(self):
        """CONTROL (can fail): the same cell, decided -> no colour, no carrier,
        no guess counted."""
        v = _vrd(7000, CELL, Q.DYNAMIC, ["sf"], reason="spelled")
        v["decider"] = "adjudicate_dynamic"
        v["detail"] = {"words": [{"text": "sf", "spelled": True, "x_page": 120.0}]}
        xml, rep = SX.to_musicxml(_page_with(v))
        d = _directions(xml)
        self.assertEqual(len(d), 1)
        dyn = d[0].find("direction-type/dynamics")
        self.assertIsNone(dyn.get("color"))
        self.assertIsNotNone(dyn.find("sf"))
        self.assertIsNone(d[0].find("direction-type/other-direction"))
        self.assertEqual(rep["guessed"]["dynamics"], 0)
        self.assertEqual(rep["written"]["dynamics"], 1)


def _log_with(prior_candidates, words):
    """A frozen Log holding one NARROWED dynamic verdict, for the rule."""
    from tools.omr.staged import record as R
    from tools.omr.staged.record import Candidate, Log, Outcome, Verdict
    log = Log()
    sub = R.cell(0, 0, 0, 0)
    log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=Q.DYNAMIC,
        outcome=Outcome.NARROWED, value=None, decider="adjudicate_dynamic",
        reason="unspellable", used=(), basis=(),
        candidates=tuple(Candidate(value=w, support=s)
                         for w, s in prior_candidates.items()),
        detail={"words": words}))
    return log, sub


def _word(support):
    return [{"text": "?f", "spelled": False, "completions": sorted(support),
             "completion_support": dict(support)}]


class TestTheInkPick(unittest.TestCase):
    def _run(self, support, words=None):
        log, sub = _log_with(support, words if words is not None else _word(support))
        return INFS.collapse_dynamic_by_ink(log, sub)

    def test_a_clear_lead_is_picked_with_its_margin_RED(self):
        p = self._run({"ff": 0.75, "fp": 0.45, "fz": 0.05})
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0].value, "ff")
        self.assertAlmostEqual(p[0].detail["margin"], 0.30)
        self.assertEqual(p[0].detail["runner_up"], "fp")

    def test_a_tie_inside_the_margin_picks_nothing(self):
        self.assertEqual(self._run({"sf": 0.52, "mf": 0.46, "rf": 0.05}), [])

    def test_an_open_letter_nobody_scored_picks_nothing(self):
        """Evidence below the floor is no evidence (the broken `s` of tile 11)."""
        self.assertEqual(self._run({"sf": 0.05, "mf": 0.05, "rf": 0.05}), [])
        self.assertEqual(self._run({"sf": 0.29, "mf": 0.01}), [])

    def test_two_unspellable_runs_are_not_collapsed(self):
        sup = {"ff": 0.9, "pp": 0.1}
        self.assertEqual(self._run(sup, _word(sup) + _word(sup)), [])

    def test_a_decided_dynamic_is_never_touched(self):
        from tools.omr.staged import record as R
        from tools.omr.staged.record import Log, Outcome, Verdict
        log = Log()
        sub = R.cell(0, 0, 0, 0)
        log.record(Verdict(id=log._next_id("vrd"), subject=sub, quantity=Q.DYNAMIC,
                           outcome=Outcome.DECIDED, value=["sf"],
                           decider="adjudicate_dynamic", reason="spelled",
                           used=(), basis=(), detail={}))
        self.assertEqual(INFS.collapse_dynamic_by_ink(log, sub), [])

    def test_the_rule_is_registered_and_never_reads_a_frequency(self):
        INF._ensure_rules()
        names = [r.inference.value for r in INF.RULES]
        self.assertIn("collapse_dynamic_by_ink", names)
        rule = [r for r in INF.RULES
                if r.inference.value == "collapse_dynamic_by_ink"][0]
        self.assertEqual(set(rule.reads), {Q.DYNAMIC, Q.DYNAMIC_LETTER})


class TestAdjudicateRanksTheOpenLetterByTheInk(unittest.TestCase):
    """`adjudicate_dynamic` over the twins the second look files for an UNREAD
    letter: never spelled by height or lexicon, ranked by the reader's score."""

    def _log(self, scores, ink_h=1.0):
        from tools.omr.staged import adjudicate
        from tools.omr.staged import adjudicators  # noqa: F401
        from tools.omr.staged import gather as G
        from tools.omr.staged import record as R
        from tools.omr.staged.record import Log, READERS
        log = Log()

        def letter(gi, l, x0, x1, score, unread, h):
            extra = {"how": "unread"} if unread else {}
            log.observe(
                R.glyph(0, 0, 0, 0, gi), Q.DYNAMIC_LETTER, "dynamic" + l.upper(),
                reader=READERS.LETTER_LOOK if unread else READERS.DETECTOR,
                frame=G.FRAME_PAGE, score=score, letter=l, cell_frame="cell:0",
                bbox_page_px=[x0, 100.0, x1, 125.0],
                x_center_page=(x0 + x1) / 2.0, y_center_page=112.0,
                staff_bottom_line_page=90.0, staff_spacing_px=10.0,
                band_offset_spaces=1.0, in_hairpin_band=True,
                ink_height_spaces=h, **extra)
        letter(0, "f", 130, 170, 0.88, False, 2.5)
        for gi, (l, sc) in enumerate(scores.items(), start=1):
            letter(gi, l, 100, 118, sc, True, ink_h)
        log.freeze()
        adjudicate.run(log)
        return log.verdict(Q.DYNAMIC, R.cell(0, 0, 0, 0))

    def test_candidates_carry_the_inks_own_scores_RED(self):
        v = self._log({"s": 0.05, "m": 0.59, "r": 0.05})
        self.assertEqual(v.outcome.value, "narrowed")
        sup = {c.value: c.support for c in v.candidates}
        self.assertAlmostEqual(sup["mf"], 0.59, places=2)
        self.assertAlmostEqual(sup["sf"], 0.05, places=2)

    def test_one_letter_the_ink_height_would_leave_is_still_not_written_plain(self):
        """CONTROL (can fail): twins `s`/`m` at an x-height ink. The 2.68 twin
        rule would have resolved a lone surviving letter and spelled a word;
        for an UNREAD slot it must stay a guess."""
        v = self._log({"s": 0.4, "m": 0.1}, ink_h=1.0)
        self.assertEqual(v.outcome.value, "narrowed")
        self.assertIsNone(v.value)


class TestTheInksOwnEvidence(unittest.TestCase):
    def _h(self, cls, conf, box, scale=10.0):
        return LL.Hypothesis(cls, conf, box, scale)

    def test_the_lower_of_two_erasures_is_the_evidence(self):
        slot = (0, 0, 20, 30)
        a = [self._h("dynamicM", 0.739, (0, 0, 20, 30)),
             self._h("dynamicS", 0.30, (0, 0, 20, 30))]
        b = [self._h("dynamicS", 0.40, (0, 0, 20, 30))]
        ev = LL.slot_evidence(slot, a, b, [])
        self.assertEqual(ev["m"], 0.0)       # one erasure alone is no evidence
        self.assertEqual(ev["s"], 0.30)

    def test_the_read_letters_own_boxes_are_not_the_slots_evidence(self):
        """CONTROL: the strong `f`'s box covers the slot (tile 9); it must not
        score `f` for the slot."""
        slot = (0, 0, 10, 30)
        own = (0, 0, 40, 30)
        ev = LL.slot_evidence(slot, [self._h("dynamicF", 0.88, own)], None, [own])
        self.assertEqual(ev, {})

    def test_a_hypothesis_beside_the_slot_is_not_about_it(self):
        ev = LL.slot_evidence((0, 0, 10, 10),
                              [self._h("dynamicP", 0.9, (50, 0, 60, 10))], None, [])
        self.assertEqual(ev, {})


if __name__ == "__main__":
    unittest.main()
