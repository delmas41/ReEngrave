"""ROADMAP 2.103 -- a GUESSED symbol is visible in the file (Sean 2026-10-12,
DECISIONS: *"I don't want any hidden."*).

Three kinds of symbol: READ (written plain), GUESSED (written AND flagged,
carrying the candidates it was chosen from), UNREAD (already marked; not this
item's). GUESSED = the standing verdict came from INFER (`decider` begins
`infer:`) or from a bar-sum settlement in EVALUATE (`reconcile_duration`).
Display and accounting only: not one pitch or duration may move.

The `*_RED` tests fail on the tree before this item; the READ controls are the
positive controls that stop the flag passing by colouring everything.
"""
from __future__ import annotations

import copy
import json
import re
import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import export as SX
from tools.omr.staged import lilypond as LY
from tools.omr.staged.record import Q
from tools.omr.tests.test_staged_export import (
    QUARTER, _add_rest, _obs, _one_staff_page, _vrd)

EIGHTH = {"beats": 0.5, "written": 0.5, "dots": 0, "beam_levels": 1}
CANDS = [{"value": dict(EIGHTH), "support": 2.0},
         {"value": dict(QUARTER, beam_levels=0), "support": 1.0}]
WHOLE_BAR = {"beats": 4.0, "written": 4.0, "dots": 0, "is_rest": True,
             "measure_rest": True}


def _guess(page, gi, *, decider, value=EIGHTH, candidates=CANDS):
    """Make note `gi`'s duration a NARROWED reading superseded by `decider`."""
    sub = f"glyph/0/0/0/0/{gi}"
    vs = page["record"]["verdicts"]
    old = next(v for v in vs if v["subject"] == sub and v["quantity"] == Q.DURATION)
    old.update(outcome="narrowed", value=None, decider="adjudicate_duration",
               reason="beams_ambiguous", candidates=copy.deepcopy(candidates))
    new = _vrd(5000 + gi, sub, Q.DURATION, value)
    new.update(decider=decider, supersedes=old["id"], basis=[old["id"]],
               reason="r", candidates=copy.deepcopy(candidates) if decider.startswith("infer:") else [])
    vs.append(new)
    return page


def _page():
    page = _one_staff_page(
        notes=[("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER), ("F4", QUARTER)])
    _guess(page, 1, decider="infer:collapse_duration_by_column")
    _guess(page, 2, decider="reconcile_duration")
    return page


def _notes(xml):
    return ET.fromstring(xml).findall(".//note")


class TestMusicXml(unittest.TestCase):
    def test_a_guessed_note_is_coloured_and_carries_its_candidates_RED(self):
        xml, _ = SX.to_musicxml(_page())
        n = _notes(xml)
        self.assertEqual(n[1].get("color"), SX.GUESS_COLOR)
        carrier = n[1].find("notations/other-notation")
        self.assertIsNotNone(carrier)
        body = json.loads(carrier.text.split(" ", 1)[1])
        self.assertEqual(body["rule"], "collapse_duration_by_column")
        self.assertEqual(body["stage"], "INFER")
        self.assertEqual([c["support"] for c in body["candidates"]], [2.0, 1.0])

    def test_a_bar_sum_settlement_is_guessed_too_and_keeps_the_prior_candidates_RED(self):
        xml, _ = SX.to_musicxml(_page())
        n = _notes(xml)
        self.assertEqual(n[2].get("color"), SX.GUESS_COLOR)
        body = json.loads(n[2].find("notations/other-notation").text.split(" ", 1)[1])
        self.assertEqual((body["rule"], body["stage"]),
                         ("reconcile_duration", "EVALUATE"))
        self.assertEqual(len(body["candidates"]), 2)

    def test_READ_notes_stay_plain(self):
        xml, _ = SX.to_musicxml(_page())
        n = _notes(xml)
        for i in (0, 3):
            self.assertIsNone(n[i].get("color"))
            self.assertIsNone(n[i].find("notations/other-notation"))

    def test_a_lone_whole_rest_sized_to_the_bar_is_a_convention_and_stays_READ(self):
        page = _one_staff_page(notes=[], meter={"numerator": 4, "denominator": 4,
                                                "raw": "4/4"})
        _add_rest(page, 0, "restWhole", dict(WHOLE_BAR))
        for v in page["record"]["verdicts"]:
            if v["quantity"] == Q.DURATION:
                v["decider"] = "size_measure_rest"
        xml, rep = SX.to_musicxml(page)
        rest = _notes(xml)[0]
        self.assertIsNotNone(rest.find("rest"))
        self.assertIsNone(rest.get("color"))
        self.assertEqual(rep["guessed"]["total"], 0)

    def test_an_inferred_rest_is_coloured_RED(self):
        page = _one_staff_page(notes=[])
        _add_rest(page, 0, "restQuarter", {"beats": 1.0, "written": 1.0, "dots": 0,
                                           "is_rest": True})
        _guess(page, 0, decider="infer:collapse_duration_by_column",
               value={"beats": 1.0, "written": 1.0, "dots": 0, "is_rest": True})
        xml, rep = SX.to_musicxml(page)
        rest = _notes(xml)[0]
        self.assertIsNotNone(rest.find("rest"))
        self.assertEqual(rest.get("color"), SX.GUESS_COLOR)
        self.assertEqual(rep["guessed"]["rests"], 1)

    def test_the_music_is_unchanged_only_the_flag_is_added_RED(self):
        flagged, _ = SX.to_musicxml(_page())
        base_page = _page()
        for v in base_page["record"]["verdicts"]:
            v["decider"] = "t"            # nothing is a guess any more
        base, rep0 = SX.to_musicxml(base_page)
        self.assertEqual(rep0["guessed"]["total"], 0)
        self.assertNotEqual(flagged, base)
        stripped = re.sub(r' color="[^"]*"', "", flagged)
        stripped = re.sub(r"\n\s*<notations>\s*<other-notation.*?</notations>",
                          "", stripped, flags=re.S)
        self.assertEqual(stripped, base)

    def test_the_report_counts_per_family_and_per_rule_and_balances_RED(self):
        _xml, rep = SX.to_musicxml(_page())
        g = rep["guessed"]
        self.assertEqual((g["notes"], g["rests"], g["total"]), (2, 0, 2))
        self.assertEqual(g["by_rule"], {"collapse_duration_by_column": 1,
                                        "reconcile_duration": 1})
        self.assertEqual(rep["notes_not_written_total"], 0)


class TestLilyPond(unittest.TestCase):
    def test_guessed_notes_are_tweaked_and_the_legend_is_in_the_header_RED(self):
        ly, rep = LY.to_lilypond(_page())
        self.assertEqual(ly.count("\\tweak color #guessedColor"), 2)
        self.assertIn("guessedColor", ly.split("\\header")[0])
        self.assertIn("GUESSED", ly.split("\\score")[0])
        self.assertEqual(rep["guessed"]["notes"], 2)

    def test_a_page_with_no_guess_has_no_colour_and_no_legend(self):
        page = _page()
        for v in page["record"]["verdicts"]:
            v["decider"] = "t"
        ly, _rep = LY.to_lilypond(page)
        self.assertNotIn("guessedColor", ly)
        self.assertNotIn("GUESSED", ly)

    def test_a_guessed_rest_uses_the_rest_grob_RED(self):
        page = _one_staff_page(notes=[])
        _add_rest(page, 0, "restQuarter", {"beats": 1.0, "written": 1.0, "dots": 0,
                                           "is_rest": True})
        _guess(page, 0, decider="infer:collapse_duration_by_column",
               value={"beats": 1.0, "written": 1.0, "dots": 0, "is_rest": True})
        ly, _ = LY.to_lilypond(page)
        self.assertIn("\\once \\override Rest.color = #guessedColor r4", ly)


class TestProvenance(unittest.TestCase):
    def test_a_pitch_read_through_an_inferred_clef_is_guessed_RED(self):
        page = _one_staff_page(notes=[("C4", QUARTER)])
        vs = page["record"]["verdicts"]
        clef = next(v for v in vs if v["quantity"] == Q.CLEF)
        clef.update(decider="infer:fill_clef_gap")
        pitch = next(v for v in vs if v["quantity"] == Q.PITCH)
        pitch["basis"] = [clef["id"]]
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(_notes(xml)[0].get("color"), SX.GUESS_COLOR)
        self.assertEqual(rep["guessed"]["by_rule"], {"fill_clef_gap": 1})


if __name__ == "__main__":
    unittest.main()
