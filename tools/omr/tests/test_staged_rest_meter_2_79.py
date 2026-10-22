"""ROADMAP 2.79 -- a whole-bar rest takes the length of the meter WRITTEN in
force at ITS bar, and a bar whose lone rest says otherwise is never written.

THE FAULT (overnight `20261010-night`, Brahms 1/i Breitkopf): the acceptance
control `bars_add_up` read 29 OVERFULL bars -- bars 10-14 of 14 parts, one
whole-bar rest with no `<type>` and `<duration>` 9/8 long under a written
`<time>` of 6/8. The system's `Q.METER` was ONE verdict whose `segments` said
9/8 at bar 8 and a corroborated return to 6/8 at bar 9. EXPORT wrote
`<time>` from `record.meter_at(value, bar)`; EVALUATE's `size_measure_rest`
(and `reconcile_duration`, and `reinstate_rest_between_staves`) read the
verdict's TOP-LEVEL numerator/denominator -- the OPENING segment -- for every
bar of the system. `record.meter_at`'s own docstring says why no consumer
should: "a bar past a change would get the wrong answer".

THE HOLE (why nothing caught it): `export._bar_holds_out` treats a LONE
measure rest as the bar whatever its `<duration>` (CLAUDE.md §10), so a lone
rest was never measured against the meter at all. The convention is right;
the exemption was wider than it. A measure rest stands for the bar, so its
length IS the written meter's -- a rest that says otherwise is two parts of
the system disagreeing about the bar, and that is a bar we cannot vouch for
(rule 8): held out and counted.

The `*_RED` tests fail on the unrepaired tree; the rest are the positive
controls that stop the repair passing by refusing everything (CLAUDE.md §6b).

The two OTHER rules that read the same field are in
`test_staged_rest_meter_siblings_2_79.py` -- a separate change with a separate
effect on the record.
"""
from __future__ import annotations

import json
import unittest
import xml.etree.ElementTree as ET

from tools.omr import acceptance
from tools.omr.staged import consequences
from tools.omr.staged import evaluate
from tools.omr.staged import export as SX
from tools.omr.staged import lilypond as LY
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict
from tools.omr.tests.test_staged_export import _add_rest, _one_staff_page

# 9/8 at bar 8, a printed return to 6/8 at bar 9 (cells 0 and 1 of the system):
# the shape of Brahms 1/i p1 system 0. The TOP-LEVEL numerator/denominator is
# the OPENING segment, exactly as `rhythm._with_segments` writes it.
SEGMENTED = {
    "numerator": 9, "denominator": 8, "raw": "9/8",
    "segments": [
        {"from_cell": 0, "numerator": 9, "denominator": 8, "raw": "9/8"},
        {"from_cell": 1, "numerator": 6, "denominator": 8, "raw": "6/8",
         "corroborated": True},
    ],
}
SIX_EIGHT = {"numerator": 6, "denominator": 8, "raw": "6/8"}
WHOLE_REST = {"beats": 4.0, "written": 4.0, "dots": 0, "is_rest": True}


def _v(log, sub, q, outcome, value, reason="t", detail=None, candidates=()):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome,
        value=value, decider="test", reason=reason, detail=detail or {},
        candidates=candidates))


def _system_meter(log, value):
    return _v(log, R.system(0, 0), Q.METER, Outcome.DECIDED, value)


def _lone_rest(log, cell, staff=1):
    sub = R.glyph(0, 0, staff, cell, 0)
    _v(log, sub, Q.DURATION, Outcome.DECIDED, dict(WHOLE_REST),
       reason="rest_class", detail={"rest": "restWhole"})
    return sub


def _size(log, cell, staff=1):
    """Fire `size_measure_rest` on one cell exactly as `evaluate` does: the
    cause is the SYSTEM's `Q.METER` verdict, whatever the cell."""
    meter = log.verdict(Q.METER, R.system(0, 0))
    return consequences.size_measure_rest(log, R.cell(0, 0, staff, cell), meter)


# ─────────────────────────────────────────────────────────────────────────────
# EVALUATE -- `size_measure_rest` reads the meter at ITS bar
# ─────────────────────────────────────────────────────────────────────────────


class TestARestTakesTheMeterInForceAtItsBar(unittest.TestCase):
    def test_a_rest_after_the_printed_return_is_the_RETURNED_length_RED(self):
        """Bars 10-14 of Brahms: cell 4 is under the 6/8 segment, so the bar
        is three quarters. The unrepaired rule read the opening 9/8 and wrote
        4.5."""
        log = Log()
        _system_meter(log, SEGMENTED)
        rest = _lone_rest(log, 4)
        self.assertEqual(len(_size(log, 4)), 1)
        got = log.verdict(Q.DURATION, rest)
        self.assertTrue(got.value["measure_rest"])
        self.assertEqual(got.value["beats"], 3.0)
        self.assertEqual(got.value["written"], 3.0)

    def test_the_bar_UNDER_the_opening_segment_is_still_its_length(self):
        """Positive control: the rest at cell 0 IS in the 9/8 bar."""
        log = Log()
        _system_meter(log, SEGMENTED)
        rest = _lone_rest(log, 0)
        self.assertEqual(len(_size(log, 0)), 1)
        self.assertEqual(log.verdict(Q.DURATION, rest).value["beats"], 4.5)

    def test_the_first_bar_of_a_later_segment_takes_it_RED(self):
        """The boundary: `from_cell` 1 starts the 6/8, so cell 1 is 3.0."""
        log = Log()
        _system_meter(log, SEGMENTED)
        rest = _lone_rest(log, 1)
        self.assertEqual(len(_size(log, 1)), 1)
        self.assertEqual(log.verdict(Q.DURATION, rest).value["beats"], 3.0)

    def test_an_unchanged_meter_sizes_every_bar_alike(self):
        """Positive control: one segment (what almost every system is)."""
        log = Log()
        _system_meter(log, dict(SIX_EIGHT, segments=[
            dict(SIX_EIGHT, from_cell=0)]))
        rest = _lone_rest(log, 4)
        self.assertEqual(len(_size(log, 4)), 1)
        self.assertEqual(log.verdict(Q.DURATION, rest).value["beats"], 3.0)

    def test_a_record_with_NO_segments_key_still_sizes_by_its_value(self):
        """Positive control: an older record, or a hand-built verdict, has no
        `segments` and `meter_at` answers the value itself."""
        log = Log()
        _system_meter(log, dict(SIX_EIGHT))
        rest = _lone_rest(log, 4)
        self.assertEqual(len(_size(log, 4)), 1)
        self.assertEqual(log.verdict(Q.DURATION, rest).value["beats"], 3.0)

    def test_a_bar_NO_segment_covers_is_not_sized_RED(self):
        """Rule 8. `meter_at` answers None for a bar before the first
        segment -- "3/4 from bar 8, unknown before" -- and that is a real
        answer. The unrepaired rule read the top-level 3/4 and sized the rest
        of bar 3 as three quarters anyway: a meter nobody read, asserted."""
        log = Log()
        _system_meter(log, {
            "numerator": 3, "denominator": 4, "raw": "3/4",
            "segments": [{"from_cell": 7, "numerator": 3, "denominator": 4,
                          "raw": "3/4"}]})
        rest = _lone_rest(log, 3)
        self.assertEqual(_size(log, 3), [])
        self.assertNotIn("measure_rest", log.verdict(Q.DURATION, rest).value)

    def test_and_the_bar_the_segment_DOES_cover_is_sized(self):
        """The sibling of the test above: same verdict, cell 8."""
        log = Log()
        _system_meter(log, {
            "numerator": 3, "denominator": 4, "raw": "3/4",
            "segments": [{"from_cell": 7, "numerator": 3, "denominator": 4,
                          "raw": "3/4"}]})
        rest = _lone_rest(log, 8)
        self.assertEqual(len(_size(log, 8)), 1)
        self.assertEqual(log.verdict(Q.DURATION, rest).value["beats"], 3.0)


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT -- a lone measure rest is the bar, but it is the WRITTEN bar
# ─────────────────────────────────────────────────────────────────────────────


def _lone(beats, *, measure_rest=True):
    return {"duration_beats": beats, "kind": "rest",
            "rest": {"measure_rest": measure_rest}}


class TestALoneMeasureRestIsTheWrittenBar(unittest.TestCase):
    SIX_EIGHT_DICT = {"numerator": 6, "denominator": 8}

    def test_a_lone_rest_of_the_meters_length_is_not_held_out(self):
        """Positive control: 3.0 beats in 6/8 at divisions 16."""
        self.assertIsNone(SX._bar_holds_out(
            [_lone(3.0)], None, 16, self.SIX_EIGHT_DICT))

    def test_a_lone_rest_LONGER_than_the_meter_is_held_out_RED(self):
        held = SX._bar_holds_out([_lone(4.5)], None, 16, self.SIX_EIGHT_DICT)
        self.assertIsNotNone(held)
        self.assertEqual(held["want_units"], 48)
        self.assertEqual(held["voices"][0]["units"], 72)
        self.assertTrue(held["voices"][0]["is_the_bar"])
        self.assertTrue(held["voices"][0]["measure_rest_length_disagrees"])

    def test_a_lone_rest_SHORTER_than_the_meter_is_held_out_RED(self):
        held = SX._bar_holds_out([_lone(1.5)], None, 16, self.SIX_EIGHT_DICT)
        self.assertIsNotNone(held)
        self.assertTrue(held["voices"][0]["measure_rest_length_disagrees"])

    def test_the_length_of_the_WRITTEN_meter_is_the_one_asked(self):
        """The same 4.5-beat rest is the bar under 9/8: only the meter
        changed, so the verdict is the meter's and not the rest's."""
        self.assertIsNone(SX._bar_holds_out(
            [_lone(4.5)], None, 16, {"numerator": 9, "denominator": 8}))

    def test_no_meter_no_verdict_still(self):
        """Rule 8 the other way: a bar with no written meter has nothing to
        disagree with, and is not held out for it."""
        self.assertIsNone(SX._bar_holds_out([_lone(4.5)], None, 16, None))

    def test_a_rest_that_is_not_flagged_a_measure_rest_is_summed_as_before(self):
        """Control for the rule's scope: an ordinary whole rest is an event of
        its own length (2.8's old arithmetic), neither more nor less held."""
        self.assertIsNotNone(SX._bar_holds_out(
            [_lone(4.0, measure_rest=False)], None, 16, self.SIX_EIGHT_DICT))
        self.assertIsNone(SX._bar_holds_out(
            [_lone(3.0, measure_rest=False)], None, 16, self.SIX_EIGHT_DICT))


class TestTheFileNeverWritesAWrongLengthMeasureRest(unittest.TestCase):
    def _page(self, rest_beats):
        page = _one_staff_page(notes=[], meter=dict(SIX_EIGHT))
        _add_rest(page, 5, "restWhole",
                  {"beats": rest_beats, "written": rest_beats, "dots": 0,
                   "is_rest": True, "measure_rest": True})
        return page

    def test_a_wrong_length_lone_rest_is_held_out_and_counted_RED(self):
        xml, rep = SX.to_musicxml(self._page(4.5))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)
        self.assertEqual(rep["notes_not_written"]["bar_does_not_add_up"], 1)
        self.assertEqual(rep["written"].get("measure_rests_read", 0), 0)
        # ...and the file is one the acceptance control reads clean.
        control = acceptance.bars_add_up(xml)
        self.assertEqual((control["overfull"], control["short"]), (0, 0))

    def test_a_right_length_lone_rest_is_written_as_the_bar(self):
        """Positive control: the same page with the rest the meter's length."""
        xml, rep = SX.to_musicxml(self._page(3.0))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)
        self.assertEqual(rep["written"]["measure_rests_read"], 1)
        rest = ET.fromstring(xml).find(".//rest")
        self.assertEqual(rest.get("measure"), "yes")
        control = acceptance.bars_add_up(xml)
        self.assertEqual((control["overfull"], control["short"]), (0, 0))
        self.assertEqual(control["exact"], 1)

    def test_the_held_bar_names_why_RED(self):
        _xml, rep = SX.to_musicxml(self._page(4.5))
        (bar,) = rep["bars_held_out_sum"]["held"]
        self.assertTrue(bar["voices"][0]["measure_rest_length_disagrees"])

    def test_the_lilypond_path_holds_the_same_bar_out_RED(self):
        """`_bar_holds_out` is the ONE copy both exporters ask, so the two
        files cannot disagree about which bars were held."""
        _ly, rep = LY.to_lilypond(self._page(4.5))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)
        _ly, rep = LY.to_lilypond(self._page(3.0))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)


# ─────────────────────────────────────────────────────────────────────────────
# THE SEAM -- EVALUATE's length against EXPORT's `<time>`, end to end
# ─────────────────────────────────────────────────────────────────────────────


def _segmented_staff(n_cells=5):
    """One staff, one system, `n_cells` bars, each holding ONE whole-rest
    glyph as ADJUDICATE leaves it (4.0, unsized); a segmented system meter.
    Built as a LOG so `evaluate.run` is the real stage, then serialised for
    EXPORT -- the seam the two halves' own tests could not see."""
    log = Log()
    st = R.staff(0, 0, 0)
    sysk = R.system(0, 0)
    _v(log, sysk, Q.SYSTEM_STAFF_COUNT, Outcome.DECIDED, 1)
    _v(log, R.DOCUMENT, Q.PART_PARTITION, Outcome.DECIDED,
       {"join": "ordinal", "staves_per_system": 1}, reason="ordinal")
    _v(log, st, Q.MEASURE_PARTITION, Outcome.DECIDED, n_cells)
    _v(log, st, Q.CLEF, Outcome.DECIDED, "treble")
    _v(log, sysk, Q.METER, Outcome.DECIDED, dict(SEGMENTED))
    for cell in range(n_cells):
        g = R.glyph(0, 0, 0, cell, 0)
        log.observe(g, Q.GLYPH_BOX, ["restWhole", 300, 50, 20, 30],
                    reader=READERS.DETECTOR, frame=f"cell:{cell}",
                    score=0.9, category="rest")
        log.observe(g, Q.REST, "restWhole", reader=READERS.DETECTOR,
                    frame=f"cell:{cell}", score=0.9, category="rest")
        _v(log, g, Q.DURATION, Outcome.DECIDED, dict(WHOLE_REST),
           reason="rest_class", detail={"rest": "restWhole"})
    return log


class TestEvaluateAndExportAgreeOnTheBar(unittest.TestCase):
    def _file(self):
        log = _segmented_staff()
        evaluate.run(log)
        return SX.to_musicxml(
            json.loads(json.dumps({"record": log.to_json(), "summary": {}},
                                  default=str)))

    def test_every_measure_rest_is_the_length_of_the_time_beside_it_RED(self):
        xml, rep = self._file()
        control = acceptance.bars_add_up(xml)
        self.assertEqual((control["overfull"], control["short"]), (0, 0))
        self.assertEqual(control["exact"], 5)
        durations = [
            int(m.find("note/duration").text)
            for m in ET.fromstring(xml).findall(".//measure")]
        div = int(ET.fromstring(xml).find(".//divisions").text)
        # bar 1 is the 9/8 bar; bars 2-5 are the 6/8 the plate returns to.
        self.assertEqual(durations, [round(4.5 * div)] + [3 * div] * 4)

    def test_none_of_them_needed_the_hold_out_to_be_right(self):
        """The hold-out is the BACKSTOP and must be quiet on a correct run: a
        file that is clean only because the exporter threw the bars away
        would pass the control above and say nothing."""
        _xml, rep = self._file()
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)
        self.assertEqual(rep["written"]["measure_rests_read"], 5)

    def test_the_time_signatures_are_written_where_they_change(self):
        xml, _rep = self._file()
        times = [(m.get("number"),
                  m.findtext("attributes/time/beats"),
                  m.findtext("attributes/time/beat-type"))
                 for m in ET.fromstring(xml).findall(".//measure")
                 if m.find("attributes/time") is not None]
        self.assertEqual(times, [("1", "9", "8"), ("2", "6", "8")])


if __name__ == "__main__":
    unittest.main()
