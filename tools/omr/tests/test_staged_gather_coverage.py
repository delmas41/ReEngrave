"""Standing check: the two lists cannot silently go stale.

⚠️ A TEST RATHER THAN A DOCUMENT, because the artefact this replaces is the
one shape this repo has been bitten by most. CLAUDE.md carries a fixed defect
that stayed open in prose for two days and seeded a work order to re-close it;
the handoff that asked for this inventory opens by correcting two false claims
in its predecessor that "cost real time". A hand-written list of what the
gather stage collects would be wrong within a week.

So the lists are derived, and these tests assert the DERIVATION still binds:
that the tool sees a quantity a gatherer really emits, that it does not
declare coverage for one only abstained on, and that neither the legacy event
vocabulary nor the detector class space can grow a member the report is blind
to.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import gather_coverage as GC


class TestTheDerivationBinds(unittest.TestCase):
    """The AST walk must track the code, not a list beside it."""

    def test_a_loop_bound_quantity_is_seen_as_observed(self) -> None:
        """⚠️ THE FIRST RUN OF THIS TOOL GOT THIS WRONG AND INVENTED A BUG.

        `gather_cv_lines` emits through a loop variable:

            for quantity, kind in ((Q.STEM, "stems"), (Q.BEAM_STROKE, "beams")):
                log.observe(sub, quantity, ...)

        A visitor reading only `Q.X` literals at the call site reported
        `Q.STEM` as never gathered -- and `adjudicate_duration` declares it in
        `wants=`, so the report accused a working reader of starving a working
        decision. The resolver is load-bearing and this is what pins it.
        """
        got = GC.gathered()
        self.assertIn("STEM", got)
        self.assertIn("gather_cv_lines", got["STEM"]["observed_by"],
                      "Q.STEM is observed through a loop variable; the AST "
                      "walker must resolve loop-bound quantities")

    def test_observe_and_abstain_are_not_the_same_coverage(self) -> None:
        """A quantity only ever ABSTAINED on is declared, not collected."""
        src = '''
def gather_thing(log, cells):
    log.abstain(sub, Q.WEDGE_BOX, reader=READERS.DETECTOR,
                reason=ABSTAIN.NOT_IMPLEMENTED)
'''
        got = GC.gathered(source=src)
        self.assertEqual(got["WEDGE_BOX"]["observed_by"], [])
        self.assertEqual(got["WEDGE_BOX"]["abstained_by"], ["gather_thing"])

    def test_the_report_separates_the_four_populations(self) -> None:
        rep = GC.report()
        self.assertTrue(rep["gathered"]["observed"])
        # A verdict is not a gather gap: `adjudicate` owns it by design.
        self.assertIn("CLEF", rep["not_gathered"]["verdict_elsewhere"])
        self.assertNotIn("CLEF", rep["not_gathered"]["declared_ungathered"])


class TestNothingGrowsUnseen(unittest.TestCase):
    """The two anti-drift contracts, both of which must fail loudly."""

    def test_every_legacy_event_key_is_accounted(self) -> None:
        """⚠️ A key added to an event and to neither table FAILS HERE.

        Without this, widening the legacy vocabulary silently widens the
        staged record's blind spot -- which is how `kind`, `x_position` and
        `voices` came to be missing without anyone noticing.
        """
        unaccounted = GC.unaccounted()
        self.assertEqual(
            unaccounted, {},
            "legacy event keys in neither LEGACY_TO_Q nor NO_VOCABULARY: "
            f"{sorted(unaccounted)}. Map it, or record it as a finding.")

    def test_every_detector_family_is_mapped(self) -> None:
        cs = GC.class_space_coverage()
        self.assertEqual(
            cs["unmapped"], [],
            f"detector families missing from FAMILY_TO_Q: {cs['unmapped']}")
        self.assertGreater(cs["classes"], 100,
                           "the class space failed to parse")


class TestTheFindingsAreStillTrue(unittest.TestCase):
    """⚠️ AN ENTRY THAT IS CLOSED MUST LEAVE ITS TABLE.

    `export_coverage.test_the_inventory_has_no_stale_entries` exists for the
    same reason: an inventory that keeps closed entries stops describing the
    code and starts describing its history. These fail the day the gap is
    filled, which is the point -- the failure is the notification.
    """

    def test_no_vocabulary_entries_still_have_no_vocabulary(self) -> None:
        from tools.omr.staged.record import Q
        names = {n.lower() for n in dir(Q) if n.isupper()}
        for key in GC.NO_VOCABULARY:
            self.assertNotIn(
                key.lower(), names,
                f"`{key}` now has a Q of its own -- remove it from "
                "NO_VOCABULARY, it is no longer a finding")

    def test_chords_are_the_reported_gap(self) -> None:
        """The finding that started this: simultaneity has no name."""
        for key in ("kind", "x_position", "events", "voices"):
            self.assertIn(key, GC.NO_VOCABULARY,
                          f"`{key}` is part of the chord/event gap")

    def test_every_declared_stub_is_reported_with_its_input_state(self) -> None:
        """⚠️ THE STRUCTURAL FINDING: a stub is not always one repair.

        All six declared stubs want at least one measurement no gatherer
        emits, so writing the adjudicator would leave it abstaining for lack
        of evidence. If a stub ever stops being starved, this test fails and
        the claim in FINDINGS.md must be re-read.
        """
        starv = GC.stub_starvation()
        self.assertEqual(len(starv), 6, f"expected 6 declared stubs, got {sorted(starv)}")
        for name, row in starv.items():
            self.assertTrue(
                row["ungathered_inputs"],
                f"{name} is no longer input-starved -- update FINDINGS.md")


if __name__ == "__main__":
    unittest.main()
