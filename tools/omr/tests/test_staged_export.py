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
        ornaments: a family nobody has decided exists, with the detector's own
        count of it beside the zero. **It has now moved TWICE** — off `rest`
        when `Q.REST` landed 2026-09-09, and off `fermata` when
        `Q.FERMATA_OWNER` landed 2026-09-10 — and each move is the right
        outcome: a closed gap must leave the list, or the report stops
        describing the pipeline and starts describing its history.

        ⚠️ Counted by CLASS. `ornamentTrill` carries the detector's `ornament`
        CATEGORY, which it shares with all ten `artic*` classes and with
        `fermata*`; counting by category reported 300 ornaments on a page
        holding none."""
        page = _one_staff_page(notes=[("C4", QUARTER)])
        page["record"]["observations"].append(
            _obs(500, "glyph/0/0/0/0/9", Q.GLYPH_BOX,
                 ["ornamentTrill", 10, 10, 20, 20], category="ornament"))
        rep = SX.coverage(page)
        f = next(r for r in rep["families"] if r["family"] == "ornament")
        self.assertEqual(f["status"], "NO_QUANTITY")
        self.assertIsNone(f["quantity"])
        self.assertEqual(f["detector_glyphs"], 1)
        self.assertEqual(rep["detected_and_unrepresented"]["ornament"], 1)

    def test_the_quantityless_families_are_DECLARED_so_the_next_one_is_loud(self):
        """⚠️ DERIVED, so a family that quietly loses its quantity fails here
        rather than dropping out of the headline. The set shrinks as the
        wiring pass runs; it must never grow silently."""
        blank = {fam for fam, (q, _c, _ct) in SX.FAMILIES.items() if q is None}
        self.assertEqual(blank, {"ornament"}, blank)

    def test_rests_are_NO_LONGER_a_NO_QUANTITY_family(self):
        """The gap this file recorded on 2026-09-09 morning, closed the same
        day. A closed gap must leave the list, or the report stops describing
        the pipeline and starts describing its history."""
        rep = SX.coverage(_one_staff_page(notes=[("C4", QUARTER)]))
        rest = next(r for r in rep["families"] if r["family"] == "rest")
        self.assertEqual(rest["quantity"], Q.REST)
        self.assertNotEqual(rest["status"], "NO_QUANTITY")

    def test_fermatas_are_NO_LONGER_a_NO_QUANTITY_family(self):
        """Closed 2026-09-10, and named here for the same reason rests are."""
        rep = SX.coverage(_one_staff_page(notes=[("C4", QUARTER)]))
        f = next(r for r in rep["families"] if r["family"] == "fermata")
        self.assertEqual(f["quantity"], Q.FERMATA_OWNER)
        self.assertNotEqual(f["status"], "NO_QUANTITY")

    def test_a_starved_stub_is_reported_apart_from_a_plain_stub(self):
        """⚠️ `starved` means the adjudicator is a stub AND its input is never
        gathered — two pieces of work wearing one name. Five stubs were in
        that state until the gather site landed; the report must still be able
        to say it, so this asserts the DISTINCTION rather than a census."""
        page = _one_staff_page(notes=[("C4", QUARTER)])
        rep = SX.coverage(page)
        by = {r["family"]: r for r in rep["families"]}
        # ⚠️ THE PLAIN-STUB EXEMPLAR HAS CHANGED TWICE AND THE TEST HAS NOT.
        # `slur` left this census on 2026-09-09 when `arc_kind` stopped being a
        # stub; `articulation` left it on 2026-09-10 when
        # `articulation_owner` did. `wedge` is the plain-stub case now and
        # `direction` is still the starved one. Asserting the DISTINCTION,
        # never a census — which is why each of those took a one-line edit
        # here rather than a rewrite.
        self.assertEqual(by["wedge"]["status"], "stub",
                         "wedge_box is gathered: a plain stub")
        # ⚠️ `direction` reports `stub`, NOT `starved`, and the two tools
        # disagree about it on purpose-by-accident: `coverage()` calls a
        # quantity fed when a gather SITE exists, and `Q.DIRECTION_WORD` has
        # one that only ever ABSTAINS (`gather_coverage`'s "abstain-only"
        # category). So a rung that runs and reads nothing is "gathered" here
        # and "starved" there. Asserted as it IS rather than as it reads,
        # with the divergence named — an undocumented disagreement between
        # two derived inventories is how one of them quietly stops being
        # believed.
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


class TestAFamilyCannotLeaveEVERYBucket(unittest.TestCase):
    """⚠️ RAISED BY THE METER/BOUNDARY SESSION AGAINST THIS FIX, and it was
    right. Both headlines are status FILTERS, and a filter cannot say where a
    family went: `dynamic` left `detected_and_unrepresented` silently the day
    it stopped being a stub, and adding a second filtered headline reproduces
    that surprise one level up.

    The census is a PARTITION, so a family that leaves one bucket must appear
    in another.
    """

    def _rep(self, **written):
        page = _one_staff_page(notes=[("C4", QUARTER)])
        page["record"]["observations"].append(
            _obs(970, "glyph/0/0/0/0/9", Q.GLYPH_BOX,
                 ["dynamicForte", 300, 90, 20, 20], category="dynamic"))
        page["record"]["verdicts"].append(_vrd(
            971, "cell/0/0/0/0", Q.DYNAMIC, ["f"], reason="spelled"))
        page["record"]["verdicts"][-1]["detail"] = {
            "words": [{"text": "f", "spelled": True, "x_page": 300.0}]}
        return SX.coverage(page, written=dict(written))

    def test_every_family_is_filed_exactly_once(self):
        rep = self._rep(notes=1)
        c = rep["status_census"]
        self.assertTrue(c["balanced"])
        self.assertEqual(c["n_filed"], c["n_families"])
        self.assertEqual(c["n_families"], len(SX.FAMILIES))

    def test_nothing_lands_in_UNACCOUNTED(self):
        """⚠️ The escape hatch must always be empty. A status invented later
        and belonging to no headline shows up HERE rather than nowhere — the
        same inversion `NOT_NOTATION` uses, where the default for something
        nobody thought about is *reported*."""
        self.assertEqual(self._rep(notes=1)["status_census"]["unaccounted"], [])

    def test_a_family_that_CHANGES_bucket_is_still_filed(self):
        """The exact motion that started this: `dynamic` moves from
        `decided_but_unwritten` to `emitted` when the exporter writes it. It
        must be visible in the census on BOTH sides, never absent from one."""
        before = self._rep(notes=1)["status_census"]
        after = self._rep(notes=1, dynamics=1)["status_census"]
        self.assertIn("dynamic", before["decided_but_unwritten"])
        self.assertNotIn("dynamic", before["emitted"])
        self.assertIn("dynamic", after["emitted"])
        self.assertNotIn("dynamic", after["decided_but_unwritten"])
        for c in (before, after):
            self.assertTrue(c["balanced"])

    def test_an_UNKNOWN_status_is_filed_once_not_twice(self):
        """⚠️ The first draft double-counted it — `setdefault` into
        `unaccounted` and then an `if` that appended again — so `n_filed`
        over-counted and `balanced` would have gone False for the wrong
        reason. A balance check that lies is worse than none."""
        rows = [{"family": "made_up", "status": "a_status_nobody_declared"},
                {"family": "note", "status": "emitted"}]
        c = SX._census(rows)
        self.assertEqual(c["unaccounted"], ["made_up"])
        self.assertEqual(c["n_filed"], 2)
        self.assertTrue(c["balanced"])


class TestTheDotIsONEFactUnderALiveDurationReader(unittest.TestCase):
    """⚠️ FLAGGED BY THE DURATION-READER SESSION: `adjudicate_duration` gained
    flag/dot attachment, so `Q.DURATION` verdicts now carry `dots` where ZERO
    did before — 156 on a 3-page engraved fixture. This exporter reads
    `max(dur["dots"], derived_dots)`, so a path that was dead is now live
    under it.

    The `max` is the paid-for rule — summing them wrote a double-dotted
    quarter for every single-dotted one, 82 edits on one fixture — and it is
    only SAFE while `written` already encodes the dot. Verified on a fresh run
    of Beethoven 5 p3 after the merge: **0 disagreements over 865 decided
    durations** between `dots` and what `written` implies. ⚠️ Only 1 of those
    865 carried a dot at all, because the detector fires ~35 dots over 2347
    noteheads on a scan against 157 over 1118 on an engraving — so that run is
    a weak exercise of the path and these tests are the real guard.
    """

    def _one(self, written, dots):
        page = _one_staff_page(
            notes=[("C4", {"beats": written, "written": written, "dots": dots})])
        xml, _ = SX.to_musicxml(page)
        return xml

    def test_a_dotted_value_is_not_double_dotted(self):
        """written=1.5 implies one dot AND the verdict says one dot: `max`
        must give ONE, never two."""
        xml = self._one(1.5, 1)
        self.assertEqual(xml.count("<dot/>"), 1)

    def test_a_verdict_dot_on_an_undotted_written_value_still_writes_one(self):
        """`max` takes the verdict's dot even where the arithmetic implies
        none — that is what makes it a `max` and not an `and`."""
        self.assertEqual(self._one(1.0, 1).count("<dot/>"), 1)

    def test_no_dots_anywhere_is_still_no_dots(self):
        self.assertEqual(self._one(1.0, 0).count("<dot/>"), 0)

    def test_the_exporter_takes_MAX_and_not_a_SUM(self):
        """Anti-drift on the 82-edit lesson: a sum would write two."""
        import inspect
        src = inspect.getsource(SX._place_notes)
        self.assertIn('max(int(dur.get("dots") or 0), derived_dots)', src)


# ─────────────────────────────────────────────────────────────────────────────
# Arcs — decided for a day with no route to a file
# ─────────────────────────────────────────────────────────────────────────────

#: ⚠️ NOT ZERO, AND THAT IS THE POINT. A page box in CORNERS `[x0,y0,x1,y1]`
#: and a detection box in WIDTH form `[x,y,w,h]` are INDISTINGUISHABLE when
#: x0 == 0 and y0 == 0, because then `x1 == w` and `y1 == h`. This project has
#: already paid for that confusion once (the CV hairpin reader's fixture), so
#: every fixture here is offset well away from the origin and the two
#: spellings disagree in every coordinate.
PX, PY = 1000.0, 400.0

CELL_W, CELL_H = 500.0, 120.0
SPACE = 10.0


def _arc_page(*, arcs, n_measures=1, kinds=None, gap=0.0, chord_on=None):
    """A one-staff part whose bars carry `arcs`, each `(cell, x0, x1)`.

    Boxes are PAGE pixels: cell `m` spans `PX + m*(CELL_W+gap)` to that plus
    `CELL_W`, so `gap` opens a real space between two bars and `gap=0` makes
    them abut, which is what a barline looks like to the merge.
    """
    kinds = kinds or {}
    obs, vrd = [], []
    n = 0
    gi = 0

    def cell_x0(m):
        return PX + m * (CELL_W + gap)

    for m in range(n_measures):
        x0 = cell_x0(m)
        obs.append(_obs(n, f"cell/0/0/0/{m}", Q.CELL_BOX,
                        [x0, PY, x0 + CELL_W, PY + CELL_H]))
        n += 1
        # four notes across the bar, in page pixels AND canonically
        for k in range(4):
            hx = x0 + 60 + k * 110
            sub = f"glyph/0/0/0/{m}/{gi}"
            obs.append(_obs(n, sub, Q.GLYPH_BOX,
                            ["noteheadBlackOnLine", 60 + k * 110, 50, 30, 26],
                            category="notehead",
                            bbox_page_px=[hx, PY + 50, hx + 30, PY + 76]))
            n += 1
            obs.append(_obs(n, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine"))
            n += 1
            vrd.append(_vrd(n, sub, Q.PITCH, "CDEF"[k] + "4"))
            n += 1
            vrd.append(_vrd(n, sub, Q.DURATION, QUARTER))
            n += 1
            gi += 1
            if chord_on is not None and (m, k) == chord_on:
                # a SECOND head in the same column: one chord, two <note>s
                sub2 = f"glyph/0/0/0/{m}/{gi}"
                head2 = ["noteheadBlackOnLine", 60 + k * 110, 70, 30, 26]
                obs.append(_obs(n, sub2, Q.GLYPH_BOX, head2,
                                category="notehead",
                                bbox_page_px=[hx, PY + 70, hx + 30, PY + 96]))
                n += 1
                obs.append(_obs(n, sub2, Q.NOTEHEAD_CLASS, head2[0]))
                n += 1
                vrd.append(_vrd(n, sub2, Q.PITCH, "A5"))
                n += 1
                vrd.append(_vrd(n, sub2, Q.DURATION, QUARTER))
                n += 1
                gi += 1

    for a, (m, ax0, ax1) in enumerate(arcs):
        sub = f"glyph/0/0/0/{m}/{500 + a}"
        x0 = cell_x0(m)
        box = [x0 + ax0, PY + 20, x0 + ax1, PY + 40]
        obs.append(_obs(n, sub, Q.ARC_BOX, "slur", category="slur",
                        bbox_page_px=box))
        n += 1
        vrd.append(_vrd(n, sub, Q.ARC_KIND, kinds.get(a, "slur")))
        n += 1
        vrd.append(_vrd(n, sub, Q.ARC_OWNER, "staff/0/0/0"))
        n += 1

    obs.append(_obs(n, "staff/0/0/0", Q.STAFF_SPACING, SPACE))
    n += 1
    obs.append(_obs(n, "staff/0/0/0", Q.STAFF_LINES,
                    [PY + 40, PY + 50, PY + 60, PY + 70, PY + 80]))
    n += 1
    vrd.append(_vrd(900, "staff/0/0/0", Q.MEASURE_PARTITION, n_measures))
    vrd.append(_vrd(901, "staff/0/0/0", Q.CLEF, "treble"))
    vrd.append(_vrd(902, "system/0/0", Q.SYSTEM_STAFF_COUNT, 1))
    vrd.append(_vrd(903, "document", Q.PART_PARTITION,
                    {"join": "ordinal", "staves_per_system": 1},
                    reason="ordinal"))
    return _log_json(obs, vrd)


class TestArcsReachTheFile(unittest.TestCase):
    """⚠️⚠️ `arc_kind` AND `arc_owner` DECIDED 199 ARCS A PAGE AND
    `grep '<slur' staged/export.py` RETURNED ZERO. The value existed and
    nothing read it -- inside the architecture built to stop exactly that,
    and one day after the same shape was found and fixed for the dynamics.
    """

    def test_a_slur_over_two_notes_writes_one_span(self):
        xml, rep = SX.to_musicxml(_arc_page(arcs=[(0, 50, 190)]))
        self.assertEqual(xml.count('<slur '), 2)
        self.assertIn('<slur number="1" type="start"/>', xml)
        self.assertIn('<slur number="1" type="stop"/>', xml)
        self.assertEqual(rep["written"]["slurs"], 1)

    def test_a_tie_writes_tied_and_NOT_a_slur(self):
        """A tie carries no `number=` -- it names its two notes and there is
        nothing to allocate."""
        xml, rep = SX.to_musicxml(
            _arc_page(arcs=[(0, 50, 190)], kinds={0: "tie"}))
        self.assertEqual(xml.count('<slur '), 0)
        self.assertIn('<tied type="start"/>', xml)
        self.assertIn('<tied type="stop"/>', xml)
        self.assertEqual(rep["written"]["ties"], 1)
        self.assertEqual(rep["written"].get("slurs", 0), 0)

    def test_the_file_still_parses(self):
        xml, _ = SX.to_musicxml(_arc_page(arcs=[(0, 50, 190)]))
        ET.fromstring(xml)

    def test_a_page_with_no_arcs_writes_none(self):
        """The positive control: a battery that only ever asserts a slur IS
        written passes by writing slurs everywhere."""
        xml, rep = SX.to_musicxml(_arc_page(arcs=[]))
        self.assertEqual(xml.count('<slur '), 0)
        self.assertEqual(rep["written"].get("slurs", 0), 0)


class TestTheBarlineDoesNotMakeTwoSlurs(unittest.TestCase):
    """⚠️⚠️ CELLS ARE CUT PER MEASURE, SO AN ARC CROSSING A BARLINE IS
    DETECTED AS TWO -- 32 of 199 arcs on one real page (16.1%) begin at their
    cell's left edge. Emitting each half as its own `<slur>` writes TWO where
    the music has ONE, which is what kept an implemented and tested
    `annotate_slurs` out of the legacy exporter until 2026-09-01.

    ⚠️ AND OMR-NED WOULD NOT HAVE CAUGHT IT: the metric is symmetric, so
    emitting MORE symbols is rewarded, and the legacy slur work's first cut
    LOWERED pooled OMR-NED while RAISING the edit count. Only a test can hold
    this.
    """

    #: an arc running to its cell's right edge, and one resuming at the next
    #: cell's left edge, at the same height -- the cross-barline signature.
    HALVES = [(0, 300, CELL_W), (1, 0, 200)]

    def test_two_halves_at_the_edges_become_ONE_slur(self):
        xml, rep = SX.to_musicxml(
            _arc_page(arcs=self.HALVES, n_measures=2))
        self.assertEqual(rep["written"]["slurs"], 1)
        self.assertEqual(xml.count('<slur '), 2)      # one start, one stop

    def test_it_starts_in_bar_1_and_stops_in_bar_2(self):
        """A merged slur is only merged if its ends land in DIFFERENT bars;
        counting one span would also pass if both ends collapsed into one."""
        xml, _ = SX.to_musicxml(_arc_page(arcs=self.HALVES, n_measures=2))
        root = ET.fromstring(xml)
        bars = root.findall(".//measure")
        starts = [i for i, m in enumerate(bars)
                  if m.findall('.//slur[@type="start"]')]
        stops = [i for i, m in enumerate(bars)
                 if m.findall('.//slur[@type="stop"]')]
        self.assertEqual((starts, stops), ([0], [1]))

    def test_two_arcs_NOT_at_the_edges_stay_TWO_slurs(self):
        """The control that makes the merge a reading rather than a rule that
        joins whatever it finds: same two bars, same two arcs, moved off the
        boundary."""
        _xml, rep = SX.to_musicxml(
            _arc_page(arcs=[(0, 60, 180), (1, 60, 180)], n_measures=2))
        self.assertEqual(rep["written"]["slurs"], 2)

    def test_halves_at_DIFFERENT_heights_stay_two(self):
        """`_SLUR_CONTINUATION_DY_SPACES` is 2.0 staff spaces, and it is doing
        work here: two arcs meeting at a barline are one curve only if they
        meet at the same HEIGHT."""
        page = _arc_page(arcs=self.HALVES, n_measures=2)
        for o in page["record"]["observations"]:
            if o["quantity"] == Q.ARC_BOX and o["subject"].endswith("/501"):
                b = o["detail"]["bbox_page_px"]
                o["detail"]["bbox_page_px"] = [b[0], b[1] + SPACE * 6,
                                               b[2], b[3] + SPACE * 6]
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["written"]["slurs"], 2)


class TestAnArcGoesWhereItsOWNERSays(unittest.TestCase):
    """⚠️ THE OWNER, NOT THE SUBJECT -- and for an arc the stakes are higher
    than for a notehead. Where two staves sit far apart the upper cell reaches
    ink the lower does not, so an arc can exist ONLY in the wrong staff and no
    duplicate rule can see the contest. Brahms 1's Timpani exported 4 slurs
    and 1 tie against a truth of ZERO, all of them Violin 1's.
    """

    def test_an_arc_owned_elsewhere_does_not_reach_this_part(self):
        page = _arc_page(arcs=[(0, 50, 190)])
        for v in page["record"]["verdicts"]:
            if v["quantity"] == Q.ARC_OWNER:
                v["value"] = "staff/0/0/9"        # a staff with no measures
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(xml.count('<slur '), 0)
        self.assertEqual(rep["arcs_not_written"],
                         {"arc_owner_staff_has_no_measures": 1})

    def test_an_undecided_kind_is_COUNTED_by_its_reason(self):
        page = _arc_page(arcs=[(0, 50, 190)])
        for v in page["record"]["verdicts"]:
            if v["quantity"] == Q.ARC_KIND:
                v["outcome"], v["value"] = "abstained", None
                v["reason"] = "no_arc_box"
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["arcs_not_written"], {"kind_no_arc_box": 1})

    def test_an_arc_with_NO_PAGE_FRAME_is_refused_not_defaulted(self):
        """⚠️ The merge and the note comparison both happen in page pixels. An
        arc whose page rectangle gather DECLINED must not be placed in the
        canonical frame instead -- that is the fault that made
        `Q.ONSET_COLUMN` report 1,062 columns of nothing."""
        page = _arc_page(arcs=[(0, 50, 190)])
        for o in page["record"]["observations"]:
            if o["quantity"] == Q.ARC_BOX:
                o["detail"].pop("bbox_page_px")
                o["detail"]["frame_note"] = "no page box"
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(xml.count('<slur '), 0)
        self.assertEqual(rep["arcs_not_written"], {"arc_no_page_frame": 1})


class TestTheArcShortfallIsNOTInTheNoteBalance(unittest.TestCase):
    """⚠️⚠️ AN ARC IS NOT A NOTE. `notes_not_written` feeds the accounting
    control -- every notehead and rest in the log is written or counted, and
    the two must sum to the log's own rows. Folding arc drops into it would
    inflate one side by a family the other side does not count, so
    `to_musicxml` would raise `Unbalanced` for a reason that has nothing to do
    with notes: a control reporting a defect it was not built to see.
    """

    def test_a_dropped_arc_leaves_the_note_balance_intact(self):
        page = _arc_page(arcs=[(0, 50, 190)])
        for v in page["record"]["verdicts"]:
            if v["quantity"] == Q.ARC_OWNER:
                v["value"] = "staff/0/0/9"
        _xml, rep = SX.to_musicxml(page)          # must not raise
        self.assertTrue(rep["balance"]["balanced"])
        self.assertEqual(rep["notes_not_written_total"], 0)
        self.assertEqual(rep["arcs_not_written_total"], 1)


def _slurred_pitches(xml):
    """`(start pitches, stop pitches)` — WHICH notes each span binds."""
    root = ET.fromstring(xml)
    out = {"start": [], "stop": []}
    for note in root.findall(".//note"):
        p = note.find("pitch")
        name = ((p.findtext("step") or "") + (p.findtext("octave") or "")
                if p is not None else "rest")
        for sl in note.findall(".//slur"):
            out[sl.get("type")].append(name)
    return out["start"], out["stop"]


class TestASpanBindsTheRIGHTNotes(unittest.TestCase):
    """⚠️⚠️ WRITTEN BECAUSE A MUTATION SURVIVED, and it was the trap this
    module's own comment names. Reading a CORNER box `[x0,y0,x1,y1]` as a
    WIDTH box `[x,y,w,h]` turns a 140px arc into a 1190px one -- and every
    assertion above still passed, because a wider arc still produces exactly
    one span with one start and one stop. **Counting spans cannot see the
    frame error; only naming the NOTES can.**

    ⚠️ The fixture's bars are offset to page x 1000 for the same reason: at
    x0 == 0 the two spellings agree in every coordinate, so a fixture at the
    origin cannot tell them apart either.
    """

    def test_a_slur_binds_only_the_notes_it_COVERS(self):
        # bar 0's four heads sit at page x 1060, 1170, 1280, 1390 (w 30), so
        # their centres are 1075, 1185, 1295, 1405. This arc spans the middle
        # two and neither outer one.
        xml, _ = SX.to_musicxml(_arc_page(arcs=[(0, 160, 310)]))
        self.assertEqual(_slurred_pitches(xml), (["D4"], ["E4"]))

    def test_a_WIDER_arc_binds_more_notes(self):
        """The positive control: the test above must be reading the geometry,
        not just reporting the second and third note of every bar."""
        xml, _ = SX.to_musicxml(_arc_page(arcs=[(0, 160, 420)]))
        self.assertEqual(_slurred_pitches(xml), (["D4"], ["F4"]))

    def test_a_tie_binds_the_right_pair_too(self):
        xml, _ = SX.to_musicxml(
            _arc_page(arcs=[(0, 160, 310)], kinds={0: "tie"}))
        root = ET.fromstring(xml)
        tied = {t.get("type"): n.find("pitch").findtext("step") + "4"
                for n in root.findall(".//note")
                for t in n.findall(".//tied")}
        self.assertEqual(tied, {"start": "D4", "stop": "E4"})


class TestAChordCarriesOneSpanNotFour(unittest.TestCase):
    """⚠️⚠️ ALSO WRITTEN BECAUSE A MUTATION SURVIVED. MusicXML takes a chord's
    FIRST `<note>` as its representative, so a `<slur>` hung off every member
    opens N spans of the same number and closes one -- an unpaired start per
    extra head, which makes the file malformed rather than merely wrong.
    Every test above used single notes, so marking all members passed all of
    them.
    """

    def test_a_slur_starting_on_a_CHORD_marks_one_note(self):
        xml, rep = SX.to_musicxml(
            _arc_page(arcs=[(0, 160, 310)], chord_on=(0, 1)))
        starts, stops = _slurred_pitches(xml)
        self.assertEqual((len(starts), len(stops)), (1, 1))
        self.assertEqual(rep["written"]["slurs"], 1)

    def test_the_chord_really_is_a_chord(self):
        """The positive control: without it, the assertion above would pass on
        a fixture whose second head never became a note at all."""
        xml, _ = SX.to_musicxml(
            _arc_page(arcs=[(0, 160, 310)], chord_on=(0, 1)))
        root = ET.fromstring(xml)
        self.assertEqual(len(root.findall(".//note/chord")), 1)

    def test_a_TIE_on_a_chord_also_marks_one_note(self):
        """⚠️ A THIRD MUTATION SURVIVOR: the slur test above does not cover the
        tie flags, which travel to `_mxl_note` as their own two arguments.

        ⚠️ FIRST NOTE ONLY IS THE LEGACY POSITION, MATCHED RATHER THAN
        RE-DECIDED: `_mxl_voice_events` writes `tied_to_next and ni == 0` with
        the comment "a chord is beamed and slurred once, through its first
        note". Whether a chord's every member ought to carry its own `<tie>`
        is a real question about the convention; it is not one for the STAGED
        exporter to answer differently from the legacy one, because then the
        same record would export two ways depending on which path wrote it.
        """
        xml, _ = SX.to_musicxml(
            _arc_page(arcs=[(0, 160, 310)], kinds={0: "tie"}, chord_on=(0, 1)))
        root = ET.fromstring(xml)
        self.assertEqual(len(root.findall('.//tied[@type="start"]')), 1)
        self.assertEqual(len(root.findall('.//tied[@type="stop"]')), 1)
        self.assertEqual(len(root.findall(".//note/chord")), 1)


class TestNoArcVanishesUNCOUNTED(unittest.TestCase):
    """⚠️⚠️ THE POINT OF AN EXPORT REPORT IS THAT A SHORTFALL IS A NUMBER AND
    NOT A SILENCE. Both of these were live holes in the first cut of this
    pass, and both are the shape this repo keeps paying for: a value computed,
    then dropped on a branch that returns nothing.
    """

    def test_an_arc_binding_too_FEW_notes_is_counted(self):
        """`_paired_spans` refuses a curve covering fewer than two heads --
        one end would leave an unpaired `<slur type="start">` and an INVALID
        file -- and returns only the survivors. On a scan the usual cause is
        that the notes under the arc were never detected."""
        # an arc sitting between two notes, covering neither centre
        xml, rep = SX.to_musicxml(_arc_page(arcs=[(0, 100, 120)]))
        self.assertEqual(xml.count('<slur '), 0)
        self.assertEqual(rep["arcs_not_written"],
                         {"arc_binds_fewer_than_two_notes": 1})

    def test_an_arc_in_a_bar_with_NO_GEOMETRY_is_counted(self):
        """`_merge_arcs_across_barlines` opens each bar with "no box, or no
        spacing, then break the chain and move on" -- correct, there is no
        unit to measure a boundary in -- but its `continue` skips that bar's
        arcs whole."""
        page = _arc_page(arcs=[(0, 50, 190)])
        page["record"]["observations"] = [
            o for o in page["record"]["observations"]
            if o["quantity"] != Q.CELL_BOX]
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(xml.count('<slur '), 0)
        self.assertEqual(rep["arcs_not_written"],
                         {"arc_bar_has_no_geometry": 1})

    def test_every_placed_arc_is_written_or_counted(self):
        """The accounting property itself, over a mixed page -- the control
        that would catch a THIRD hole nobody has thought of yet."""
        page = _arc_page(
            arcs=[(0, 160, 310),       # binds D4..E4
                  (0, 100, 120),       # binds nothing
                  (1, 160, 310)],      # binds D4..E4 of bar 2
            n_measures=2)
        _xml, rep = SX.to_musicxml(page)
        written = rep["written"]["slurs"] + rep["written"].get("ties", 0)
        self.assertEqual(written + rep["arcs_not_written_total"], 3)


def _two_system_page(*, arcs):
    """One part printed on TWO systems, each one bar, each its own staff.

    ⚠️ TWO STAVES, NOT TWO BARS OF ONE. That is what a system break IS: the
    part continues on a different staff object further down the page, and the
    two staves' lines sit at different page y. The merge has to compare a
    resuming arc's height RELATIVE TO EACH STAFF'S OWN TOP LINE, because
    absolute page y differs by a whole system — which is why `tops` exists.
    """
    obs, vrd = [], []
    n, gi = 0, 0
    for sysi in range(2):
        # ⚠️ system 1's staff sits 600px lower on the page. If `tops` were
        # ignored, its arcs would look 600px away from system 0's and nothing
        # would ever join across the break.
        dy = sysi * 600.0
        x0 = PX
        obs.append(_obs(n, f"cell/0/{sysi}/0/0", Q.CELL_BOX,
                        [x0, PY + dy, x0 + CELL_W, PY + dy + CELL_H]))
        n += 1
        for k in range(4):
            hx = x0 + 60 + k * 110
            sub = f"glyph/0/{sysi}/0/0/{gi}"
            obs.append(_obs(n, sub, Q.GLYPH_BOX,
                            ["noteheadBlackOnLine", 60 + k * 110, 50, 30, 26],
                            category="notehead",
                            bbox_page_px=[hx, PY + dy + 50, hx + 30,
                                          PY + dy + 76]))
            n += 1
            obs.append(_obs(n, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine"))
            n += 1
            vrd.append(_vrd(n, sub, Q.PITCH, "CDEF"[k] + str(4 + sysi)))
            n += 1
            vrd.append(_vrd(n, sub, Q.DURATION, QUARTER))
            n += 1
            gi += 1
        obs.append(_obs(n, f"staff/0/{sysi}/0", Q.STAFF_SPACING, SPACE))
        n += 1
        obs.append(_obs(n, f"staff/0/{sysi}/0", Q.STAFF_LINES,
                        [PY + dy + 40, PY + dy + 50, PY + dy + 60,
                         PY + dy + 70, PY + dy + 80]))
        n += 1
        vrd.append(_vrd(900 + sysi, f"staff/0/{sysi}/0",
                        Q.MEASURE_PARTITION, 1))
        vrd.append(_vrd(910 + sysi, f"staff/0/{sysi}/0", Q.CLEF, "treble"))
        vrd.append(_vrd(920 + sysi, f"system/0/{sysi}",
                        Q.SYSTEM_STAFF_COUNT, 1))

    for a, (sysi, ax0, ax1, ady) in enumerate(arcs):
        dy = sysi * 600.0
        sub = f"glyph/0/{sysi}/0/0/{500 + a}"
        obs.append(_obs(n, sub, Q.ARC_BOX, "slur", category="slur",
                        bbox_page_px=[PX + ax0, PY + dy + ady,
                                      PX + ax1, PY + dy + ady + 20]))
        n += 1
        vrd.append(_vrd(n, sub, Q.ARC_KIND, "slur"))
        n += 1
        vrd.append(_vrd(n, sub, Q.ARC_OWNER, f"staff/0/{sysi}/0"))
        n += 1

    vrd.append(_vrd(903, "document", Q.PART_PARTITION,
                    {"join": "ordinal", "staves_per_system": 1},
                    reason="ordinal"))
    return _log_json(obs, vrd)


class TestASlurCrossesASystemBreak(unittest.TestCase):
    """⚠️ THE JUNCTION IS NOT THE BARLINE'S, and `_merge_arcs_across_barlines`
    recognises the two differently. A resuming half after a break begins some
    way INSIDE its cell, because the cell opens with a clef and a key
    signature — so a left-edge test would never fire and the two halves would
    stay two slurs. `_resumes_after_system_break` anchors on the first NOTE
    instead.

    ⚠️ AND THIS IS WHY `_pair_arcs` IS A PART PASS. A part's junction between
    two systems is a junction of ONE PART printed on TWO STAFF OBJECTS, so a
    per-staff pass cannot see it at all.
    """

    def test_two_halves_across_the_break_become_ONE_slur(self):
        # system 0: an arc running out to its cell's right edge.
        # ⚠️ system 1: an arc running IN FROM THE MARGIN AND ENDING ON THE
        # FIRST NOTE (centre 75). That end position is the whole rule, not an
        # incidental of the fixture: a resuming fragment "lies entirely BEFORE
        # that note -- it runs in from the margin and ends on it", while a
        # slur merely BEGINNING on the first note runs the other way. The two
        # are told apart by WHICH SIDE OF THE NOTE the ink is on, so a
        # fixture whose fragment overshoots the note is not a resuming
        # fragment at all -- as the first draft of this test discovered.
        _xml, rep = SX.to_musicxml(_two_system_page(
            arcs=[(0, 300, CELL_W, 20), (1, 0, 78, 20)]))
        self.assertEqual(rep["written"]["slurs"], 1)
        self.assertEqual(rep["arcs_not_written"], {})   # nothing left over

    def test_it_really_spans_the_two_SYSTEMS(self):
        """Counting one span would also pass if both ends collapsed into one
        system — the pitches say which system each end is in, because system 1
        is written an octave up."""
        xml, _ = SX.to_musicxml(_two_system_page(
            arcs=[(0, 300, CELL_W, 20), (1, 0, 78, 20)]))
        starts, stops = _slurred_pitches(xml)
        self.assertEqual([p[-1] for p in starts], ["4"])   # system 0
        self.assertEqual([p[-1] for p in stops], ["5"])    # system 1

    def test_halves_at_DIFFERENT_heights_stay_two(self):
        """⚠️ THE CONTROL THAT PROVES `tops` IS BEING USED. Heights are
        compared RELATIVE to each staff's own top line; if the rule fell back
        to absolute page y, system 1's arc would be 600px away and NOTHING
        would ever join, so this test would pass for the wrong reason and the
        test above would fail. The two together pin it."""
        _xml, rep = SX.to_musicxml(_two_system_page(
            arcs=[(0, 300, CELL_W, 20), (1, 0, 78, 20 + SPACE * 6)]))
        # ⚠️ NOT "two slurs" -- and the first draft asserted that and was
        # wrong. A resuming fragment ENDS ON the first note of its system, so
        # standing alone it binds exactly ONE note and `_paired_spans` refuses
        # it: one end would leave an unpaired `<slur type="start">`. So the
        # unmerged outcome is 1 written + 1 COUNTED, which is a sharper
        # discriminator than a span total anyway -- it separates "the two did
        # not join" from "the second one never existed".
        self.assertEqual(rep["written"]["slurs"], 1)
        self.assertEqual(rep["arcs_not_written"],
                         {"arc_binds_fewer_than_two_notes": 1})

    def test_the_part_really_is_ONE_part(self):
        """The positive control: two systems that failed to join into one part
        would make every assertion above vacuous."""
        _xml, rep = SX.to_musicxml(_two_system_page(arcs=[]))
        self.assertEqual(rep["written"]["parts"], 1)
        self.assertEqual(rep["part_join"]["join_used"], "ordinal")


class TestTheCounterCountsWhatREACHEDTheFile(unittest.TestCase):
    """⚠️⚠️ FOUND ON A REAL PAGE, NOT BY REVIEW: the report said 55 slurs
    where the file held 23. `voicing._chord_span_states` DROPS a span whose
    start and stop landed in the SAME CHORD -- "a slur from a note to itself
    is a curve to nowhere" -- and `_paired_spans` cannot catch those, because
    it refuses two ends on one DETECTION while a chord is several detections
    at one x. 32 of 55 marked spans on Litolff p.2.

    ⚠️ The lesson is the FAMILIES table's own, arriving from a new direction:
    a quantity's verdict says what was DECIDED, and only the exporter's
    counter says what reached the FILE. A counter placed where the mark is SET
    is measuring the first and reporting it as the second.
    """

    def test_a_slur_whose_ends_share_a_CHORD_is_not_counted_as_written(self):
        # one arc covering only the chord column: both ends land in it
        xml, rep = SX.to_musicxml(
            _arc_page(arcs=[(0, 160, 200)], chord_on=(0, 1)))
        self.assertEqual(xml.count('<slur '), 0)
        self.assertEqual(rep["written"].get("slurs", 0), 0)
        self.assertEqual(rep["arcs_not_written"], {"arc_ends_in_one_chord": 1})

    def test_the_arc_really_WAS_marked_first(self):
        """The positive control: without it the assertion above would pass on
        an arc that was refused earlier and never marked at all -- a different
        finding wearing the same number."""
        xml, rep = SX.to_musicxml(
            _arc_page(arcs=[(0, 160, 200)], chord_on=(0, 1)))
        self.assertEqual(rep["written"]["slur_spans_marked"], 1)
        self.assertEqual(len(ET.fromstring(xml).findall(".//note/chord")), 1)

    def test_written_plus_dropped_still_accounts_for_every_arc(self):
        page = _arc_page(arcs=[(0, 160, 310), (0, 100, 120)], chord_on=(0, 1))
        _xml, rep = SX.to_musicxml(page)
        w = rep["written"]
        written = w.get("slurs", 0) + w.get("ties", 0)
        self.assertEqual(written + rep["arcs_not_written_total"], 2)


class TestArticulationsReachTheFile(unittest.TestCase):
    """⚠️ THE ADJUDICATOR AND THE EMISSION LANDED TOGETHER, and this class is
    why. `adjudicate_dynamic` decided for a day with `grep '<dynamics'`
    returning zero; `arc_kind` decided 199 arcs a page with no `<slur>`. Both
    were found by forensics INSIDE the architecture built to stop it. A stub
    whose adjudicator lands alone is a fresh `decided_and_unwritten` row.
    """

    def _page(self, marks, notes=(("C4", QUARTER), ("D4", QUARTER))):
        """`marks` = [(notehead_index, articulation_kind)]."""
        page = _one_staff_page(notes=list(notes), meter={
            "numerator": 4, "denominator": 4, "raw": "4/4"})
        for k, (gi, kind) in enumerate(marks):
            sub = f"glyph/0/0/0/0/{900 + k}"
            page["record"]["observations"].append(
                _obs(900 + k, sub, Q.ARTICULATION_MARK,
                     f"artic{kind.capitalize()}Above", side="above",
                     x0=100 * gi, x1=100 * gi + 6, y0=0, y1=6))
            page["record"]["verdicts"].append(
                _vrd(900 + k, sub, Q.ARTICULATION_OWNER,
                     f"glyph/0/0/0/0/{gi}", reason="nearest_on_declared_side"))
            page["record"]["verdicts"][-1]["detail"] = {"articulation": kind}
        return page

    def test_a_decided_articulation_is_written_onto_its_note(self):
        xml, rep = SX.to_musicxml(self._page([(0, "staccato")]))
        root = ET.fromstring(xml)
        notes = list(root.iter("note"))
        kinds = [[c.tag for c in a]
                 for n in notes
                 for a in n.iter("articulations")]
        self.assertEqual(kinds, [["staccato"]])
        self.assertEqual(rep["written"]["articulations"], 1)

    def test_the_KIND_travels__a_tenuto_is_not_a_staccato(self):
        xml, _ = SX.to_musicxml(self._page([(1, "tenuto")]))
        self.assertIn("<tenuto/>", xml)
        self.assertNotIn("<staccato/>", xml)

    def test_with_no_marks_the_file_is_byte_identical(self):
        """The control: this pass may not touch a page that prints none."""
        a, _ = SX.to_musicxml(self._page([]))
        b, _ = SX.to_musicxml(self._page([]))
        self.assertEqual(a, b)
        self.assertNotIn("<articulations>", a)

    def test_a_mark_whose_note_was_never_written_is_COUNTED(self):
        """⚠️ A shortfall that is not counted is indistinguishable from ink
        that was never read. The owner names a glyph no cell holds."""
        page = self._page([])
        sub = "glyph/0/0/0/0/950"
        page["record"]["observations"].append(
            _obs(950, sub, Q.ARTICULATION_MARK, "articStaccatoAbove",
                 side="above", x0=0, x1=6, y0=0, y1=6))
        page["record"]["verdicts"].append(
            _vrd(950, sub, Q.ARTICULATION_OWNER, "glyph/0/0/0/0/777",
                 reason="nearest_on_declared_side"))
        page["record"]["verdicts"][-1]["detail"] = {"articulation": "staccato"}
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(
            rep["articulations_not_written"].get(
                "artic_owning_notehead_not_written"), 1)
        self.assertTrue(rep["articulation_balance"]["balanced"])

    def test_an_abstained_mark_is_counted_BY_ITS_REASON(self):
        page = self._page([])
        sub = "glyph/0/0/0/0/951"
        page["record"]["observations"].append(
            _obs(951, sub, Q.ARTICULATION_MARK, "articulationStaccato",
                 x0=0, x1=6, y0=0, y1=6))
        page["record"]["verdicts"].append(
            _vrd(951, sub, Q.ARTICULATION_OWNER, None, outcome="abstained",
                 reason="no_side_declared"))
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(
            rep["articulations_not_written"].get("artic_no_side_declared"), 1)

    def test_the_balance_is_a_PARTITION_over_every_gathered_mark(self):
        page = self._page([(0, "staccato"), (1, "accent")])
        _xml, rep = SX.to_musicxml(page)
        b = rep["articulation_balance"]
        self.assertEqual(b["marks_in_log"], b["written"] + b["not_written"])
        self.assertTrue(b["balanced"])

    def test_EVERY_member_of_a_chord_wears_its_own_mark(self):
        """⚠️ NOT the slur rule. A span goes on the chord's FIRST note because
        MusicXML takes it as the chord's representative; an articulation is not
        a span, and hoisting three staccati onto the first note would write one
        dot where the page prints three."""
        page = _one_staff_page(notes=[("C4", QUARTER), ("E4", QUARTER)], meter={
            "numerator": 4, "denominator": 4, "raw": "4/4"})
        # put both heads at the same x so they group as one chord
        for o in page["record"]["observations"]:
            if o["quantity"] == Q.GLYPH_BOX and o["value"][0].startswith("note"):
                o["value"][1] = 100
        for k, gi in enumerate((0, 1)):
            sub = f"glyph/0/0/0/0/{960 + k}"
            page["record"]["observations"].append(
                _obs(960 + k, sub, Q.ARTICULATION_MARK, "articStaccatoAbove",
                     side="above", x0=100, x1=106, y0=0, y1=6))
            page["record"]["verdicts"].append(
                _vrd(960 + k, sub, Q.ARTICULATION_OWNER,
                     f"glyph/0/0/0/0/{gi}", reason="nearest_on_declared_side"))
            page["record"]["verdicts"][-1]["detail"] = {
                "articulation": "staccato"}
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(xml.count("<staccato/>"), 2)
        self.assertEqual(rep["written"]["articulations"], 2)

    def test_the_placement_pass_IS_CALLED(self):
        """⚠️ AN AST CHECK. The whole failure mode this class exists for is a
        pass that runs and a file that does not change, so the call site is
        asserted rather than inferred from a green behavioural test."""
        import inspect
        src = inspect.getsource(SX.build)
        self.assertIn("_place_articulations(rec, runs)", src)

    def test_the_counter_lives_where_the_ELEMENT_is_written(self):
        """⚠️ Not where the mark is ATTACHED. The two numbers differ, and a
        counter at the attach reports the first while claiming the second —
        the arc export reported 55 slurs into a file holding 23.

        ⚠️ DERIVED, not a named function. The first draft asserted the counter
        was in `_part_xml` and failed because the render lives one function
        down in `_measure_events_xml` — and repointing a test at whichever
        function happens to pass is how a test gets named for a hazard it does
        not reach. So: the counter must sit in the SAME function that calls
        `_mxl_note`, whichever that is.
        """
        import ast
        import inspect
        tree = ast.parse(inspect.getsource(SX))
        renders, counts = set(), set()
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            body = ast.dump(fn)
            if "_mxl_note" in body:
                renders.add(fn.name)
            if "'articulations'" in body and "counters" in body:
                counts.add(fn.name)
        self.assertTrue(renders, "nothing calls _mxl_note any more")
        self.assertTrue(
            renders & counts,
            f"the articulation counter is in {counts or 'nowhere'} and the "
            f"note is rendered in {renders}")
        self.assertNotIn(
            'counters["articulations"]',
            inspect.getsource(SX._place_articulations),
            "the counter is at the ATTACH, which reports a different number")


def _add_fermata(page, gi, x, cls="fermataAbove", *, owner_gi=None,
                 outcome="decided", reason="contains_the_mark"):
    """A fermata mark plus its owner verdict, in the shape gather emits."""
    sub = f"glyph/0/0/0/0/{gi}"
    page["record"]["observations"].append(
        _obs(500 + gi, sub, Q.FERMATA_MARK, cls, x0=x, x1=x + 14,
             y0=0, y1=10, side="above"))
    v = _vrd(550 + gi, sub, Q.FERMATA_OWNER,
             None if owner_gi is None else f"glyph/0/0/0/0/{owner_gi}",
             outcome=outcome, reason=reason)
    v["detail"] = {"carrier": "notehead"}
    page["record"]["verdicts"].append(v)
    return page


class TestFermatasReachTheFile(unittest.TestCase):
    """⚠️ THE THIRD LEG. `articulation_owner` established that a stub's
    "one repair" is three -- adjudicator, emission, counter -- and both
    `adjudicate_dynamic` and `arc_kind` decided into no file for a day."""

    def test_a_fermata_on_a_note_is_written_and_counted(self):
        page = _add_fermata(_one_staff_page(notes=[("C4", QUARTER)]),
                            9, 100, owner_gi=0)
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(len(ET.fromstring(xml).findall(".//fermata")), 1)
        self.assertEqual(rep["written"]["fermatas"], 1)

    def test_a_fermata_on_a_REST_is_written(self):
        """⚠️ The commonest carrier on a conductor's page, and the case the
        articulation path structurally cannot reach: `_mxl_note` keeps
        `<fermata>` OUTSIDE the `<articulations>` block for exactly this."""
        page = _one_staff_page(notes=[])
        _add_rest(page, 0, "restWhole", {"beats": 4.0, "written": 4.0,
                                         "dots": 0, "measure_rest": True})
        _add_fermata(page, 9, 300, owner_gi=0)
        xml, rep = SX.to_musicxml(page)
        root = ET.fromstring(xml)
        self.assertEqual(len(root.findall(".//fermata")), 1)
        self.assertIsNotNone(root.find(".//note/rest"))
        self.assertEqual(rep["written"]["fermatas"], 1)

    def test_two_marks_on_ONE_CHORD_write_ONE_fermata(self):
        """⚠️ HOISTED, unlike an articulation. One pause hangs over the whole
        chord, so it goes on the chord's first `<note>`; each member wearing
        its own would print three where the page prints one.

        ⚠️ And the balance must NOT call that a loss -- which is why the
        fermata control is a partition and not an equality.
        """
        page = _one_staff_page(notes=[("C4", QUARTER), ("E4", QUARTER)])
        # Both heads at the same x: `group_chords_in_measure` makes one chord.
        for o in page["record"]["observations"]:
            if o["quantity"] == Q.GLYPH_BOX:
                o["value"][1] = 100
        _add_fermata(page, 9, 100, owner_gi=0)
        _add_fermata(page, 10, 100, owner_gi=1)
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(len(ET.fromstring(xml).findall(".//fermata")), 1)
        self.assertEqual(rep["written"]["fermatas"], 1)
        bal = rep["fermata_balance"]
        self.assertEqual(bal["marks_in_log"], 2)
        self.assertEqual(bal["absorbed_by_a_shared_event"], 1)
        self.assertTrue(bal["balanced"])

    def test_a_mark_owned_by_a_NON_FIRST_chord_member_still_reaches_the_file(self):
        """⚠️ FOUND BY A MUTATION ARM, not by review. `group_chords_in_measure`
        sorts a chord LOWEST NOTE FIRST, and `adjudicate_fermata_owner` names
        whichever member its x test picked — so reading the hoist off the
        chord's FIRST head alone loses every fermata owned by any other
        member, and every test above happened to own the first.
        """
        page = _one_staff_page(notes=[("C4", QUARTER), ("E4", QUARTER)])
        for i, o in enumerate(
                [o for o in page["record"]["observations"]
                 if o["quantity"] == Q.GLYPH_BOX]):
            o["value"][1] = 100                # one chord...
            o["value"][2] = 100 - 20 * i       # ...glyph 1 is the UPPER note
        _add_fermata(page, 9, 100, owner_gi=1)  # ...so it sorts LAST
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(len(ET.fromstring(xml).findall(".//fermata")), 1)
        self.assertEqual(rep["written"]["fermatas"], 1)

    def test_an_abstained_mark_is_COUNTED_not_swallowed(self):
        page = _add_fermata(_one_staff_page(notes=[("C4", QUARTER)]),
                            9, 100, outcome="abstained", reason="no_carrier")
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(len(ET.fromstring(xml).findall(".//fermata")), 0)
        self.assertEqual(rep["fermatas_not_written"]["fermata_no_carrier"], 1)
        self.assertTrue(rep["fermata_balance"]["balanced"])

    def test_a_mark_whose_owner_was_never_written_is_counted(self):
        """A note can be decided and still dropped (no pitch, a narrowed
        duration), and the pause then has nothing to hang on."""
        page = _add_fermata(_one_staff_page(notes=[(None, QUARTER)]),
                            9, 100, owner_gi=0)
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(
            rep["fermatas_not_written"]["fermata_owning_glyph_not_written"], 1)

    def test_a_page_with_no_fermata_writes_none(self):
        """The positive control's other half: a family that writes one mark
        wherever asked would pass every test above."""
        _xml, rep = SX.to_musicxml(_one_staff_page(notes=[("C4", QUARTER)]))
        self.assertEqual(rep["written"].get("fermatas", 0), 0)
        self.assertEqual(rep["fermata_balance"]["marks_in_log"], 0)


def _two_voice_page(*, rest_gi=None):
    """A one-staff bar the record says holds TWO voices."""
    notes = [("C4", QUARTER), ("E4", QUARTER)]
    page = _one_staff_page(notes=notes)
    voices = [[0], [1]]
    rests = []
    if rest_gi is not None:
        _add_rest(page, rest_gi, "restQuarter", QUARTER)
        voices = [[0, rest_gi], [1, rest_gi]]
        rests = [rest_gi]
    page["record"]["verdicts"].append(
        _vrd(950, "cell/0/0/0/0", Q.VOICES,
             {"n_voices": 2, "voices": voices, "rests_in_every_voice": rests},
             reason="two_voices"))
    return page


class TestTwoVoicesReachTheFile(unittest.TestCase):
    """⚠️ THE STAGED PATH WROTE `<voice>1</voice>` ON EVERYTHING UNTIL
    2026-09-10, which was not merely a simplification: `_paired_spans` takes a
    `voice_of` map to refuse an arc whose ends land in different streams — such
    an arc is unpaired at BOTH and makes the file INVALID — and this exporter
    passed it an empty dict."""

    def test_the_second_stream_is_voice_2_behind_a_backup(self):
        xml, rep = SX.to_musicxml(_two_voice_page())
        root = ET.fromstring(xml)
        self.assertEqual(sorted(v.text for v in root.iter("voice")), ["1", "2"])
        self.assertEqual(len(root.findall(".//backup")), 1)
        self.assertEqual(rep["written"]["two_voice_bars"], 1)

    def test_the_backup_duration_is_what_voice_1_CONSUMED(self):
        """⚠️ Getting this wrong does not produce a wrong-LOOKING file, it
        produces a second voice offset from the first by a beat."""
        xml, rep = SX.to_musicxml(_two_voice_page())
        root = ET.fromstring(xml)
        divisions = rep["written"]["divisions"]
        self.assertEqual(int(root.find(".//backup/duration").text), divisions)

    def test_a_rest_is_written_ONCE_PER_VOICE_and_the_balance_survives(self):
        """⚠️ THE COVER, NOT A PARTITION. Each voice needs its own bar to sum,
        so the rest is written twice — and the note-accounting control is an
        EQUALITY, so the duplicate has to be NAMED or it raises `Unbalanced`
        for correct behaviour."""
        xml, rep = SX.to_musicxml(_two_voice_page(rest_gi=7))
        self.assertEqual(len(ET.fromstring(xml).findall(".//rest")), 2)
        self.assertEqual(rep["written"]["rests_duplicated_across_voices"], 1)
        self.assertTrue(rep["balance"]["balanced"])
        self.assertEqual(rep["balance"]["rests_duplicated_across_voices"], 1)

    def test_a_ONE_voice_verdict_writes_no_backup(self):
        """The positive control: an exporter that split whatever it was given
        would pass every test above."""
        page = _one_staff_page(notes=[("C4", QUARTER), ("E4", QUARTER)])
        page["record"]["verdicts"].append(
            _vrd(950, "cell/0/0/0/0", Q.VOICES,
                 {"n_voices": 1, "voices": [[0, 1]],
                  "rests_in_every_voice": []}, reason="one_voice"))
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(len(ET.fromstring(xml).findall(".//backup")), 0)
        self.assertEqual(rep["written"].get("two_voice_bars", 0), 0)

    def test_NO_verdict_behaves_exactly_as_before(self):
        """A bar whose voices were never decided must be untouched — the
        wiring pass may connect a decision, it may not let one guess."""
        page = _one_staff_page(notes=[("C4", QUARTER), ("E4", QUARTER)])
        xml, _rep = SX.to_musicxml(page)
        root = ET.fromstring(xml)
        self.assertEqual(len(root.findall(".//backup")), 0)
        self.assertEqual({v.text for v in root.iter("voice")}, {"1"})

    def test_a_chord_STRADDLING_two_streams_refuses_the_split(self):
        """⚠️⚠️ FOUND BY THE ACCOUNTING CONTROL ON A REAL PAGE, NOT BY REVIEW.
        `Q.VOICES` partitions `Q.EVENT`'s groups — every notehead the record
        READ — while the exporter groups only the ones it can WRITE, so the
        two groupings need not agree and a chord the exporter formed can span
        two of the record's streams. Every one of its notes was then written
        TWICE: 7 such events on Litolff `984073` p1-3, which is the 17 extra
        the balance reported to the unit.

        ⚠️ REFUSED, NOT MAJORITY-VOTED. Picking the stream holding most of the
        chord's notes would be the EXPORTER deciding a question the record did
        not answer — the same overreach as collapsing a narrowed duration by
        argmax, which this module refuses one screen up.
        """
        page = _one_staff_page(notes=[("C4", QUARTER), ("E4", QUARTER)])
        for o in page["record"]["observations"]:          # one chord
            if o["quantity"] == Q.GLYPH_BOX:
                o["value"][1] = 100
        page["record"]["verdicts"].append(
            _vrd(950, "cell/0/0/0/0", Q.VOICES,
                 {"n_voices": 2, "voices": [[0], [1]],
                  "rests_in_every_voice": []}, reason="two_voices"))
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(len(ET.fromstring(xml).findall(".//backup")), 0)
        self.assertEqual(
            rep["written"]["two_voice_bars_refused_event_straddles_two_streams"],
            1)
        self.assertTrue(rep["balance"]["balanced"])
        self.assertEqual(len(ET.fromstring(xml).findall(".//note")), 2,
                         "the straddling chord was written twice")

    def test_the_refusals_are_counted_APART(self):
        """Their repairs differ — two groupings disagreeing against a bar
        whose notes were dropped — so one total would send the next reader to
        the wrong place."""
        page = _one_staff_page(notes=[("C4", QUARTER), (None, QUARTER)])
        page["record"]["verdicts"].append(
            _vrd(950, "cell/0/0/0/0", Q.VOICES,
                 {"n_voices": 2, "voices": [[0], [1]],
                  "rests_in_every_voice": []}, reason="two_voices"))
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(
            rep["written"]["two_voice_bars_refused_a_stream_has_no_written_note"],
            1)
        self.assertNotIn(
            "two_voice_bars_refused_event_straddles_two_streams",
            rep["written"])

    def test_a_FERMATA_on_a_shared_rest_does_not_break_its_balance(self):
        """⚠️ A rest is written once per voice, so ONE mark can produce TWO
        `<fermata>` elements — and the fermata control is `written +
        not_written <= marks_in_log`, which that would break for correct
        behaviour."""
        page = _two_voice_page(rest_gi=7)
        _add_fermata(page, 9, 300, owner_gi=7)
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(len(ET.fromstring(xml).findall(".//fermata")), 2)
        self.assertTrue(rep["fermata_balance"]["balanced"],
                        rep["fermata_balance"])

    def test_a_stream_the_exporter_could_not_FILL_is_no_split_at_all(self):
        """⚠️ The verdict saw two voices among the notes it READ. If every
        note of one stream was dropped on the way out (no pitch, a narrowed
        duration), writing an empty `<backup>`-separated voice puts a
        `<backup>` in the file for nothing."""
        page = _one_staff_page(notes=[("C4", QUARTER), (None, QUARTER)])
        page["record"]["verdicts"].append(
            _vrd(950, "cell/0/0/0/0", Q.VOICES,
                 {"n_voices": 2, "voices": [[0], [1]],
                  "rests_in_every_voice": []}, reason="two_voices"))
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(len(ET.fromstring(xml).findall(".//backup")), 0)
        self.assertEqual(rep["written"].get("two_voice_bars", 0), 0)
