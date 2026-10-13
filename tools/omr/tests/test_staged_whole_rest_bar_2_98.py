"""ROADMAP 2.98 -- a LONE whole rest is the bar, in the bar the FILE writes,
meter verdict or not (CLAUDE.md §10; Sean 2026-10-12: tiles 4-6, 3 of 3).

THE FAULT (2.96, the 2026-10-11 night records): 458 held bars were ONE whole
rest left at 4 beats. 403 are Brahms bars on a system whose `Q.METER`
ABSTAINED, so EVALUATE's `size_measure_rest` (cause: a DECIDED meter) never
fired; 30 are Litolff bars with a decided meter where a SECOND, notehead-class
box on the rest's own ink -- which ADJUDICATE decided is a whole rest, and
which EXPORT refuses as `ink_is_a_whole_rest` -- kept the bar from being
"lone" in EVALUATE.

Two parts, two stages (see `export._lone_whole_rest_is_the_bar` for why part 1
is EXPORT's): the `*_RED` tests fail on the unrepaired tree; the rest are the
positive controls that stop the repair passing by sizing everything.
"""
from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from tools.omr import acceptance
from tools.omr.staged import consequences
from tools.omr.staged import export as SX
from tools.omr.staged import lilypond as LY
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict
from tools.omr.tests.test_staged_export import (
    QUARTER, _add_rest, _obs, _one_staff_page, _vrd)

TWO_FOUR = {"numerator": 2, "denominator": 4, "raw": "2/4"}
SIX_EIGHT = {"numerator": 6, "denominator": 8, "raw": "6/8"}
UNFLAGGED_WHOLE = {"beats": 4.0, "written": 4.0, "dots": 0, "is_rest": True}


# ─────────────────────────────────────────────────────────────────────────────
# PART 1 -- EXPORT: the file's own meter in force sizes a lone whole rest
# ─────────────────────────────────────────────────────────────────────────────


def _two_system_page(second_rests, *, meter_on_second):
    """System 0: two quarters in 2/4 (the file declares `<time>` there).
    System 1: `second_rests` = [(class, duration dict)], filed in its only
    bar; its meter filed or NOT. MusicXML cannot un-declare a meter, so the
    second system is in 2/4 to any reader."""
    page = _one_staff_page(notes=[("C4", QUARTER), ("D4", QUARTER)],
                           meter=TWO_FOUR)
    rec = page["record"]
    for gi, (cls, dur) in enumerate(second_rests):
        sub = f"glyph/0/1/0/0/{gi}"
        rec["observations"].append(
            _obs(4000 + gi, sub, Q.GLYPH_BOX, [cls, 300, 50, 20, 30],
                 category="rest"))
        rec["observations"].append(
            _obs(4100 + gi, sub, Q.REST, cls, category="rest"))
        rec["verdicts"].append(_vrd(4200 + gi, sub, Q.DURATION, dur))
    rec["verdicts"].append(_vrd(4400, "staff/0/1/0", Q.MEASURE_PARTITION, 1))
    rec["verdicts"].append(_vrd(4401, "staff/0/1/0", Q.CLEF, "treble"))
    rec["verdicts"].append(_vrd(4402, "system/0/1", Q.SYSTEM_STAFF_COUNT, 1))
    if meter_on_second:
        rec["verdicts"].append(_vrd(4403, "system/0/1", Q.METER, TWO_FOUR))
    return page


def _second_bar(xml):
    return ET.fromstring(xml).findall(".//measure")[1]


class TestALoneWholeRestOnAMeterlessSystemIsTheFilesBar(unittest.TestCase):
    def test_it_is_written_as_the_bar_and_not_held_out_RED(self):
        """Brahms 1/i: the system's `Q.METER` abstained, the part carries
        2/4, and a lone 4.0 `restWhole` sat held out. RED before 2.98."""
        xml, rep = SX.to_musicxml(_two_system_page(
            [("restWhole", dict(UNFLAGGED_WHOLE))], meter_on_second=False))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)
        bar = _second_bar(xml)
        rest = bar.find("note/rest")
        self.assertEqual(rest.get("measure"), "yes")
        div = int(ET.fromstring(xml).find(".//divisions").text)
        self.assertEqual(int(bar.find("note/duration").text), 2 * div)
        self.assertEqual(rep["written"]["measure_rests_sized_by_the_file_meter"], 1)
        self.assertEqual(rep["written"]["measure_rests_sized_by_a_carried_meter"], 1)
        control = acceptance.bars_add_up(xml)
        self.assertEqual((control["overfull"], control["short"]), (0, 0))

    def test_the_length_is_the_FILES_not_a_default_four(self):
        """The 2.79 failure mode: a whole rest sized to a meter other than
        the one written at that bar. In 2/4 the bar is 2 quarters, not 4."""
        xml, _rep = SX.to_musicxml(_two_system_page(
            [("restWhole", dict(UNFLAGGED_WHOLE))], meter_on_second=False))
        div = int(ET.fromstring(xml).find(".//divisions").text)
        self.assertNotEqual(
            int(_second_bar(xml).find("note/duration").text), 4 * div)

    def test_a_system_that_DECLARES_its_meter_gets_the_same_answer(self):
        xml, rep = SX.to_musicxml(_two_system_page(
            [("restWhole", dict(UNFLAGGED_WHOLE))], meter_on_second=True))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)
        self.assertEqual(_second_bar(xml).find("note/rest").get("measure"), "yes")
        self.assertEqual(
            rep["written"]["measure_rests_sized_by_a_carried_meter"], 0)

    def test_no_meter_in_force_stays_as_it_was(self):
        """Never an invented meter: a part that has declared no `<time>`
        sizes nothing and asserts no `measure="yes"` (rule 8)."""
        page = _one_staff_page(notes=[], meter=None)
        _add_rest(page, 0, "restWhole", dict(UNFLAGGED_WHOLE))
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["written"]["measure_rests_sized_by_the_file_meter"], 0)
        self.assertIsNone(ET.fromstring(xml).find(".//rest").get("measure"))


class TestTheLilyPondPathAgrees(unittest.TestCase):
    def test_the_same_bar_is_not_held_out_in_the_ly_either_RED(self):
        page = _two_system_page(
            [("restWhole", dict(UNFLAGGED_WHOLE))], meter_on_second=False)
        _ly, rep = LY.to_lilypond(page)
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)
        _xml, xrep = SX.to_musicxml(page)
        self.assertEqual(xrep["bars_held_out_sum"]["bars"], 0)


class TestOnlyALoneDotlessWholeRestIsTheBar(unittest.TestCase):
    """The positive controls: each of these must NOT be sized."""

    def test_a_whole_rest_in_a_bar_that_ALSO_holds_notes_is_not_the_bar(self):
        page = _two_system_page([], meter_on_second=False)
        _two = _two_system_page(
            [("restWhole", dict(UNFLAGGED_WHOLE))], meter_on_second=False)
        rec = _two["record"]
        sub = "glyph/0/1/0/0/1"
        rec["observations"] += [
            _obs(5000, sub, Q.GLYPH_BOX,
                 ["noteheadBlackOnLine", 100, 50, 40, 40], category="notehead"),
            _obs(5001, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine")]
        rec["verdicts"] += [_vrd(5002, sub, Q.PITCH, "E4"),
                            _vrd(5003, sub, Q.DURATION, QUARTER)]
        _xml, rep = SX.to_musicxml(_two)
        self.assertEqual(rep["written"]["measure_rests_sized_by_the_file_meter"], 0)
        self.assertEqual(rep["written"].get("measure_rests_read", 0), 0)
        del page

    def test_a_lone_HALF_rest_is_not_the_bar(self):
        xml, rep = SX.to_musicxml(_two_system_page(
            [("restHalf", {"beats": 2.0, "written": 2.0, "dots": 0,
                           "is_rest": True})], meter_on_second=False))
        self.assertEqual(rep["written"]["measure_rests_sized_by_the_file_meter"], 0)
        self.assertIsNone(_second_bar(xml).find("note/rest").get("measure"))

    def test_a_lone_DOTTED_whole_rest_is_not_the_bar(self):
        _xml, rep = SX.to_musicxml(_two_system_page(
            [("restWhole", {"beats": 6.0, "written": 4.0, "dots": 1,
                            "is_rest": True})], meter_on_second=False))
        self.assertEqual(rep["written"]["measure_rests_sized_by_the_file_meter"], 0)

    def test_the_helper_refuses_two_events(self):
        ev = {"kind": "rest", "duration_beats": 4.0, "dots": 0,
              "rest": {"class": "restWhole"}}
        self.assertIsNone(SX._lone_whole_rest_is_the_bar([ev, ev], TWO_FOUR))
        self.assertIsNotNone(SX._lone_whole_rest_is_the_bar([ev], TWO_FOUR))
        self.assertIsNone(SX._lone_whole_rest_is_the_bar([ev], None))

    def test_an_already_marked_measure_rest_is_left_to_the_equality(self):
        """EVALUATE's own sizing (2.79) stays the one `_bar_holds_out`
        judges: a wrong-length marked rest is still held, not re-sized."""
        ev = {"kind": "rest", "duration_beats": 4.5, "dots": 0,
              "rest": {"class": "restWhole", "measure_rest": True}}
        self.assertIsNone(SX._lone_whole_rest_is_the_bar([ev], TWO_FOUR))


# ─────────────────────────────────────────────────────────────────────────────
# PART 2 -- EVALUATE: a second box on the rest's own ink does not make it two
# ─────────────────────────────────────────────────────────────────────────────

CELL = R.cell(0, 0, 1, 3)


def _v(log, sub, q, outcome, value, reason="t", detail=None):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome,
        value=value, decider="test", reason=reason, detail=detail or {}))


def _box(log, sub, bbox):
    log.observe(sub, Q.GLYPH_BOX, ["x", 0, 0, 1, 1], reader=READERS.DETECTOR,
                frame="cell:3", score=0.9, bbox_page_px=list(bbox))


def _rest(log, g=0, bbox=(100.0, 200.0, 124.0, 211.0)):
    sub = R.glyph(0, 0, 1, 3, g)
    _box(log, sub, bbox)
    _v(log, sub, Q.DURATION, Outcome.DECIDED, dict(UNFLAGGED_WHOLE),
       reason="rest_class", detail={"rest": "restWhole"})
    return sub


def _head(log, g, bbox, *, whole_rest_ink):
    sub = R.glyph(0, 0, 1, 3, g)
    _box(log, sub, bbox)
    _v(log, sub, Q.DURATION, Outcome.DECIDED,
       {"beats": 1.0, "written": 1.0, "dots": 0}, reason="head_and_marks")
    if whole_rest_ink is not None:
        _v(log, sub, Q.NOTEHEAD_IS_A_WHOLE_REST, Outcome.DECIDED,
           whole_rest_ink, reason="outline_and_slot")
    return sub


def _meter(log):
    return _v(log, R.system(0, 0), Q.METER, Outcome.DECIDED,
              {"numerator": 2, "denominator": 4, "raw": "2/4"})


def _fire(log, meter):
    return consequences.size_measure_rest(log, CELL, meter)


class TestASecondBoxOnTheRestsOwnInk(unittest.TestCase):
    def test_a_twin_decided_whole_rest_ink_is_set_aside_RED(self):
        log = Log()
        rest = _rest(log)
        twin = _head(log, 1, (100.5, 199.5, 124.5, 211.0),
                     whole_rest_ink=True)
        out = _fire(log, _meter(log))
        self.assertEqual(len(out), 1)
        now = log.verdict(Q.DURATION, rest)
        self.assertTrue(now.value["measure_rest"])
        self.assertEqual(now.value["beats"], 2.0)
        self.assertIn(twin.to_key(), now.detail["set_aside"])

    def test_a_head_elsewhere_in_the_bar_keeps_it_unsized(self):
        """Positive control: the same verdict on a box that is NOT on the
        rest's ink is another thing in the bar (Litolff (16,0,0,14))."""
        log = Log()
        _rest(log)
        _head(log, 1, (400.0, 300.0, 424.0, 311.0), whole_rest_ink=True)
        self.assertEqual(_fire(log, _meter(log)), [])

    def test_a_real_head_on_the_same_spot_keeps_it_unsized(self):
        """No whole-rest verdict (or a False one) = a note we cannot rule out."""
        for verdict in (None, False):
            log = Log()
            _rest(log)
            _head(log, 1, (100.5, 199.5, 124.5, 211.0),
                  whole_rest_ink=verdict)
            self.assertEqual(_fire(log, _meter(log)), [], verdict)

    def test_an_ABSTAINED_whole_rest_verdict_does_not_set_it_aside(self):
        log = Log()
        _rest(log)
        twin = _head(log, 1, (100.5, 199.5, 124.5, 211.0),
                     whole_rest_ink=None)
        _v(log, twin, Q.NOTEHEAD_IS_A_WHOLE_REST, Outcome.ABSTAINED, None,
           reason="no_evidence")
        self.assertEqual(_fire(log, _meter(log)), [])

    def test_with_the_exporters_refusal_OFF_the_box_is_a_note_and_stands(self):
        import os
        os.environ["OMR_WHOLE_REST_INK"] = "0"
        try:
            log = Log()
            _rest(log)
            _head(log, 1, (100.5, 199.5, 124.5, 211.0), whole_rest_ink=True)
            self.assertEqual(_fire(log, _meter(log)), [])
        finally:
            del os.environ["OMR_WHOLE_REST_INK"]

    def test_a_real_head_beside_the_twin_still_blocks(self):
        log = Log()
        _rest(log)
        _head(log, 1, (100.5, 199.5, 124.5, 211.0), whole_rest_ink=True)
        _head(log, 2, (300.0, 150.0, 324.0, 161.0), whole_rest_ink=None)
        self.assertEqual(_fire(log, _meter(log)), [])


if __name__ == "__main__":
    unittest.main()
