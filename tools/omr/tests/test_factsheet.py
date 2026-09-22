"""The fact sheet: provenance by shape, hand facts winning, and the scorecard.

⚠️ Every fixture here is SYNTHETIC. The module reads `library/` and the real
records when it can, and neither is in the tree -- a test that needed them
would pass on one machine and be skipped everywhere else, which is how a
guard stops guarding.
"""

import contextlib
import json
import unittest
from pathlib import Path

from tools.omr import factsheet as F


def _staff(page, sysi, idx, *, label=None, inst=None, reason="label", bars=8):
    subj = f"staff/{page}/{sysi}/{idx}"
    obs = ([{"subject": subj, "quantity": "margin_label", "value": label}]
           if label else [])
    ver = [{"subject": subj, "quantity": "instrument",
            "outcome": "decided" if inst else "abstained",
            "value": {"name": inst} if inst else None, "reason": reason},
           {"subject": subj, "quantity": "clef", "outcome": "decided",
            "value": "treble", "reason": "scored"},
           {"subject": subj, "quantity": "measure_partition",
            "outcome": "decided", "value": bars, "reason": "read"}]
    return obs, ver


def _record(systems):
    """systems: {(page, sys): [(label, instrument), ...]}"""
    obs, ver = [], []
    for (pg, sy), staves in systems.items():
        ver.append({"subject": f"system/{pg}/{sy}",
                    "quantity": "system_membership",
                    "outcome": "decided", "value": len(staves),
                    "reason": "counted"})
        for i, (lab, inst) in enumerate(staves):
            o, v = _staff(pg, sy, i, label=lab, inst=inst,
                          reason="label" if inst else "not_in_lexicon")
            obs += o
            ver += v
    return {"observations": obs, "verdicts": ver, "abstentions": []}


FULL = [("Fl.", "Flute"), ("Ob.", "Oboe"), ("Hr.", "Horn"),
        ("Trp.", "Trumpet"), ("Vl.", "Violin")]


class TestTheShapeCarriesTheProvenance(unittest.TestCase):
    def test_a_bare_leaf_is_a_hand_fact_and_a_dict_one_is_not(self):
        self.assertEqual(F.source_of("Flute"), "hand")
        self.assertEqual(F.source_of(F.fact("Flute", "reader")), "reader")
        self.assertEqual(F.value_of(F.fact("Flute", "reader")), "Flute")
        self.assertEqual(F.value_of("Flute"), "Flute")

    def test_null_is_nobodys_answer_not_a_humans(self):
        self.assertEqual(F.source_of(None), "unread")

    def test_a_container_is_not_a_leaf(self):
        """⚠️ THE REGRESSION. `source_of` answers 'hand' for anything that is
        not a machine fact, so without `is_leaf` a whole sheet reads as one
        hand fact and `merge` returns it untouched -- a believable zero from
        a merge that never ran."""
        self.assertFalse(F.is_leaf({"a": 1}))
        self.assertFalse(F.is_leaf([1, 2]))
        self.assertTrue(F.is_leaf(F.fact(1, "reader")))
        self.assertTrue(F.is_leaf("x"))
        self.assertTrue(F.is_leaf(None))

    def test_fact_refuses_an_unknown_tier(self):
        with self.assertRaises(ValueError):
            F.fact(1, "vibes")

    def test_walk_skips_metadata_so_the_scorecard_counts_only_facts(self):
        sheet = {"sheet_version": 1, "pdf": "x.pdf", "check": ["a"],
                 "_README": "hi", "work": {"a": F.fact(1, "reader")}}
        self.assertEqual([p for p, _ in F.walk(sheet)], ["work.a"])


class TestMergeKeepsTheHumanAndRecoversTheDisagreement(unittest.TestCase):
    def setUp(self):
        self.rec = _record({(0, 0): FULL})
        self.sheet = F.draft("x--imslp999999.pdf", record=self.rec)

    def test_merge_actually_descends(self):
        """The container bug, end to end: a re-draft must update machine
        facts rather than hand the old sheet straight back."""
        old = json.loads(json.dumps(self.sheet))
        old["movement"]["meter"] = None
        merged = F.merge(old, F.draft("x--imslp999999.pdf", record=self.rec))
        self.assertEqual(F.value_of(merged["lineup"]["full"][0]), "Flute")
        self.assertEqual(F.source_of(merged["lineup"]["full"][0]), "reader")

    def test_a_hand_fact_wins_and_the_reader_is_kept_beside_it(self):
        old = json.loads(json.dumps(self.sheet))
        old["lineup"]["full"][3] = "Trombone"
        merged = F.merge(old, self.sheet)
        leaf = merged["lineup"]["full"][3]
        self.assertEqual(F.value_of(leaf), "Trombone")
        self.assertEqual(F.source_of(leaf), "hand")
        self.assertEqual(leaf["reader_said"], "Trumpet")

    def test_agreeing_with_the_reader_is_not_a_disagreement(self):
        old = json.loads(json.dumps(self.sheet))
        old["lineup"]["full"][3] = "Trumpet"          # confirmed, not corrected
        merged = F.merge(old, self.sheet)
        self.assertNotIn("reader_said", merged["lineup"]["full"][3])
        self.assertEqual(F.report(merged)["disagreements"], 0)

    def test_the_scorecard_counts_the_override(self):
        old = json.loads(json.dumps(self.sheet))
        old["lineup"]["full"][3] = "Trombone"
        r = F.report(F.merge(old, self.sheet))
        self.assertEqual(r["disagreements"], 1)
        self.assertEqual(r["corrected_fields"], ["lineup.full[3]"])

    def test_filling_a_blank_is_not_an_override(self):
        old = json.loads(json.dumps(self.sheet))
        old["lineup"]["systems"]["p0/s0"]["first_ref_measure"] = 1
        r = F.report(F.merge(old, self.sheet))
        self.assertEqual(r["disagreements"], 0)
        self.assertEqual(r["hand_supplied"], 1)


class TestItRefusesToDeriveFromANameTheLexiconRefused(unittest.TestCase):
    def test_a_raw_label_is_not_as_good_as_a_named_instrument(self):
        self.assertEqual(F._name_of({"instrument": "Horn", "label": "Hr."}),
                         ("Horn", "instrument"))
        self.assertEqual(F._name_of({"instrument": None, "label": "in C 1 2"}),
                         ("in C 1 2", "label_only"))
        self.assertEqual(F._name_of({}), (None, "unread"))

    def test_suppression_is_not_derived_when_a_name_was_refused(self):
        """The live Brahms fault: a horn label truncated to `in C 1 2` made a
        13-staff system report Trumpet AND the mangled string as suppressed."""
        weak = [("Fl.", "Flute"), ("in C 1 2", None), ("Trp.", "Trumpet")]
        rec = _record({(0, 0): weak, (0, 1): [("Fl.", "Flute"), ("Hr.", "Horn")]})
        sheet = F.draft("x--imslp999999.pdf", record=rec)
        self.assertIsNone(sheet["lineup"]["systems"]["p0/s1"]["suppressed"])
        self.assertTrue(any("lexicon refused" in c or "not fully named" in c
                            for c in sheet["check"]))

    def test_the_canonical_lineup_prefers_the_best_named_widest_system(self):
        rec = _record({(0, 0): [("Fl.", "Flute"), ("(C)", None)],
                       (0, 1): [("Fl.", "Flute"), ("Hr.", "Horn")]})
        sheet = F.draft("x--imslp999999.pdf", record=rec)
        self.assertEqual([F.value_of(f) for f in sheet["lineup"]["full"]],
                         ["Flute", "Horn"])

    def test_it_abstains_even_when_the_refused_name_happens_to_match(self):
        """⚠️ THE MUTATION-FOUND GAP. Where the SAME raw string the lexicon
        refused appears in both systems, `_missing` reports nothing unmatched
        and the suppression list looks derivable -- so the `reliable` guard is
        the only thing standing between us and a list derived by matching two
        unresolved strings. On the real Brahms plate that same staff prints
        `in C 1 2`, `(C)` and `Hr.` on three different systems, so the match
        is luck and not evidence."""
        weak = [("Fl.", "Flute"), ("in C 1 2", None), ("Trp.", "Trumpet")]
        rec = _record({(0, 0): weak, (0, 1): weak[:2]})
        sheet = F.draft("x--imslp999999.pdf", record=rec)
        short = sheet["lineup"]["systems"]["p0/s1"]
        self.assertIsNone(short["suppressed"],
                          "derived a suppression list from a name the lexicon "
                          "refused, by matching the raw string to itself")

    def test_suppression_is_derived_when_every_name_is_solid(self):
        rec = _record({(0, 0): FULL, (0, 1): [FULL[0], FULL[1], FULL[4]]})
        sheet = F.draft("x--imslp999999.pdf", record=rec)
        self.assertEqual(
            F.value_of(sheet["lineup"]["systems"]["p0/s1"]["suppressed"]),
            ["Horn", "Trumpet"])


class TestMissingIsMultisetAwareAndReportsUnmatched(unittest.TestCase):
    def test_two_violins_and_one_printed_is_one_missing(self):
        self.assertEqual(F._missing(["Violin", "Violin"], ["Violin"]),
                         (["Violin"], []))

    def test_a_staff_in_no_slot_of_the_lineup_is_reported(self):
        self.assertEqual(F._missing(["Flute"], ["Flute", "Tuba"]),
                         ([], ["Tuba"]))


class TestItNeverGuessesAcrossTheTwoIdSpaces(unittest.TestCase):
    def test_several_candidate_movements_are_proposed_never_picked(self):
        cands, how = F._dossier_candidates("beethoven--symphony-5",
                                           "beethoven-sym5")
        if len(cands) > 1:                       # true with the committed data
            self.assertEqual(how, "catalog")
            sheet = F.draft("b--imslp984073.pdf")
            self.assertIsNone(sheet["movement"]["dossier_id"])
            self.assertTrue(any("dossier_id" in c for c in sheet["check"]))

    def test_the_committed_prefix_outranks_the_filename_heuristic(self):
        by_prefix, how = F._dossier_candidates("nonsense--work", "beethoven-sym5")
        self.assertEqual(how, "catalog")
        self.assertTrue(by_prefix)


class TestAnUnknownPdfAbstainsRatherThanInventing(unittest.TestCase):
    def test_a_pdf_the_catalog_does_not_hold(self):
        sheet = F.draft("something-nobody-has.pdf")
        self.assertIsNone(sheet["work"]["work_id"])
        self.assertTrue(any("not in the catalog" in c for c in sheet["check"]))
        self.assertEqual(F.report(sheet)["machine_supplied"], 0)


class TestAbsentIsNotTheSameAsDeclined(unittest.TestCase):
    def test_a_reader_that_never_ran_says_so(self):
        rec = _record({(0, 0): [("x", None)]})
        rec["abstentions"] = [{"subject": "staff/0/0/0",
                               "quantity": "margin_label",
                               "reason": "not_implemented"}]
        rec["observations"] = []
        sheet = F.draft("x--imslp999999.pdf", record=rec)
        self.assertTrue(any("never ran" in c for c in sheet["check"]))
        self.assertTrue(any("READER HEALTH" in c for c in sheet["check"]))


if __name__ == "__main__":
    unittest.main()



class TestOneBarNumberPlacesEverySystemAfterIt(unittest.TestCase):
    def _sheet(self, bars=(4, 5, 6)):
        rec = _record({(0, i): FULL for i in range(len(bars))})
        for i, b in enumerate(bars):
            for v in rec["verdicts"]:
                if v["quantity"] == "measure_partition" \
                        and v["subject"].startswith(f"staff/0/{i}/"):
                    v["value"] = b
        return F.draft("x--imslp999999.pdf", record=rec), rec

    def test_the_chain_runs_from_the_one_hand_value(self):
        sheet, rec = self._sheet()
        sheet["lineup"]["systems"]["p0/s0"]["first_ref_measure"] = 1
        merged = F.merge(sheet, F.draft("x--imslp999999.pdf", record=rec))
        got = [F.value_of(v["first_ref_measure"])
               for v in merged["lineup"]["systems"].values()]
        self.assertEqual(got, [1, 5, 10])
        self.assertEqual(
            F.source_of(merged["lineup"]["systems"]["p0/s1"]["first_ref_measure"]),
            "derived")

    def test_a_later_hand_value_re_anchors_the_chain(self):
        sheet, rec = self._sheet()
        sheet["lineup"]["systems"]["p0/s0"]["first_ref_measure"] = 1
        sheet["lineup"]["systems"]["p0/s1"]["first_ref_measure"] = 90
        merged = F.merge(sheet, F.draft("x--imslp999999.pdf", record=rec))
        got = [F.value_of(v["first_ref_measure"])
               for v in merged["lineup"]["systems"].values()]
        self.assertEqual(got, [1, 90, 95])

    def test_nothing_is_chained_without_an_anchor(self):
        sheet, rec = self._sheet()
        merged = F.merge(sheet, F.draft("x--imslp999999.pdf", record=rec))
        self.assertTrue(all(v["first_ref_measure"] is None
                            for v in merged["lineup"]["systems"].values()))

    def test_the_chain_stops_where_the_reader_decided_no_bar_count(self):
        """⚠️ A chain that guessed one span would put every later system wrong
        while looking exactly as confident as the ones that are right."""
        sheet, rec = self._sheet()
        sheet["lineup"]["systems"]["p0/s0"]["first_ref_measure"] = 1
        sheet["lineup"]["systems"]["p0/s1"]["bars"] = None
        notes = F.chain_windows(sheet)
        self.assertEqual(
            F.value_of(sheet["lineup"]["systems"]["p0/s2"]["first_ref_measure"]),
            None)
        self.assertTrue(any("chain STOPS" in n for n in notes))



DOSSIER = {
    "work_id": "x", "n_parts": 6,
    "parts": [
        {"slot": 0, "name": "Flute 1", "written_clef": "treble"},
        {"slot": 1, "name": "Flute 2", "written_clef": "treble"},
        {"slot": 2, "name": "Horn 1", "written_clef": "treble"},
        {"slot": 3, "name": "Trumpet", "written_clef": "treble"},
        {"slot": 4, "name": "Timpani", "written_clef": "bass"},
        {"slot": 5, "name": "Cello", "written_clef": "bass"},
    ],
}
LINEUP = ["Fl.", "Hr.", "Trp.", "Pk.", "Vc."]
JOIN = [[0, 1], [2], [3], [4], [5]]


def _sheet_with_join(suppressed_by_system, n_staves_by_system=None):
    systems = {k: {"n_staves": F.fact(n, "reader"), "bars": F.fact(8, "reader"),
                   "suppressed": v, "first_ref_measure": None}
               for k, (v, n) in suppressed_by_system.items()}
    return {"pdf": "x.pdf", "sheet_version": 1, "_README": "", "check": [],
            "work": {}, "movement": {"dossier_id": "d"},
            "lineup": {"full": list(LINEUP), "parts": [list(j) for j in JOIN],
                       "systems": systems}}


class TestTheDossierReachesThePipelineOnlyThroughAConfirmedSheet(unittest.TestCase):
    """Sean, 2026-09-21: 'let the dossier only reach the pipeline through a
    confirmed sheet.' The benchmark path must be structurally unable to
    consume one, not merely trusted not to."""

    def test_an_unconfirmed_dossier_id_is_refused(self):
        sheet = F.draft("b--imslp984073.pdf")
        sheet["movement"]["dossier_id"] = F.fact("beethoven-sym5-mvt1", "dossier")
        d, why = F.dossier_for(sheet)
        self.assertIsNone(d)
        self.assertIn("nobody confirmed", why)

    def test_a_sheet_naming_no_dossier_is_refused(self):
        d, why = F.dossier_for({"movement": {"dossier_id": None}})
        self.assertIsNone(d)

    def test_the_staged_cli_has_no_dossier_flag(self):
        """⚠️ The structural half of the ruling. If this ever fails, a truth
        file can reach a measurement path again."""
        src = (Path(__file__).resolve().parents[1]
               / "staged" / "__main__.py").read_text()
        self.assertNotIn('"--dossier"', src)
        self.assertIn('"--sheet"', src)

    def test_a_confirmed_id_is_admitted_and_says_who_admitted_it(self):
        sheet = _sheet_with_join({"p0/s0": ([], 5)})
        with _dossier_on_disk("d", DOSSIER):
            d, why = F.dossier_for(sheet)
        self.assertIsNotNone(d)
        self.assertEqual(d["admitted_by"]["confirmed_by"], "hand")
        self.assertEqual(d["admitted_by"]["dossier_id"], "d")


class TestTheJoinIsSuppliedAndPerSystem(unittest.TestCase):
    def test_no_join_means_no_seed(self):
        sheet = _sheet_with_join({"p0/s0": ([], 5)})
        sheet["lineup"]["parts"] = [None] * 5
        seeds, why = F.clef_by_staff(sheet, DOSSIER)
        self.assertEqual(seeds, {})
        self.assertIn("no staff-to-part join is confirmed", why)

    def test_a_full_system_seeds_every_staff(self):
        sheet = _sheet_with_join({"p0/s0": ([], 5)})
        seeds, _ = F.clef_by_staff(sheet, DOSSIER)
        self.assertEqual(seeds["p0/s0"],
                         {0: "treble", 1: "treble", 2: "treble",
                          3: "bass", 4: "bass"})

    def test_a_short_system_SHIFTS_and_does_not_graft(self):
        """⚠️⚠️ THE ONE THAT MATTERS. Index 3 is the Timpani (bass) on a full
        system and the Cello on one that drops the Timpani -- a single
        index-keyed dict would seed `bass` onto whatever sits at 3. Here the
        shift is real: dropping Pk. leaves Vc. at index 3."""
        sheet = _sheet_with_join({"p0/s0": ([], 5), "p0/s1": (["Pk."], 4)})
        seeds, _ = F.clef_by_staff(sheet, DOSSIER)
        self.assertEqual(seeds["p0/s1"],
                         {0: "treble", 1: "treble", 2: "treble", 3: "bass"})
        self.assertEqual(len(seeds["p0/s1"]), 4)

    def test_an_unconfirmed_suppression_list_skips_that_system(self):
        sheet = _sheet_with_join({"p0/s0": ([], 5), "p0/s1": (None, 4)})
        seeds, why = F.clef_by_staff(sheet, DOSSIER)
        self.assertNotIn("p0/s1", seeds)
        self.assertIn("SKIPPED", why)

    def test_unconfirmed_skips_EVEN_WHEN_the_count_would_reconcile(self):
        """⚠️ THE MUTATION-FOUND GAP. The sibling test used a mismatched count,
        so the reconciliation guard caught it and the None-check was never
        exercised. Here the counts agree, and the rule that must hold is the
        doctrine's and not arithmetic's: ONLY A CONFIRMED FACT SEEDS. A
        machine-derived `suppressed: []` is the READER's claim that this system
        prints the full lineup, and trusting it is trusting the thing the sheet
        exists to check."""
        sheet = _sheet_with_join({"p0/s1": (None, 5)})   # 5 == len(LINEUP)
        seeds, why = F.clef_by_staff(sheet, DOSSIER)
        self.assertNotIn("p0/s1", seeds)
        self.assertIn("SKIPPED", why)

    def test_a_machine_derived_empty_suppression_does_not_seed(self):
        sheet = _sheet_with_join({"p0/s0": (F.fact([], "derived"), 5)})
        seeds, _ = F.clef_by_staff(sheet, DOSSIER)
        self.assertEqual(seeds, {})

    def test_the_two_independent_facts_must_reconcile(self):
        """The human read the margin; the reader counted the staves. Where
        they disagree, one of them is wrong about that system."""
        sheet = _sheet_with_join({"p0/s1": (["Pk."], 3)})   # 5-1=4, reader says 3
        seeds, why = F.clef_by_staff(sheet, DOSSIER)
        self.assertNotIn("p0/s1", seeds)
        self.assertIn("reader counted 3", why)

    def test_a_suppressed_name_not_in_the_lineup_is_refused(self):
        sheet = _sheet_with_join({"p0/s1": (["Tuba"], 4)})
        seeds, why = F.clef_by_staff(sheet, DOSSIER)
        self.assertNotIn("p0/s1", seeds)
        self.assertIn("no slot of lineup.full", why)

    def test_a_staff_whose_parts_disagree_abstains(self):
        d = json.loads(json.dumps(DOSSIER))
        d["parts"][1]["written_clef"] = "bass"      # Flute 2 now disagrees
        sheet = _sheet_with_join({"p0/s0": ([], 5)})
        seeds, why = F.clef_by_staff(sheet, d)
        self.assertNotIn(0, seeds["p0/s0"])
        self.assertIn("disagree", why)

    def test_present_indices_is_multiset_aware(self):
        self.assertEqual(F._present_indices(["V", "V", "Vc"], ["V"]), [1, 2])
        self.assertIsNone(F._present_indices(["V"], ["Tuba"]))

    def test_the_join_is_drafted_only_when_it_needs_no_judgement(self):
        rec = _record({(0, 0): FULL})               # 5 staves
        same = F.draft("x--imslp999999.pdf", record=rec)
        same["movement"]["n_reference_parts"] = F.fact(5, "dossier")
        drafted = F._draft_lineup(F._reader_view(rec), n_parts=5)[0]["parts"]
        self.assertEqual([F.value_of(x) for x in drafted],
                         [[0], [1], [2], [3], [4]])
        condensed = F._draft_lineup(F._reader_view(rec), n_parts=9)[0]["parts"]
        self.assertTrue(all(x is None for x in condensed),
                        "a condensed page must not be joined by name")


class TestGatherReadsThePerSystemShape(unittest.TestCase):
    def test_the_seam(self):
        """⚠️ A SEAM TEST, because the two halves are in different modules and
        nothing else forces them to agree about the shape."""
        src = (Path(__file__).resolve().parents[1]
               / "staged" / "gather.py").read_text()
        self.assertIn('clefs.get(f"p{c.page_index}/s{key[0]}")', src)


@contextlib.contextmanager
def _dossier_on_disk(name, payload):
    d = F._dossier_dir()
    f = d / f"{name}.json"
    existed = f.exists()
    f.write_text(json.dumps(payload))
    try:
        yield f
    finally:
        if not existed:
            f.unlink(missing_ok=True)
