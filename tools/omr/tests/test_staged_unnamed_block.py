"""THE UNNAMED BLOCK AT THE FOOT OF A SYSTEM — placed, or narrowed, or not.

Sean, 2026-09-17, on a plate that labels its strings on the opening system and
nowhere else: *"If we had 4 or 5 staves that showed up last in the system
without a name in the margin they are almost surely strings."*

⚠️ THE SPLIT IS THE SUBJECT OF THIS FILE, not the placement. `adjudicate_slot_
index` does what the page FORCES -- a block that exactly fills the reference's
trailing family run has one order-preserving map and takes it -- and NARROWS
where it does not. The convention that finishes the job (*a short string block
is short at its FOOT, because the bottom pair is condensed*) is a claim about
engraving practice rather than about this page, so it lives in INFER, is
labelled, and can be argued out of by a clef.

⚠️ THE POSITIVE CONTROLS ARE IN THE SAME CLASS AS THE REFUSALS, for the fourth
time in this repo: a battery of refusal tests passes by refusing everything, so
`test_a_block_that_fills_the_run_is_decided` and
`test_the_convention_collapses_every_member_but_the_last` are what stop a rule
that returns None unconditionally from reading green.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, evaluate, infer
from tools.omr.staged import adjudicators          # noqa: F401 -- registers
from tools.omr.staged import inferences            # noqa: F401 -- registers
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

#: The Litolff Beethoven 5 shape, cut down to the part that matters: a lineup
#: whose TRAILING run is one family, and short systems that stop labelling it.
#: ⚠️ `Contrabasso`, not `Basso` -- the lexicon reads a bare `Basso` as a BASS
#: VOICE, which is a real defect this project documents and which would put a
#: non-string at the foot of the reference and silently shorten the run. The
#: fixture must not depend on that bug in either direction.
#: ⚠️ THE SHORT SYSTEMS MUST BE GENUINELY SHORTER THAN THIS. A system printing
#: as many staves as the reference takes the FULL-LINEUP branch, where position
#: is the answer and this rule is never reached -- the first draft of this file
#: built every fixture at the reference's own size and four tests measured that
#: branch instead, which is a fixture that does not reach the code it names.
#:
#: ⚠️ ONE `Violino` ONLY. The reference this document actually has prints
#: `Violino I` and `Violino II`, both of which the lexicon resolves to `Violin`
#: -- and a name appearing twice makes `_forced_pairing` ambiguous by design,
#: so a labelled violin would force NOTHING and the trimming test would be
#: measuring the ambiguity rather than the trim. The real-record arm covers the
#: repeated-name shape; this file keeps the fixture unambiguous on purpose.
FULL = ["Flauti", "Oboi", "Clarinetti", "Corni",
        "Violino I", "Viola", "Violoncello", "Contrabasso"]
#: slots   0         1        2             3
#:         4            5        6              7
STRING_RUN = [4, 5, 6, 7]
WINDS = ["Flauti", "Oboi", "Corni"]


def _document(systems, clefs=None, page=0):
    """`systems[i]` is a list of labels; `None` is a staff printing none.

    `clefs` is `{(system, ordinal): glyph}`, observed as `Q.CLEF_GLYPH`.
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
            glyph = (clefs or {}).get((s, i))
            if glyph is not None:
                log.observe(sub, Q.CLEF_GLYPH, glyph,
                            reader=READERS.DETECTOR, frame="cell", score=0.9)
    adjudicate.run(log)
    return log


def _v(log, system, ordinal, page=0):
    return log.verdict(Q.SLOT_INDEX, R.staff(page, system, ordinal))


def _run_infer(log):
    return infer.run(log, evaluate.Report(fired=[], skipped=[], stubs=[]))


class TestTheAdjudicatorPlacesOnlyWhatIsForced(unittest.TestCase):

    def test_a_block_that_fills_the_run_is_decided(self):
        """POSITIVE CONTROL. Five unnamed staves, five string slots, one map."""
        log = _document([FULL, WINDS + [None] * 4])
        got = [_v(log, 1, i) for i in range(3, 7)]
        self.assertEqual([v.outcome for v in got], [Outcome.DECIDED] * 4)
        self.assertEqual([v.value for v in got], STRING_RUN)
        self.assertEqual({v.reason for v in got}, {"family_block"})

    def test_a_block_one_short_is_narrowed_not_decided(self):
        """"It is one of these" — the answer this decision could not give."""
        log = _document([FULL, WINDS + [None] * 3])
        got = [_v(log, 1, i) for i in range(3, 6)]
        self.assertEqual([v.outcome for v in got], [Outcome.NARROWED] * 3)
        self.assertEqual([[c.value for c in v.candidates] for v in got],
                         [[4, 5], [5, 6], [6, 7]])

    def test_every_candidate_is_inside_the_run(self):
        """The narrowing bounds the inference: INFER cannot leave the family."""
        log = _document([FULL, WINDS + [None] * 3])
        for i in range(3, 6):
            for c in _v(log, 1, i).candidates:
                self.assertIn(c.value, STRING_RUN)

    def test_a_block_two_short_is_refused(self):
        """`FAMILY_BLOCK_MAX_DEFICIT`: which slots went missing is a guess."""
        log = _document([FULL, WINDS + [None] * 2])
        for i in range(3, 5):
            v = _v(log, 1, i)
            self.assertEqual(v.outcome, Outcome.ABSTAINED)
            self.assertEqual(v.reason, "unnamed_in_short_system")

    def test_an_interior_unnamed_staff_is_not_placed(self):
        """The claim is about a SUFFIX. A staff with names below it is not one."""
        log = _document([FULL,
                         ["Flauti", None, "Corni", "Violino I", "Viola",
                          "Violoncello", "Contrabasso"]])
        v = _v(log, 1, 1)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "unnamed_in_short_system")

    def test_an_interior_unnamed_staff_is_not_placed_WITH_a_block_below(self):
        """⚠️ THE FIXTURE ABOVE DOES NOT REACH THE GUARD, AND A MUTATION ARM
        SAID SO. With names below it there is no trailing block at all, so the
        deficit cap refuses that staff first and deleting `here < b0` changes
        nothing -- a test passing for a reason that is not the one it names.

        Here the system HAS a block, and an interior unnamed staff sits above
        it. Without the guard its block index is NEGATIVE and `run[i]` wraps
        round to the far end of the reference: silently, and onto another
        family.
        """
        log2 = _document([FULL,
                          ["Flauti", None, "Corni", "Violino I"] + [None] * 3])
        interior = _v(log2, 1, 1)
        self.assertEqual(interior.outcome, Outcome.ABSTAINED)
        self.assertEqual(interior.reason, "unnamed_in_short_system")
        # and the block BELOW it is still placed -- the guard is a refusal
        # about one staff, not about the system.
        self.assertEqual(_v(log2, 1, 4).outcome, Outcome.DECIDED)

    def test_a_block_longer_than_the_run_is_refused(self):
        """Six unnamed staves cannot be five string slots."""
        log = _document([FULL, ["Flauti", "Oboi"] + [None] * 5])
        for i in range(2, 7):
            self.assertEqual(_v(log, 1, i).outcome, Outcome.ABSTAINED)

    def test_the_run_is_trimmed_by_what_the_named_staves_took(self):
        """A labelled Violino I inside the run leaves the block the rest."""
        log = _document([FULL, WINDS + ["Violino I"] + [None] * 3])
        got = [_v(log, 1, i) for i in range(4, 7)]
        self.assertEqual([v.outcome for v in got], [Outcome.DECIDED] * 3)
        self.assertEqual([v.value for v in got], [5, 6, 7])

    def test_the_adjudicator_reads_no_clef(self):
        """⚠️ THE CIRCULARITY GUARD, ASSERTED BEHAVIOURALLY.

        `adjudicate_clef` weights the instrument at 1.0 in the other
        direction, so a slot placed off a clef closes a loop. Contradicting
        every glyph in the block must therefore change NOTHING here -- the
        clef is INFER's term, not this decision's.
        """
        plain = _document([FULL, WINDS + [None] * 4])
        lying = _document([FULL, WINDS + [None] * 4],
                          clefs={(1, i): "clefF" for i in range(3, 7)})
        for i in range(3, 7):
            self.assertEqual(_v(plain, 1, i).value, _v(lying, 1, i).value)


class TestTheConventionLivesInInfer(unittest.TestCase):

    SHORT = WINDS + [None] * 3

    def test_the_convention_collapses_every_member_but_the_last(self):
        """POSITIVE CONTROL for the rule, and the shape of the claim.

        ⚠️ ROADMAP 2.1b CHANGED WHAT "the last" MEANS HERE, and this fixture
        happens to land exactly on the case it changed: `FULL`'s trailing
        string run is `[Violin, Viola, Cello, Contrabass]`, so on a block
        short by one the LAST member's own two candidates are `[Cello,
        Contrabass]` -- the condensed `Violoncello e Basso` pair -- and it
        is now collapsed too, onto the Cello slot, exactly like the members
        above it. See `TestTheCondensedPairIsPlacedOnTheCelloSlot` below for
        the case that still stays NARROWED: a pair that is NOT [Cello,
        Contrabass]."""
        log = _document([FULL, self.SHORT])
        _run_infer(log)
        got = [_v(log, 1, i) for i in range(3, 6)]
        self.assertEqual([v.outcome for v in got], [Outcome.DECIDED] * 3)
        self.assertEqual([v.value for v in got], [4, 5, 6])

    def test_every_inference_is_labelled_and_supersedes_the_narrowing(self):
        log = _document([FULL, self.SHORT])
        _run_infer(log)
        for i in range(3, 5):
            v = _v(log, 1, i)
            self.assertTrue(v.detail.get("inferred"))
            self.assertEqual(v.detail.get("rule"),
                             "collapse_slot_index_to_family_block")
            self.assertIsNotNone(v.supersedes)

    def test_a_contradicting_clef_withdraws_the_WHOLE_block(self):
        """⚠️ A SHIFTED BLOCK IS ONE ERROR, NOT ONE PER STAFF.

        A tacet Violino II would put the deficit at the TOP, and the third
        staff would then be in BASS clef where front-alignment expects the
        viola's alto. Refusing only that staff would keep the two wrong
        placements the contradiction is evidence for.
        """
        log = _document([FULL, self.SHORT],
                        clefs={(1, 3): "clefG", (1, 5): "clefG"})
        _run_infer(log)
        for i in range(3, 6):
            self.assertEqual(_v(log, 1, i).outcome, Outcome.NARROWED)

    def test_an_agreeing_clef_does_not_stop_it(self):
        """The positive control for the test above: the term is not a gate."""
        log = _document([FULL, self.SHORT], clefs={(1, 3): "clefG"})
        _run_infer(log)
        self.assertEqual(_v(log, 1, 3).outcome, Outcome.DECIDED)

    def test_a_block_with_no_clef_at_all_is_still_inferred(self):
        """⚠️ SILENCE IS NOT CONTRADICTION. The plate this was measured on
        reads ZERO C clefs, so the viola never speaks; a rule that required
        corroboration would be silent exactly where the corroboration is."""
        log = _document([FULL, self.SHORT])
        _run_infer(log)
        self.assertEqual(_v(log, 1, 3).outcome, Outcome.DECIDED)

    def test_a_staff_disagreeing_with_itself_is_not_a_witness(self):
        """⚠️ ONE ANSWER OR NONE, NEVER A VOTE. A staff carrying both a
        `clefG` and a `clefF` cannot agree with itself, and picking its
        majority here would be a second clef DECISION sitting outside
        `adjudicate_clef`. It contributes NOTHING -- which is silence, and
        silence is not contradiction, so the block is inferred as before."""
        # Built by hand rather than through `_document`, because that helper
        # takes ONE glyph per staff and the whole point here is two.
        log2 = Log()
        systems = [FULL, self.SHORT]
        for s_i, names in enumerate(systems):
            log2.observe(R.system(0, s_i), Q.SYSTEM_STAFF_COUNT, len(names),
                         reader=READERS.GEOMETRY, frame="system")
            for i, name in enumerate(names):
                sub = R.staff(0, s_i, i)
                log2.observe(sub, Q.STAFF_ORDINAL, i,
                             reader=READERS.GEOMETRY, frame="system")
                if name is not None:
                    log2.observe(sub, Q.MARGIN_LABEL, name,
                                 reader=READERS.SURYA, frame="page")
                if (s_i, i) == (1, 3):
                    for g in ("clefG", "clefF"):
                        log2.observe(sub, Q.CLEF_GLYPH, g,
                                     reader=READERS.DETECTOR, frame="cell",
                                     score=0.9)
        adjudicate.run(log2)
        _run_infer(log2)
        self.assertEqual(_v(log2, 1, 3).outcome, Outcome.DECIDED)

    def test_a_deficit_the_adjudicator_never_emits_is_still_declined(self):
        """⚠️ THE CROSS-MODULE CONTRACT, MADE REACHABLE.

        `FAMILY_BLOCK_MAX_DEFICIT` holds the narrowing to one missing slot,
        so INFER's own `len(run) != len(members) + 1` guard can never fire on
        a record this tree produces -- and a mutation arm duly SURVIVED
        deleting it. It is kept because the two live in different modules and
        are free to drift, and it is tested by widening the cap so the
        adjudicator emits the shape the guard exists to refuse.
        """
        from tools.omr.staged.adjudicators import identity as ID
        was = ID.FAMILY_BLOCK_MAX_DEFICIT
        ID.FAMILY_BLOCK_MAX_DEFICIT = 2
        try:
            log = _document([FULL, WINDS + [None] * 2])
            self.assertEqual(_v(log, 1, 3).outcome, Outcome.NARROWED)
            _run_infer(log)
            self.assertEqual(_v(log, 1, 3).outcome, Outcome.NARROWED)
        finally:
            ID.FAMILY_BLOCK_MAX_DEFICIT = was

    def test_it_never_touches_a_forced_block(self):
        """Rule 3 of the stage: an inference may not overturn a reading."""
        log = _document([FULL, WINDS + [None] * 4])
        _run_infer(log)
        for i in range(3, 7):
            v = _v(log, 1, i)
            self.assertEqual(v.reason, "family_block")
            self.assertFalse(v.detail.get("inferred"))

    def test_the_rule_is_registered_and_targets_the_slot(self):
        """⚠️ `staged/brakes.py` measured 1 of 28 decisions able to hand work
        to INFER. This is the second target quantity, and a rule that stopped
        being registered would otherwise vanish with the suite green."""
        targets = {r.inference.value: r.target for r in infer.RULES}
        self.assertEqual(targets.get("collapse_slot_index_to_family_block"),
                         Q.SLOT_INDEX)


class TestTheCondensedPairIsPlacedOnTheCelloSlot(unittest.TestCase):
    """ROADMAP 2.1b. Sean, 2026-09-22, after the print
    (`benchmarks/omr-cello-bass-convention-2026-09/FINDINGS.md`): "the string
    family always includes all five; if there are only four lines the bass
    is doubling the celli or it comes in later." When the LAST member of a
    short block narrows to exactly the reference's [Cello, Contrabass] pair,
    it is a condensed `Violoncello e Basso` staff and is collapsed onto the
    Cello slot too -- never onto any OTHER pair, which is what the second and
    third tests below pin.
    """

    def test_cello_and_contrabass_collapses_with_the_detail_EXPORT_reads(self):
        """POSITIVE CONTROL, run RED against the unrepaired
        `collapse_slot_index_to_family_block` (it left the last member
        narrowed unconditionally, so this failed before the rule read the
        reference's own instrument names)."""
        log = _document([FULL, WINDS + [None] * 3])
        _run_infer(log)
        last = _v(log, 1, 5)
        self.assertEqual(last.outcome, Outcome.DECIDED)
        self.assertEqual(last.value, 6)                 # the Cello slot
        self.assertEqual(last.detail.get("rule"),
                         "collapse_slot_index_to_family_block")
        self.assertTrue(last.detail.get("inferred"))
        # ⚠️ THE ONE DETAIL `staged/export.py`'s join reads.
        self.assertEqual(last.detail.get("condensed_with_slot"), 7)
        self.assertIsNotNone(last.supersedes)

    def test_a_viola_and_cello_pair_does_not_collapse(self):
        """A block short by one from a THREE-slot string run (no Contrabass
        printed at all) leaves its last member's candidates at [Viola,
        Cello] -- not the condensed pair, and it stays exactly as narrow as
        `adjudicate_slot_index` left it."""
        no_bass = WINDS + ["Violino I", "Viola", "Violoncello"]
        log = _document([no_bass, WINDS + [None] * 2])
        _run_infer(log)
        last = _v(log, 1, 4)
        self.assertEqual(last.outcome, Outcome.NARROWED)
        self.assertEqual([c.value for c in last.candidates], [4, 5])
        self.assertFalse(last.detail.get("inferred"))

    def test_a_reference_with_no_contrabass_slot_does_not_collapse(self):
        """The trailing run the block is short from need not be strings at
        all -- here it is winds, with the reference's OWN Contrabass slot
        sitting elsewhere, already forced onto a NAMED staff and outside
        this block's run entirely (this system's four named strings pair to
        it directly, by name). ⚠️ THE SYSTEM MUST PRINT FEWER STAVES THAN
        THE REFERENCE, not merely leave some unnamed, or `adjudicate_slot_
        index` takes the full-lineup (position-is-the-answer) branch and this
        rule is never reached -- the fixture file's own standing warning
        about the first draft of this file. The pair the two-staff wind
        block narrows to is [Oboi, Clarinetti], and neither is a Cello or a
        Contrabass."""
        winds_last = ["Violino I", "Viola", "Violoncello", "Contrabasso",
                      "Flauti", "Oboi", "Clarinetti"]
        short = ["Violino I", "Viola", "Violoncello", "Contrabasso",
                None, None]
        log = _document([winds_last, short])
        _run_infer(log)
        last = _v(log, 1, 5)
        self.assertEqual(last.outcome, Outcome.NARROWED)
        self.assertEqual([c.value for c in last.candidates], [5, 6])
        self.assertFalse(last.detail.get("inferred"))


if __name__ == "__main__":
    unittest.main()
