"""The staged exporter: does it write the file, and does it ACCOUNT for what
it did not write.

⚠️ These are "is this stage working" tests, not better-or-worse tests. Each
asserts a paid-for POSITION from `tools/omr/export.py`, or the accounting
property that makes the staged path different from the legacy one.
"""

import json
import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import export as SX
from tools.omr.staged.record import Q


def _log_json(observations, verdicts, abstentions=()):
    return {"record": {"observations": list(observations),
                       "verdicts": list(verdicts),
                       "abstentions": list(abstentions),
                       "counts": {}},
            "summary": {}}


def _obs(i, subject, quantity, value, **detail):
    return {"id": f"obs:{i:06d}", "subject": subject, "quantity": quantity,
            "value": value, "reader": "detector", "frame": "cell:0",
            "score": 0.9, "detail": detail, "basis": []}


def _vrd(i, subject, quantity, value, outcome="decided", reason="x",
         candidates=()):
    return {"id": f"vrd:{i:06d}", "subject": subject, "quantity": quantity,
            "outcome": outcome, "value": value, "decider": "t",
            "reason": reason, "considered": [], "used": [], "missing": [],
            "declined": [], "excluded": [], "correlated": [],
            "candidates": list(candidates), "basis": [], "margin": None,
            "supersedes": None, "detail": {}}


def _add_rest(page, gi, cls, dur):
    """A rest glyph plus its decided duration, in the shape gather emits."""
    sub = f"glyph/0/0/0/0/{gi}"
    page["record"]["observations"].append(
        _obs(600 + gi, sub, Q.GLYPH_BOX, [cls, 300, 50, 20, 30],
             category="rest"))
    page["record"]["observations"].append(
        _obs(700 + gi, sub, Q.REST, cls, category="rest"))
    page["record"]["verdicts"].append(_vrd(800 + gi, sub, Q.DURATION, dur))
    return page


def _one_staff_page(*, notes, meter=None, clef="treble", n_measures=1):
    """A one-staff, one-system page carrying `notes` = [(pos, pitch, dur)]."""
    obs, vrd = [], []
    n = 0
    for gi, (pitch, dur) in enumerate(notes):
        sub = f"glyph/0/0/0/0/{gi}"
        obs.append(_obs(n, sub, Q.GLYPH_BOX,
                        ["noteheadBlackOnLine", 100 * gi, 50, 40, 40],
                        category="notehead"))
        n += 1
        obs.append(_obs(n, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine"))
        n += 1
        if pitch is not None:
            vrd.append(_vrd(n, sub, Q.PITCH, pitch))
            n += 1
        if dur is not None:
            vrd.append(_vrd(n, sub, Q.DURATION, dur))
        else:
            vrd.append(_vrd(n, sub, Q.DURATION, None, outcome="narrowed",
                            reason="beams_ambiguous",
                            candidates=[{"value": {"written": 0.5}, "support": 2.0},
                                        {"value": {"written": 0.25}, "support": 2.0}]))
        n += 1
    vrd.append(_vrd(900, "staff/0/0/0", Q.MEASURE_PARTITION, n_measures))
    vrd.append(_vrd(901, "staff/0/0/0", Q.CLEF, clef))
    vrd.append(_vrd(902, "system/0/0", Q.SYSTEM_STAFF_COUNT, 1))
    vrd.append(_vrd(903, "document", Q.PART_PARTITION,
                    {"join": "ordinal", "staves_per_system": 1},
                    reason="ordinal"))
    if meter is not None:
        vrd.append(_vrd(904, "system/0/0", Q.METER, meter))
    return _log_json(obs, vrd)


QUARTER = {"beats": 1.0, "written": 1.0, "dots": 0}


class TestItWritesAFile(unittest.TestCase):
    def test_a_page_becomes_parseable_musicxml(self):
        xml, _ = SX.to_musicxml(_one_staff_page(notes=[("C4", QUARTER)]))
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, "score-partwise")
        self.assertEqual(len(root.findall("part")), 1)
        self.assertEqual(
            root.find(".//note/pitch/step").text, "C")

    def test_a_bar_with_no_events_is_PADDED_and_counted_as_such(self):
        """⚠️ `empty_bars_padded`, NOT `measure_rests_read`. We read NOTHING
        in this bar; a bar where a whole rest was actually read is a different
        fact, and conflating them reports a page as full of measure rests when
        what it is full of is unread bars."""
        xml, rep = SX.to_musicxml(_one_staff_page(notes=[], n_measures=2))
        self.assertEqual(rep["written"]["empty_bars_padded"], 2)
        self.assertEqual(rep["written"].get("measure_rests_read", 0), 0)
        self.assertEqual(len(ET.fromstring(xml).findall(".//rest")), 2)


class TestThePaidForPositions(unittest.TestCase):
    def test_measure_yes_is_withheld_when_the_meter_is_unknown(self):
        """⚠️ `_measure_rest_beats` falls back to 4.0 with no meter, so
        asserting `measure="yes"` on a page whose meter we never read is a
        guess dressed as a fact."""
        xml, rep = SX.to_musicxml(_one_staff_page(notes=[], n_measures=1))
        self.assertEqual(rep["written"]["empty_bars_padded_without_meter"], 1)
        self.assertIsNone(ET.fromstring(xml).find(".//rest").get("measure"))

    def test_measure_yes_IS_written_when_the_meter_is_known(self):
        xml, rep = SX.to_musicxml(_one_staff_page(
            notes=[], n_measures=1,
            meter={"numerator": 2, "denominator": 4, "raw": "2/4"}))
        self.assertEqual(
            rep["written"].get("empty_bars_padded_without_meter", 0), 0)
        self.assertEqual(ET.fromstring(xml).find(".//rest").get("measure"), "yes")

    def test_divisions_is_an_LCM_so_a_triplet_is_exact(self):
        """⚠️ The power-of-two ladder returns 16 and 16 thirds is not a whole
        number, so every triplet would round short. The LCM of powers of two
        IS their maximum, so plain music gets the same number."""
        plain = _one_staff_page(notes=[("C4", QUARTER)])
        _, rep = SX.to_musicxml(plain)
        self.assertEqual(rep["written"]["divisions"], 4)

        third = dict(QUARTER, beats=1.0 / 3.0)
        _, rep3 = SX.to_musicxml(_one_staff_page(notes=[("C4", third)]))
        self.assertEqual(rep3["written"]["divisions"] % 3, 0)

    def test_the_symbol_comes_from_the_matched_LETTER_and_not_from_the_numbers(self):
        """⚠️ `4/4` and a common-time `C` are one bar length and two
        engravings. The staged `raw` is the template reader's matched glyph,
        so it IS evidence — unlike the legacy `_propagated_meter` `raw`, which
        is synthesised."""
        letter = SX._meter_dict({"numerator": 4, "denominator": 4, "raw": "C"})
        digits = SX._meter_dict({"numerator": 4, "denominator": 4, "raw": "4/4"})
        self.assertEqual(letter.get("symbol"), "common")
        self.assertIsNone(digits.get("symbol"))
        self.assertEqual(
            SX._meter_dict({"numerator": 2, "denominator": 2,
                            "raw": "C|"}).get("symbol"), "cut")

    def test_a_note_with_no_pitch_is_not_defaulted_to_treble(self):
        """A staff whose clef abstained produces no pitches; the exporter must
        not undo that by inventing one."""
        xml, rep = SX.to_musicxml(_one_staff_page(notes=[(None, QUARTER)]))
        self.assertEqual(rep["notes_not_written"]["no_pitch"], 1)
        self.assertEqual(ET.fromstring(xml).findall(".//pitch"), [])


class TestTheExporterDoesNotDecide(unittest.TestCase):
    def test_a_NARROWED_duration_is_dropped_and_counted_never_collapsed(self):
        """⚠️ The candidates carry `support`, so an argmax is one line away —
        and it would overturn, in the exporter and silently, a decision
        `adjudicate_duration` explicitly declined to make."""
        xml, rep = SX.to_musicxml(_one_staff_page(notes=[("C4", None)]))
        self.assertEqual(rep["notes_not_written"]["duration_narrowed"], 1)
        self.assertEqual(rep["written"].get("notes", 0), 0)
        self.assertEqual(ET.fromstring(xml).findall(".//pitch"), [])


class TestTheAccountingControl(unittest.TestCase):
    def test_every_notehead_is_either_written_or_counted(self):
        _, rep = SX.to_musicxml(_one_staff_page(
            notes=[("C4", QUARTER), ("D4", None), (None, QUARTER)]))
        b = rep["balance"]
        self.assertEqual(b["noteheads_in_log"], 3)
        self.assertEqual(b["events_written"] + b["events_not_written"], 3)
        self.assertTrue(b["balanced"])

    def test_RESTS_are_inside_the_control_too(self):
        """⚠️ They were outside it while they had no quantity, which is
        exactly how 838 glyphs stayed invisible: a balance that does not count
        a family cannot be unbalanced by losing one."""
        page = _one_staff_page(notes=[("C4", QUARTER)])
        _add_rest(page, 5, "restQuarter", {"beats": 1.0, "written": 1.0,
                                           "dots": 0, "is_rest": True})
        _, rep = SX.to_musicxml(page)
        b = rep["balance"]
        self.assertEqual(b["rests_in_log"], 1)
        self.assertEqual(b["events_in_log"], 2)
        self.assertEqual(b["events_written"], 2)
        self.assertTrue(b["balanced"])

    def test_an_unbalanced_export_RAISES_rather_than_reporting_a_flag(self):
        """⚠️ `symbol_ledger.coverage_check` computed exactly this control,
        reported `balanced=False` on 9 of 20 rows, and was read by nothing."""
        page = _one_staff_page(notes=[("C4", QUARTER)])
        original = SX._place_notes

        def swallow(rec, runs):
            original(rec, runs)
            for run in runs.values():
                run.cells.clear()
            return {}                       # ... and count nothing

        SX._place_notes = swallow
        try:
            with self.assertRaises(SX.Unbalanced):
                SX.to_musicxml(page)
        finally:
            SX._place_notes = original


class TestCoverageNamesTheFourZEROS(unittest.TestCase):
    def test_a_family_with_NO_QUANTITY_is_named_and_its_ink_counted(self):
        """⚠️ THE FINDING THIS MODULE EXISTS TO SURFACE, still live for
        fermatas and ornaments: a family nobody has decided exists, with the
        detector's own count of it beside the zero. **Rests were the worst
        case and are no longer in it** — `Q.REST` landed 2026-09-09 — which is
        why this test moved to a family that still has none rather than being
        deleted."""
        page = _one_staff_page(notes=[("C4", QUARTER)])
        page["record"]["observations"].append(
            _obs(500, "glyph/0/0/0/0/9", Q.GLYPH_BOX,
                 ["fermataAbove", 10, 10, 20, 20], category="ornament"))
        rep = SX.coverage(page)
        f = next(r for r in rep["families"] if r["family"] == "fermata")
        self.assertEqual(f["status"], "NO_QUANTITY")
        self.assertIsNone(f["quantity"])
        self.assertEqual(f["detector_glyphs"], 1)
        self.assertEqual(rep["detected_and_unrepresented"]["fermata"], 1)

    def test_rests_are_NO_LONGER_a_NO_QUANTITY_family(self):
        """The gap this file recorded on 2026-09-09 morning, closed the same
        day. A closed gap must leave the list, or the report stops describing
        the pipeline and starts describing its history."""
        rep = SX.coverage(_one_staff_page(notes=[("C4", QUARTER)]))
        rest = next(r for r in rep["families"] if r["family"] == "rest")
        self.assertEqual(rest["quantity"], Q.REST)
        self.assertNotEqual(rest["status"], "NO_QUANTITY")

    def test_a_starved_stub_is_reported_apart_from_a_plain_stub(self):
        """⚠️ `starved` means the adjudicator is a stub AND its input is never
        gathered — two pieces of work wearing one name. Five stubs were in
        that state until the gather site landed; the report must still be able
        to say it, so this asserts the DISTINCTION rather than a census."""
        page = _one_staff_page(notes=[("C4", QUARTER)])
        rep = SX.coverage(page)
        by = {r["family"]: r for r in rep["families"]}
        self.assertEqual(by["slur"]["status"], "stub",
                         "arc_box is gathered now: this is a plain stub")
        self.assertEqual(by["direction"]["status"], "stub")
        # and the mechanism that reports `starved` still works
        import tools.omr.staged.inventory as inv
        sites, indirect = inv._gather_sites()
        self.assertIn(Q.ARC_BOX, sites)

    def test_a_family_that_came_out_is_not_listed_as_missing(self):
        rep = SX.coverage(_one_staff_page(notes=[("C4", QUARTER)]))
        by = {r["family"]: r for r in rep["families"]}
        self.assertEqual(by["note"]["status"], "emitted")
        self.assertNotIn("note", rep["detected_and_unrepresented"])


class TestThePartJoinIsTheVERDICTS(unittest.TestCase):
    def test_the_ordinal_join_makes_one_part_per_slot_across_systems(self):
        obs, vrd = [], []
        for sysi in (0, 1):
            for st in (0, 1):
                vrd.append(_vrd(len(vrd), f"staff/0/{sysi}/{st}",
                                Q.MEASURE_PARTITION, 2))
                vrd.append(_vrd(len(vrd) + 100, f"staff/0/{sysi}/{st}",
                                Q.CLEF, "treble"))
            vrd.append(_vrd(len(vrd) + 200, f"system/0/{sysi}",
                            Q.SYSTEM_STAFF_COUNT, 2))
        vrd.append(_vrd(999, "document", Q.PART_PARTITION,
                        {"join": "ordinal", "staves_per_system": 2},
                        reason="ordinal"))
        _, rep = SX.to_musicxml(_log_json(obs, vrd))
        self.assertEqual(rep["part_join"]["join_used"], "ordinal")
        self.assertEqual(rep["written"]["parts"], 2)

    def test_a_slot_join_verdict_is_HONOURED_not_second_guessed(self):
        """⚠️ The slot join is measured wrong on 3 of 27 staves on one page,
        and that is not a licence for the exporter to override it. An exporter
        that quietly disagrees with a decision is how a measured judgement
        goes missing."""
        obs, vrd = [], []
        # two systems, DIFFERENT staff counts -- the ordinal join refuses
        for sysi, n in ((0, 2), (1, 1)):
            for st in range(n):
                vrd.append(_vrd(len(vrd), f"staff/0/{sysi}/{st}",
                                Q.MEASURE_PARTITION, 1))
                vrd.append(_vrd(len(vrd) + 100, f"staff/0/{sysi}/{st}",
                                Q.SLOT_INDEX, st))
            vrd.append(_vrd(len(vrd) + 300, f"system/0/{sysi}",
                            Q.SYSTEM_STAFF_COUNT, n))
        vrd.append(_vrd(999, "document", Q.PART_PARTITION,
                        {"join": "slot", "slots": [0, 1]}, reason="slot"))
        _, rep = SX.to_musicxml(_log_json(obs, vrd))
        self.assertEqual(rep["part_join"]["join_used"], "slot")
        self.assertEqual(rep["written"]["parts"], 2)   # not 3 fragments
        self.assertFalse(rep["part_join"]["fragmented"])

    def test_a_deduced_anchor_falls_back_to_FRAGMENTS_and_says_so(self):
        vrd = []
        for sysi, n in ((0, 2), (1, 1)):
            for st in range(n):
                vrd.append(_vrd(len(vrd), f"staff/0/{sysi}/{st}",
                                Q.MEASURE_PARTITION, 1))
            vrd.append(_vrd(len(vrd) + 300, f"system/0/{sysi}",
                            Q.SYSTEM_STAFF_COUNT, n))
        vrd.append(_vrd(999, "document", Q.PART_PARTITION,
                        {"join": "ordinal", "reason": "slots_unusable"},
                        reason="deduced_anchor"))
        _, rep = SX.to_musicxml(_log_json([], vrd))
        self.assertEqual(rep["part_join"]["join_used"], "fragments")
        self.assertTrue(rep["part_join"]["fragmented"])
        self.assertEqual(rep["written"]["parts"], 3)


class TestTuplets(unittest.TestCase):
    def test_only_the_ratios_OWN_MEMBERS_are_scaled(self):
        """⚠️ A tuplet is a fact of a GROUP inside the bar, not of the bar.
        Scaling every note in the cell would shorten every untupleted note in
        it by a third."""
        page = _one_staff_page(notes=[("C4", QUARTER), ("D4", QUARTER)])
        page["record"]["verdicts"].append(_vrd(
            777, "cell/0/0/0/0", Q.TUPLET_RATIO,
            {"actual": 3, "normal": 2, "members": [0]}, reason="digit"))
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["written"]["tuplet_notes"], 1)
        self.assertEqual(len(ET.fromstring(xml).findall(".//time-modification")), 1)

    def test_the_written_TYPE_survives_the_ratio(self):
        """A triplet's noteheads are ORDINARY eighths: the ratio scales the
        TIME and `<type>` keeps the printed value."""
        eighth = {"beats": 0.5, "written": 0.5, "dots": 0}
        page = _one_staff_page(notes=[("C4", eighth)])
        page["record"]["verdicts"].append(_vrd(
            777, "cell/0/0/0/0", Q.TUPLET_RATIO,
            {"actual": 3, "normal": 2, "members": [0]}, reason="digit"))
        xml, _ = SX.to_musicxml(page)
        note = ET.fromstring(xml).find(".//note")
        self.assertEqual(note.find("type").text, "eighth")
        self.assertEqual(note.find("time-modification/actual-notes").text, "3")


class TestDots(unittest.TestCase):
    def test_the_dot_is_one_fact_not_two(self):
        """⚠️ Summing the type's prefix and the dot count wrote a
        DOUBLE-dotted quarter for every single-dotted one -- 82 edits on one
        fixture. `max`, not `+`."""
        dotted = {"beats": 1.5, "written": 1.5, "dots": 1}
        xml, _ = SX.to_musicxml(_one_staff_page(notes=[("C4", dotted)]))
        note = ET.fromstring(xml).find(".//note")
        self.assertEqual(note.find("type").text, "quarter")
        self.assertEqual(len(note.findall("dot")), 1)


if __name__ == "__main__":
    unittest.main()


class TestTheStandingVerdict(unittest.TestCase):
    """⚠️ `supersedes` resolved the way `record.Log.verdict` resolves it, not
    by a second spelling of the rule. A consequence RESTATES values —
    `move_glyph` re-pitches a glyph whose owner changed — so exporting the
    first row would ship what a later decision overturned."""

    def test_a_superseded_pitch_does_not_reach_the_file(self):
        page = _one_staff_page(notes=[("C4", QUARTER)])
        first = next(v for v in page["record"]["verdicts"]
                     if v["quantity"] == Q.PITCH)
        later = dict(first, id="vrd:999999", value="G5",
                     supersedes=first["id"], reason="moved")
        page["record"]["verdicts"].append(later)
        xml, _ = SX.to_musicxml(page)
        self.assertEqual(ET.fromstring(xml).find(".//note/pitch/step").text, "G")

    def test_the_superseding_row_is_the_one_kept_even_out_of_order(self):
        """If every row for a key was superseded, the last still stands rather
        than the value vanishing."""
        page = _one_staff_page(notes=[("C4", QUARTER)])
        first = next(v for v in page["record"]["verdicts"]
                     if v["quantity"] == Q.PITCH)
        first["supersedes"] = "vrd:000000"
        xml, _ = SX.to_musicxml(page)
        self.assertEqual(ET.fromstring(xml).find(".//note/pitch/step").text, "C")


class TestRestsReachTheFile(unittest.TestCase):
    """⚠️ 838 rest glyphs over four real pages reached `GLYPH_BOX` and nothing
    else until `Q.REST` landed on 2026-09-09. These assert the whole chain:
    the gathered class, the decided duration, and the element."""

    def test_an_ordinary_rest_is_written_with_its_value(self):
        page = _one_staff_page(notes=[("C4", QUARTER)])
        _add_rest(page, 5, "rest8th",
                  {"beats": 0.5, "written": 0.5, "dots": 0, "is_rest": True})
        xml, rep = SX.to_musicxml(page)
        root = ET.fromstring(xml)
        rests = root.findall(".//note/rest")
        self.assertEqual(len(rests), 1)
        self.assertIsNone(rests[0].get("measure"))
        self.assertEqual(rep["written"]["rests"], 1)
        note = [n for n in root.findall(".//note") if n.find("rest") is not None][0]
        self.assertEqual(note.find("type").text, "eighth")

    def test_a_MEASURE_rest_carries_measure_yes_and_NO_type(self):
        """⚠️ The two go together. The glyph stands for the BAR, so there is
        no note value to name — `<rest measure="yes"/>` and no `<type>`."""
        page = _one_staff_page(
            notes=[], meter={"numerator": 2, "denominator": 4, "raw": "2/4"})
        _add_rest(page, 5, "restWhole",
                  {"beats": 2.0, "written": 2.0, "dots": 0, "is_rest": True,
                   "measure_rest": True})
        xml, rep = SX.to_musicxml(page)
        root = ET.fromstring(xml)
        rest = root.find(".//note/rest")
        self.assertEqual(rest.get("measure"), "yes")
        note = root.find(".//note")
        self.assertIsNone(note.find("type"))
        self.assertEqual(rep["written"]["measure_rests_read"], 1)

    def test_a_measure_rest_is_exportable_where_the_bar_reduces_to_no_value(self):
        """⚠️ A bar length of 5/4 reduces to no single (possibly dotted) note
        value, and demanding one would refuse the bar the convention exists
        for. The same number on a NOTE is still refused."""
        page = _one_staff_page(
            notes=[], meter={"numerator": 5, "denominator": 4, "raw": "5/4"})
        _add_rest(page, 5, "restWhole",
                  {"beats": 5.0, "written": 5.0, "dots": 0, "is_rest": True,
                   "measure_rest": True})
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["written"]["measure_rests_read"], 1)
        self.assertEqual(rep["notes_not_written_total"], 0)
        self.assertEqual(
            ET.fromstring(xml).find(".//note/duration").text, "20")

    def test_a_rest_is_never_asked_for_a_pitch(self):
        """Requiring one is what kept rests out of the file for as long as
        they had no quantity; asking now would keep them out for a second,
        subtler reason."""
        page = _one_staff_page(notes=[])
        _add_rest(page, 5, "restQuarter",
                  {"beats": 1.0, "written": 1.0, "dots": 0, "is_rest": True})
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["notes_not_written"].get("no_pitch", 0), 0)
        self.assertEqual(ET.fromstring(xml).findall(".//pitch"), [])
        self.assertEqual(rep["written"]["rests"], 1)

    def test_an_UNREADABLE_rest_is_dropped_and_counted_as_a_REST(self):
        """`restHBar` names no single value, so `adjudicate_duration` abstains
        — and the shortfall is reported under its own key rather than folded
        in with the notes."""
        page = _one_staff_page(notes=[])
        sub = "glyph/0/0/0/0/5"
        page["record"]["observations"].append(
            _obs(601, sub, Q.GLYPH_BOX, ["restHBar", 300, 50, 20, 30],
                 category="rest"))
        page["record"]["observations"].append(
            _obs(701, sub, Q.REST, "restHBar", category="rest"))
        page["record"]["verdicts"].append(
            _vrd(801, sub, Q.DURATION, None, outcome="abstained",
                 reason="unreadable_rest"))
        _, rep = SX.to_musicxml(page)
        self.assertEqual(rep["notes_not_written"]["rest_duration_abstained"], 1)
        self.assertTrue(rep["balance"]["balanced"])
