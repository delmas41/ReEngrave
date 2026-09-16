"""A part TACET on a system must still hold that system's bars — if it can.

⚠️ The defect these pin: `_part_xml` walked the part's own RUNS, so a part
whose staff is suppressed on a system wrote nothing at all for it. On Litolff
Beethoven 5 pp.1-4 three parts held 93 measures against eight parts' 111, and
one part simply STOPPED after bar 16.

⚠️⚠️ AND THE HALF THAT MATTERS MORE: a MusicXML rest carries a `<duration>`,
and `_measure_rest_beats` falls back to **4.0** when no meter was read — so
padding a 2/4 bar off an unread meter writes a rest twice too long. Nothing
forces a tacet bar to exist; it is ours to invent or not. So the rule REFUSES
where the length is unknown, and half of these tests are about that refusal.

⚠️ THESE DRIVE `to_musicxml` END TO END rather than `_pad_tacet_span` alone,
because the benchmark arm beside them cannot: a cloud container has no weights,
so that arm splices measures into an ALREADY-EXPORTED file and is structurally
blind to everything upstream of `_part_xml`. The two instruments have opposite
blind spots on purpose.
"""

import re
import unittest

from tools.omr.staged import export as SX
from tools.omr.staged.record import Q


M24 = {"numerator": 2, "denominator": 4}
M34 = {"numerator": 3, "denominator": 4}


def _log_json(verdicts):
    return {"record": {"observations": [], "verdicts": list(verdicts),
                       "abstentions": [], "counts": {}},
            "summary": {}}


def _vrd(i, subject, quantity, value, outcome="decided", reason="x"):
    return {"id": f"vrd:{i:06d}", "subject": subject, "quantity": quantity,
            "outcome": outcome, "value": value, "decider": "t",
            "reason": reason, "considered": [], "used": [], "missing": [],
            "declined": [], "excluded": [], "correlated": [],
            "candidates": [], "basis": [], "margin": None,
            "supersedes": None, "detail": {}}


def _page(systems, meters=None, *, slots=None, join="slot"):
    """`systems` = [[(staff, slot, n_measures_or_None), ...], ...] per system.

    `meters` is one `Q.METER` value per system, or None for a system whose
    meter was never read — which is the whole point of half this file.
    """
    meters = meters or [None] * len(systems)
    vrd, n = [], 0
    for sysi, staves in enumerate(systems):
        for staff, slot, nm in staves:
            key = f"staff/0/{sysi}/{staff}"
            if nm is None:
                vrd.append(_vrd(n, key, Q.MEASURE_PARTITION, None,
                                outcome="abstained", reason="no_barlines"))
            else:
                vrd.append(_vrd(n, key, Q.MEASURE_PARTITION, nm))
            n += 1
            vrd.append(_vrd(n, key, Q.CLEF, "treble"))
            n += 1
            if slot is not None:
                vrd.append(_vrd(n, key, Q.SLOT_INDEX, slot))
                n += 1
        vrd.append(_vrd(n, f"system/0/{sysi}", Q.SYSTEM_STAFF_COUNT,
                        len(staves)))
        n += 1
        if meters[sysi] is not None:
            vrd.append(_vrd(n, f"system/0/{sysi}", Q.METER, meters[sysi]))
            n += 1
    value = ({"join": "slot", "slots": slots or []} if join == "slot"
             else {"join": "ordinal", "staves_per_system": len(systems[0])})
    vrd.append(_vrd(9999, "document", Q.PART_PARTITION, value, reason=join))
    return _log_json(vrd)


def _measures(xml):
    """`{part id: [(number, block)]}` straight out of the emitted text."""
    out = {}
    for chunk in re.split(r'(?=  <part id=")', xml):
        m = re.match(r'  <part id="(P\d+)"', chunk)
        if m:
            out[m.group(1)] = [
                (int(mo.group(1)), mo.group(0)) for mo in
                re.finditer(r'<measure number="(\d+)">.*?</measure>',
                            chunk, re.S)]
    return out


def _numbers(xml):
    return {pid: [n for n, _b in rows] for pid, rows in _measures(xml).items()}


#: One staff on system 0, TWO on system 1 — so P2 is tacet on system 0, which
#: is the shape a printed score makes whenever a part enters late.
SYSTEMS = [[(0, 0, 3)], [(0, 0, 2), (1, 1, 2)]]
KNOWN = _page(SYSTEMS, [M24, M24], slots=[0, 1])
UNKNOWN = _page(SYSTEMS, [None, None], slots=[0, 1])


class TestATacetSpanIsPadded(unittest.TestCase):
    def test_the_tacet_part_holds_the_systems_bars_it_does_not_print(self):
        """⚠️ THE WHOLE DEFECT. P2 held two measures where the document has
        five, so a reader asking for bar 2 got nothing from it."""
        xml, rep = SX.to_musicxml(KNOWN)
        self.assertEqual(_numbers(xml)["P1"], [1, 2, 3, 4, 5])
        self.assertEqual(_numbers(xml)["P2"], [1, 2, 3, 4, 5])
        self.assertEqual(rep["tacet_padding"]["bars_padded"], 3)

    def test_a_padded_bar_is_a_full_measure_rest_SIZED_TO_THE_BAR(self):
        """Not a whole rest: `measure="yes"` and the meter's own length."""
        xml, rep = SX.to_musicxml(KNOWN)
        div = rep["written"]["divisions"]
        block = dict(_measures(xml)["P2"])[1]
        self.assertIn('<rest measure="yes"/>', block)
        self.assertIn(f"<duration>{int(2 * 4.0 / 4 * div)}</duration>", block)
        self.assertNotIn("<pitch>", block)
        # ⚠️ AND NOT A `<type>`: a measure rest names the BAR, and writing
        # `<type>half</type>` beside it is the right number by the wrong
        # reasoning -- the hazard `size_measure_rest` records.
        self.assertNotIn("<type>", block)

    def test_a_padded_bar_states_no_clef_and_no_key(self):
        """It is not printed here; we have neither, and inventing one would
        put this part on a staff the page does not give it."""
        xml, _ = SX.to_musicxml(KNOWN)
        for n in (1, 2, 3):
            block = dict(_measures(xml)["P2"])[n]
            self.assertNotIn("<clef>", block)
            self.assertNotIn("<key>", block)

    def test_padding_ADDS_measures_and_changes_none_of_the_part_s_own(self):
        """⚠️ THE CONTROL THAT MATTERS, and it is why `_pad_tacet_span` leaves
        `prev` alone. Here it is asserted on the part's own `<note>` content
        and on the numbers; the BYTE-level form — *delete exactly the inserted
        blocks and the base file comes back* — needs a real document and lives
        in `benchmarks/omr-tacet-padding-2026-09/probe/padding_arm.py`.

        ⚠️ The attribute stream legitimately DOES differ at bar 4: a padded
        span states no clef, so the first real run after it still finds `prev`
        at its sentinel and writes its clef, exactly as it would have if it
        were the part's opening measure — which it was, before padding."""
        on, _ = SX.to_musicxml(KNOWN)
        self.assertEqual(_numbers(on)["P2"], [1, 2, 3, 4, 5])
        added = set(_numbers(on)["P2"]) - {4, 5}
        self.assertEqual(added, {1, 2, 3})
        # P1 is tacet nowhere, so its rendering of system 1's two bars is what
        # P2's OWN two bars must still be: same staff shape, same meter.
        mine = [b for n, b in _measures(on)["P2"] if n in (4, 5)]
        theirs = [b for n, b in _measures(on)["P1"] if n in (4, 5)]
        notes = lambda bs: re.findall(          # noqa: E731
            r"<note>.*?</note>", "".join(bs), re.S)
        self.assertTrue(notes(mine))            # positive control: not empty
        self.assertEqual(notes(mine), notes(theirs))

    def test_a_LEADING_pad_still_declares_divisions(self):
        """A part tacet on the document's FIRST system would otherwise open
        with a measure carrying no `<attributes>` at all."""
        xml, _ = SX.to_musicxml(KNOWN)
        first_block = dict(_measures(xml)["P2"])[1]
        self.assertIn("<divisions>", first_block)
        # ...and the real run that follows does NOT restate them
        self.assertNotIn("<divisions>", dict(_measures(xml)["P2"])[4])

    def test_the_meter_is_asked_PER_BAR_not_per_system(self):
        """⚠️ A system can print a meter CHANGE part-way through. A span that
        took one meter for the whole system is the fault `_part_xml` carried
        for a year, reintroduced in a new branch."""
        segmented = {"numerator": 2, "denominator": 4,
                     "segments": [{"from_cell": 0, "numerator": 2,
                                   "denominator": 4},
                                  {"from_cell": 2, "numerator": 3,
                                   "denominator": 4}]}
        xml, rep = SX.to_musicxml(_page(SYSTEMS, [segmented, M24],
                                        slots=[0, 1]))
        div = rep["written"]["divisions"]
        blocks = dict(_measures(xml)["P2"])
        self.assertIn(f"<duration>{div * 2}</duration>", blocks[1])
        self.assertIn(f"<duration>{div * 2}</duration>", blocks[2])
        self.assertIn(f"<duration>{div * 3}</duration>", blocks[3])


class TestWhereTheLengthIsUnknownItIsRefused(unittest.TestCase):
    def test_no_meter_means_NO_padded_bar(self):
        """⚠️⚠️ THE REFUSAL. `_measure_rest_beats(None)` is 4.0 — a whole
        rest — and on a 2/4 document that is twice the bar. A tacet bar does
        not have to be written at all, so it is not."""
        xml, rep = SX.to_musicxml(UNKNOWN)
        self.assertEqual(_numbers(xml)["P2"], [4, 5])
        self.assertEqual(rep["tacet_padding"]["bars_padded"], 0)
        self.assertEqual(
            rep["tacet_padding"]["bars_not_padded_without_meter"], 3)

    def test_the_POSITIVE_CONTROL_in_the_same_class(self):
        """⚠️ A battery of refusal tests passes by refusing everything. The
        SAME page with a meter read on it pads all three bars."""
        _xml_off, rep_off = SX.to_musicxml(UNKNOWN)
        _xml_on, rep_on = SX.to_musicxml(KNOWN)
        self.assertEqual(rep_off["tacet_padding"]["bars_padded"], 0)
        self.assertEqual(rep_on["tacet_padding"]["bars_padded"], 3)

    def test_it_pads_the_bars_it_CAN_and_counts_the_rest(self):
        """A meter on one system and not another: per-bar, not all-or-none."""
        xml, rep = SX.to_musicxml(_page(
            [[(0, 0, 3)], [(0, 0, 2)], [(0, 0, 2), (1, 1, 2)]],
            [M24, None, M24], slots=[0, 1]))
        self.assertEqual(rep["tacet_padding"]["bars_padded"], 3)
        self.assertEqual(
            rep["tacet_padding"]["bars_not_padded_without_meter"], 2)
        self.assertEqual(_numbers(xml)["P2"], [1, 2, 3, 6, 7])

    def test_the_refusal_INVENTS_NO_BAR_and_the_4_0_fallback_is_not_ours(self):
        """⚠️ THE DISTINCTION THIS WHOLE JOB TURNS ON, asserted rather than
        argued. With no meter, P2's OWN eventless bars 4 and 5 still come out
        as a 4.0 whole rest — that is the exporter's standing behaviour for a
        bar the page PRINTS for this staff, `measure="yes"` withheld, and it
        is what `OMR_METER_CARRY` is for. What the padding must not do is add
        that same fabricated length to bars the page prints for this part NOT
        AT ALL: those numbers stay absent."""
        xml, rep = SX.to_musicxml(UNKNOWN)
        div = rep["written"]["divisions"]
        blocks = dict(_measures(xml)["P2"])
        self.assertEqual(sorted(blocks), [4, 5])          # nothing invented
        # the pre-existing fallback, on the part's OWN bars, unchanged
        self.assertIn(f"<duration>{div * 4}</duration>", blocks[4])
        self.assertNotIn('measure="yes"', blocks[4])


class TestTheReportSaysWhatHappened(unittest.TestCase):
    def test_the_partition_balances(self):
        _xml, rep = SX.to_musicxml(KNOWN)
        t = rep["tacet_padding"]
        self.assertEqual(t["tacet_bar_total"], 3)
        self.assertTrue(t["balanced"])
        self.assertEqual(t["spans"], [{"part": "P2", "systems": ["0/0"],
                                       "bars": 3}])

    def test_the_counters_are_written_even_when_ZERO(self):
        """⚠️ A `Counter` holds only the keys something touched, so *"nothing
        needed padding"* and *"this was never computed"* would read alike —
        the `empty_bars_padded_without_meter` lesson, next door."""
        _xml, rep = SX.to_musicxml(_page([[(0, 0, 2), (1, 1, 2)]], [M24],
                                         slots=[0, 1]))
        self.assertEqual(rep["written"]["tacet_bars_padded"], 0)
        self.assertEqual(
            rep["written"]["tacet_bars_not_padded_without_meter"], 0)
        self.assertEqual(rep["tacet_padding"]["tacet_bar_total"], 0)

    def test_a_REFUSED_number_line_reports_a_reason_and_not_a_zero(self):
        """⚠️ With no bar sequence nothing was even looked at, and that is a
        different fact from "there was nothing to pad"."""
        # two staves of one system reading different lengths: unnumberable
        page = _page([[(0, 0, 3), (1, 1, 2)], [(0, 0, 2), (1, 1, 2)]],
                     [M24, M24], slots=[0, 1])
        _xml, rep = SX.to_musicxml(page)
        self.assertIsNotNone(rep["measure_numbering"].get("refused"))
        t = rep["tacet_padding"]
        self.assertEqual(t["refused"], "the_document_bar_sequence_was_refused")
        self.assertIsNone(t["tacet_bar_total"])
        self.assertEqual(t["bars_padded"], 0)

    def test_padding_does_not_touch_the_eventless_bar_counter(self):
        """⚠️ A bar the page prints and we read nothing in, and a bar the page
        prints for this part not at all, are TWO facts with two repairs.
        `empty_bars_padded` must never absorb a padded tacet bar."""
        _xml, rep = SX.to_musicxml(KNOWN)
        # every real bar here is eventless (no detections in the fixture),
        # so the two counters are both non-zero and must not have merged
        self.assertEqual(rep["written"]["tacet_bars_padded"], 3)
        self.assertEqual(rep["written"]["empty_bars_padded"], 7)


class TestItWritesNoNotes(unittest.TestCase):
    def test_the_note_content_is_identical_with_and_without_padding(self):
        """The padding adds silence; if it ever adds or moves a note the
        change has left its scope."""
        on, _ = SX.to_musicxml(KNOWN)
        off, _ = SX.to_musicxml(UNKNOWN)
        self.assertEqual(re.findall(r"<pitch>.*?</pitch>", on, re.S),
                         re.findall(r"<pitch>.*?</pitch>", off, re.S))
        # positive control: the two files DO differ
        self.assertNotEqual(on, off)


if __name__ == "__main__":
    unittest.main()
