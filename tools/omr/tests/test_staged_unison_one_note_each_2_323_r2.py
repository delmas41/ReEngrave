"""ROADMAP 2.323 r2 (`OMR_UNISON_KEPT_FOR_BOTH`, built OFF) -- a TWO-note chord in a two-voice bar is one note each.

Sean 2026-11-19, shown Brahms bassoons bar 80 (two dotted notes on one stem, two ties) and asked whether the two players take one note each
or both play both: "One note each". His unison rule covers "a single note or a single rest" only. OUR READING (the manager's, not his words):
the printed chord stays as printed; the other voice carries ONLY the note that is its player's (printed in voice 1: the LOWER note to voice 2;
printed in voice 2: the UPPER note to voice 1). A chord of THREE or more notes is not covered: left as flag OFF writes it, counted.

CONTROL: the REAL chord of bassoon bar 80 (Ab3 + Gb4) from `data_unison_kept_for_both_2_323.json`. The record prints it in voice 2, so the
"printed in voice 1, lower note to voice 2" arrangement is the same real events with the voices swapped (CONSTRUCTED, labelled so). The control
can fail: `test_round_1_copied_both_notes` runs the same bar through the round-1 behaviour (whole-chord copy, reproduced here by taking no head)
and shows both notes land in the other voice.
"""
import collections
import copy
import os
import unittest
from unittest import mock

from tools.omr.staged import export as E
from tools.omr.tests import test_staged_unison_kept_for_both_2_323 as R1

ENV = E.UNISON_KEPT_FOR_BOTH_ENV
BAR = "bassoon_bar80_two_parts_then_dotted_chord"


def _hidden_pitches(placed, div):
    m = R1._xml_voices(placed, div)
    return [(n.findtext("voice"), n.findtext("pitch/step") + n.findtext("pitch/octave")) for n in m.findall("note")
            if n.get("print-object") == "no" and n.find("rest") is None]


def _printed_pitches(placed, div):
    m = R1._xml_voices(placed, div)
    return [(n.findtext("voice"), n.findtext("pitch/step") + n.findtext("pitch/octave"), n.find("chord") is not None) for n in m.findall("note")
            if n.get("print-object") != "no" and n.find("rest") is None]


class TestTwoNoteChordIsOneNoteEach(unittest.TestCase):
    def test_printed_in_voice_2_the_upper_player_gets_the_upper_note_only(self):
        on, c, div, _ = R1._place(BAR, True)
        self.assertEqual(_hidden_pitches(on, div), [("1", "G4")])                 # Gb4, the upper note -- never Ab3
        self.assertEqual(c["two_voice_unison_copies_kept_chord_upper"], 1)
        self.assertEqual(c["two_voice_unison_copies_kept_chord_lower"], 0)
        printed = _printed_pitches(on, div)
        self.assertIn(("2", "A3", False), printed)                               # the page's chord is untouched: both heads, voice 2
        self.assertIn(("2", "G4", True), printed)

    def test_printed_in_voice_1_the_lower_player_gets_the_lower_note_only(self):
        # CONSTRUCTED from the real events: the record's chord (voice 2) put in voice 1, the held quarter and rest as they are
        streams, meter, div = R1._bar(BAR)
        q1, rest, q2, chord = streams[0][0], streams[0][1], streams[1][0], streams[1][-1]
        counters = collections.Counter()
        with mock.patch.dict(os.environ, {ENV: "1"}):
            placed = E._place_voices_in_time([[q1, rest, chord], [q2, rest]], meter, div, [], counters, family=E.FAMILY_WIND)
        self.assertIsNotNone(placed)
        self.assertEqual(R1._kinds(placed[1])[-1], E.UNISON_COPY_KIND)
        self.assertEqual(_hidden_pitches(placed, div), [("2", "A3")])             # Ab3, the LOWER note only
        self.assertEqual(counters["two_voice_unison_copies_kept_chord_lower"], 1)

    def test_round_1_copied_both_notes(self):
        # the control fails on round 1's behaviour: with no head taken (what round 1 wrote) both notes land in the other voice
        on, _c, div, _ = R1._place(BAR, True)
        on[0][-1].pop("take")
        self.assertEqual(sorted(_hidden_pitches(on, div)), [("1", "A3"), ("1", "G4")])

    def test_printed_notes_do_not_change_against_flag_off(self):
        on, _c, div, _ = R1._place(BAR, True)
        off, _c2, _d, _m = R1._place(BAR, False)
        self.assertEqual(R1._printed(R1._xml_voices(on, div)), R1._printed(R1._xml_voices(off, div)))

    def test_a_chord_of_three_notes_is_left_as_the_forward_and_counted(self):
        streams, meter, div = R1._bar(BAR)
        chord = streams[1][-1]
        third = copy.deepcopy(chord["noteheads"][0])
        third["pitch"] = "Db4"
        third["bbox"] = [1226, 350, 144, 121]
        chord["noteheads"].insert(1, third)
        counters = collections.Counter()
        with mock.patch.dict(os.environ, {ENV: "1"}):
            placed = E._place_voices_in_time(copy.deepcopy(streams), meter, div, [], counters, family=E.FAMILY_WIND)
        with mock.patch.dict(os.environ, {ENV: "0"}):
            off = E._place_voices_in_time(copy.deepcopy(streams), meter, div, [], collections.Counter(), family=E.FAMILY_WIND)
        self.assertEqual(R1._kinds(placed[0])[-1], E.FORWARD_KIND)
        self.assertEqual(R1._kinds(placed[0]), R1._kinds(off[0]))                # exactly as flag off writes it
        self.assertEqual(counters["two_voice_unison_marks_left_three_plus_chord"], 1)
        self.assertEqual(sum(v for k, v in counters.items() if k.startswith("two_voice_unison_copies_kept_chord")), 0)

    def test_a_copys_tie_is_dropped_where_its_partner_is_not_in_its_voice(self):
        streams, meter, div = R1._bar(BAR)
        for h in streams[1][-1]["noteheads"]:
            h["tied_to_next"] = True
        with mock.patch.dict(os.environ, {ENV: "1"}):
            placed = E._place_voices_in_time(streams, meter, div, [], collections.Counter(), family=E.FAMILY_WIND)
        lines, _u = E._measure_events_xml(placed[0], div, collections.Counter(), voice=1)
        self.assertTrue(any('print-object="no"' in ln and '<tie type="start"' in ln for ln in lines))       # carried by the copy ...
        out = E._drop_dangling_unison_ties(["<measure>"] + lines + ["</measure>"])
        self.assertFalse(any('print-object="no"' in ln and '<tie type="start"' in ln for ln in out))        # ... dropped: no partner in its voice


class TestByTheStaffsInstrument(unittest.TestCase):
    """Sean 2026-11-19: one note each only where the instrument plays one note at a time; strings keep the chord (double/triple/quadruple
    stops); timpani, harp and piano are one player per staff; an instrument not known takes neither rule. The real bassoon bar 80 events, the
    family set by the test (the family is what the record's `Q.PART_NAME` says; see `staff_unison_family`)."""

    def _on(self, family):
        streams, meter, div = R1._bar(BAR)
        counters = collections.Counter()
        with mock.patch.dict(os.environ, {ENV: "1"}):
            placed = E._place_voices_in_time(streams, meter, div, [], counters, family=family)
        return placed, counters, div

    def test_a_string_staff_keeps_the_whole_chord_for_both_voices(self):
        placed, c, div = self._on(E.FAMILY_STRING)
        self.assertEqual(sorted(_hidden_pitches(placed, div)), [("1", "A3"), ("1", "G4")])
        self.assertEqual(c["two_voice_unison_copies_kept_chord_whole"], 1)
        self.assertEqual(c["two_voice_unison_bars_string"], 1)
        wind, _c, _d = self._on(E.FAMILY_WIND)
        self.assertEqual(len(_hidden_pitches(wind, div)), 1)                     # the control can fail: a wind staff splits it

    def test_a_string_chord_of_three_is_kept_whole_too(self):
        streams, meter, div = R1._bar(BAR)
        chord = streams[1][-1]
        third = copy.deepcopy(chord["noteheads"][0])
        third["pitch"] = "Db4"
        third["bbox"] = [1226, 350, 144, 121]
        chord["noteheads"].insert(1, third)
        with mock.patch.dict(os.environ, {ENV: "1"}):
            placed = E._place_voices_in_time(streams, meter, div, [], collections.Counter(), family=E.FAMILY_STRING)
        self.assertEqual(len(_hidden_pitches(placed, div)), 3)

    def test_one_player_and_unknown_staves_are_written_as_flag_off(self):
        for fam, key in ((E.FAMILY_ONE_PLAYER, "one_player_staff"), (E.FAMILY_UNKNOWN, "instrument_not_known"), (None, "instrument_not_known")):
            placed, c, div = self._on(fam)
            off, _c, _d, _m = R1._place(BAR, False)
            self.assertEqual(R1._kinds(placed[0]), R1._kinds(off[0]))
            self.assertEqual(R1._kinds(placed[1]), R1._kinds(off[1]))
            self.assertEqual(c["two_voice_unison_copies_kept"], 0)
            self.assertEqual(_hidden_pitches(placed, div), [])
            self.assertEqual(c["two_voice_unison_marks_left_" + key], 2)        # the lone rest and the lone chord
            self.assertEqual(c["two_voice_unison_bars_" + key], 1)

    def test_the_family_comes_from_the_instrument_the_record_holds(self):
        for name, want in (("Bassoon", E.FAMILY_WIND), ("Horn", E.FAMILY_WIND), ("Violin", E.FAMILY_STRING), ("Cello", E.FAMILY_STRING),
                           ("Timpani", E.FAMILY_ONE_PLAYER), ("Harp", E.FAMILY_ONE_PLAYER), ("Piano", E.FAMILY_ONE_PLAYER),
                           ("Chorus", E.FAMILY_UNKNOWN), ("not an instrument", E.FAMILY_UNKNOWN), (None, E.FAMILY_UNKNOWN)):
            self.assertEqual(E.staff_unison_family(name), want, name)


if __name__ == "__main__":
    unittest.main()
