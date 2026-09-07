"""The off-roster deduced-name veto.

Every test here was run RED first, by breaking the mechanism it guards — the
list of which break makes which test fail is in
`benchmarks/omr-brahms-tuba-2026-09/verify_red.sh`.

The fixture is Brahms 1 / Breitkopf's finale, reduced to what the rule reads:
sixteen slots, fifteen named from a margin label or the document roster, and
slot 9 — the SECOND TROMBONE STAFF of a section braced over two staves —
deduced as `Tuba` by the score-order prior, in a work whose roster is
`3 trombones, 0 tuba`.
"""
from __future__ import annotations

import unittest

from tools.omr.absent_instrument import find_vetoes
from tools.omr.offroster_name import (VETOABLE_SOURCES, enabled,
                                      find_offroster_vetoes, summarise)

FINALE = ["Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon", "Horn",
          "Horn", "Trumpet", "Trombone", "Tuba", "Timpani", "Violin",
          "Violin", "Viola", "Cello", "Contrabass"]
#: The work's IMSLP roster, `source_kind: catalog` — no tuba.
ROSTER = {"Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon", "Horn",
          "Trumpet", "Trombone", "Timpani", "Violin", "Viola", "Cello",
          "Contrabass"}


def _page(page_index: int, source_of_9: str = "score_order"):
    names = {i: n for i, n in enumerate(FINALE)}
    source = {i: "label" for i in range(16)}
    source[6] = "roster"
    source[9] = source_of_9
    keys = [(page_index, 0, i) for i in range(16)]
    slot_by_staff = {k: k[2] for k in keys}
    return keys, slot_by_staff, names, source


class TestTheRule(unittest.TestCase):

    def test_a_deduced_offroster_name_is_vetoed(self):
        keys, slots, names, source = _page(45)
        v = find_offroster_vetoes(
            staff_keys=keys, slot_by_staff=slots,
            instrument_name_by_slot=names, instrument_source=source,
            admissible=ROSTER)
        self.assertEqual([r["slot"] for r in v], [9])
        self.assertEqual(v[0]["instrument"], "Tuba")
        self.assertEqual(v[0]["source"], "score_order")

    def test_every_on_roster_name_survives(self):
        keys, slots, names, source = _page(45)
        v = find_offroster_vetoes(
            staff_keys=keys, slot_by_staff=slots,
            instrument_name_by_slot=names, instrument_source=source,
            admissible=ROSTER)
        self.assertNotIn("Trombone", {r["instrument"] for r in v})
        self.assertEqual(len(v), 1)

    def test_a_read_name_is_never_vetoed_even_off_roster(self):
        """The veto is about DEDUCTION. A label is a reading and out of scope.

        If the margin actually prints `Tuba` on a work whose roster has none,
        that is a lexicon or an OCR fault and belongs to the reader — the same
        boundary `absent_instrument.py` draws with "the staff speaks for
        itself".
        """
        keys, slots, names, source = _page(45, source_of_9="label")
        v = find_offroster_vetoes(
            staff_keys=keys, slot_by_staff=slots,
            instrument_name_by_slot=names, instrument_source=source,
            admissible=ROSTER)
        self.assertEqual(v, [])

    def test_a_disambiguated_label_is_out_of_scope(self):
        """`score_order_ambiguity` is a LABEL the prior chose a reading for."""
        self.assertNotIn("score_order_ambiguity", VETOABLE_SOURCES)
        keys, slots, names, source = _page(
            45, source_of_9="score_order_ambiguity")
        v = find_offroster_vetoes(
            staff_keys=keys, slot_by_staff=slots,
            instrument_name_by_slot=names, instrument_source=source,
            admissible=ROSTER)
        self.assertEqual(v, [])

    def test_the_staffs_own_label_does_NOT_exempt_it(self):
        """The measured reversal. See the module docstring.

        `absent_instrument.py` exempts a staff that speaks for itself, because
        there the staff's own label CORROBORATES the carried name. Here the
        name is deduced and the staff's own label CONTRADICTS it — and on four
        full finale systems of Brahms 1 the page reads `Trombone`, the truth
        says `Trombone`, and the exemption would keep `Tuba`.
        """
        keys, slots, names, source = _page(45)
        v = find_offroster_vetoes(
            staff_keys=keys, slot_by_staff=slots,
            instrument_name_by_slot=names, instrument_source=source,
            admissible=ROSTER, evidence={45: {9: "Trombone"}})
        self.assertEqual([r["slot"] for r in v], [9])
        self.assertEqual(v[0]["read"], "Trombone",
                         "the contradicting label is REPORTED on the record")


class TestItAbstainsRatherThanStrips(unittest.TestCase):
    """The most dangerous failure available to this layer, guarded first."""

    def test_no_roster_vetoes_nothing(self):
        keys, slots, names, source = _page(45)
        for admissible in (None, set(), frozenset()):
            with self.subTest(admissible=admissible):
                self.assertEqual(find_offroster_vetoes(
                    staff_keys=keys, slot_by_staff=slots,
                    instrument_name_by_slot=names, instrument_source=source,
                    admissible=admissible), [])

    def test_the_summary_distinguishes_abstention_from_a_clean_run(self):
        s_none = summarise([], None, None)
        s_clean = summarise([], ROSTER, "brahms--symphony-1")
        self.assertIsNone(s_none["roster"])
        self.assertIsNotNone(s_clean["roster"])
        self.assertEqual(s_none["staff_records_vetoed"], 0)
        self.assertEqual(s_clean["staff_records_vetoed"], 0)


class TestTheFlag(unittest.TestCase):

    def test_default_is_off(self):
        self.assertFalse(enabled({}))

    def test_the_accepted_spellings(self):
        for raw in ("1", "on", "true", "YES", " On "):
            self.assertTrue(enabled({"OMR_ROSTER_SCORE_ORDER_VETO": raw}), raw)
        for raw in ("0", "off", "", "no", "report"):
            self.assertFalse(enabled({"OMR_ROSTER_SCORE_ORDER_VETO": raw}), raw)


class TestTheAttestationVetoCannotDoThis(unittest.TestCase):
    """Measured, not assumed — and the reason is worth pinning.

    `absent_instrument.find_vetoes` is blind to this for TWO independent
    reasons, so widening only the first would change nothing. Both are asserted
    here so a future session cannot "fix" this by relaxing `VETOABLE_SOURCES`
    over there and believe it worked.
    """

    def _evidence(self):
        # Every slot but 9 attested on the page; `Tuba` attested nowhere.
        return {45: {i: FINALE[i] for i in range(16) if i != 9}}

    def test_it_is_out_of_scope_by_source(self):
        from tools.omr import absent_instrument as ai
        self.assertEqual(ai.VETOABLE_SOURCES, ("label",))

    def test_and_admitting_the_source_still_does_not_catch_it(self):
        keys, slots, names, source = _page(45)
        v = find_vetoes(
            staff_keys=keys, slot_by_staff=slots,
            instrument_name_by_slot=names,
            # the source scope widened by hand, which is the "obvious fix"
            instrument_source={k: "label" for k in source},
            evidence=self._evidence(), window=0, rule="span",
            anchored_exempt=False, reference_size=16)
        self.assertEqual([r for r in v if r["instrument"] == "Tuba"], [],
                         "an attestation test cannot speak to a name that was "
                         "never attested anywhere")


class TestTheWiring(unittest.TestCase):
    """Source-level anti-drift, in the shape `TestEventlessMeasureKeepsItsMarks`
    uses — because the alternative harness cannot see this half.

    `benchmarks/omr-spans-veto-composition-2026-09/probe/compose.py`, which is
    what every arm in this thread runs, builds its result as
    `[{"page_index": i, "systems": []}]` and feeds the staves in separately, so
    the loop that writes `instrument_veto` onto a staff dict iterates NOTHING
    there. The end-to-end probe therefore proves the rule and the summary and
    says nothing at all about the marker. These do.
    """

    def _source(self) -> str:
        from tools.omr import contextual
        return __import__("pathlib").Path(contextual.__file__).read_text()

    def test_the_veto_reaches_the_names(self):
        """Its keys must join `vetoed_keys`, which is what withholds a name."""
        src = self._source()
        self.assertIn("vetoed_keys = vetoed_keys | offroster_vetoed_keys", src)

    def test_the_two_vetoes_keep_separate_markers(self):
        """One asks 'was this read near here', the other 'can it be right'.

        Merging the markers would make a refusal unattributable on the record.
        """
        src = self._source()
        self.assertIn('"offroster_name" if key in offroster_vetoed_keys', src)
        self.assertIn('else "absent_instrument"', src)

    def test_the_blast_radius_is_the_exported_name_and_nothing_else(self):
        """A `score_order` name reaches NO consumer except `<part-name>`.

        This is what makes the change priceable without running either
        benchmark family, so it is pinned rather than argued:

        * `contextual._not_clef_evidence` holds `score_order`, so
          `read_instruments` — the only instrument map `clef_correction` is
          ever handed — cannot contain a deduced slot. Both the FILL path and
          the `treble_override` path are therefore unreachable for one, the
          latter twice over (it also tests `sources.get(slot) == "label"`);
        * `_dedupe_cross_staff_detections`' written-range veto runs BEFORE the
          contextual pass and off the dossier, not off these names;
        * `label_contradiction` and `transcribe` only REPORT the source.

        So removing a deduced name changes the exported part name and the
        reports, and musicdiff does not score `<part-name>`.
        """
        src = self._source()
        self.assertIn('_not_clef_evidence = {"score_order"}', src)
        self.assertIn("if instrument_source.get(slot) not in "
                      "_not_clef_evidence", src)

    def test_it_reads_no_catalog_of_its_own(self):
        """The supplier is `work_roster.py`; a second reader is how two
        rosters come to disagree."""
        from tools.omr import offroster_name
        src = __import__("pathlib").Path(offroster_name.__file__).read_text()
        for forbidden in ("catalog.json", "json.load", "open("):
            self.assertNotIn(forbidden, src.split('"""', 2)[-1],
                             f"{forbidden} in the module body")


if __name__ == "__main__":
    unittest.main()
