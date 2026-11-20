"""ROADMAP 2.323 (`OMR_UNISON_KEPT_FOR_BOTH`, ON by default) -- a unison in a two-voice bar is printed once and kept for both parts.

Sean 2026-11-19 (page-facts §1; DECISIONS): "if there is a measure with multiple voices in it, even if it goes down to a single note or a single
rest, those are treated as unisons unless there is a solo marking"; "When there are 2 voices it should print 1 but keep track of both parts on
that voice". STAGED, EXPORT only (`export._place_columns`, `_unison_copy_lines`, `_measure_events_xml`, `_drop_dangling_unison_ties`).

CONTROLS (CLAUDE.md rule 7): built from the REAL events of Brahms Symphony 1 mvt 1 (Breitkopf), pdf page index 5, as the 20261117-night record
writes them (`data_unison_kept_for_both_2_323.json`, cut by the lane's scratch dump from `_place_voices_in_time`'s own input):

* `bassoon_bar80...` -- Bassoons, printed bar 80 (cell 1 of staff 3, system 0): a quarter on both players, an eighth rest, then a dotted chord alone.
* `horn_bar92` -- Horns, printed bar 92 (Sean's tile 4): the held quarter on both, then an eighth rest, a D eighth and two rests alone.
* `horn_bar91` -- Horns, printed bar 91: every stretch is a voice's own mark; nothing here is alone, so ON writes it as OFF does.

Each control CAN FAIL: every assertion that a copy stands in the other voice is run with the flag OFF and must be False there. The record writes
printed bars 81 (one voice) and 93 (one voice, its second tie not read) as ONE voice today -- the rule needs a bar written as two voices, so those
two are not controls (finding in the lane report). The tie tests are built from a real event with the tie flags SET BY THE TEST (the horn bar's
own ties are not read in the record: constructed, labelled so).
"""
import collections
import copy
import json
import os
import re
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

from tools.omr.staged import export as E
from tools.omr.staged import lilypond as LY

FX = os.path.join(os.path.dirname(__file__), "data_unison_kept_for_both_2_323.json")
ENV = E.UNISON_KEPT_FOR_BOTH_ENV


def _bar(name):
    with open(FX) as f:
        d = json.load(f)[name]
    events = [copy.deepcopy(e) for e in d["events"]]
    streams = [[events[i] for i in s] for s in d["streams"]]     # shared events stay ONE object, as the writer's streams do
    return streams, d["meter"], d["divisions"]


def _place(name, flag):
    streams, meter, divisions = _bar(name)
    counters = collections.Counter()
    with mock.patch.dict(os.environ, {ENV: "1" if flag else "0"}):
        placed = E._place_voices_in_time(streams, meter, divisions, [], counters, family=E.FAMILY_WIND)
    assert placed is not None, "the real bar must place"
    return placed, counters, divisions, meter


def _kinds(stream):
    return [e.get("kind") for e in stream]


def _units(stream, divisions):
    return sum(E._event_units(e, divisions) for e in stream)


def _xml_voices(placed, divisions):
    """The bar as `_measure_xml` writes it: voice 1, `<backup>`, voice 2 -- parsed."""
    out, units = E._measure_events_xml(placed[0], divisions, collections.Counter(), voice=1)
    out.append(f"<backup><duration>{units}</duration></backup>")
    second, _ = E._measure_events_xml(placed[1], divisions, collections.Counter(), voice=2)
    out.extend(second)
    return ET.fromstring("<m>" + "\n".join(out) + "</m>")


def _printed(m):
    return [(n.findtext("voice"), n.findtext("pitch/step"), n.findtext("pitch/octave"), n.findtext("type"), n.find("rest") is not None)
            for n in m.findall("note") if n.get("print-object") != "no"]


def _hidden(m):
    return [(n.findtext("voice"), n.findtext("pitch/step"), n.findtext("pitch/octave"), n.findtext("type"), n.find("rest") is not None)
            for n in m.findall("note") if n.get("print-object") == "no"]


class TestFlagIsOnByDefault(unittest.TestCase):
    def test_deny_list(self):
        """ON by default since 2026-11-19 (Sean: "Land it"); only 0/false/no/off switch it OFF."""
        for v, want in (("", True), ("0", False), ("off", False), ("no", False), ("false", False), ("OFF", False), ("1", True), ("true", True),
                        ("YES", True), ("on", True)):
            with mock.patch.dict(os.environ, {ENV: v}):
                self.assertEqual(E.unison_kept_for_both_enabled(), want, v)
        with mock.patch.dict(os.environ):
            os.environ.pop(ENV, None)
            self.assertTrue(E.unison_kept_for_both_enabled())


class TestRealControlBars(unittest.TestCase):
    def test_bassoon_bar_carries_the_lone_chord_and_rest_in_both_voices(self):
        on, c_on, div, _ = _place("bassoon_bar80_two_parts_then_dotted_chord", True)
        # voice 1: quarter, eighth rest, then the dotted chord of voice 2's line is carried (copy); voice 2: quarter, the rest carried, dotted chord
        self.assertEqual(_kinds(on[0]), ["chord", "rest", E.UNISON_COPY_KIND])
        self.assertEqual(_kinds(on[1]), ["chord", E.UNISON_COPY_KIND, "chord"])
        self.assertNotIn(E.FORWARD_KIND, _kinds(on[0]) + _kinds(on[1]))
        self.assertEqual(c_on["two_voice_unison_copies_kept_rest"], 1)
        self.assertEqual(c_on["two_voice_unison_copies_kept_chord_upper"], 1)    # r2: one note of the two-note chord, not both
        for st in on:
            self.assertEqual(_units(st, div), 12)               # every voice still adds up to the 6/8 bar
        self.assertIs(on[0][2]["of"], on[1][2])                 # the very mark the page prints, never a new reading
        self.assertIs(on[1][1]["of"], on[0][1])

    def test_the_control_fails_with_the_flag_off(self):
        off, c_off, div, _ = _place("bassoon_bar80_two_parts_then_dotted_chord", False)
        self.assertNotIn(E.UNISON_COPY_KIND, _kinds(off[0]) + _kinds(off[1]))
        self.assertEqual(_kinds(off[0]), ["chord", "rest", E.FORWARD_KIND])     # today: the other player is carried across with <forward>
        self.assertEqual(c_off["two_voice_unison_copies_kept"], 0)

    def test_horn_bar_92_carries_the_lone_eighth_and_rests(self):
        on, c, div, _ = _place("horn_bar92", True)
        self.assertEqual(_kinds(on[0]), ["chord", "rest", "chord", "rest", "rest"])         # voice 1 is its own printed marks
        self.assertEqual(_kinds(on[1]), ["chord"] + [E.UNISON_COPY_KIND] * 4)               # voice 2: the held quarter, then all four carried
        carried_d = on[1][2]["of"]
        self.assertEqual([h["pitch"] for h in carried_d["noteheads"]], ["D5"])
        for st in on:
            self.assertEqual(_units(st, div), 12)
        off, _c, _d, _m = _place("horn_bar92", False)
        self.assertEqual(_kinds(off[1]), ["chord"] + [E.FORWARD_KIND] * 4)                  # the control can fail: flag off keeps the forwards

    def test_horn_bar_91_is_not_placed_today_so_the_flag_cannot_act(self):
        # FINDING, not forced: the record reads the printed dotted quarter of bar 91 as a quarter (its dot is not read), so the bar sums to 5/8 in a
        # 6/8 meter and `_place_voices_in_time` declines it either way; the flag writes it exactly as OFF does
        streams, meter, div = _bar("horn_bar91")
        for flag in ("0", "1"):
            counters = collections.Counter()
            with mock.patch.dict(os.environ, {ENV: flag}):
                self.assertIsNone(E._place_voices_in_time(copy.deepcopy(streams), meter, div, [], counters, family=E.FAMILY_WIND))
            self.assertEqual(counters["two_voice_bars_not_placed_the_fuller_voice_does_not_come_to_the_bar"], 1)

    def test_the_same_bars_place_either_way(self):
        # EXPORT's decision to write a bar as two voices is untouched: with the flag off or on the same bars place (or refuse) for the same reason
        for name in ("bassoon_bar80_two_parts_then_dotted_chord", "horn_bar92", "horn_bar91"):
            streams, meter, div = _bar(name)
            res = []
            for flag in ("0", "1"):
                with mock.patch.dict(os.environ, {ENV: flag}):
                    res.append(E._place_voices_in_time(copy.deepcopy(streams), meter, div, [], collections.Counter(), family=E.FAMILY_WIND) is None)
            self.assertEqual(res[0], res[1])


class TestTheFileCarriesBothPartsAndPrintsOne(unittest.TestCase):
    def test_printed_notes_and_rests_are_identical_on_and_off(self):
        for name in ("bassoon_bar80_two_parts_then_dotted_chord", "horn_bar92"):
            on, _c, div, _m = _place(name, True)
            off, _c2, _d, _m2 = _place(name, False)
            self.assertEqual(_printed(_xml_voices(on, div)), _printed(_xml_voices(off, div)), name)

    def test_the_second_voice_holds_the_marks_not_printed_in_place_of_forwards(self):
        on, _c, div, _m = _place("bassoon_bar80_two_parts_then_dotted_chord", True)
        m = _xml_voices(on, div)
        hid = _hidden(m)
        # r2 (Sean 2026-11-19, "One note each"): the printed chord (Ab3 + Gb4, voice 2) stays whole; voice 1's player gets the UPPER note only
        self.assertEqual(sorted(hid), sorted([("1", "G", "4", "quarter", False), ("2", None, None, "eighth", True)]))
        self.assertEqual(len(m.findall("forward")), 0)
        for n in m.findall("note"):
            if n.get("print-object") == "no":
                self.assertEqual(n.get("print-spacing"), "no")     # the copy takes no room on the engraved page
        # a printed dot rides with the copy's value
        self.assertEqual(sum(1 for n in m.findall("note") if n.get("print-object") == "no" and n.find("dot") is not None), 1)
        off, _c2, _d, _m2 = _place("bassoon_bar80_two_parts_then_dotted_chord", False)
        mo = _xml_voices(off, div)
        self.assertEqual(_hidden(mo), [])                           # the control can fail: OFF writes no copy, only a forward
        self.assertEqual(len(mo.findall("forward")), 2)

    def test_each_voice_adds_up_in_the_file(self):
        for name in ("bassoon_bar80_two_parts_then_dotted_chord", "horn_bar92"):
            on, _c, div, _m = _place(name, True)
            m = _xml_voices(on, div)
            for voice in ("1", "2"):
                total = sum(int(n.findtext("duration")) for n in m.findall("note") if n.findtext("voice") == voice and n.find("chord") is None)
                total += sum(int(f.findtext("duration")) for f in m.findall("forward") if f.findtext("voice") == voice)
                self.assertEqual(total, 12, (name, voice))

    def test_a_copy_carries_no_slur_beam_articulation_or_blue(self):
        streams, meter, div = _bar("horn_bar92")
        d5 = streams[0][2]
        d5["slur_states"] = [(1, "start")]
        d5["beam_states"] = {1: "begin"}
        d5["noteheads"][0]["articulations"] = ["staccato"]
        d5["noteheads"][0]["guess"] = {"quantity": "accidental", "rule": "x", "stage": "infer", "chosen": 0.5, "candidates": []}
        with mock.patch.dict(os.environ, {ENV: "1"}):
            placed = E._place_voices_in_time(streams, meter, div, [], collections.Counter(), family=E.FAMILY_WIND)
        m = _xml_voices(placed, div)
        copy_d5 = [n for n in m.findall("note") if n.get("print-object") == "no" and n.findtext("pitch/step") == "D"][0]
        self.assertIsNone(copy_d5.find("notations"))
        self.assertIsNone(copy_d5.get("color"))
        self.assertEqual(copy_d5.findtext("voice"), "2")

    def test_the_copy_is_not_counted_as_a_note_or_rest_of_the_page(self):
        streams, meter, div = _bar("horn_bar92")
        with mock.patch.dict(os.environ, {ENV: "1"}):
            placed = E._place_voices_in_time(streams, meter, div, [], collections.Counter(), family=E.FAMILY_WIND)
        counters = collections.Counter()
        E._measure_events_xml(placed[1], div, counters, voice=2)
        self.assertEqual(counters["notes"] + counters["rests"], 1)           # only the held quarter of voice 2 is a note of the page
        self.assertEqual(counters["unison_copies_written"], 4)


class TestTiesStayWholeInTheirOwnVoice(unittest.TestCase):
    """Constructed from a REAL event (horn bar 92's D5 eighth) with the tie flags set here."""

    def _copy_lines(self, voice, start=False, stop=False):
        streams, meter, div = _bar("horn_bar92")
        d5 = copy.deepcopy(streams[0][2])
        d5["noteheads"][0]["tied_to_next"] = start
        d5["noteheads"][0]["tied_from_prev"] = stop
        cp = E._unison_copy_event(d5, E._event_units(d5, div), d5["x_position"], div)
        return E._unison_copy_lines(cp, div, voice)

    def _printed_line(self, voice, start=False, stop=False):
        streams, meter, div = _bar("horn_bar92")
        d5 = copy.deepcopy(streams[0][2])
        d5["noteheads"][0]["tied_to_next"] = start
        d5["noteheads"][0]["tied_from_prev"] = stop
        out, _u = E._measure_events_xml([d5], div, collections.Counter(), voice=voice)
        return out

    @staticmethod
    def _ties(lines):
        return re.findall(r'<tie type="(\w+)"', "\n".join(lines))

    def test_a_copy_tied_to_a_copy_of_the_next_bar_keeps_its_tie(self):
        lines = (["<measure>"] + self._copy_lines("2", start=True) + ["</measure>", "<measure>"] + self._copy_lines("2", stop=True) + ["</measure>"])
        out = E._drop_dangling_unison_ties(lines)
        self.assertEqual(self._ties(out), ["start", "stop"])
        self.assertIn('<tied type="start"', "\n".join(out))

    def test_a_copy_tie_start_with_no_partner_in_its_voice_is_dropped(self):
        # the next bar is a single-voice bar: its D5 is in voice 1, so voice 2's copy has nothing to tie to
        lines = (["<measure>"] + self._copy_lines("2", start=True) + ["</measure>", "<measure>"] + self._printed_line("1", stop=True) + ["</measure>"])
        out = E._drop_dangling_unison_ties(lines)
        self.assertEqual(self._ties(out), ["stop"])                           # the printed note keeps ITS tie stop; the copy's start is gone
        self.assertEqual(self._ties(lines), ["start", "stop"])                # the control: before the pass the dangling start was there
        self.assertNotIn("<tied type=\"start\"", "\n".join(out))

    def test_a_copy_tie_stop_with_no_start_in_its_voice_is_dropped(self):
        lines = (["<measure>"] + self._printed_line("1", start=True) + ["</measure>", "<measure>"] + self._copy_lines("2", stop=True) + ["</measure>"])
        out = E._drop_dangling_unison_ties(lines)
        self.assertEqual(self._ties(out), ["start"])

    def test_a_printed_notes_ties_are_never_touched(self):
        lines = ["<measure>"] + self._printed_line("1", start=True) + ["</measure>", "<measure>"] + self._printed_line("1", stop=True) + ["</measure>"]
        self.assertEqual(E._drop_dangling_unison_ties(lines), lines)

    def test_a_part_with_no_copy_comes_back_as_it_came(self):
        lines = ["<measure>"] + self._printed_line("1", start=True) + ["</measure>"]
        self.assertIs(E._drop_dangling_unison_ties(lines), lines)


class TestTheEngravedPageShowsOne(unittest.TestCase):
    def test_lilypond_writes_the_copy_as_the_skip_a_forward_is(self):
        streams, meter, div = _bar("horn_bar92")
        with mock.patch.dict(os.environ, {ENV: "1"}):
            on = E._place_voices_in_time(copy.deepcopy(streams), meter, div, [], collections.Counter(), family=E.FAMILY_WIND)
        with mock.patch.dict(os.environ, {ENV: "0"}):
            off = E._place_voices_in_time(copy.deepcopy(streams), meter, div, [], collections.Counter(), family=E.FAMILY_WIND)
        text_on = [LY._lily_event_marked(e, {}) for e in on[1]]
        text_off = [LY._lily_event_marked(e, {}) for e in off[1]]
        self.assertEqual(text_on[0], text_off[0])
        self.assertEqual(text_on[1:], ["s1*1/8"] * 4)                       # four invisible skips ...
        self.assertEqual(text_on, text_off)                                  # ... the very text the forwards give: the engraved page is unchanged


if __name__ == "__main__":
    unittest.main()
