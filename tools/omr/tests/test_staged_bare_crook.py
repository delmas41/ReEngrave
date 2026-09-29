"""ROADMAP 2.26b — a BARE crook, no instrument word at all, placed by the
braced neighbour it continues AND an independent roster witness.

⚠️ THE SHAPE, MEASURED ON A REAL DOCUMENT (Brahms 1/i, Breitkopf 317803).
Roadmap 2.26 answered `ambiguous_pairing` (a TIED name whose own text still
carried a disambiguating crook) but deliberately left `unnamed_in_short_
system` untouched: a bare `"(Es)"`/`"(C)"` names NO instrument at all, so
placing it needs an assumption about the PAGE (a bare crook always
continues the braced neighbour above it) this repo had not asked Sean.
Sean's answer, via `benchmarks/omr-staff-identity-2026-09/HORN-CROOK-
RESEARCH.md`: yes for THIS movement, because nothing else in it is crooked
in C or Es -- an answer that is conditional on there being no OTHER
crooked family to confuse it with, which is exactly why the rule needs a
SECOND witness (the roster) and not just the reference lineup's own text
repeating itself.

⚠️ THE POSITIVE CONTROL IS IN THE SAME CLASS AS THE REFUSALS, for the same
reason every other file in this family keeps one.
"""
from __future__ import annotations

import os
import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  -- registers them
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators.identity import _bare_crook
from tools.omr.staged.record import Log, Outcome, Q, READERS


def _document(systems, roster=None, page=0):
    """Mirrors `test_staged_slot_crook.py`'s own `_document`, plus an
    OPTIONAL document-scoped `Q.ROSTER_ENTRY` row. `roster`, if given, is
    the `"crooked"` map (`{instrument: [crook, ...]}`) -- the one field
    `_roster_crook_owners` reads; every other roster field is filled with
    a plausible, admissible (`source_kind: "catalog"`) minimum.

    ⚠️ `OMR_SLOT_CONSTRAINTS=0` FOR THE DURATION OF THE BUILD, restored
    after. The constraint channels (`_apply_constraints`, order/family/
    clef) are a SEPARATE, earlier-roadmap mechanism this file is not
    testing, and left enabled they can independently narrow or decide an
    unnamed staff before this rule ever runs on some shapes -- exactly the
    ambiguity roadmap 2.26's own harness avoided by keeping its synthetic
    references small. Isolating the flag here, rather than shrinking the
    reference further, keeps the reference wide enough to hold the roadmap
    2.26b shape (an INTERIOR bare-crook staff, never the trailing one
    `_place_in_family_block` already owns).
    """
    old = os.environ.get("OMR_SLOT_CONSTRAINTS")
    os.environ["OMR_SLOT_CONSTRAINTS"] = "0"
    try:
        log = Log()
        for s, texts in enumerate(systems):
            log.observe(R.system(page, s), Q.SYSTEM_STAFF_COUNT, len(texts),
                        reader=READERS.GEOMETRY, frame="system")
            for i, text in enumerate(texts):
                sub = R.staff(page, s, i)
                log.observe(sub, Q.STAFF_ORDINAL, i,
                            reader=READERS.GEOMETRY, frame="system")
                if text is not None:
                    log.observe(sub, Q.MARGIN_LABEL, text,
                                reader=READERS.SURYA, frame="page")
        if roster is not None:
            value = {"work_id": "test", "instruments": ["Horn"],
                     "families": ["brass"], "complete": True,
                     "source_kind": "catalog", "crooked": roster}
            log.observe(R.DOCUMENT, Q.ROSTER_ENTRY, value,
                        reader=READERS.CATALOG, frame="page")
        adjudicate.run(log)
        return log
    finally:
        if old is None:
            os.environ.pop("OMR_SLOT_CONSTRAINTS", None)
        else:
            os.environ["OMR_SLOT_CONSTRAINTS"] = old


def _slot_verdict(log, page, system, i):
    return log.verdict(Q.SLOT_INDEX, R.staff(page, system, i))


def _slots(log, system, n, page=0):
    out = []
    for i in range(n):
        v = _slot_verdict(log, page, system, i)
        out.append(v.value if v.outcome is Outcome.DECIDED else v.reason)
    return out


# 5-slot reference: Horn braced at 1/2 (crooked C, Es, exactly Brahms 1's
# own text), Fagotti and Oboi bracket it so the bare staff in a short
# system is INTERIOR -- never the trailing staff `_place_in_family_block`
# already claims.
REFERENCE = ["Flauti", "(C) Hr.", "Hr. (Es)", "Fagotti", "Oboi"]

# The short system every test starts from: staff 2 is the bare crook under
# test; staff 3 (named) makes it interior; staff 4 (Oboi) is tacet here,
# which is what makes the system SHORT (4 of 5) in the first place.
SHORT_ES = ["Flauti", "(C) Hr.", "(Es)", "Fagotti"]
SHORT_C = ["Flauti", "(C) Hr.", "(C)", "Fagotti"]


class TestBareCrook(unittest.TestCase):
    def test_extracts_the_crook_and_nothing_else(self):
        self.assertEqual(_bare_crook("(Es)"), "ES")
        self.assertEqual(_bare_crook(" (C) "), "C")

    def test_an_instrument_word_disqualifies_it(self):
        """⚠️ THE LINE 2.26 AND 2.26b SPLIT ON. `"(C) Hr."` carries a crook
        AND a name -- that is `_crook_tokens`'/roadmap 2.26's population,
        never this one."""
        self.assertIsNone(_bare_crook("(C) Hr."))
        self.assertIsNone(_bare_crook("Hr. (Es)"))

    def test_no_parenthetical_is_not_a_bare_crook_either(self):
        self.assertIsNone(_bare_crook("Hr."))
        self.assertIsNone(_bare_crook(None))


class TestTheDecision(unittest.TestCase):
    def test_a_bare_crook_is_placed_ON_ITS_BRACE_WITH_A_CORROBORATING_ROSTER(self):
        """⚠️ THE POSITIVE CASE. Real text off the real record, both
        conditions satisfied: the reference brace repeats `Horn` with `Es`
        among its crooks, and the roster names `Horn` alone for `Es`."""
        log = _document([REFERENCE, SHORT_ES], roster={"Horn": ["C", "ES"]})
        got = _slots(log, 1, 4)
        self.assertEqual(got[2], 2)   # slot 2 = "Hr. (Es)" in the reference
        v = _slot_verdict(log, 0, 1, 2)
        self.assertEqual(v.reason, "paired_by_bare_crook")
        self.assertEqual(v.detail["instrument"], "Horn")
        self.assertEqual(v.detail["roster_owners"], ["Horn"])

    def test_the_OTHER_crook_picks_the_OTHER_slot(self):
        log = _document([REFERENCE, SHORT_C], roster={"Horn": ["C", "ES"]})
        got = _slots(log, 1, 4)
        self.assertEqual(got[2], 1)   # slot 1 = "(C) Hr." in the reference
        v = _slot_verdict(log, 0, 1, 2)
        self.assertEqual(v.reason, "paired_by_bare_crook")

    def test_NO_ROSTER_AT_ALL_still_abstains(self):
        """⚠️⚠️ THE HONEST DEFAULT. Real Brahms's own catalog `InstrDetail`
        names no crook at all (`HORN-CROOK-RESEARCH.md`) -- this rule is
        DEAD AT ZERO on every roster this repo has gathered so far, and
        must stay refused rather than fall back to the page alone."""
        log = _document([REFERENCE, SHORT_ES], roster=None)
        v = _slot_verdict(log, 0, 1, 2)
        self.assertNotEqual(v.reason, "paired_by_bare_crook")
        self.assertIsNot(v.outcome, Outcome.DECIDED)

    def test_A_ROSTER_WITH_TWO_FAMILIES_CROOKED_IN_THE_SAME_KEY_abstains(self):
        """⚠️ CONTROL. The roster itself is ambiguous -- Horn AND Clarinet
        both attested crooked in Es -- so the independent witness cannot
        corroborate a single instrument and the rule must refuse, exactly
        as `_forced_pairing` refuses a name the reference prints twice."""
        log = _document([REFERENCE, SHORT_ES],
                        roster={"Horn": ["ES"], "Clarinet": ["ES"]})
        v = _slot_verdict(log, 0, 1, 2)
        self.assertNotEqual(v.reason, "paired_by_bare_crook")
        self.assertIsNot(v.outcome, Outcome.DECIDED)

    def test_A_ROSTER_WITH_TRUMPETS_AND_HORNS_IN_C_abstains(self):
        """⚠️ CONTROL, the other crook. Horn AND Trumpet both attested
        crooked in C -- the exact shape `HORN-CROOK-RESEARCH.md` names as
        where the convention would break (\"two different transposing
        families shared a crook name\")."""
        log = _document([REFERENCE, SHORT_C],
                        roster={"Horn": ["C"], "Trumpet": ["C"]})
        v = _slot_verdict(log, 0, 1, 2)
        self.assertNotEqual(v.reason, "paired_by_bare_crook")
        self.assertIsNot(v.outcome, Outcome.DECIDED)

    def test_a_crook_the_reference_brace_never_carries_still_abstains(self):
        """The roster corroborates `"D"` for Horn, but neither reference
        slot of the Horn brace prints it -- (a) fails, refuse."""
        log = _document([REFERENCE, ["Flauti", "(C) Hr.", "(D)", "Fagotti"]],
                        roster={"Horn": ["C", "ES", "D"]})
        v = _slot_verdict(log, 0, 1, 2)
        self.assertNotEqual(v.reason, "paired_by_bare_crook")
        self.assertIsNot(v.outcome, Outcome.DECIDED)

    def test_a_single_crook_instrument_is_not_a_brace(self):
        """`Bassoon` (`Fagotti`) is not REPEATED in the reference, so it is
        not a braced pair and carries no crook to disambiguate at all --
        matching its own bare crook by coincidence must not resolve, roster
        or not."""
        ref = ["Flauti", "(C) Hr.", "Hr. (Es)", "Fagotti (D)", "Oboi"]
        log = _document([ref, ["Flauti", "(C) Hr.", "(D)", "Oboi"]],
                        roster={"Bassoon": ["D"]})
        v = _slot_verdict(log, 0, 1, 2)
        self.assertNotEqual(v.reason, "paired_by_bare_crook")
        self.assertIsNot(v.outcome, Outcome.DECIDED)

    def test_the_full_system_is_UNCHANGED(self):
        """The equal-count population never enters the short-system branch
        at all and must not move."""
        log = _document([REFERENCE, REFERENCE], roster={"Horn": ["C", "ES"]})
        for s in (0, 1):
            self.assertEqual(_slots(log, s, len(REFERENCE)), [0, 1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
