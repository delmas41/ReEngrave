"""THE THREE CHANNELS AS CONSTRAINTS -- order, family block, clef.

Sean, 2026-09-22: *"margin names, instrumentation lists from the doc or a
dossier, Order, family brackets should all come first in determining what the
instrument is"*, and the clef only where we are sure of it.

⚠️ THE POSITIVE CONTROLS ARE IN THE SAME CLASS AS THE REFUSALS. A battery of
refusal tests passes by refusing everything -- this repo's own lesson, four
times over -- so `test_the_clef_forces_a_staff_the_block_only_narrowed` and
`test_a_partly_forced_block_is_still_collapsed_by_infer` are what stop a
branch that returns None unconditionally from reading green.

⚠️ THE FIXTURE MUST BE SHORTER THAN THE REFERENCE. A system printing as many
staves as the lineup takes the FULL-LINEUP branch, where position is the
answer and none of this is reached -- the sibling file records four tests that
measured that branch by accident.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, evaluate, infer
from tools.omr.staged import adjudicators          # noqa: F401 -- registers
from tools.omr.staged import inferences            # noqa: F401 -- registers
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import identity
from tools.omr.staged.record import Log, Outcome, Q, READERS

#: One `Violino` only, for the reason the sibling fixture records: a repeated
#: name makes `_forced_pairing` ambiguous BY DESIGN and the test would then be
#: measuring the ambiguity.
FULL = ["Flauti", "Oboi", "Clarinetti", "Corni",
        "Violino I", "Viola", "Violoncello", "Contrabasso"]
STRING_RUN = [4, 5, 6, 7]
WINDS = ["Flauti", "Oboi", "Corni"]

#: `4|4` -- the winds and the strings, as the interior barlines would stop.
BLOCKS_FULL = [0, 0, 0, 0, 1, 1, 1, 1]


def _document(systems, *, clefs=None, blocks=None, page=0):
    """`systems[i]` is a list of labels; `None` is a staff printing none.

    `clefs` is `{(system, ordinal): glyph or located-name}` and `blocks` is
    `{system: [block id by ordinal]}`.
    """
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
            row = (blocks or {}).get(s)
            if row is not None and i < len(row):
                log.observe(sub, Q.BRACKET_BLOCK, row[i],
                            reader=READERS.GEOMETRY, frame="page")
            got = (clefs or {}).get((s, i))
            if got is None:
                continue
            if got.startswith("clef"):
                log.observe(sub, Q.CLEF_GLYPH, got,
                            reader=READERS.DETECTOR, frame="cell", score=0.9)
            else:
                log.observe(sub, Q.CLEF_LOCATED, got,
                            reader=READERS.CV_LOCATOR, frame="header_window",
                            score=0.85)
    adjudicate.run(log)
    return log


def _v(log, system, ordinal, page=0):
    return log.verdict(Q.SLOT_INDEX, R.staff(page, system, ordinal))


def _run_infer(log):
    return infer.run(log, evaluate.Report(fired=[], skipped=[], stubs=[]))


class TestTheClefNarrowsWhatPositionCannot(unittest.TestCase):

    def test_the_clef_forces_a_staff_the_block_only_narrowed(self):
        """POSITIVE CONTROL, and the whole point of the branch.

        Three unnamed staves on a four-slot string run: the family block
        narrows every one of them to two candidates. An ALTO clef on the
        MIDDLE one can only be the Viola slot, and the staves above and below
        it then follow by order alone.

        ⚠️ THE ALTO MUST GO WHERE A VIOLA CAN ACTUALLY STAND, and the first
        draft of this test put it on the LAST staff -- where no
        order-preserving map can place it, because only one run slot lies
        above the Viola and two staves would have to share it. A fixture that
        makes its own claim impossible tests nothing.

        ⚠️⚠️ AND THE THIRD STAFF STAYS NARROWED, WHICH IS THE RULE BEING
        RIGHT RATHER THAN SHORT. It reads a BASS clef, and both the
        Violoncello and the Contrabasso slots are written in one -- the clef
        cannot separate them and neither can position. That is the condensed
        pair this plate actually prints, and the second draft of this test
        expected all three to decide.
        """
        short = WINDS + [None] * 3
        log = _document([FULL, short],
                        clefs={(1, 3): "clefG", (1, 4): "alto", (1, 5): "clefF"},
                        blocks={0: BLOCKS_FULL, 1: [0, 0, 0, 1, 1, 1]})
        got = [_v(log, 1, i) for i in range(3, 6)]
        self.assertEqual([v.outcome for v in got[:2]], [Outcome.DECIDED] * 2)
        self.assertEqual([v.value for v in got[:2]], [4, 5])
        self.assertEqual({v.reason for v in got[:2]}, {"forced_by_constraints"})
        self.assertEqual(got[2].outcome, Outcome.NARROWED)
        self.assertEqual([c.value for c in got[2].candidates], [6, 7])

    def test_without_the_clef_the_same_staves_are_only_narrowed(self):
        """The CONTROL for the control: identical fixture, no clef read."""
        log = _document([FULL, WINDS + [None] * 3],
                        blocks={0: BLOCKS_FULL, 1: [0, 0, 0, 1, 1, 1]})
        got = [_v(log, 1, i) for i in range(3, 6)]
        self.assertEqual([v.outcome for v in got], [Outcome.NARROWED] * 3)
        self.assertEqual({v.reason for v in got},
                         {"family_block_not_forced"})

    def test_the_flag_off_restores_the_shipped_answer_exactly(self):
        real = identity.slot_constraints_enabled
        identity.slot_constraints_enabled = lambda: False
        try:
            log = _document(
                [FULL, WINDS + [None] * 3],
                clefs={(1, 3): "clefG", (1, 4): "clefG", (1, 5): "alto"},
                blocks={0: BLOCKS_FULL, 1: [0, 0, 0, 1, 1, 1]})
        finally:
            identity.slot_constraints_enabled = real
        got = [_v(log, 1, i) for i in range(3, 6)]
        self.assertEqual([v.outcome for v in got], [Outcome.NARROWED] * 3)


class TestAChannelMayNarrowAndNeverEmpty(unittest.TestCase):

    def test_a_clef_no_slot_admits_is_dropped_not_obeyed(self):
        """⚠️ THE MEASURED HAZARD. On Litolff p2/s1 a FALSE `tenor` on a
        bassoon names a clef no reference slot admits; obeyed, the system is
        unsatisfiable and the whole channel dies with it. Here the last
        unnamed staff reads `soprano`, which no slot of this lineup is
        written in -- the channel must be DROPPED and the block's own
        narrowing must survive."""
        log = _document([FULL, WINDS + [None] * 3],
                        clefs={(1, 5): "soprano"},
                        blocks={0: BLOCKS_FULL, 1: [0, 0, 0, 1, 1, 1]})
        got = [_v(log, 1, i) for i in range(3, 6)]
        self.assertEqual([v.outcome for v in got], [Outcome.NARROWED] * 3)
        self.assertEqual([[c.value for c in v.candidates] for v in got],
                         [[4, 5], [5, 6], [6, 7]])

    def test_a_named_staff_s_clef_is_never_a_constraint(self):
        """A name already pins it, so the clef can only ever subtract -- four
        forced staves on one real system, to one wrong reading."""
        log = _document([FULL, WINDS + [None] * 3],
                        clefs={(1, 0): "soprano",        # a false read
                               (1, 3): "clefG", (1, 4): "alto", (1, 5): "clefF"},
                        blocks={0: BLOCKS_FULL, 1: [0, 0, 0, 1, 1, 1]})
        got = [_v(log, 1, i) for i in range(3, 6)]
        self.assertEqual([v.outcome for v in got[:2]], [Outcome.DECIDED] * 2,
                         "a named staff's clef must not reach the solver")
        self.assertEqual([v.value for v in got[:2]], [4, 5])

    def test_disagreeing_glyph_rows_are_no_opinion(self):
        """A measure cell holds the NEIGHBOUR's clef too. Two rows naming two
        clefs is not a vote; choosing between them is `adjudicate_clef`'s job
        and a second copy of that contest here would be free to disagree."""
        log = Log()
        sub = R.staff(0, 0, 0)
        log.observe(sub, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell", score=0.9)
        log.observe(sub, Q.CLEF_GLYPH, "clefF", reader=READERS.DETECTOR,
                    frame="cell", score=0.8)
        ev = adjudicate.Evidence(log, sub, adjudicate.REGISTRY[Q.SLOT_INDEX])
        self.assertIsNone(identity._clef_read_at(ev, sub))


class TestTheAlternatingClefsAreWhyTheChannelSurvives(unittest.TestCase):

    def test_a_cello_slot_admits_both_its_clefs(self):
        """⚠️ MEASURED, NOT ASSUMED. Breitkopf's reference reads its cello
        slot `tenor` and three later systems read it `bass`, all at margin
        4.5. A slot admitting only one of those refuses 5 of 6 systems."""
        self.assertEqual(identity._admissible_clefs(
            {"name": "Cello", "expected_clef": "bass"}), ("bass", "tenor"))

    def test_a_violin_slot_admits_only_its_own(self):
        self.assertEqual(identity._admissible_clefs(
            {"name": "Violin", "expected_clef": "treble"}), ("treble",))

    def test_a_slot_with_no_instrument_has_no_opinion(self):
        """A reference slot the document could not read must WIDEN the
        candidate set and never empty it."""
        self.assertIsNone(identity._admissible_clefs(None))
        self.assertIsNone(identity._admissible_clefs({"name": "Flute"}))

    def test_a_bass_reading_does_not_exclude_the_cello_slot(self):
        log = _document([FULL, WINDS + [None] * 3],
                        clefs={(1, 5): "clefF"},
                        blocks={0: BLOCKS_FULL, 1: [0, 0, 0, 1, 1, 1]})
        v = _v(log, 1, 5)
        cands = [c.value for c in v.candidates] if v.candidates else [v.value]
        self.assertIn(6, cands, "the Violoncello slot must stay admissible")


class TestItFiltersTheBlockAndDoesNotReplaceIt(unittest.TestCase):

    def test_a_partly_forced_block_is_still_collapsed_by_infer(self):
        """⚠️⚠️ THE REGRESSION THIS FILE EXISTS FOR. Deciding two members of
        a block used to remove them from `inferences._block_members`, which
        requires the narrowings to cover `0..k-1` -- the block then had holes,
        INFER skipped it whole, and TWO Violas the shipped path places
        correctly came out narrowed. A branch additive in its own terms can
        still subtract through a rule downstream of it."""
        short = WINDS + [None] * 3
        log = _document([FULL, short],
                        clefs={(1, 3): "clefG"},
                        blocks={0: BLOCKS_FULL, 1: [0, 0, 0, 1, 1, 1]})
        before = [_v(log, 1, i).outcome for i in range(3, 6)]
        self.assertIn(Outcome.DECIDED, before, "the fixture must PARTLY force")
        self.assertIn(Outcome.NARROWED, before, "and must leave a narrowing")
        _run_infer(log)
        got = [_v(log, 1, i) for i in range(3, 6)]
        self.assertEqual([v.outcome for v in got[:2]], [Outcome.DECIDED] * 2)
        self.assertEqual([v.value for v in got[:2]], [4, 5])

    def test_the_narrowing_keeps_the_block_s_own_reason_and_detail(self):
        """INFER reads `family_block_not_forced` and its detail keys; a filter
        that renamed either would silently switch that rule off."""
        log = _document([FULL, WINDS + [None] * 3],
                        blocks={0: BLOCKS_FULL, 1: [0, 0, 0, 1, 1, 1]})
        v = _v(log, 1, 3)
        self.assertEqual(v.reason, "family_block_not_forced")
        for key in ("block_size", "block_index", "block_first_ordinal",
                    "run", "run_clefs"):
            self.assertIn(key, v.detail)


if __name__ == "__main__":
    unittest.main()


class TestTheGuardsTheFirstBatteryWasBLINDTo(unittest.TestCase):
    """⚠️⚠️ SIX ARMS SURVIVED THE FIRST RUN OF `mutate_rule.py` AND EVERY ONE
    WAS A REAL GAP. The tests above assert the OUTCOME, and most of these
    guards are invisible in an outcome: a channel that is silently dropped and
    a channel that contributes nothing produce the same verdict. These reach
    the mechanism directly.
    """

    #: The reference of `FULL`, as `_constrained_slots` sees it.
    REF_NAMES = ["Flute", "Oboe", "Clarinet", "Horn",
                 "Violin", "Viola", "Cello", "Contrabass"]
    REF_BLOCKS = [0, 0, 0, 0, 1, 1, 1, 1]
    REF_CLEFS = [("treble",), ("treble",), ("treble",), ("treble",),
                 ("treble",), ("alto",), ("bass", "tenor"), ("bass",)]

    def _solve(self, names, blocks, clefs, *, ref_names=None, ref_blocks=None,
               ref_clefs=None):
        ref_names = self.REF_NAMES if ref_names is None else ref_names
        ref_blocks = self.REF_BLOCKS if ref_blocks is None else ref_blocks
        ref_clefs = self.REF_CLEFS if ref_clefs is None else ref_clefs
        bmap = identity._block_map(blocks, ref_blocks)
        return identity._solve(len(names), names, blocks, clefs, ref_names,
                               ref_blocks, ref_clefs, bmap)

    def test_a_contradictory_clef_is_DROPPED_and_named(self):
        """⚠️ THE DROP IS INVISIBLE IN THE VERDICT. A channel silently
        discarded and a channel that merely added nothing leave the same
        narrowing behind, so only the mechanism can be asked. `soprano` is a
        clef no slot of this lineup is written in."""
        sols, dropped = self._solve(
            names=["Flute", "Oboe", "Horn", None, None, None],
            blocks=[0, 0, 0, 1, 1, 1],
            clefs=[None, None, None, None, None, "soprano"])
        self.assertTrue(sols, "the solver must still answer")
        self.assertEqual(dropped, ["clef"])

    def test_a_clef_that_fits_is_NOT_dropped(self):
        """The positive control for the arm above: nothing to drop."""
        sols, dropped = self._solve(
            names=["Flute", "Oboe", "Horn", None, None, None],
            blocks=[0, 0, 0, 1, 1, 1],
            clefs=[None, None, None, None, "alto", None])
        self.assertTrue(sols)
        self.assertEqual(dropped, [])

    def test_an_unnamed_reference_slot_admits_every_named_staff(self):
        """⚠️⚠️ MEASURED ON BREITKOPF, whose reference lineup has THREE slots
        the reader could not name -- one of them the horn staff whose label
        truncates to `'(C)'`. Requiring a named staff to MATCH a slot name
        made every system holding them unsatisfiable. `None` on the reference
        side means *we do not know what this slot is*; it excludes nobody."""
        ref = list(self.REF_NAMES)
        ref[1] = None                       # the Oboe slot never resolved
        sols, dropped = self._solve(
            names=["Flute", "Oboe", "Horn", None, None, None],
            blocks=[0, 0, 0, 1, 1, 1], clefs=[None] * 6, ref_names=ref)
        self.assertTrue(sols, "an unreadable slot must not empty the map")
        self.assertEqual(dropped, [])

    def test_a_system_with_FEWER_family_blocks_silences_the_channel(self):
        """A system printing fewer blocks than the reference has had a whole
        SECTION go tacet, and WHICH section is exactly what an index map would
        be guessing. The channel says nothing rather than aligning anyway."""
        self.assertIsNone(identity._block_map([0, 0, 0], self.REF_BLOCKS))
        self.assertEqual(identity._block_map([3, 3, 7, 7], [0, 0, 1, 1]),
                         {3: 0, 7: 1})

    def test_a_narrowing_the_filter_KEEPS_keeps_the_block_s_reason(self):
        """⚠️ INFER reads `family_block_not_forced` AND its detail keys, so a
        filter that renamed either would switch that rule off silently."""
        log = _document([FULL, WINDS + [None] * 3],
                        blocks={0: BLOCKS_FULL, 1: [0, 0, 0, 1, 1, 1]})
        v = _v(log, 1, 3)
        self.assertEqual(v.reason, "family_block_not_forced")
        self.assertIn("run", v.detail)

    def test_the_SHRINK_branch_is_unreachable_at_the_current_deficit_cap(self):
        """⚠️⚠️ A BRANCH THAT CANNOT FIRE CANNOT BE WRONG AND CANNOT BE RIGHT,
        and this one is named rather than left to be re-discovered.

        `_apply_constraints` can return a SMALLER narrowing, and under
        `FAMILY_BLOCK_MAX_DEFICIT = 1` it never does: a block one slot short
        narrows every member to exactly `deficit + 1 == 2` candidates, so the
        filter either leaves both (and stands aside) or leaves one (and
        decides). A still-plural shrink needs three candidates, which needs a
        deficit of two, which that constant refuses.

        The branch is KEPT rather than deleted because raising the cap is a
        live possibility and silently dropping the narrowing then would lose
        information. This test is what tells the next reader that the cap and
        the branch are coupled -- and it will fail, loudly, the day the cap
        moves without a test for the branch.
        """
        self.assertEqual(identity.FAMILY_BLOCK_MAX_DEFICIT, 1)
        log = _document([FULL, WINDS + [None] * 3],
                        blocks={0: BLOCKS_FULL, 1: [0, 0, 0, 1, 1, 1]})
        for i in range(3, 6):
            v = _v(log, 1, i)
            if v.outcome is Outcome.NARROWED:
                self.assertEqual(len(v.candidates), 2)

    def test_the_clef_is_read_for_unnamed_staves_only(self):
        """⚠️ THE GUARD IS IN TWO PLACES and the first battery could only
        mutate one, so the arm read as an equivalent mutant. This asserts the
        POPULATION site: a named staff's clef is never even collected, so a
        false reading on it cannot reach the solver however `_admissible` is
        written."""
        import inspect
        src = inspect.getsource(identity._apply_constraints)
        self.assertIn("if names[sub.staff] is None:", src,
                      "the clef must be collected for unnamed staves only")
        self.assertIn("mine is None", inspect.getsource(identity._admissible),
                      "and excluded again where it is applied")
