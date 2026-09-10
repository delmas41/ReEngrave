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

    def test_no_family_is_mapped_to_None_while_a_Q_exists(self) -> None:
        """⚠️ THE SAME STALENESS CLASS AS THE PLURAL BUG, one table over.

        `rest` sat at None for a day after `Q.REST` landed. A family recorded
        as unnamed while the record names it is a finding that has silently
        expired, so this asks the vocabulary rather than trusting the table.
        """
        for fam, quantity in GC.FAMILY_TO_Q.items():
            if quantity is not None or fam in GC.FAMILY_Q_IS_ELSEWHERE:
                continue
            owner = GC.q_covering(fam)
            self.assertIsNone(
                owner,
                f"family `{fam}` is now named by Q.{owner} -- map it in "
                "FAMILY_TO_Q, or record why not in FAMILY_Q_IS_ELSEWHERE")

    def test_the_elsewhere_exemptions_are_still_needed(self) -> None:
        """An exemption whose Q has gone must LEAVE the table."""
        for fam in GC.FAMILY_Q_IS_ELSEWHERE:
            self.assertIsNotNone(
                GC.q_covering(fam),
                f"`{fam}` no longer has a Q anywhere -- drop the exemption")

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
        """⚠️ THIS TEST HAD THE BUG IT EXISTS TO PREVENT, AND IT BIT.

        It compared lowercased names for EXACT equality, so the legacy key
        `events` never matched `Q.EVENT` — singular against plural — and the
        entry stayed in NO_VOCABULARY after main had CLOSED it. The stale
        claim reached a PR body, CLAUDE.md, PROJECT_BRIEF and a findings file,
        and was merged to main. `rest` sat mapped to None after `Q.REST`
        landed, the same class of miss.

        ⚠️ What caught it was a DIFFERENT test — the stub-starvation guard
        above, failing during a trial merge. The guard whose job this was
        passed. `q_covering` is the repair.
        """
        for key in GC.NO_VOCABULARY:
            owner = GC.q_covering(key)
            self.assertIsNone(
                owner,
                f"`{key}` is now named by Q.{owner} -- move it to "
                "LEGACY_TO_Q, it is no longer a finding")

    def test_the_guard_catches_a_plural_key_against_a_singular_Q(self) -> None:
        """The exact miss above, pinned so it cannot recur."""
        self.assertEqual(GC.q_covering("events"), "EVENT")
        self.assertEqual(GC.q_covering("rests"), "REST")
        # ...and does NOT over-match: `Q.STEM` carries a stem's BOX and says
        # nothing about which way it points, so these are different quantities.
        self.assertIsNone(GC.q_covering("stem_direction"))

    def test_the_chord_gap_is_CLOSED_and_stays_accounted(self) -> None:
        """⚠️ THE FINDING THAT STARTED THIS IS FIXED — by sibling sessions,
        not by this work. `Q.EVENT` names the simultaneity, and its docstring
        settles `x_position` beside it: the x POSITION is a measurement
        `GLYPH_BOX` already carries, the SIMULTANEITY is the interpretation.
        What must not happen is these keys falling out of both tables and
        going unnoticed a second time.
        """
        for key in ("kind", "x_position", "events", "n_events"):
            self.assertIn(key, GC.LEGACY_TO_Q,
                          f"`{key}` must stay mapped, not silently dropped")
            self.assertNotIn(key, GC.NO_VOCABULARY)
        self.assertEqual(GC.LEGACY_TO_Q["kind"], "EVENT")

    def test_what_is_STILL_unnamed(self) -> None:
        """The seven that survive, so a future closure is a loud failure."""
        self.assertEqual(
            sorted(GC.NO_VOCABULARY),
            ["fermata", "ornaments", "stem_direction", "tied_from_prev",
             "tied_to_next", "voice_index", "voices"])

    def test_every_declared_stub_is_reported_with_its_input_state(self) -> None:
        """⚠️ THE STRUCTURAL FINDING, AND THE MERGE THAT HALF-CLOSED IT.

        Measured on this session's own branch, ALL SIX declared stubs wanted a
        measurement no gatherer emitted — `a stub is two repairs, not one`, and
        the committed `out/gather-coverage.json` still records that state.

        ⚠️ THE MERGED TREE IS DIFFERENT, AND THIS TEST IS HOW THAT WAS FOUND.
        Two sibling sessions landed the four gatherers this finding called
        "NAMING gaps, and cheap: the ink is already in the log" —
        `gather_glyph_families` (ARC_BOX, ARTICULATION_MARK) and
        `gather_dynamic_letters` / `gather_wedge_boxes` (DYNAMIC_LETTER,
        WEDGE_BOX). So in the merged tree:

          * `dynamic` is no longer a stub at all — its adjudicator is written
            AND its input gathered, both repairs done at once, which is the
            finding CONFIRMED rather than contradicted;
          * of the five stubs left, only `direction` is still starved, and it
            is the one this finding already named as the sole READING gap.

        If either half moves, this fails and FINDINGS.md must be re-read.
        """
        starv = GC.stub_starvation()
        # ⚠️ FOUR since 2026-09-09: `arc_kind` was filled, so it left this
        # list. The count is asserted so that filling or ADDING a stub is a
        # deliberate edit here rather than a silent drift — which is what this
        # guard is for.
        self.assertEqual(len(starv), 4,
                         f"expected 4 declared stubs, got {sorted(starv)}")
        self.assertNotIn("DYNAMIC", starv,
                         "`dynamic` graduated: adjudicator written and input "
                         "gathered. A stub roster that keeps a graduated "
                         "entry describes history, not the pipeline.")
        starved = {q for q, v in starv.items() if v["ungathered_inputs"]}
        self.assertEqual(starved, {"DIRECTION"},
                         "only the reading gap should still be starved; the "
                         "four naming gaps were closed by the sibling "
                         "sessions in this merge")
        # ⚠️ The four fed stubs are now ONE repair each: the adjudicator.
        # Assert that positively, so a gatherer being deleted underneath them
        # fails here instead of turning a written decision into a silent
        # abstention.
        for name, row in starv.items():
            if name == "DIRECTION":
                continue
            self.assertEqual(
                row["ungathered_inputs"], [],
                f"{name} lost an input it had after the merge -- writing its "
                f"adjudicator would now produce abstentions, not decisions")


if __name__ == "__main__":
    unittest.main()
