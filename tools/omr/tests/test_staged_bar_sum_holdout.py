"""ROADMAP 2.8: a bar whose durations do not sum to the meter is HELD OUT.

Sean, 2026-09-23 (`docs/DECISIONS.md`): *"hold out — I don't care about print
right now — I want to know what we are getting correct."* A bar we could not
read to its meter is a bar we could not read, so it exports as the same marked
empty bar a bar we read NOTHING in gets, and every notehead and rest in it is
counted under a named refusal so the accounting EQUALITY still balances.
Nothing pads, trims or re-times a bar to fit.

⚠️ THIS FILE WAS RUN RED AGAINST THE UNREPAIRED TREE FIRST — `259773e5`'s
`export.py` in place, this file as written:
`benchmarks/omr-bar-sum-holdout-2026-09/out/tests-RED.txt`.

⚠️ AND THE RED RUN IS WEAKER EVIDENCE THAN IT LOOKS, WHICH IS SAID HERE
RATHER THAN LEFT TO BE NOTICED. Most of these tests read
`report["bars_held_out_sum"]`, a key the old exporter does not write at all,
so they fail there on a `KeyError` rather than on the behaviour. The one that
goes red for the RIGHT reason on the old tree is the one that asserts a
POSITIVE fact about it, and the tests in
`TestTheBarThatDOESAddUpIsStillWritten`, `TestTheWholeRestConvention`,
`TestAChordIsOneEvent` and `TestWhereTheMeterIsUnknownNothingIsHeldOut` are
the positive controls that stop the refusal passing by refusing everything
(CLAUDE.md §6b): each has a sibling asserting the same shape is REFUSED, and
the pair differs by one fact — the x's, the ratio, the meter.

⚠️ No test in this file reads module source text (CLAUDE.md §6c). The
one-copy-of-the-arithmetic claim is checked by COMPARING TWO NUMBERS
(`TestOneCopyOfTheArithmetic`), not by grepping for a call.
"""

import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import export as SX
from tools.omr.staged.record import Q
from tools.omr.tests.test_staged_export import (
    QUARTER, _add_rest, _obs, _one_staff_page, _vrd)

TWO_FOUR = {"numerator": 2, "denominator": 4, "raw": "2/4"}
EIGHTH = {"beats": 0.5, "written": 0.5, "dots": 0}
REFUSAL = "bar_does_not_add_up"


def _bar(notes, meter=TWO_FOUR, n_measures=1):
    return _one_staff_page(notes=notes, meter=meter, n_measures=n_measures)


def _stack(page, xs, pitches, dur=QUARTER, first_index=20, cell=0):
    """Extra noteheads at chosen x positions — a CHORD when the x's agree.

    `_one_staff_page` spaces its notes 100 apart, which is what makes them
    separate events; `group_chords_in_measure` groups by x, so a chord has to
    be built by hand. Used for the §10 double-counting trap and its negative
    control.
    """
    for k, (x, pitch) in enumerate(zip(xs, pitches)):
        gi = first_index + k
        sub = f"glyph/0/0/0/{cell}/{gi}"
        page["record"]["observations"].append(
            _obs(2000 + gi, sub, Q.GLYPH_BOX,
                 ["noteheadBlackOnLine", x, 50, 40, 40], category="notehead"))
        page["record"]["observations"].append(
            _obs(2100 + gi, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine"))
        page["record"]["verdicts"].append(_vrd(2200 + gi, sub, Q.PITCH, pitch))
        page["record"]["verdicts"].append(_vrd(2300 + gi, sub, Q.DURATION, dur))
    return page


def _measures(xml):
    return ET.fromstring(xml).findall(".//measure")


class TestABarThatDoesNotAddUpIsHeldOut(unittest.TestCase):
    def test_three_decided_quarters_in_two_four_are_held_out(self):
        """The fact 2.8 exists for: three quarters cannot be a 2/4 bar, and
        the old exporter wrote all three anyway."""
        xml, rep = SX.to_musicxml(
            _bar([("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)]))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)
        self.assertEqual(rep["notes_not_written"][REFUSAL], 3)
        self.assertEqual(rep["written"].get("notes", 0), 0)
        self.assertEqual(ET.fromstring(xml).findall(".//pitch"), [])

    def test_the_held_bar_is_the_same_marked_empty_bar_an_unread_bar_gets(self):
        """⚠️ `_mxl_empty_measure`'s path, NOT a shortened bar and NOT a bar
        with a mark on it. Sean asked for the bar to be held out, and the
        measure the file holds is the one a bar we read nothing in holds."""
        xml, _rep = SX.to_musicxml(
            _bar([("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)]))
        root = ET.fromstring(xml)
        rests = root.findall(".//note/rest")
        self.assertEqual(len(rests), 1)
        self.assertEqual(rests[0].get("measure"), "yes")
        self.assertEqual(root.find(".//note/duration").text, "8")

    def test_it_is_NOT_counted_as_a_bar_we_read_nothing_in(self):
        """⚠️ `empty_bars_padded` means *the detector found no event here*.
        This bar is full of events that do not add up, and the repairs are
        opposite — recall against rhythm. Conflating them would report a page
        as full of unread bars when what it is full of is misread rhythm."""
        _xml, rep = SX.to_musicxml(
            _bar([("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)]))
        self.assertEqual(rep["written"].get("empty_bars_padded", 0), 0)
        self.assertEqual(rep["written"]["bars_held_out_sum"], 1)

    def test_a_SHORT_bar_is_held_out_too(self):
        """Short and overfull are one fact — the bar does not add up — and
        neither is repaired by padding it out or trimming it back."""
        _xml, rep = SX.to_musicxml(_bar([("C4", QUARTER)]))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)
        self.assertEqual(rep["notes_not_written"][REFUSAL], 1)

    def test_every_held_bar_is_named_by_page_system_staff_and_cell(self):
        """ROADMAP 2.8 asks for the census to name every held bar. A count
        can only be argued about; a coordinate can be opened against the
        plate."""
        _xml, rep = SX.to_musicxml(
            _bar([("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)]))
        held = rep["bars_held_out_sum"]["held"]
        self.assertEqual(len(held), 1)
        row = held[0]
        for k in ("page", "system", "staff", "cell", "measure"):
            self.assertIn(k, row)
        self.assertEqual((row["page"], row["system"], row["staff"],
                          row["cell"]), (0, 0, 0, 0))
        self.assertEqual(row["noteheads_and_rests"], 3)
        self.assertEqual(row["want_quarters"], 2.0)
        self.assertEqual(row["quarters"], [3.0])


class TestTheBarThatDOESAddUpIsStillWritten(unittest.TestCase):
    """⚠️⚠️ THE POSITIVE CONTROLS. A refusal with no positive control in the
    same class passes by refusing everything (CLAUDE.md §6b), and these are
    the cases that say the hold-out is a TEST and not a switch. They cannot
    go RED against the unrepaired tree — that tree wrote every bar — which is
    exactly why they are the control and not the evidence."""

    def test_two_quarters_in_two_four_are_written(self):
        xml, rep = SX.to_musicxml(_bar([("C4", QUARTER), ("D4", QUARTER)]))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)
        self.assertNotIn(REFUSAL, rep["notes_not_written"])
        self.assertEqual(rep["written"]["notes"], 2)
        self.assertEqual(len(ET.fromstring(xml).findall(".//pitch")), 2)

    def test_the_figure_is_reported_even_when_it_is_zero(self):
        """*"we held out none"* must not read like *"this was never
        computed"* — the `empty_bars_padded_without_meter` lesson."""
        _xml, rep = SX.to_musicxml(_bar([("C4", QUARTER), ("D4", QUARTER)]))
        self.assertIn("bars_held_out_sum", rep["written"])
        self.assertEqual(rep["written"]["bars_held_out_sum"], 0)
        self.assertEqual(rep["written"]["bars_with_events"], 1)


class TestTheWholeRestConvention(unittest.TestCase):
    def test_a_lone_whole_rest_is_the_BAR_whatever_the_meter(self):
        """⚠️ CLAUDE.md §10: a whole rest means the BAR whatever the meter.
        `<rest measure="yes"/>` carries no note value, so there is nothing to
        measure against the meter — and judging it by its `<duration>` would
        hold out the one bar the convention exists for. Here the rest is
        written four quarters long in a 2/4 bar, which is the shape
        `size_measure_rest` leaves behind where it could not size it."""
        page = _bar([])
        _add_rest(page, 5, "restWhole",
                  {"beats": 4.0, "written": 4.0, "dots": 0, "is_rest": True,
                   "measure_rest": True})
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)
        self.assertEqual(rep["written"]["measure_rests_read"], 1)
        self.assertNotIn(REFUSAL, rep["notes_not_written"])

    def test_a_measure_rest_sharing_its_bar_is_NOT_the_bar(self):
        """The negative control for the rule above, and the reason it says
        LONE. Two events cannot both occupy the whole bar, so a measure rest
        beside a quarter is a bar that does not add up like any other — and
        without this the exemption would wave through every bar holding one."""
        page = _bar([("C4", QUARTER)])
        _add_rest(page, 5, "restWhole",
                  {"beats": 2.0, "written": 2.0, "dots": 0, "is_rest": True,
                   "measure_rest": True})
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)
        self.assertEqual(rep["notes_not_written"][REFUSAL], 2)


class TestAChordIsOneEvent(unittest.TestCase):
    """CLAUDE.md §10's double-counting trap: a chord's members share one x and
    one stem, and summing per NOTEHEAD is how the bar-sum arithmetic was wrong
    the last time this project computed it."""

    def test_a_three_note_chord_plus_a_quarter_fills_a_two_four_bar(self):
        page = _bar([("C4", QUARTER)])
        _stack(page, [400, 400, 400], ["E4", "G4", "B4"])
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)
        self.assertEqual(rep["written"]["notes"], 4)

    def test_the_SAME_FOUR_HEADS_spread_out_are_four_events_and_are_held(self):
        """The negative control: identical durations, identical count, only
        the x's differ. If the check counted heads rather than events this
        would pass too, and the test above would prove nothing."""
        page = _bar([("C4", QUARTER)])
        _stack(page, [400, 500, 600], ["E4", "G4", "B4"])
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)
        self.assertEqual(rep["notes_not_written"][REFUSAL], 4)


class TestATupletScalesTheTime(unittest.TestCase):
    def _triplet_page(self, force_thirds):
        """A 2/4 bar of three triplet eighths and a quarter.

        ⚠️ `force_thirds` puts a note of 1/3 quarter in the NEXT bar, purely
        so `_divisions` returns a multiple of three. That is not decoration:
        `_divisions` reads each detection's own `duration_beats`, which for a
        triplet eighth is the WRITTEN 0.5, so nothing about a triplet makes
        the LCM divisible by 3 — see the second test in this class.
        """
        page = _bar([("C4", EIGHTH), ("D4", EIGHTH), ("E4", EIGHTH),
                     ("F4", QUARTER)], n_measures=2)
        page["record"]["verdicts"].append(_vrd(
            777, "cell/0/0/0/0", Q.TUPLET_RATIO,
            {"actual": 3, "normal": 2, "members": [0, 1, 2]}))
        if force_thirds:
            _stack(page, [100], ["G4"],
                   dur={"beats": 1.0 / 3.0, "written": 1.0, "dots": 0},
                   cell=1)
        return page

    def test_three_triplet_eighths_and_a_quarter_fill_a_two_four_bar(self):
        """⚠️ A tuplet scales the time and leaves the written value alone.
        Three eighths are 1.5 quarters written and 1.0 played, so the bar adds
        up only if the ratio is applied — unscaled it reads 2.5 and the bar
        would be held out for the reader's correct answer."""
        _xml, rep = SX.to_musicxml(self._triplet_page(force_thirds=True))
        self.assertEqual(rep["written"]["tuplet_notes"], 3)
        self.assertEqual(rep["written"]["divisions"] % 3, 0)
        held = [h["cell"] for h in rep["bars_held_out_sum"]["held"]]
        self.assertNotIn(0, held)          # the triplet bar is WRITTEN
        self.assertEqual(rep["written"]["notes"], 4)

    def test_a_triplet_IS_held_out_where_divisions_is_not_a_multiple_of_three(self):
        """⚠️⚠️ A DEFECT THIS RULE EXPOSES AND DOES NOT REPAIR, recorded
        rather than worked around. `_divisions`' own docstring says it "must
        include the tuplet ratio, because that is where a third comes from" —
        and it does not: it reads each detection's `duration_beats`, the
        WRITTEN value, so a page whose only thirds come from tuplet MARKS gets
        `divisions=4` and every triplet eighth is written `<duration>1` where
        the exact value is 4/3. Three of them are then 3 units against the
        bar's 8, and 2.8 holds the bar out — correctly, because the FILE does
        not add up. The repair is in `_divisions`, which is upstream of this
        rule and outside ROADMAP 2.8; this test pins the behaviour so the
        cost is visible and the next reader is sent to the right function."""
        _xml, rep = SX.to_musicxml(self._triplet_page(force_thirds=False))
        self.assertEqual(rep["written"]["divisions"], 4)
        held = [h["cell"] for h in rep["bars_held_out_sum"]["held"]]
        self.assertIn(0, held)

    def test_the_same_bar_without_the_ratio_does_NOT_add_up(self):
        """The control for the test above: without the ratio the identical
        four notes are 2.5 quarters and the bar is held out. It is what makes
        the scaling a measurement rather than a hope."""
        _xml, rep = SX.to_musicxml(
            _bar([("C4", EIGHTH), ("D4", EIGHTH), ("E4", EIGHTH),
                  ("F4", QUARTER)]))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)


class TestItNeverCountsOneHeadTwice(unittest.TestCase):
    def test_a_NARROWED_duration_stays_under_its_own_refusal(self):
        """⚠️ THE ORDERING, AND IT IS STRUCTURAL RATHER THAN CHECKED. A note
        whose duration is NARROWED is refused by `_place_notes` and never
        reaches a cell, so the bar 2.8 measures holds only DECIDED events and
        no head can land in both buckets. This bar's remaining quarter is one
        of two, so the bar IS held out — and the narrowed head is still
        counted exactly once, under `duration_narrowed`."""
        _xml, rep = SX.to_musicxml(_bar([("C4", QUARTER), ("D4", None)]))
        self.assertEqual(rep["notes_not_written"]["duration_narrowed"], 1)
        self.assertEqual(rep["notes_not_written"][REFUSAL], 1)
        self.assertEqual(rep["notes_not_written_total"], 2)
        self.assertEqual(rep["balance"]["noteheads_in_log"], 2)
        self.assertTrue(rep["balance"]["balanced"])

    def test_a_bar_whose_remaining_events_DO_add_up_is_written(self):
        """The other side of the same ordering: the narrowed head is held
        back, the two that remain fill the bar, and 2.8 does not fire. The
        bar is missing a note and the report says so under
        `duration_narrowed` — which is the honest place for it."""
        _xml, rep = SX.to_musicxml(
            _bar([("C4", QUARTER), ("D4", QUARTER), ("E4", None)]))
        self.assertEqual(rep["notes_not_written"]["duration_narrowed"], 1)
        self.assertNotIn(REFUSAL, rep["notes_not_written"])
        self.assertEqual(rep["written"]["notes"], 2)

    def test_the_accounting_equality_still_balances(self):
        """⚠️ The control `to_musicxml` RAISES on. Every notehead and rest in
        the log is written or counted under a named refusal; a held-out bar
        moves events from the first to the second and must move all of
        them."""
        page = _bar([("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)])
        _add_rest(page, 5, "restEighth",
                  {"beats": 0.5, "written": 0.5, "dots": 0, "is_rest": True})
        _xml, rep = SX.to_musicxml(page)
        b = rep["balance"]
        self.assertEqual(b["events_in_log"], 4)
        self.assertEqual(b["events_written"], 0)
        self.assertEqual(b["events_not_written"], 4)
        self.assertTrue(b["balanced"])
        self.assertEqual(rep["status_census"]["unaccounted"], [])

    def test_the_refusal_reaches_the_per_system_counter_too(self):
        """⚠️ `build` asserts the per-system refusals sum to the per-reason
        total, and this refusal is filed from the RENDER — after that
        assertion has already run. `to_musicxml` re-asserts it; this is the
        test that the second call site is wired to both counters, which is
        exactly what `build_sheet.py`'s stale copy was not."""
        _xml, rep = SX.to_musicxml(
            _bar([("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)]))
        by_sys = rep["notes_not_written_by_system"]
        self.assertEqual(by_sys["0/0"][REFUSAL], 3)
        self.assertEqual(
            sum(sum(c.values()) for c in by_sys.values()),
            rep["notes_not_written_total"])


class TestWhereTheMeterIsUnknownNothingIsHeldOut(unittest.TestCase):
    def test_a_bar_with_no_meter_is_UNASSESSABLE_and_is_written(self):
        """⚠️ Rule 8, in the direction it is easiest to get wrong.
        `_measure_rest_beats` falls back to 4.0 with no meter; reading that
        as *"this bar is four quarters long"* would hold out every 2/4 bar on
        a page whose meter never settled — CANNOT TELL converted into a
        definite answer, and a very expensive one."""
        _xml, rep = SX.to_musicxml(
            _bar([("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)],
                 meter=None))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)
        self.assertEqual(rep["written"]["notes"], 3)
        self.assertEqual(rep["written"]["bars_with_events_without_a_meter"], 1)


def _two_system_page(meter_on_second):
    """Two systems of one staff; the SECOND may or may not file a meter.

    The first system declares 2/4 and the file writes `<time>` there. MusicXML
    has no way to UN-declare a meter, so every bar of the second system is in
    2/4 to any reader — whatever `Q.METER` filed, or did not file, for it.
    """
    page = _one_staff_page(notes=[("C4", QUARTER), ("D4", QUARTER)],
                           meter=TWO_FOUR)
    rec = page["record"]
    # a second system: one staff, three quarters in its only bar
    for gi, pitch in enumerate(("E4", "F4", "G4")):
        sub = f"glyph/0/1/0/0/{gi}"
        rec["observations"].append(
            _obs(3000 + gi, sub, Q.GLYPH_BOX,
                 ["noteheadBlackOnLine", 100 * gi, 50, 40, 40],
                 category="notehead"))
        rec["observations"].append(
            _obs(3100 + gi, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine"))
        rec["verdicts"].append(_vrd(3200 + gi, sub, Q.PITCH, pitch))
        rec["verdicts"].append(_vrd(3300 + gi, sub, Q.DURATION, QUARTER))
    rec["verdicts"].append(_vrd(3400, "staff/0/1/0", Q.MEASURE_PARTITION, 1))
    rec["verdicts"].append(_vrd(3401, "staff/0/1/0", Q.CLEF, "treble"))
    rec["verdicts"].append(_vrd(3402, "system/0/1", Q.SYSTEM_STAFF_COUNT, 1))
    if meter_on_second:
        rec["verdicts"].append(_vrd(3403, "system/0/1", Q.METER, TWO_FOUR))
    return page


class TestTheMeterInForceIsTheFilesOwn(unittest.TestCase):
    """⚠️⚠️ THE BAR IS JUDGED AGAINST WHAT THE FILE CLAIMS, NOT AGAINST WHAT
    THE RECORD FILED AT IT. `<time>` is written only where it CHANGES, so a
    system whose meter never settled still has one in force for a reader.
    Judging those bars UNASSESSABLE let the file assert a length nothing
    checked: on Breitkopf Brahms 1 that was 3,826 of 5,803 bars with events,
    and the independent control found 3,132 of them not adding up while the
    exporter believed it had assessed nothing."""

    def test_a_bar_on_a_meterless_system_is_judged_by_the_carried_time(self):
        _xml, rep = SX.to_musicxml(_two_system_page(meter_on_second=False))
        held = rep["bars_held_out_sum"]
        self.assertEqual(held["bars"], 1)
        self.assertEqual(held["bars_judged_by_a_carried_meter"], 1)
        self.assertTrue(held["held"][0]["meter_carried_in_file"])
        self.assertEqual(held["held"][0]["want_quarters"], 2.0)

    def test_the_same_bar_is_judged_the_same_way_when_the_meter_IS_filed(self):
        """The control: the carry must reach the SAME verdict the declaration
        does, or the rule is deciding by provenance rather than by length."""
        _xml, rep = SX.to_musicxml(_two_system_page(meter_on_second=True))
        held = rep["bars_held_out_sum"]
        self.assertEqual(held["bars"], 1)
        self.assertEqual(held["bars_judged_by_a_carried_meter"], 0)
        self.assertFalse(held["held"][0]["meter_carried_in_file"])

    def test_an_unread_bar_is_sized_by_the_carried_meter_not_by_four(self):
        """⚠️ `_measure_rest_beats(None)` is 4.0. An eventless bar on a
        meterless system used to be written as a four-quarter whole rest into
        a part the file had already declared to be in 2/4 — a bar
        contradicting the file's own claim about its length. 232 such bars on
        Brahms, and they were the whole residue after the hold-out."""
        page = _two_system_page(meter_on_second=False)
        # strip the second system's notes: now it is a bar we read NOTHING in
        rec = page["record"]
        rec["observations"] = [o for o in rec["observations"]
                               if "/0/1/0/" not in o["subject"]]
        rec["verdicts"] = [v for v in rec["verdicts"]
                           if "glyph/0/1/0/" not in v["subject"]]
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["written"]["empty_bars_padded"], 1)
        self.assertEqual(rep["written"]["empty_bars_sized_by_a_carried_meter"], 1)
        self.assertEqual(rep["written"]["empty_bars_padded_without_meter"], 0)
        durations = [int(d.text) for d in ET.fromstring(xml).iter("duration")]
        self.assertNotIn(16, durations)     # 4.0 quarters at divisions 4
        self.assertEqual(durations[-1], 8)  # the 2/4 bar it is actually in

    def test_with_no_time_declared_ANYWHERE_the_fallback_still_stands(self):
        """The other side: a part that has declared no `<time>` at all has no
        claim to hold a bar to, so nothing is held out and `measure="yes"` is
        still withheld. Rule 8 — the carry may not manufacture a meter, only
        read back one the file already wrote."""
        _xml, rep = SX.to_musicxml(
            _bar([("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)],
                 meter=None))
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)
        self.assertEqual(rep["written"]["bars_with_events_without_a_meter"], 1)


class TestOneCopyOfTheArithmetic(unittest.TestCase):
    def test_the_units_the_check_reasons_about_are_the_units_the_file_holds(self):
        """⚠️ `_measure_events_xml` returns the number `<backup>` is written
        from, and `_event_units` is what the hold-out sums. If the two ever
        disagreed the exporter would judge a bar by an arithmetic the file
        does not use — so they are compared here, on the same events, rather
        than asserted about the source."""
        import collections
        events = [
            {"kind": "chord", "noteheads": [
                {"pitch": "C4", "duration_beats": 1.0,
                 "duration_type": "quarter", "dots": 0},
                {"pitch": "E4", "duration_beats": 1.0,
                 "duration_type": "quarter", "dots": 0}]},
            {"kind": "rest", "duration_beats": 0.5,
             "duration_type": "eighth", "dots": 0, "rest": {}},
            {"kind": "chord", "noteheads": [
                {"pitch": "G4", "duration_beats": 0.5,
                 "duration_type": "eighth", "dots": 0,
                 "tuplet": {"actual": 3, "normal": 2}}]},
        ]
        counters = collections.Counter()
        _lines, units = SX._measure_events_xml(events, 12, counters)
        self.assertEqual(units,
                         sum(SX._event_units(ev, 12) for ev in events))
        # ⚠️ A positive control on the control: the chord must contribute ONE
        # note's worth, so the total cannot be the per-head sum.
        self.assertEqual(units, 12 + 6 + 4)


if __name__ == "__main__":
    unittest.main()
