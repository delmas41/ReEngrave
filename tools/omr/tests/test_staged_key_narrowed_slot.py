"""Roadmap 2.9c — the part check speaks to a NARROWED slot, exactly where
every candidate agrees.

⚠️ THE BRIEF: 2.9b's residual 18 Litolff key changes are all one part's,
because 13 of 15 reader-decided Cello staves get their `Q.SLOT_INDEX` from
INFER (`inferences.collapse_slot_index_to_family_block`), which runs AFTER
ADJUDICATE. At ADJUDICATE time the part check (`header._part_checked`,
through `header._slot_of`) finds a NARROWED slot, not a placed one, and the
staff goes unjudged — `benchmarks/omr-key-majority-2026-09/FINDINGS.md`
§2.9b.5a, §2.9b.7. CLAUDE.md §4a refuses moving the placement rule into
ADJUDICATE (it is BEST rather than FORCED); the fix built here is the other
shape named in §2.9b.7: the check computes what EVERY candidate slot would
conclude, and answers only where they are unanimous.

⚠️ THIS FILE IS RED ON THE UNREPAIRED TREE, and that is checkable with one
command rather than asserted here:

    git grep -n -e _slot_candidates -e slot_candidates \
        -e narrowed_slot_unanimous <sha-before-2.9c> -- tools/omr/staged/

returns NOTHING before this item, so `header._slot_candidates` cannot be
imported and the narrowed-slot fixture below raises `AttributeError` rather
than passing. It was run against the unrepaired tree and failed exactly that
way before the fix landed (see the FINDINGS.md `§2.9c` RED section).

⚠️ COHERENCE, NOT ACCURACY, exactly as `test_staged_key_by_part.py` says of
itself. Every fixture here is hand-built; the accuracy figures (Litolff base
vs arm) are in `benchmarks/omr-key-majority-2026-09/FINDINGS.md` §2.9c.

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT. Every assertion is about a
verdict the machine wrote or a value a pure function returned.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401 -- registers ADJUDICATE
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import header as H
from tools.omr.staged.record import (Candidate, Kind, Log, Outcome, Q,
                                     Subject, Verdict)

#: One staff space in the CELL's canonical frame — matches
#: `test_staged_key_by_part.py`'s `SPACE` so the two files' marker runs mean
#: the same thing.
SPACE = 85.0


def _flats(n, x0=375.0):
    return [("keyFlat", x0 + i * SPACE) for i in range(n)]


def _header(log, page, system, staff, *, markers=(), label=None,
            clef="treble"):
    """One staff's header ink. No verdicts — ADJUDICATE writes those.

    Lifted from `test_staged_key_by_part.py`'s helper of the same name,
    unchanged: the two files must mean the same thing by "one staff's
    header" or a coherence result in one would not transfer to the other.
    """
    sub = R.staff(page, system, staff)
    log.observe(sub, Q.CLEF_GLYPH,
                {"treble": "clefG", "bass": "clefF", "alto": "clefC"}[clef],
                reader="detector", frame="cell:0", score=0.95)
    log.observe(R.cell(page, system, staff, 0), Q.CELL_STAFF_SPACE, SPACE,
                reader="geometry", frame="cell:0")
    if label is not None:
        log.observe(sub, Q.MARGIN_LABEL, label, reader="text_layer",
                    frame="page")
    for kind, x in markers:
        log.observe(sub, Q.KEYSIG_MARKER, kind, reader="detector",
                    frame="cell:0", score=0.92, x=x, y_center=500)
    return sub


def _slot(log, sub, slot, instrument=None):
    """A DECIDED `Q.SLOT_INDEX`, as `adjudicate_slot_index` would leave one
    when the staff is genuinely PLACED. Lifted from `test_staged_key_by_part`.
    """
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=Q.SLOT_INDEX,
        outcome=Outcome.DECIDED, value=slot, decider="test",
        reason="paired_by_name",
        detail={"instrument": instrument} if instrument else {}))


def _narrowed_slot(log, sub, candidates):
    """A NARROWED `Q.SLOT_INDEX`, as `_place_in_family_block` leaves one when
    the trailing unnamed block is SHORT of the reference run — `"it is one
    of these"`, every candidate carrying equal support because position
    alone has run out (`identity._place_in_family_block`'s own docstring).

    ⚠️ THIS IS THE FIXTURE ROADMAP 2.9C IS ABOUT. On Litolff this is exactly
    the shape 13 of 15 reader-decided Cello staves are in: narrowed to
    {cello, its condensed contrabass double}, both non-transposing and
    reading the same key.
    """
    cands = tuple(Candidate(value=c, support=1.0) for c in candidates)
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=Q.SLOT_INDEX,
        outcome=Outcome.NARROWED, value=None, decider="test",
        reason="family_block_not_forced", candidates=cands))


#: `Q.SLOT_INDEX` is pre-recorded by the two helpers above, exactly as
#: `test_staged_key_by_part.py` does it, so it must be excluded from the
#: order the same way: placing a staff needs a page's worth of structure
#: these fixtures do not build. What is under test is what the KEY decisions
#: do with a slot already on the record, whether DECIDED or NARROWED.
_ORDER_WITHOUT_SLOTS = tuple(q for q in adjudicate.ORDER
                             if q != Q.SLOT_INDEX)


def _run(log):
    adjudicate.run(log, order=_ORDER_WITHOUT_SLOTS)
    return log


DOC = Subject(Kind.DOCUMENT)


class TestNarrowedSlotUnanimous(unittest.TestCase):
    """Roadmap 2.9c. Two non-transposing parts (cello=7, bass=8) settle on
    the SAME written key across every system that places them; a third
    staff's slot is NARROWED to exactly those two candidates and never
    placed. Because the two parts they might be agree, the part check may
    still speak — through the check, never through `adjudicate_part_key`'s
    tallies (§2.9b.7's "let the check speak to a NARROWED slot")."""

    CELLO, BASS = 7, 8

    def _settled_parts(self, log, *, n_systems=3, settled=-3):
        """`n_systems` systems, each with a DECIDED cello and bass staff
        reading `settled`, on staff ordinals distinct from the staff under
        test (ordinal 9) so the two parts' own tallies are unaffected by it.
        """
        for system in range(n_systems):
            cello = _header(log, 0, system, 3, markers=_flats(-settled))
            _slot(log, cello, self.CELLO, instrument="Violoncello")
            bass = _header(log, 0, system, 4, markers=_flats(-settled))
            _slot(log, bass, self.BASS, instrument="Contrabasso")

    def test_narrowed_to_two_unanimous_parts_is_abstained(self):
        """THE POSITIVE CASE. Both candidate parts read -3; this staff reads
        -2 and is narrowed to {cello, bass} — never placed on either."""
        log = Log()
        self._settled_parts(log)
        narrowed = _header(log, 0, 2, 9, markers=_flats(2))  # written -2
        _narrowed_slot(log, narrowed, [self.CELLO, self.BASS])
        _run(log)

        v = log.verdict(Q.KEY_SIGNATURE, narrowed)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "disagrees_with_part")
        self.assertEqual(v.detail["expected_fifths"], -3)
        self.assertEqual(v.detail["written_fifths"], -2)
        self.assertEqual(sorted(v.detail["slot_candidates"]),
                         [self.CELLO, self.BASS])
        self.assertEqual(v.detail["part_check_via"],
                         "narrowed_slot_unanimous")

        # ⚠️ AND THE NARROWED STAFF NEVER VOTED. The cello part's own tally
        # is built from exactly the 3 systems `_settled_parts` placed on
        # slot 7 -- not a fourth vote from the staff this test narrows.
        part_key = log.verdict(Q.PART_KEY, DOC)
        cello_tally = part_key.value["parts"][str(self.CELLO)]["segments"][0]
        self.assertEqual(cello_tally["tally"], {"-3": 3})

    def test_positive_control_a_decided_slot_gives_the_identical_outcome(self):
        """The SAME fixture, except the staff is PLACED (decided slot=cello)
        rather than narrowed. This is 2.9b's own shape
        (`test_staged_key_by_part.TestThePartCheck`) and must read exactly
        the same `disagrees_with_part` / expected / written figures — 2.9c
        must not have changed what a DECIDED slot's check concludes."""
        log = Log()
        self._settled_parts(log)
        placed = _header(log, 0, 2, 9, markers=_flats(2))
        _slot(log, placed, self.CELLO, instrument="Violoncello")
        _run(log)

        v = log.verdict(Q.KEY_SIGNATURE, placed)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "disagrees_with_part")
        self.assertEqual(v.detail["expected_fifths"], -3)
        self.assertEqual(v.detail["written_fifths"], -2)
        self.assertNotIn("slot_candidates", v.detail)
        self.assertNotIn("part_check_via", v.detail)

    def test_candidates_that_split_pass_through_unjudged(self):
        """The bass part settles on a DIFFERENT key than the cello — so the
        two candidates would reach different conclusions, which is exactly
        rule 8's "cannot tell which part", and the check must stay silent
        rather than guess between them."""
        # The cello settles at -3 (three flats); the bass settles at -1
        # (one flat) -- two parts genuinely disagreeing about the key, so a
        # staff that could be either one cannot be judged by both at once.
        log = Log()
        for system in range(3):
            cello = _header(log, 0, system, 3, markers=_flats(3))
            _slot(log, cello, self.CELLO, instrument="Violoncello")
            bass = _header(log, 0, system, 4, markers=_flats(1))
            _slot(log, bass, self.BASS, instrument="Contrabasso")
        narrowed = _header(log, 0, 2, 9, markers=_flats(2))  # written -2
        _narrowed_slot(log, narrowed, [self.CELLO, self.BASS])
        _run(log)

        v = log.verdict(Q.KEY_SIGNATURE, narrowed)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, -2)
        self.assertNotIn("slot_candidates", v.detail)
        self.assertNotIn("part_check_via", v.detail)

    def test_a_candidate_with_no_part_answer_passes_through_unjudged(self):
        """One candidate slot (9) has NO staff anywhere in the document —
        `Q.PART_KEY` has nothing to say about it — so even though the OTHER
        candidate (cello) agrees with nobody, the check cannot ask the
        question of a part that does not exist and stays silent."""
        log = Log()
        self._settled_parts(log)  # cello=7, bass=8 -- slot 9 never appears
        narrowed = _header(log, 0, 2, 9, markers=_flats(2))  # written -2
        _narrowed_slot(log, narrowed, [self.CELLO, 9])
        _run(log)

        v = log.verdict(Q.KEY_SIGNATURE, narrowed)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, -2)
        self.assertNotIn("slot_candidates", v.detail)
        self.assertNotIn("part_check_via", v.detail)


if __name__ == "__main__":
    unittest.main()
