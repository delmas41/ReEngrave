"""The fact sheet: provenance by shape, hand facts winning, and the scorecard.

⚠️ Every fixture here is SYNTHETIC. The module reads `library/` and the real
records when it can, and neither is in the tree -- a test that needed them
would pass on one machine and be skipped everywhere else, which is how a
guard stops guarding.
"""

import json
import unittest

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


class TestAListValuedFactIsNotAContainer(unittest.TestCase):
    """⚠️ THE BUG A REAL SHEET FOUND AND THE TESTS DID NOT. A hand-typed
    `suppressed: ["Timpani"]` is a fact whose value is a list; `lineup.full`
    is a list OF facts. Nothing about the two objects tells them apart, so
    `merge` treated the edit as a container, found nothing to merge it
    against, and threw it away."""

    def test_the_paths_are_declared_not_sniffed(self):
        self.assertTrue(F.is_list_valued("lineup.systems.p0/s1.suppressed"))
        self.assertTrue(F.is_list_valued("work.scored_for"))
        self.assertFalse(F.is_list_valued("lineup.full"))
        self.assertFalse(F.is_list_valued("lineup.systems.p0/s1.bars"))

    def test_a_hand_suppression_list_survives_a_redraft(self):
        rec = _record({(0, 0): FULL, (0, 1): FULL[:3]})
        sheet = F.draft("x--imslp999999.pdf", record=rec)
        sheet["lineup"]["systems"]["p0/s1"]["suppressed"] = ["Timpani"]
        merged = F.merge(sheet, F.draft("x--imslp999999.pdf", record=rec))
        leaf = merged["lineup"]["systems"]["p0/s1"]["suppressed"]
        self.assertEqual(F.value_of(leaf), ["Timpani"])
        self.assertEqual(F.source_of(leaf), "hand")

    def test_a_hand_suppression_list_that_disagrees_keeps_the_reader(self):
        rec = _record({(0, 0): FULL, (0, 1): [FULL[0], FULL[1], FULL[4]]})
        sheet = F.draft("x--imslp999999.pdf", record=rec)
        sheet["lineup"]["systems"]["p0/s1"]["suppressed"] = ["Trumpet"]
        merged = F.merge(sheet, F.draft("x--imslp999999.pdf", record=rec))
        leaf = merged["lineup"]["systems"]["p0/s1"]["suppressed"]
        self.assertEqual(leaf["reader_said"], ["Horn", "Trumpet"])
        self.assertEqual(F.report(merged)["disagreements"], 1)

    def test_a_hand_lineup_of_a_different_length_wins_whole(self):
        """He counted the staves off the page; the reader is the one that is
        wrong about how many there are."""
        rec = _record({(0, 0): FULL})
        sheet = F.draft("x--imslp999999.pdf", record=rec)
        sheet["lineup"]["full"] = ["Fl", "Ob", "Hr", "Trp", "Vl", "Vc"]
        merged = F.merge(sheet, F.draft("x--imslp999999.pdf", record=rec))
        self.assertEqual(merged["lineup"]["full"],
                         ["Fl", "Ob", "Hr", "Trp", "Vl", "Vc"])


class TestAnAnsweredCheckRetires(unittest.TestCase):
    """⚠️ A check label that is not a real dotted path silently never matches,
    so the to-do list keeps asking for what you already gave it -- and a list
    that lies about what is outstanding stops being read."""

    def _filled(self):
        # ⚠️ one REFUSED name, so suppression genuinely cannot be derived and
        # there is a real check to retire. With a fully-named lineup the tool
        # derives it and the check never exists -- which is what the first
        # version of this test asserted against, and it failed honestly.
        weak = [("Fl.", "Flute"), ("in C 1 2", None), ("Trp.", "Trumpet")]
        rec = _record({(0, 0): weak, (0, 1): weak[:2]})
        sheet = F.draft("x--imslp999999.pdf", record=rec)
        return sheet, rec

    def test_every_check_label_is_a_path_into_the_sheet(self):
        sheet, _ = self._filled()
        paths = {p for p, _ in F.walk(sheet)}
        for c in sheet["check"]:
            head = c.split(":", 1)[0].strip()
            if " " in head:          # prose checks (READER HEALTH) name no path
                continue
            self.assertTrue(
                any(p == head or p.startswith(head + ".")
                    or p.startswith(head + "[") or F._path_matches(p, head)
                    for p in paths),
                f"check names {head!r}, which is no path in the sheet")

    def test_answering_a_suppression_check_retires_it(self):
        sheet, rec = self._filled()
        key = "lineup.systems.p0/s1.suppressed"
        self.assertTrue(any(c.startswith(key) for c in sheet["check"]))
        sheet["lineup"]["systems"]["p0/s1"]["suppressed"] = ["Horn"]
        merged = F.merge(sheet, F.draft("x--imslp999999.pdf", record=rec))
        self.assertFalse(any(c.startswith(key) for c in merged["check"]))

    def test_the_window_check_retires_only_when_every_system_has_one(self):
        sheet, rec = self._filled()
        key = "lineup.systems.*.first_ref_measure"
        sheet["lineup"]["systems"]["p0/s0"]["first_ref_measure"] = 1
        merged = F.merge(sheet, F.draft("x--imslp999999.pdf", record=rec))
        self.assertFalse(any(c.startswith(key) for c in merged["check"]),
                         "the chain filled them all, so the ask is answered")
