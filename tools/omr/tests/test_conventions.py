"""The convention registry: does the parse reach the document, and refuse?

⚠️ Two halves, and the second is the one that matters. The first asserts the
registry parses; the second asserts `--check` GOES RED — on a duplicate id,
a vanished source entry, a count that drifted, a half-stated refutation, a
broken anchor, a missing field, an unreadable status. A check that can only
ever say "clean" is what `gather_coverage`'s anti-drift guard was, and this
suite exists so this one cannot become that.

⚠️ Every mutation is applied to a COPY in a tmp dir. Nothing here writes to
`docs/`.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.omr import conventions as C


DOC = C.default_doc_path()
TEXT = DOC.read_text(encoding="utf-8")


def _reg_from(text: str) -> C.Registry:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "engraving-conventions.md"
        path.write_text(text, encoding="utf-8")
        return C.load(path)


class TestTheParseReachesTheDocument(unittest.TestCase):
    """REACH FIRST. A parse that matches nothing reports a clean registry."""

    def setUp(self) -> None:
        self.reg = C.load()

    def test_the_positive_control_is_not_zero_anywhere(self) -> None:
        for name, value in self.reg.reach().items():
            self.assertGreater(value, 0, f"reach {name} is ZERO — parse DEAD")

    def test_every_entry_carries_every_required_field(self) -> None:
        coverage = self.reg.field_coverage()
        for name in C.REQUIRED_FIELDS:
            self.assertEqual(coverage[name], len(self.reg),
                             f"{name} is absent from some entry")

    def test_the_document_agrees_with_itself(self) -> None:
        problems = self.reg.problems()
        self.assertEqual(problems, [], "\n".join(str(p) for p in problems))

    def test_ids_and_slugs_are_unique(self) -> None:
        ids = [e.id for e in self.reg]
        slugs = [e.slug for e in self.reg]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(len(set(slugs)), len(slugs))

    def test_every_source_entry_is_carried_exactly_once(self) -> None:
        tokens = [t for e in self.reg for t in e.sources]
        self.assertEqual(len(tokens), len(set(tokens)),
                         "a source entry is claimed by two registry entries")

    def test_lookup_by_id_and_by_source_agree(self) -> None:
        for entry in self.reg:
            self.assertIs(self.reg.by_id(entry.id), entry)
            for token in entry.sources:
                self.assertIs(self.reg.by_source(token), entry)
            self.assertIs(self.reg.by_slug(entry.slug), entry)

    def test_every_status_was_readable(self) -> None:
        unreadable = [e.id for e in self.reg if e.status is C.Status.UNREADABLE]
        self.assertEqual(unreadable, [])


class TestARefutedEntryCannotBeReadAsARule(unittest.TestCase):
    """The design constraint, asserted rather than described."""

    def setUp(self) -> None:
        self.reg = C.load()

    def test_there_are_refuted_entries_at_all(self) -> None:
        # The positive control for every assertion below it.
        self.assertGreater(len(self.reg.refuted()), 0)

    def test_rule_text_refuses_a_refuted_entry(self) -> None:
        for entry in self.reg.refuted():
            with self.assertRaises(C.RefutedConvention):
                entry.rule_text()

    def test_rule_text_answers_for_a_live_entry(self) -> None:
        # ⚠️ Without this the refusal test passes by refusing everything.
        live = self.reg.live_rules()
        self.assertGreater(len(live), 0)
        for entry in live:
            self.assertEqual(entry.rule_text(), entry.says)

    def test_a_refuted_entrys_text_is_still_readable_as_evidence(self) -> None:
        # Evidence is never thrown out with the behaviour.
        for entry in self.reg.refuted():
            self.assertTrue(entry.says.strip())

    def test_refuted_entries_are_not_in_live_rules(self) -> None:
        live = {e.id for e in self.reg.live_rules()}
        for entry in self.reg.refuted():
            self.assertNotIn(entry.id, live)

    def test_refuted_entries_are_never_graded_testable(self) -> None:
        for entry in self.reg.refuted():
            self.assertIs(entry.testability, C.Testability.REFUTED)

    def test_the_nine_internal_caveats_are_live_and_flagged(self) -> None:
        caveats = [e for e in self.reg
                   if e.refutation is C.Refutation.INTERNAL_CAVEAT]
        self.assertGreater(len(caveats), 0)
        for entry in caveats:
            self.assertTrue(entry.is_live)
            self.assertFalse(entry.is_refuted)


class TestLiteratureIsNeverPromoted(unittest.TestCase):
    """A font default is not a measurement of a 19th-century plate."""

    def setUp(self) -> None:
        self.reg = C.load()

    def test_measured_figure_refuses_a_literature_only_entry(self) -> None:
        rows = self.reg.with_status(C.Status.LITERATURE_ONLY)
        self.assertGreater(len(rows), 0)
        for entry in rows:
            with self.assertRaises(C.NotMeasuredHere):
                entry.measured_figure()

    def test_measured_figure_refuses_an_asserted_entry(self) -> None:
        rows = self.reg.with_status(C.Status.ASSERTED)
        self.assertGreater(len(rows), 0)
        for entry in rows:
            with self.assertRaises(C.NotMeasuredHere):
                entry.measured_figure()

    def test_measured_figure_answers_for_a_measured_entry(self) -> None:
        rows = self.reg.with_status(C.Status.MEASURED_HERE)
        self.assertGreater(len(rows), 0)
        for entry in rows:
            self.assertEqual(entry.measured_figure(), entry.measured_here)

    def test_a_status_qualifier_is_kept_not_discarded(self) -> None:
        # "MEASURED HERE — and refuted as a reader" must not lose its tail.
        with_notes = [e for e in self.reg if e.status_note]
        self.assertGreater(len(with_notes), 0)


class TestTheCheckGoesRed(unittest.TestCase):
    """⚠️ One red arm is not a battery; every finding kind gets an arm."""

    def _problem_kinds(self, text: str):
        return {p.kind for p in _reg_from(text).problems()}

    def test_a_missing_field_is_a_finding(self) -> None:
        broken = TEXT.replace("- **Known exceptions:**", "- **Exceptions:**", 1)
        self.assertIn("MISSING FIELD", self._problem_kinds(broken))

    def test_an_unreadable_status_is_a_finding_and_not_a_default(self) -> None:
        broken = TEXT.replace("- **Status:** MEASURED HERE\n",
                              "- **Status:** probably fine\n", 1)
        kinds = self._problem_kinds(broken)
        self.assertIn("STATUS UNREADABLE", kinds)

    def test_a_vanished_source_entry_is_a_finding(self) -> None:
        broken = TEXT.replace("`[C2]`", "`[C200]`", 1)
        kinds = self._problem_kinds(broken)
        self.assertIn("SOURCE ENTRY VANISHED", kinds)

    def test_a_duplicated_source_tag_is_a_finding(self) -> None:
        # ⚠️ Asserted on SOURCE CLAIMED TWICE specifically. The first draft
        # accepted either that or a DUPLICATE ID finding, and the battery
        # showed the id half was an equivalent mutant: an id IS the first
        # source token, so it cannot duplicate alone. The check was deleted
        # and this assertion tightened onto the half that is reachable.
        broken = TEXT.replace("`[C2]`", "`[C1]`", 1)
        kinds = self._problem_kinds(broken)
        self.assertIn("SOURCE CLAIMED TWICE", kinds)

    def test_a_duplicate_slug_is_a_finding(self) -> None:
        # Two entries with the same TITLE: distinct ids, one anchor.
        first = "### A notehead sits ON a line or IN a space, on a half-space lattice"
        second = "### A notehead is one staff space tall"
        assert TEXT.count(first) == 1 and TEXT.count(second) == 1
        broken = TEXT.replace(first, second, 1)
        self.assertIn("DUPLICATE SLUG", self._problem_kinds(broken))

    def test_a_drifted_count_is_a_finding(self) -> None:
        broken = TEXT.replace("| **MEASURED HERE** | 67 |",
                              "| **MEASURED HERE** | 68 |", 1)
        self.assertIn("COUNT DISAGREES", self._problem_kinds(broken))

    def test_a_drifted_category_count_is_a_finding(self) -> None:
        broken = TEXT.replace("| Stems & beams | 18 | 9 |",
                              "| Stems & beams | 17 | 9 |", 1)
        self.assertIn("COUNT DISAGREES", self._problem_kinds(broken))

    def test_a_half_stated_refutation_is_a_finding(self) -> None:
        # A REFUTED status withdrawn while the FAILED table still lists it.
        broken = TEXT.replace("- **Status:** **REFUTED HERE — at full width.**",
                              "- **Status:** MEASURED HERE", 1)
        self.assertIn("REFUTATION HALF-STATED", self._problem_kinds(broken))

    def test_a_broken_anchor_is_a_finding(self) -> None:
        broken = TEXT.replace("](#conventions-that-failed-here)",
                              "](#conventions-that-did-not-fail)", 1)
        self.assertIn("BROKEN ANCHOR", self._problem_kinds(broken))

    def test_a_dangling_citation_is_a_finding(self) -> None:
        broken = TEXT.replace("- **`[C10]`**", "- **`[C910]`**", 1)
        self.assertIn("DANGLING CITATION", self._problem_kinds(broken))

    def test_a_conservation_row_going_missing_is_a_finding(self) -> None:
        broken = TEXT.replace(
            "| C2 | A notehead sits ON a line or IN a space, on a half-space "
            "lattice | *(same title)* | kept standalone |\n", "", 1)
        self.assertIn("CONSERVATION ROW MISSING", self._problem_kinds(broken))

    def test_a_drifted_contents_count_is_a_finding(self) -> None:
        broken = TEXT.replace("— 18\n- [Text & margin labels]",
                              "— 17\n- [Text & margin labels]", 1)
        self.assertIn("COUNT DISAGREES", self._problem_kinds(broken))

    def test_a_misaddressed_refutation_row_is_a_finding(self) -> None:
        # The FAILED table names each refuted entry TWICE — a link and a
        # tag. Point the link at a different entry and a reader following it
        # lands on a live rule believing it refuted.
        broken = TEXT.replace(
            "](#a-meter-stack-is-two-digits-aligned-in-x-and-adjacent-in-y--refuted)",
            "](#a-notehead-is-one-staff-space-tall)", 1)
        self.assertIn("REFUTATION ROW MISADDRESSED", self._problem_kinds(broken))

    def test_the_unmutated_document_is_the_positive_control(self) -> None:
        # ⚠️ Every arm above is worthless if the base is not clean.
        self.assertEqual(self._problem_kinds(TEXT), set())


class TestTheCliRefusesADeadParse(unittest.TestCase):
    """A parse that reaches nothing must exit 2, never 0."""

    def _run(self, text: str) -> int:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.md"
            path.write_text(text, encoding="utf-8")
            return C.main(["--doc", str(path), "--check"])

    def test_an_empty_document_exits_two(self) -> None:
        self.assertEqual(self._run("# nothing here\n"), 2)

    def test_a_document_whose_entry_shape_changed_exits_two(self) -> None:
        # The tag line is the discriminator; break it and NOTHING parses.
        self.assertEqual(self._run(TEXT.replace("`[C", "(C")), 2)

    def test_a_mutated_document_exits_one(self) -> None:
        broken = TEXT.replace("| **MEASURED HERE** | 67 |",
                              "| **MEASURED HERE** | 99 |", 1)
        self.assertEqual(self._run(broken), 1)

    def test_the_real_document_exits_zero(self) -> None:
        self.assertEqual(C.main(["--check"]), 0)


class TestGrades(unittest.TestCase):

    def setUp(self) -> None:
        self.reg = C.load()

    def test_testability_partitions_the_registry(self) -> None:
        total = sum(len([e for e in self.reg if e.testability is g])
                    for g in C.Testability)
        self.assertEqual(total, len(self.reg))

    def test_refutation_partitions_the_registry(self) -> None:
        total = sum(len([e for e in self.reg if e.refutation is r])
                    for r in C.Refutation)
        self.assertEqual(total, len(self.reg))

    def test_status_partitions_the_registry(self) -> None:
        total = sum(len(self.reg.with_status(s)) for s in C.Status)
        self.assertEqual(total, len(self.reg))

    def test_code_paths_are_extracted_where_the_row_names_one(self) -> None:
        with_paths = [e for e in self.reg if e.code_paths]
        self.assertGreater(len(with_paths), 0)

    def test_no_consumer_is_reported_apart_from_a_code_path(self) -> None:
        # ⚠️ Two different facts: an entry can name a path AND declare that
        # nothing READS it. Collapsing them loses the finding.
        both = [e for e in self.reg if e.code_paths and e.declares_no_consumer]
        self.assertGreater(len(both), 0)


if __name__ == "__main__":
    unittest.main()
