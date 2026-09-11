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


def _starvation_sees_a_declared_stub() -> bool:
    """Declare a stub whose input nothing gathers, and ask `stub_starvation`.

    ⚠️ THE CONTROL THAT MAKES "NO STUBS LEFT" A RESULT RATHER THAN A SHRUG.
    With Phase 1 complete every stub assertion in this file is an assertion
    that a set is EMPTY, and an empty set is what a broken derivation returns
    too. This fires the branch on purpose.
    """
    import dataclasses
    from unittest import mock
    from tools.omr.staged import adjudicate as A

    A._ensure_decisions()
    from tools.omr.staged.record import Q
    real = A.REGISTRY[Q.DIRECTION]
    fake = dataclasses.replace(
        real, quantity="a_quantity_nothing_gathers",
        wants=("a_quantity_no_rung_produces",), stub=True,
        subjects_from=None)
    with mock.patch.dict(A.REGISTRY,
                         {"a_quantity_nothing_gathers": fake}):
        starv = GC.stub_starvation()
    return any(v.get("ungathered_inputs") for v in starv.values())


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
        # ⚠️ ...and does NOT over-match. This used to assert
        # `q_covering("stem_direction") is None`, which stopped being the
        # right test on 2026-09-10 when `Q.STEM_DIRECTION` was declared: the
        # hazard was never that the name is absent, it is that a SUBSTRING
        # test would answer `STEM` for it. Asserted as INEQUALITY, which holds
        # whether or not the quantity exists.
        self.assertNotEqual(GC.q_covering("stem_direction"),
                            GC.q_covering("stem"))

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
        """The six that survive, so a future closure is a loud failure.

        ⚠️ It was SEVEN until 2026-09-10, when `fermata` left for
        `LEGACY_TO_Q` — `Q.FERMATA_MARK` reads the ink and `Q.FERMATA_OWNER`
        decides what it hangs over. The count in this docstring is the kind of
        hand-written figure that has rotted three times in this repo; the
        assertion below is the authority, not the sentence.
        """
        self.assertEqual(
            sorted(GC.NO_VOCABULARY),
            ["tied_from_prev", "tied_to_next"])

    def test_the_fermata_gap_is_CLOSED_and_stays_accounted(self) -> None:
        """Closed 2026-09-10. A closed gap must leave `NO_VOCABULARY` or the
        report describes the pipeline's history rather than the pipeline —
        and it must land in `LEGACY_TO_Q` rather than falling out of both."""
        self.assertIn("fermata", GC.LEGACY_TO_Q)
        self.assertNotIn("fermata", GC.NO_VOCABULARY)
        self.assertEqual(GC.LEGACY_TO_Q["fermata"], "FERMATA_OWNER")
        self.assertEqual(GC.FAMILY_TO_Q["fermata"], "FERMATA_MARK")

    def test_the_voice_gap_is_CLOSED_and_stays_accounted(self) -> None:
        """Closed 2026-09-10. `stem_direction` was derivable from `Q.STEM` —
        a row on the record since the CV rung was wired — and undeclared,
        which is why `adjudicate_event`'s divisi guard read
        `not_implemented`."""
        for key in ("stem_direction", "voices", "voice_index"):
            self.assertIn(key, GC.LEGACY_TO_Q, key)
            self.assertNotIn(key, GC.NO_VOCABULARY, key)
        self.assertEqual(GC.LEGACY_TO_Q["stem_direction"], "STEM_DIRECTION")
        self.assertEqual(GC.LEGACY_TO_Q["voices"], "VOICES")

    def test_the_ornament_gap_is_CLOSED_and_stays_accounted(self) -> None:
        """⚠️ CLOSING IT CLOSES NO DETECTION GAP, and the two must not be
        confused: `export_coverage.KNOWN_GAPS` records the eleven-work truth's
        only ornaments as twelve `<tremolo>` against a detector producing ZERO
        tremolo detections. The RECORD can now name the family; the PAGE still
        supplies none of it."""
        self.assertIn("ornaments", GC.LEGACY_TO_Q)
        self.assertNotIn("ornaments", GC.NO_VOCABULARY)
        self.assertEqual(GC.FAMILY_TO_Q["ornament"], "ORNAMENT_MARK")
        self.assertEqual(GC.FAMILY_TO_Q["tremolo"], "ORNAMENT_MARK",
                         "tremolo1-5 are ornaments whose class names do not "
                         "begin `ornament` -- one table, one quantity")

    def test_STEM_and_STEM_DIRECTION_stay_DIFFERENT_quantities(self) -> None:
        """⚠️ The reason `q_covering` is not a substring test, now that both
        names exist: `Q.STEM` carries a stem's BOX and says nothing about
        which way it points."""
        self.assertIsNotNone(GC.q_covering("stem"))
        self.assertEqual(GC.q_covering("stem_direction"), "STEM_DIRECTION")
        self.assertNotEqual(GC.q_covering("stem"),
                            GC.q_covering("stem_direction"))

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
        # ⚠️ ONE since 2026-09-10. `arc_kind` and `arc_owner` left this list on
        # 09-09; `articulation_owner` and then `wedge_anchor` left it on 09-10,
        # each landing with its emission and its counter rather than alone.
        # The count is asserted so that filling or ADDING a stub is a
        # deliberate edit here rather than a silent drift — which is what this
        # guard is for.
        #
        # ⚠️⚠️ THE ONE THAT REMAINS IS THE STARVED ONE, which is the shape this
        # finding predicted: every stub whose input was already gathered was
        # "one repair — write the adjudicator", and all four have now been
        # written. `direction` is the only one that was ever TWO pieces of
        # work, and it is the only one left.
        # ⚠️⚠️ ZERO SINCE 2026-09-11, WHEN `direction` -- the last, and the only
        # one that was ever TWO pieces of work -- was closed with its gatherer
        # and its adjudicator in one change. The count is asserted so that
        # ADDING a stub is a deliberate edit here rather than a silent drift,
        # and the names are in the message so the failure says which.
        self.assertEqual(len(starv), 0,
                         f"expected no declared stub, got {sorted(starv)}")
        for graduated in ("DYNAMIC", "ARTICULATION_OWNER", "WEDGE_ANCHOR",
                          "DIRECTION"):
            self.assertNotIn(graduated, starv,
                             f"`{graduated}` graduated: adjudicator written "
                             "and input gathered. A stub roster that keeps a "
                             "graduated entry describes history, not the "
                             "pipeline.")
        starved = {q for q, v in starv.items() if v["ungathered_inputs"]}
        self.assertEqual(starved, set(),
                         "the reading gap (`DIRECTION_WORD`) was the last "
                         "ungathered input and its gatherer landed with its "
                         "adjudicator")
        # ⚠️ THE POSITIVE CONTROL FOR THE TWO EMPTY SETS ABOVE. Both would
        # pass if `stub_starvation` were broken to return `{}`, which is the
        # vacuous-assertion shape this repo has shipped twice. So the
        # MECHANISM is exercised on a stub declared here.
        self.assertTrue(_starvation_sees_a_declared_stub(),
                        "`stub_starvation` cannot see a declared stub, so "
                        "the empty results above prove nothing")
        # ⚠️ The four fed stubs are now ONE repair each: the adjudicator.
        # Assert that positively, so a gatherer being deleted underneath them
        # fails here instead of turning a written decision into a silent
        # abstention.
        for name, row in starv.items():
            self.assertEqual(
                row["ungathered_inputs"], [],
                f"{name} lost an input it had after the merge -- writing its "
                f"adjudicator would now produce abstentions, not decisions")


if __name__ == "__main__":
    unittest.main()
