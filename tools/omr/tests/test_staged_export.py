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


class TestNothingDetectedGoesUnaccounted(unittest.TestCase):
    """⚠️ DERIVED, so it cannot go stale by anyone forgetting a class. The
    families claim what they claim, `NOT_NOTATION` excuses the rest WITH A
    WRITTEN REASON, and whatever is left is reported by name and count.

    A DENY-list, not an allow-list, and the direction is the point: the
    default for a class nobody has thought about is *reported*, not *silently
    unchecked*. `export_coverage`'s hand-written `VISIBLE` allow-list was
    blind to fifteen elements including the tenth export gap."""

    def test_a_class_no_family_claims_is_reported_by_name(self):
        page = _one_staff_page(notes=[("C4", QUARTER)])
        page["record"]["observations"].append(
            _obs(900, "glyph/0/0/0/0/9", Q.GLYPH_BOX,
                 ["someGlyphNobodyThoughtAbout", 1, 1, 2, 2]))
        rep = SX.coverage(page)
        self.assertEqual(rep["unclaimed_classes"],
                         {"someGlyphNobodyThoughtAbout": 1})

    def test_a_family_class_is_not_reported_as_unclaimed(self):
        page = _one_staff_page(notes=[("C4", QUARTER)])
        _add_rest(page, 5, "restWhole", {"beats": 4.0, "written": 4.0,
                                         "dots": 0, "is_rest": True})
        self.assertEqual(SX.coverage(page)["unclaimed_classes"], {})

    def test_an_EXCUSED_class_is_silent_and_says_why(self):
        page = _one_staff_page(notes=[("C4", QUARTER)])
        for i, cls in enumerate(("beam", "ledgerLine", "flag8thUp", "staff")):
            page["record"]["observations"].append(
                _obs(910 + i, f"glyph/0/0/0/0/{20 + i}", Q.GLYPH_BOX,
                     [cls, 1, 1, 2, 2]))
        self.assertEqual(SX.coverage(page)["unclaimed_classes"], {})
        for cls in ("beam", "ledgerLine", "flag", "staff"):
            self.assertTrue(SX.NOT_NOTATION[cls].strip(),
                            f"{cls} is excused with no reason")

    def test_every_excuse_names_a_reason(self):
        for cls, why in SX.NOT_NOTATION.items():
            self.assertTrue(why and why.strip(), cls)


class TestTheMeterIsReadPerBARNotPerRUN(unittest.TestCase):
    """⚠️⚠️ `Q.METER`'s `segments` REACHED NO FILE. `_part_xml` took
    `_meter_dict(run.meter)` once per staff-run and used that one meter for
    every bar of it, so a printed mid-system meter change could not be
    exported at all — and `record.meter_at`, whose own docstring says it *is*
    how a bar's meter is read, was called by nothing but its own tests.

    Measured on the boundary benchmark's engraved Brahms 1 iv: the `¢` sits on
    the record at `from_cell 6` with `staves_reading_it` = all 24 and support
    74.0, and before this the file declared `<time>` exactly once per part,
    `4/4 symbol="common"`, at measure 1.
    """

    def _page(self, segments, n_measures=4):
        return _one_staff_page(
            notes=[], n_measures=n_measures,
            meter={"numerator": segments[0]["numerator"],
                   "denominator": segments[0]["denominator"],
                   "raw": segments[0]["raw"], "segments": segments})

    def _times(self, xml):
        root = ET.fromstring(xml)
        out = []
        for m in root.iter("measure"):
            at = m.find("attributes")
            t = at.find("time") if at is not None else None
            if t is not None:
                out.append((m.get("number"),
                            f"{t.findtext('beats')}/{t.findtext('beat-type')}",
                            t.get("symbol")))
        return out

    def _run(self, page, on):
        import os
        prev = os.environ.get(SX.METER_SEGMENTS_ENV)
        # ⚠️ BOTH ARMS SET THE VARIABLE EXPLICITLY, including the off one.
        # Popping it used to mean "off" and now means "on" — the default
        # flipped on 2026-09-09 — so an arm that relies on absence silently
        # measures the other arm. This is the same trap `run_arms.py` avoids by
        # handing subprocess an environment dict with both flags set.
        os.environ[SX.METER_SEGMENTS_ENV] = "1" if on else "0"
        try:
            return SX.to_musicxml(page)
        finally:
            if prev is None:
                os.environ.pop(SX.METER_SEGMENTS_ENV, None)
            else:
                os.environ[SX.METER_SEGMENTS_ENV] = prev

    def _export(self, page, on):
        return self._run(page, on)[0]

    SEGS = [{"from_cell": 0, "numerator": 3, "denominator": 4, "raw": "3/4"},
            {"from_cell": 2, "numerator": 4, "denominator": 4, "raw": "C"}]

    def test_the_change_reaches_the_file_at_the_BAR_it_is_printed_on(self):
        times = self._times(self._export(self._page(self.SEGS), on=True))
        self.assertEqual(times, [("1", "3/4", None), ("3", "4/4", "common")])

    def test_flag_OFF_is_the_old_behaviour_exactly(self):
        """⚠️ The control every new mechanism here needs: off, only the
        system's opening is declared and it is declared once."""
        times = self._times(self._export(self._page(self.SEGS), on=False))
        self.assertEqual(times, [("1", "3/4", None)])

    def test_a_system_with_ONE_segment_is_byte_identical_either_way(self):
        """A page that prints no change must not move at all — which is what
        makes the flag's blast radius exactly 'pages with a read change'."""
        page = self._page([{"from_cell": 0, "numerator": 2,
                            "denominator": 4, "raw": "2/4"}])
        self.assertEqual(self._export(page, on=False),
                         self._export(page, on=True))

    def test_a_bar_NO_segment_covers_gets_no_time_rather_than_the_next_one(self):
        """⚠️ `meter_at` RETURNS None THERE, AND THAT IS A REAL ANSWER. A
        system can print a change at bar 2 while never stating what bars 0-1
        were in — *unknown until then, 3/4 from there* is exactly what a
        range-scoped fact can say. Inheriting the meter that FOLLOWS would
        assert a bar length the page never states, and the measure-rest
        arithmetic would then be a guess dressed as a fact.

        Measured on Litolff p.61-62: the printed `3/4` moved from measure 8,
        the first bar of its system, to measure 16 — its ninth, where the
        hand-read truth puts it.
        """
        page = self._page([{"from_cell": 2, "numerator": 3,
                            "denominator": 4, "raw": "3/4"}])
        xml, rep = self._run(page, on=True)
        self.assertEqual(self._times(xml), [("3", "3/4", None)])
        # ⚠️ and the bars BEFORE it are padded without a meter, not with the
        # one that follows them
        self.assertEqual(rep["written"].get(
            "empty_bars_padded_without_meter"), 2)
        # the control: flag off, every bar inherits the opening and none is
        # padded meterless
        _, off = self._run(page, on=False)
        self.assertEqual(off["written"].get(
            "empty_bars_padded_without_meter", 0), 0)


class TestTheMeterSegmentsFlagIsONByDefault(unittest.TestCase):
    """⚠️ Sean's call, 2026-09-09. The default is a DECISION and belongs in a
    test, not only in a docstring — this repo has had a flag site's docstring
    carry a refuted claim for a day after CLAUDE.md was corrected.

    ⚠️ AND THE `0` ESCAPE IS PART OF THE DECISION. Flipping a default without
    a working way back is not a default, it is a removal.
    """

    def setUp(self):
        import os
        self._prev = os.environ.get(SX.METER_SEGMENTS_ENV)
        os.environ.pop(SX.METER_SEGMENTS_ENV, None)

    def tearDown(self):
        import os
        if self._prev is None:
            os.environ.pop(SX.METER_SEGMENTS_ENV, None)
        else:
            os.environ[SX.METER_SEGMENTS_ENV] = self._prev

    def test_absent_means_ON(self):
        self.assertTrue(SX.meter_segments_enabled())

    def test_an_explicit_zero_still_turns_it_off(self):
        import os
        for off in ("0", "off", "false", "no", ""):
            os.environ[SX.METER_SEGMENTS_ENV] = off
            self.assertFalse(SX.meter_segments_enabled(), off)

    def test_a_typo_does_not_silently_disable_it(self):
        """⚠️ THE ASYMMETRY IS DELIBERATE AND IT REVERSED WITH THE DEFAULT.
        While it was off, `_carry_meter`'s rule applied — anything but an
        explicit "1" is off, so a typo could not switch a document ONTO a
        mechanism. On by default the hazard runs the other way: a typo must
        not switch it OFF and quietly restore the bug.

        ⚠️ `""` IS NOT A TYPO HERE, it is an off word — the repo's existing
        idiom for a `"1"`-defaulted flag (`OMR_LEFT_EDGE_SPLIT`,
        `OMR_DIRECTION_TEXT`), and what `test_roster.py::test_flag_parsing`
        pins. Whether an empty value SHOULD mean off is a real question this
        does not settle; what it declines to do is fork a third convention."""
        import os
        for typo in ("yess", "1 1", "ON!", "tru", "0x0"):
            os.environ[SX.METER_SEGMENTS_ENV] = typo
            self.assertTrue(SX.meter_segments_enabled(), repr(typo))


class TestADecidedDynamicREACHESTheFile(unittest.TestCase):
    """⚠️ THE GAP THIS CLASS EXISTS FOR: `adjudicate_dynamic` stopped being a
    stub on 2026-09-09, decides, files a verdict per cell — and
    `grep '<dynamics' staged/export.py` returned ZERO, as did the same grep
    for every other `<notations>` / `<direction>` child. *The value existed
    and nothing read it*, inside the architecture built to stop it.

    ⚠️ AND THE COVERAGE HEADLINE MOVED THE WRONG WAY WHILE IT WAS BROKEN.
    `detected_and_unrepresented_total` counts only NO_QUANTITY / starved /
    stub, so the family LEFT the headline the day it started deciding, with
    nothing reaching a file. `decided_but_unwritten` is the status that
    carried it, and the last test here pins that it is reachable.
    """

    def _page_with(self, words, *, notes, x_page=310.0, n_measures=1):
        page = _one_staff_page(notes=notes, n_measures=n_measures)
        page["record"]["verdicts"].append(_vrd(
            950, "cell/0/0/0/0", Q.DYNAMIC, list(words), reason="spelled"))
        page["record"]["verdicts"][-1]["detail"] = {
            "words": [{"text": w, "spelled": True, "x_page": x_page + 40 * i}
                      for i, w in enumerate(words)]}
        return page

    def test_a_bar_WITH_notes_carries_its_dynamic(self):
        xml, rep = SX.to_musicxml(
            self._page_with(["ff"], notes=[("C4", QUARTER)]))
        self.assertIn("<dynamics><ff/></dynamics>", xml.replace("\n", "")
                      .replace("      ", "").replace("  ", ""))
        self.assertEqual(rep["written"]["dynamics"], 1)

    def test_a_bar_with_NO_notes_still_carries_its_marks(self):
        """The legacy exporter dropped dynamics on exactly this branch for a
        month, and it takes a SCAN to see it — an engraved page puts an event
        in every bar. The staged path is fed the marks from the start."""
        xml, rep = SX.to_musicxml(self._page_with(["p"], notes=[]))
        self.assertIn("<dynamics>", xml)
        self.assertIn("<p/>", xml)
        self.assertEqual(rep["written"]["dynamics"], 1)

    def test_the_direction_precedes_the_note(self):
        """MusicXML orders `<direction>` before the `<note>`s it governs, and
        a `<direction>` carries no duration so offset 0 is legal."""
        xml, _ = SX.to_musicxml(
            self._page_with(["mf"], notes=[("C4", QUARTER)]))
        self.assertLess(xml.index("<direction "), xml.index("<note>"))

    def test_marks_come_out_in_x_ORDER_within_the_bar(self):
        xml, _ = SX.to_musicxml(
            self._page_with(["p", "f"], notes=[("C4", QUARTER)], x_page=100.0))
        self.assertLess(xml.index("<p/>"), xml.index("<f/>"))

    def test_a_NARROWED_dynamic_writes_NOTHING(self):
        """⚠️ `OMR_PARTIAL_DYNAMICS` was built, measured over the 20-row scan
        gate and REFUSED: +15 edits with NOT ONE ROW BETTER. An unspellable
        run is not `decided`, so it must not reach the file on this path
        either — the refusal is inherited, not re-litigated."""
        page = _one_staff_page(notes=[("C4", QUARTER)])
        page["record"]["verdicts"].append(_vrd(
            951, "cell/0/0/0/0", Q.DYNAMIC, None, outcome="narrowed",
            reason="unspellable",
            candidates=[{"value": "sf", "support": 1.0},
                        {"value": "sfz", "support": 1.0}]))
        xml, rep = SX.to_musicxml(page)
        self.assertNotIn("<dynamics>", xml)
        self.assertEqual(rep["written"].get("dynamics", 0), 0)

    def test_a_dynamic_verdict_is_NOT_counted_in_the_note_balance(self):
        """The accounting control counts noteheads and rests. A direction is
        neither, and folding it in would make a correct export unbalanced."""
        _, rep = SX.to_musicxml(
            self._page_with(["ff"], notes=[("C4", QUARTER)]))
        self.assertTrue(rep["balance"]["balanced"])
        self.assertEqual(rep["balance"]["events_written"], 1)


class TestTheHairpinsAreNotCountedTwice(unittest.TestCase):
    """⚠️ `dynamicCrescendoHairpin` starts with `dynamic`, so a plain prefix
    test let the `dynamic` family AND the `wedge` family both claim it — and
    where both were unrepresented the headline charged the same ink twice.
    `gather_glyph_families` is routed by CLASS "never by the detector's
    `category`" for exactly this glyph; the coverage table had the fault that
    finding exists to prevent, one module over.
    """

    def test_a_hairpin_belongs_to_wedge_and_NOT_to_dynamic(self):
        self.assertTrue(SX._claims("wedge", "dynamicCrescendoHairpin"))
        self.assertFalse(SX._claims("dynamic", "dynamicCrescendoHairpin"))

    def test_a_plain_letter_still_belongs_to_dynamic(self):
        self.assertTrue(SX._claims("dynamic", "dynamicForte"))
        self.assertFalse(SX._claims("wedge", "dynamicForte"))

    def test_no_class_is_claimed_by_two_families(self):
        """The property, not the instance — derived, so a future overlapping
        family resolves the same way with no hand-written exclusion."""
        for cls in ("dynamicCrescendoHairpin", "dynamicDiminuendoHairpin",
                    "dynamicForte", "dynamicPiano", "restWhole",
                    "noteheadBlackOnLine", "timeSig4", "tuplet3"):
            owners = [f for f in SX.FAMILIES if SX._claims(f, cls)]
            self.assertLessEqual(len(owners), 1, f"{cls} claimed by {owners}")


class TestTheStatusThatNamesAnExportGapCanActuallyFIRE(unittest.TestCase):
    """⚠️⚠️ `decided_but_unwritten` was UNREACHABLE from the day it was
    written until 2026-09-09. The branch order was

        elif decided:                      -> "decided"
        elif written is not None:          -> "decided_but_unwritten" if decided

    so the third branch consumed every decided family and the fourth could
    only ever see `decided == 0`. The guard sat on a dead branch, and a
    decision that decided and reached NO file was reported as `decided`,
    which reads like success.

    Found by the controlled A/B for the dynamics wiring, not by review: the
    BEFORE arm wrote zero `<dynamics>` and still reported
    `decided_but_unwritten: []`. *A check that cannot fail is worse than no
    check.*
    """

    def _decided_dynamic_page(self):
        page = _one_staff_page(notes=[("C4", QUARTER)])
        page["record"]["observations"].append(
            _obs(980, "glyph/0/0/0/0/9", Q.GLYPH_BOX,
                 ["dynamicForte", 300, 90, 20, 20], category="dynamic"))
        page["record"]["verdicts"].append(_vrd(
            981, "cell/0/0/0/0", Q.DYNAMIC, ["f"], reason="spelled"))
        page["record"]["verdicts"][-1]["detail"] = {
            "words": [{"text": "f", "spelled": True, "x_page": 300.0}]}
        return page

    def test_a_family_that_DECIDED_and_wrote_nothing_says_so(self):
        """The direct reachability proof: hold the verdict, withhold the
        exporter's counter, and the status must name the gap."""
        page = self._decided_dynamic_page()
        rep = SX.coverage(page, written={"notes": 1})     # no `dynamics` key
        row = next(r for r in rep["families"] if r["family"] == "dynamic")
        self.assertEqual(row["status"], "decided_but_unwritten")
        self.assertIn("dynamic", rep["decided_and_unwritten"])
        self.assertEqual(rep["decided_and_unwritten_total"], 1)

    def test_the_same_family_that_DID_write_reads_emitted(self):
        page = self._decided_dynamic_page()
        rep = SX.coverage(page, written={"notes": 1, "dynamics": 1})
        row = next(r for r in rep["families"] if r["family"] == "dynamic")
        self.assertEqual(row["status"], "emitted")
        self.assertEqual(rep["decided_and_unwritten_total"], 0)

    def test_a_family_with_NO_counter_is_not_called_a_success(self):
        """⚠️ An unmeasurable family must not read as a measured one.

        ⚠️ NO SHIPPED FAMILY REACHES THIS STATE TODAY, and the first draft of
        this test asserted it of `slur` and failed with `stub != decided_
        uncounted` — a stub is reported as a stub, correctly, before any of
        this. So the branch is exercised by REMOVING `dynamic`'s counter,
        which is exactly the shipped state of that family until this session.
        It becomes live for real at the next step: an `arc_kind` that stops
        being a stub with no counter added lands here rather than reading as
        a success."""
        page = self._decided_dynamic_page()
        original = SX.FAMILIES["dynamic"]
        SX.FAMILIES["dynamic"] = (original[0], original[1], ())
        try:
            rep = SX.coverage(page, written={"notes": 1})
        finally:
            SX.FAMILIES["dynamic"] = original
        row = next(r for r in rep["families"] if r["family"] == "dynamic")
        self.assertEqual(row["status"], "decided_uncounted")
        self.assertIn("dynamic", rep["decided_uncounted"])
        # and it is NOT counted as an export gap -- we do not know that it is
        self.assertNotIn("dynamic", rep["decided_and_unwritten"])

    def test_the_two_headlines_measure_DIFFERENT_faults(self):
        """A record gap (no quantity / stub) and an export gap (decided and
        unwritten) need different repairs, so they are counted apart. This is
        why the first headline FELL by ~284 glyphs on beet5-p3 the day
        `dynamic` stopped being a stub with nothing reaching a file."""
        page = self._decided_dynamic_page()
        rep = SX.coverage(page, written={"notes": 1})
        self.assertNotIn("dynamic", rep["detected_and_unrepresented"])
        self.assertIn("dynamic", rep["decided_and_unwritten"])
