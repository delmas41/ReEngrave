"""ROADMAP 2.90. Two voices at one x are written as two voices.

The staged exporter's heads carried no stem direction, so
`voicing.group_chords_in_measure`'s divisi guard (opposite stem directions never
merge) could not fire: two voices at one onset were fused into one chord, and
2.89 then refused the chord where the heads' values disagreed. The record HAS
each head's decided `Q.STEM_DIRECTION` / `Q.HEAD_STEM`; EXPORT now carries them.

A bar keeps the directions (two voices) only where EVERY chord of the bar has a
decided direction AND the two streams carry equal time; otherwise it is left
exactly as 2.89 left it. Heads on one stem stay one chord.
"""
import os
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from tools.omr.staged import export as SX
from tools.omr.staged.record import Q
from tools.omr.tests.test_staged_export import _one_staff_page, _vrd, QUARTER

HALF = {"beats": 2.0, "written": 2.0, "dots": 0}
METER_24 = {"numerator": 2, "denominator": 4, "raw": "2/4"}


def _stems(page, gi, direction=None, stem=None, n0=2000):
    sub = f"glyph/0/0/0/0/{gi}"
    if direction is not None:
        page["record"]["verdicts"].append(
            _vrd(n0 + 2 * gi, sub, Q.STEM_DIRECTION, direction))
    if stem is not None:
        page["record"]["verdicts"].append(
            _vrd(n0 + 2 * gi + 1, sub, Q.HEAD_STEM, stem))


def _place(page, xs):
    """Put head gi at x = xs[gi] (heads at one x stand in one column)."""
    k = 0
    for o in page["record"]["observations"]:
        if o["quantity"] == "glyph_box":
            o["value"][1] = xs[k]
            k += 1
    return page


def _two_voices_page(*, directions=("up", "down", "down"),
                     stems=("obs:A", "obs:B", "obs:C"),
                     durs=(HALF, QUARTER, QUARTER), xs=(100, 100, 300),
                     pitches=("E5", "C4", "D4")):
    """2/4. Up voice: one half note. Down voice: two quarters. The first head of
    each voice stands at x=100, so they are one onset column."""
    page = _one_staff_page(notes=list(zip(pitches, durs)), meter=METER_24)
    _place(page, xs)
    for gi, (d, st) in enumerate(zip(directions, stems)):
        _stems(page, gi, d, st)
    return page


def _notes(xml):
    out = []
    for n in ET.fromstring(xml).findall(".//note"):
        if n.find("pitch") is not None:
            out.append((n.find("pitch/step").text + n.find("pitch/octave").text,
                        n.find("voice").text if n.find("voice") is not None else None))
    return out


class TestTwoVoicesAtOneXAreTwoVoices(unittest.TestCase):
    def test_a_pair_on_opposite_decided_stems_is_written_as_two_voices(self):
        xml, rep = SX.to_musicxml(_two_voices_page())
        self.assertNotIn("chord_value_undecided", rep["notes_not_written"])
        self.assertEqual(dict(_notes(xml)), {"E5": "1", "C4": "2", "D4": "2"})
        self.assertEqual(rep["written"]["two_voice_bars"], 1)
        self.assertEqual(rep["written"]["two_voice_bars_from_exporter_stems"], 1)
        self.assertTrue(rep["balance"]["balanced"])

    def test_each_head_keeps_its_own_value(self):
        xml, _rep = SX.to_musicxml(_two_voices_page())
        types = [(n.find("pitch/step").text, n.find("type").text)
                 for n in ET.fromstring(xml).findall(".//note")
                 if n.find("pitch") is not None]
        self.assertEqual(sorted(types), [("C", "quarter"), ("D", "quarter"),
                                         ("E", "half")])

    def test_RED_CONTROL_without_the_carried_stems_the_pair_is_refused(self):
        """The pre-2.90 state: the same record with no stem verdicts. If this
        stopped being refused the test above would prove nothing."""
        page = _two_voices_page(directions=(None, None, None), stems=(None,) * 3)
        # ROADMAP 2.117 is ON by default and would keep the D; this pins the
        # whole-bar hold-out, so the flag is set off explicitly.
        with mock.patch.dict(os.environ, {"OMR_PARTIAL_BARS": "off"}):
            xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["notes_not_written"]["chord_value_undecided"], 2)
        self.assertEqual(_notes(xml), [])  # bar held out / padded, 3 notes gone
        self.assertTrue(rep["balance"]["balanced"])

    def test_the_accounting_equality_holds_both_ways(self):
        for page in (_two_voices_page(),
                     _two_voices_page(directions=(None,) * 3, stems=(None,) * 3)):
            _xml, rep = SX.to_musicxml(page)
            self.assertTrue(rep["balance"]["balanced"])


class TestWhatStaysAsItWas(unittest.TestCase):
    def test_POSITIVE_CONTROL_one_stem_two_heads_disagreeing_is_still_refused(self):
        """Two heads on ONE stem are one chord (2.78); disagreeing values stay
        refused by 2.89 and are never made into two voices."""
        page = _two_voices_page(directions=("up", "up", "up"),
                                stems=("obs:A", "obs:A", "obs:A"))
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["notes_not_written"]["chord_value_undecided"], 2)
        self.assertNotIn("two_voice_bars_from_exporter_stems", rep["written"])

    def test_one_stem_never_becomes_two_voices_even_if_the_record_says_so(self):
        page = _two_voices_page(directions=("up", "down", "down"),
                                stems=("obs:A", "obs:A", "obs:C"))
        _xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["notes_not_written"]["chord_value_undecided"], 2)
        self.assertEqual(
            rep["part_join"]["divisi_at_export"]["stems_with_two_directions_taken_off"], 1)

    def test_an_undecided_direction_elsewhere_in_the_bar_leaves_it_fused(self):
        """Voice 1 is where `split_events_into_voices` puts an unknown event: a
        guess about a stem nobody read. The bar is left as 2.89 left it."""
        page = _two_voices_page(directions=("up", "down", None),
                                stems=("obs:A", "obs:B", None))
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["notes_not_written"]["chord_value_undecided"], 2)
        self.assertEqual(
            rep["part_join"]["divisi_at_export"]["bars_left_fused_an_undecided_direction_in_the_bar"], 1)
        self.assertNotIn("two_voice_bars_from_exporter_stems", rep["written"])
        self.assertTrue(rep["balance"]["balanced"])

    def test_streams_of_unequal_time_leave_the_bar_fused(self):
        page = _two_voices_page(durs=(HALF, QUARTER, HALF))      # 2 vs 3 quarters
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(
            rep["part_join"]["divisi_at_export"]["bars_left_fused_streams_carry_unequal_time"], 1)
        self.assertTrue(rep["balance"]["balanced"])

    def test_opposite_directions_that_AGREE_in_value_still_write_both_notes(self):
        page = _two_voices_page(durs=(HALF, HALF, None), directions=("up", "down", None),
                                stems=("obs:A", "obs:B", None))
        # a 2/4 bar of two half notes in two voices: nothing is lost by the carry
        page["record"]["observations"] = [
            o for o in page["record"]["observations"]
            if not o["subject"].endswith("/2")]
        page["record"]["verdicts"] = [
            v for v in page["record"]["verdicts"] if not v["subject"].endswith("/2")]
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(sorted(p for p, _ in _notes(xml)), ["C4", "E5"])
        self.assertTrue(rep["balance"]["balanced"])


class TestTheSplitIsTheExportersOwnAndOnlyForPairs(unittest.TestCase):
    def test_divisi_pairs_needs_opposite_directions_at_one_onset(self):
        def ev(x, d):
            return {"kind": "chord", "x_position": x, "stem_direction": d,
                    "noteheads": [{"bbox": [0, 0, 40, 40]}]}
        self.assertEqual(len(SX._divisi_pairs([ev(100, "up"), ev(110, "down")])), 1)
        self.assertEqual(SX._divisi_pairs([ev(100, "up"), ev(300, "down")]), [])
        self.assertEqual(SX._divisi_pairs([ev(100, "up"), ev(100, "up")]), [])
        self.assertEqual(SX._divisi_pairs([ev(100, "up"), ev(100, None)]), [])


if __name__ == "__main__":
    unittest.main()
