"""A SHORT system pairs by instrument NAME, and abstains where it cannot.

⚠️ THIS IS THE RULE `adjudicate_slot_index`'s OWN DOCSTRING HAS DESCRIBED IN
BOLD SINCE IT WAS WRITTEN, and which the function did not contain: it returned
the staff's ordinal on every path. `adjudicate_part_partition` then consumed a
table that was the position and the exporter joined systems of 12, 11 and 8
staves by position -- 12 of 75 staff-systems on the wrong instrument, a Timpani
part carrying the Viola's key signature
(`benchmarks/omr-part-join-phase2-2026-09/FINDINGS.md`).

⚠️ THE POSITIVE CONTROL IS IN THE SAME CLASS AS THE REFUSALS, deliberately and
for the third time in this repo: a battery of refusal tests passes by refusing
everything, so `test_the_short_system_is_paired_by_name` is what stops a rule
that abstains unconditionally from reading green.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  -- registers them
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators.identity import (
    _forced_pairing, _pick_reference)
from tools.omr.staged.record import Log, Outcome, Q, READERS


# The Litolff Beethoven 5 shape, cut down: a full lineup, then a system that
# suppresses an INTERIOR part. The interior suppression is the whole of it --
# a trailing one is invisible to an ordinal join.
FULL = ["Flauti", "Oboi", "Clarinetti", "Fagotti", "Corni", "Trombe",
        "Timpani", "Viola", "Violoncello"]
SHORT = ["Flauti", "Clarinetti", "Fagotti", "Corni"]


def _document(systems, page=0):
    """`systems` is a list of label lists; `None` prints a staff with no label."""
    log = Log()
    for s, names in enumerate(systems):
        log.observe(R.system(page, s), Q.SYSTEM_STAFF_COUNT, len(names),
                    reader=READERS.GEOMETRY, frame="system")
        for i, name in enumerate(names):
            sub = R.staff(page, s, i)
            log.observe(sub, Q.STAFF_ORDINAL, i,
                        reader=READERS.GEOMETRY, frame="system")
            if name is not None:
                log.observe(sub, Q.MARGIN_LABEL, name,
                            reader=READERS.SURYA, frame="page")
    adjudicate.run(log)
    return log


def _slots(log, system, n, page=0):
    out = []
    for i in range(n):
        v = log.verdict(Q.SLOT_INDEX, R.staff(page, system, i))
        out.append(v.value if v.outcome is Outcome.DECIDED else v.reason)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# The pairing itself, as a pure function
# ─────────────────────────────────────────────────────────────────────────────


class TestTheForcedPairing(unittest.TestCase):
    def test_an_interior_suppression_leaves_a_GAP(self):
        """The information a slot has and an ordinal does not."""
        self.assertEqual(
            _forced_pairing(["A", "C", "D"], ["A", "B", "C", "D"]),
            [0, 2, 3])

    def test_an_unnamed_staff_is_never_placed(self):
        """⚠️ `slots.align` WOULD place it, by position, and that is where the
        whole-work run's off-by-three lives. Here it comes back None."""
        self.assertEqual(
            _forced_pairing(["A", None, "D"], ["A", "B", "C", "D"]),
            [0, None, 3])

    def test_a_name_the_reference_never_prints_is_not_placed(self):
        self.assertEqual(
            _forced_pairing(["A", "Z"], ["A", "B", "C"]), [0, None])

    def test_a_repeated_name_with_ONE_staff_is_ambiguous(self):
        """Reference prints Violin twice; the system prints it once. Which
        one? There is no answer, so there is no value."""
        self.assertEqual(_forced_pairing(["V"], ["V", "V"]), [None])

    def test_a_repeated_name_with_BOTH_staves_is_forced(self):
        """And the same page that makes the case above ambiguous makes this
        one certain -- monotonicity does all the work."""
        self.assertEqual(_forced_pairing(["V", "V"], ["V", "V"]), [0, 1])

    def test_two_staves_competing_for_ONE_reference_slot_both_abstain(self):
        """⚠️⚠️ THE CASE CONDITION (a) ALONE GETS WRONG, and it is the common
        one on an orchestral page. Each staff's candidate set is the single
        slot 0 -- uniquely, and mutually exclusively -- so a rule asking only
        "is the candidate unique" places BOTH in part 0. Condition (b) asks
        whether a best pairing could leave the staff unpaired, and here one
        always can."""
        self.assertEqual(_forced_pairing(["V", "V"], ["V"]), [None, None])

    def test_an_empty_reference_places_nothing(self):
        self.assertEqual(_forced_pairing(["A"], []), [None])

    def test_the_placements_are_strictly_increasing(self):
        """A post-condition rather than a case: a pairing that went backwards
        would put a lower staff on a higher part, which is a graft by another
        route."""
        got = [j for j in _forced_pairing(
            ["A", "C", "E", None, "G"],
            ["A", "B", "C", "D", "E", "F", "G"]) if j is not None]
        self.assertEqual(got, sorted(set(got)))
        self.assertEqual(got, [0, 2, 4, 6])


# ─────────────────────────────────────────────────────────────────────────────
# The reference lineup
# ─────────────────────────────────────────────────────────────────────────────


class TestTheReferenceLineup(unittest.TestCase):
    """⚠️ A system can omit a tacet part and can never invent one, so the
    LARGEST system is a lower bound on the lineup. That is a structural claim,
    not a fit -- which is what separates it from `slots.build_reference`, whose
    recurring-shape rule once named 149 Brahms staves an instrument the work
    has not got."""

    def _sizes(self, *pairs):
        return {R.system(0, s): n for s, n in pairs}

    def test_the_widest_system_wins(self):
        names = {R.system(0, 0): ["A", "B"], R.system(0, 1): ["A", "B", "C"]}
        sub, ref = _pick_reference(self._sizes((0, 2), (1, 3)), 3, names)
        self.assertEqual(sub, R.system(0, 1))
        self.assertEqual(ref, ["A", "B", "C"])

    def test_a_tie_on_size_goes_to_the_system_naming_most(self):
        names = {R.system(0, 0): [None, None, None],
                 R.system(0, 1): ["A", "B", "C"]}
        sub, _ = _pick_reference(self._sizes((0, 3), (1, 3)), 3, names)
        self.assertEqual(sub, R.system(0, 1))

    def test_two_equally_named_systems_that_DISAGREE_abstain(self):
        """⚠️ Taking the first would be a coin flip wearing a subject key."""
        names = {R.system(0, 0): ["A", "B"], R.system(0, 1): ["A", "Z"]}
        self.assertIsNone(_pick_reference(self._sizes((0, 2), (1, 2)), 2, names))

    def test_two_equally_named_systems_that_AGREE_are_fine(self):
        """The positive control for the refusal above."""
        names = {R.system(0, 0): ["A", "B"], R.system(0, 1): ["A", "B"]}
        sub, ref = _pick_reference(self._sizes((0, 2), (1, 2)), 2, names)
        self.assertEqual(ref, ["A", "B"])
        self.assertEqual(sub, R.system(0, 0))

    def test_the_reference_row_is_padded_to_the_widest_size(self):
        """A system whose trailing staves read no name still has that many
        slots, and a short row would silently shorten the lineup."""
        names = {R.system(0, 0): ["A"]}
        _, ref = _pick_reference(self._sizes((0, 3)), 3, names)
        self.assertEqual(ref, ["A", None, None])


# ─────────────────────────────────────────────────────────────────────────────
# End to end through `adjudicate.run`
# ─────────────────────────────────────────────────────────────────────────────


class TestTheDecision(unittest.TestCase):
    def test_the_short_system_is_paired_by_name(self):
        """⚠️ THE POSITIVE CONTROL. Without it every refusal below is
        satisfied by a rule that abstains unconditionally."""
        log = _document([FULL, SHORT])
        self.assertEqual(_slots(log, 0, len(FULL)), list(range(len(FULL))))
        # Oboi is suppressed, so Clarinetti keeps slot 2 instead of sliding
        # up to 1 -- which is the graft, to the staff.
        self.assertEqual(_slots(log, 1, len(SHORT)), [0, 2, 3, 4])
        for i in range(len(SHORT)):
            v = log.verdict(Q.SLOT_INDEX, R.staff(0, 1, i))
            self.assertEqual(v.reason, "paired_by_name")

    def test_the_full_system_is_UNCHANGED_and_still_positional(self):
        """The equal-count population is where the ordinal join was measured
        identical to truth on 3 documents. It must not move."""
        log = _document([FULL, FULL])
        for s in (0, 1):
            self.assertEqual(_slots(log, s, len(FULL)),
                             list(range(len(FULL))))

    def test_a_short_system_staff_with_no_name_abstains(self):
        """⚠️ PREFER A FRAGMENT TO A GRAFT. The exporter already strands a
        staff with no slot into its own part; that is visibly unfinished,
        where a grafted part looks like a clean score."""
        log = _document([FULL, ["Flauti", None, "Corni"]])
        got = _slots(log, 1, 3)
        self.assertEqual(got[0], 0)
        self.assertEqual(got[1], "unnamed_in_short_system")
        self.assertEqual(got[2], 4)

    def test_a_reference_that_names_NOTHING_is_its_own_refusal(self):
        """⚠️ Different from "this staff has no name", and it wants a
        different repair: a reader, not a re-read of one staff."""
        log = _document([[None] * len(FULL), [None] * 3])
        self.assertEqual(_slots(log, 1, 3), ["reference_names_nothing"] * 3)

    def test_an_unpairable_name_and_an_ambiguous_one_are_told_apart(self):
        log = _document([["Flauti", "Violino I", "Violino II"],
                         ["Tuba", "Violino I"]])
        self.assertEqual(_slots(log, 1, 2),
                         ["not_in_reference", "ambiguous_pairing"])

    def test_the_gapped_table_reaches_the_PART_JOIN(self):
        """⚠️⚠️ THE WHOLE CHAIN, AND THE ONE ASSERTION THAT MATTERS.
        `_slots_are_ordinals` refused a contiguous table because it carried
        nothing the ordinal did not. A gapped one does, so `part_partition`
        stops saying `deduced_anchor` and joins by slot."""
        log = _document([FULL, SHORT])
        v = log.verdict(Q.PART_PARTITION, R.DOCUMENT)
        self.assertEqual(v.reason, "slot")
        self.assertEqual(v.value["join"], "slot")

    def test_and_it_still_REFUSES_where_no_name_was_read(self):
        """The other side of the same control: reading no labels must leave
        the refusal exactly as it was."""
        log = _document([[None] * len(FULL), [None] * 4])
        v = log.verdict(Q.PART_PARTITION, R.DOCUMENT)
        self.assertEqual(v.reason, "deduced_anchor")


if __name__ == "__main__":
    unittest.main()
