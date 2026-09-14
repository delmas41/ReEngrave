"""`<measure number=N>` must name ONE INSTANT in every part of the file.

⚠️ The defect these pin: `_part_xml` counted 1, 2, 3 … down each part from its
own first bar, so a part whose staff is SUPPRESSED on a system skipped those
bars and every later number in it was short by that system's length. On
Litolff Beethoven 5 pp.1-4 page 4's first system opened at measure 64 or 82
depending on which part you read.

⚠️ AND THESE TESTS DRIVE `to_musicxml` END TO END rather than
`_document_bar_offsets` alone, because the benchmark arm beside them cannot:
a cloud container has no weights, so that arm re-numbers an ALREADY-EXPORTED
file and is structurally blind to everything upstream of `_part_xml`. The two
instruments have opposite blind spots on purpose.
"""

import re
import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import export as SX
from tools.omr.staged.record import Q


def _log_json(observations, verdicts):
    return {"record": {"observations": list(observations),
                       "verdicts": list(verdicts),
                       "abstentions": [], "counts": {}},
            "summary": {}}


def _vrd(i, subject, quantity, value, outcome="decided", reason="x"):
    return {"id": f"vrd:{i:06d}", "subject": subject, "quantity": quantity,
            "outcome": outcome, "value": value, "decider": "t",
            "reason": reason, "considered": [], "used": [], "missing": [],
            "declined": [], "excluded": [], "correlated": [],
            "candidates": [], "basis": [], "margin": None,
            "supersedes": None, "detail": {}}


def _page(systems, *, join="slot", slots=None):
    """`systems` = [[(staff, slot, n_measures_or_None), ...], ...] per system.

    `None` for the measure count means `measure_partition` ABSTAINED on that
    staff — which is NOT the same as a decided zero, and telling them apart is
    what the document numbering needs.
    """
    vrd = []
    n = 0
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
    value = ({"join": "slot", "slots": slots or []} if join == "slot"
             else {"join": "ordinal", "staves_per_system": len(systems[0])})
    vrd.append(_vrd(9999, "document", Q.PART_PARTITION, value, reason=join))
    return _log_json([], vrd)


def _numbers(xml):
    """`{part id: [measure numbers]}` straight out of the emitted text."""
    out = {}
    for chunk in re.split(r'(?=  <part id=")', xml):
        m = re.match(r'  <part id="(P\d+)"', chunk)
        if m:
            out[m.group(1)] = [int(x) for x in
                               re.findall(r'<measure number="(\d+)"', chunk)]
    return out


#: One staff on system 0; TWO on system 1 — so the second part is tacet on the
#: FIRST system, which is the shape whose numbers the incumbent gets wrong.
TACET_FIRST = _page([[(0, 0, 3)],
                     [(0, 0, 2), (1, 1, 2)]], slots=[0, 1])


class TestTheDocumentNumbersTheBars(unittest.TestCase):
    def test_a_part_tacet_on_an_EARLIER_system_still_starts_where_it_stands(self):
        """⚠️ THE WHOLE DEFECT, in four numbers. Under the incumbent the
        second part opened at 1 — naming system 0's first bar, which it does
        not print — instead of at 4."""
        xml, rep = SX.to_musicxml(TACET_FIRST)
        self.assertEqual(rep["measure_numbering"]["scheme"], "document")
        self.assertEqual(rep["measure_numbering"]["document_bars"], 5)
        nums = _numbers(xml)
        self.assertEqual(nums["P1"], [1, 2, 3, 4, 5])
        self.assertEqual(nums["P2"], [4, 5])

    def test_a_number_names_one_instant_and_an_instant_has_one_number(self):
        xml, _ = SX.to_musicxml(TACET_FIRST)
        nums = _numbers(xml)
        # P1's 4th and 5th measures and P2's two are system 1 bars 0 and 1.
        self.assertEqual(nums["P1"][3:], nums["P2"])
        self.assertEqual(len(set(nums["P2"])), len(nums["P2"]))

    def test_the_offsets_are_the_systems_own_bar_counts_accumulated(self):
        _, rep = SX.to_musicxml(TACET_FIRST)
        rows = {r["system"]: r for r in rep["measure_numbering"]["systems"]}
        self.assertEqual(rows["0/0"]["bars"], 3)
        self.assertEqual(rows["0/0"]["offset"], 0)
        self.assertEqual(rows["0/1"]["bars"], 2)
        self.assertEqual(rows["0/1"]["offset"], 3)

    def test_an_ABSTAINING_staff_is_not_a_dissenting_vote_for_zero(self):
        """⚠️ `n_measures` reads 0 for an abstention AND for a decided zero,
        and the tally must not confuse them: one staff saying nothing cannot
        make its system's length undecidable."""
        page = _page([[(0, 0, 3), (1, 1, None)],
                      [(0, 0, 2), (1, 1, 2)]], slots=[0, 1])
        _, rep = SX.to_musicxml(page)
        num = rep["measure_numbering"]
        self.assertEqual(num["scheme"], "document")
        rows = {r["system"]: r for r in num["systems"]}
        self.assertEqual(rows["0/0"]["bars"], 3)
        self.assertEqual(rows["0/0"]["staves_deciding"], 1)


class TestItRefusesRatherThanFabricating(unittest.TestCase):
    """⚠️ A fallback must never convert *"cannot tell"* into a definite
    answer. Each of these is a real condition, and each falls back to the
    exporter's PREVIOUS per-part numbering — never to a guessed offset."""

    def test_staves_that_disagree_about_a_systems_length_refuse_the_scheme(self):
        page = _page([[(0, 0, 3), (1, 1, 4)],
                      [(0, 0, 2), (1, 1, 2)]], slots=[0, 1])
        xml, rep = SX.to_musicxml(page)
        num = rep["measure_numbering"]
        self.assertEqual(num["scheme"], "per_part")
        self.assertEqual(num["refused"],
                         "a_system_bar_count_could_not_be_determined")
        self.assertEqual(num["undetermined_systems"][0]["reason"],
                         "staves_disagree_about_the_bar_count")
        self.assertEqual(num["undetermined_systems"][0]["readings"], [3, 4])
        self.assertIsNone(num["document_bars"])
        # and the file is numbered exactly as it was before this change
        self.assertEqual(_numbers(xml)["P1"], [1, 2, 3, 4, 5])

    def test_a_MAJORITY_is_not_taken_it_is_refused(self):
        """Nine staves say 4 and one says 3. A vote would be *most likely*,
        which is INFER-stage work; a wiring pass may connect a decision and
        may not let one guess."""
        staves = [(i, i, 4) for i in range(9)] + [(9, 9, 3)]
        page = _page([staves], slots=list(range(10)))
        _, rep = SX.to_musicxml(page)
        self.assertEqual(rep["measure_numbering"]["scheme"], "per_part")
        self.assertEqual(rep["measure_numbering"]["undetermined_systems"][0]
                         ["readings"], [3, 4])

    def test_a_system_no_staff_read_refuses_rather_than_counting_it_as_zero(self):
        page = _page([[(0, 0, None), (1, 1, None)],
                      [(0, 0, 2), (1, 1, 2)]], slots=[0, 1])
        _, rep = SX.to_musicxml(page)
        num = rep["measure_numbering"]
        self.assertEqual(num["scheme"], "per_part")
        self.assertEqual(num["undetermined_systems"][0]["reason"],
                         "no_staff_decided_its_bar_count")

    def test_two_runs_of_one_part_on_one_system_refuse(self):
        """Reachable only through the slot join: two staves carrying one slot
        share an offset, so both would emit the same numbers inside one
        part."""
        page = _page([[(0, 0, 2), (1, 0, 2)],
                      [(0, 0, 2)]], slots=[0])
        xml, rep = SX.to_musicxml(page)
        num = rep["measure_numbering"]
        self.assertEqual(num["scheme"], "per_part")
        self.assertEqual(num["refused"], "a_part_holds_two_runs_on_one_system")
        self.assertEqual(num["colliding_systems"], ["0/0"])
        self.assertEqual(_numbers(xml)["P1"], [1, 2, 3, 4, 5, 6])

    def test_the_report_is_written_even_when_the_scheme_fires(self):
        """*"we numbered the document"* and *"this figure was never
        computed"* must not read alike."""
        _, rep = SX.to_musicxml(TACET_FIRST)
        self.assertIn("measure_numbering", rep)
        self.assertNotIn("refused", rep["measure_numbering"])


class TestItWritesNoMusic(unittest.TestCase):
    def test_only_the_number_attribute_moves(self):
        """⚠️ THE CONTROL THAT DECIDES WHETHER THIS JOB STAYED IN SCOPE. The
        same parts rendered under both schemes must be byte-identical once the
        `number=` attribute is blanked — and the POSITIVE control is that with
        it in they differ, or the comparison is being run against two copies
        of one arm."""
        rec = SX.Record(TACET_FIRST)
        parts = SX.build(rec)[0]
        offsets, num = SX._document_bar_offsets(parts)
        self.assertEqual(num["scheme"], "document")
        divisions = SX._divisions(parts)
        import collections
        doc, per = [], []
        for i, part in enumerate(parts):
            doc.append(SX._part_xml(rec, part, f"P{i + 1}", divisions,
                                    collections.Counter(), offsets))
            per.append(SX._part_xml(rec, part, f"P{i + 1}", divisions,
                                    collections.Counter(), None))
        blank = lambda s: re.sub(r'<measure number="\d+">',            # noqa: E731
                                 '<measure number="N">', s)
        self.assertNotEqual(doc, per, "positive control: nothing renumbered")
        self.assertEqual([blank(s) for s in doc], [blank(s) for s in per])

    def test_the_counters_are_identical_under_both_schemes(self):
        rec = SX.Record(TACET_FIRST)
        parts = SX.build(rec)[0]
        offsets, _ = SX._document_bar_offsets(parts)
        divisions = SX._divisions(parts)
        import collections
        got = []
        for offs in (offsets, None):
            c = collections.Counter()
            for i, part in enumerate(parts):
                SX._part_xml(rec, part, f"P{i + 1}", divisions, c, offs)
            got.append(dict(c))
        self.assertEqual(got[0], got[1])

    def test_the_file_still_parses(self):
        xml, _ = SX.to_musicxml(TACET_FIRST)
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, "score-partwise")
        self.assertEqual(len(root.findall("part")), 2)


class TestTheOrdinalJoinIsUnaffected(unittest.TestCase):
    def test_every_part_on_every_system_numbers_identically_either_way(self):
        """A document with no suppressed staff has nothing for this to fix,
        and the numbering must be the SAME — otherwise the change would be
        moving numbers on files it has no business touching."""
        page = _page([[(0, None, 3), (1, None, 3)],
                      [(0, None, 2), (1, None, 2)]], join="ordinal")
        xml, rep = SX.to_musicxml(page)
        self.assertEqual(rep["part_join"]["join_used"], "ordinal")
        self.assertEqual(rep["measure_numbering"]["scheme"], "document")
        self.assertEqual(_numbers(xml)["P1"], [1, 2, 3, 4, 5])
        self.assertEqual(_numbers(xml)["P2"], [1, 2, 3, 4, 5])


if __name__ == "__main__":
    unittest.main()
