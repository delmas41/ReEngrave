"""ROADMAP 2.26b — a BARE crook, no instrument word at all, placed by the
braced neighbour it continues AND the engraver's own document-wide
abbreviation convention.

⚠️ THE SHAPE, MEASURED ON A REAL DOCUMENT (Brahms 1/i, Breitkopf 317803).
Roadmap 2.26 answered `ambiguous_pairing` (a TIED name whose own text still
carried a disambiguating crook) but deliberately left `unnamed_in_short_
system` untouched: a bare `"(Es)"`/`"(C)"` names NO instrument at all, so
placing it needs an assumption about the PAGE (a bare crook always
continues the braced neighbour above it) this repo had not asked Sean.
Sean's answer, via `benchmarks/omr-staff-identity-2026-09/HORN-CROOK-
RESEARCH.md`: yes for THIS movement, because nothing else in it is crooked
in C or Es.

⚠️⚠️ THE FIRST CUT ASKED THE ROSTER FOR THAT "nothing else" FACT AND IT IS
DEAD AT ZERO ON EVERY REAL RECORD THIS REPO HOLDS: the catalog's own
`InstrDetail` says `"4 horns, 2 trumpets, ... timpani, strings"` — never a
crook. What actually decides it is the PLATE's own convention: an
abbreviation, once attached to an instrument anywhere in the piece, is not
reused for a different one — checked against every labelled staff in the
DOCUMENT (`_document_crook_owners`), not the reference alone. **This is an
INFERENCE from the engraver's convention, not a second, independent
witness** — every row it reads is the same `Q.MARGIN_LABEL` the reference
match already reads, merely widened. The ROSTER, where it happens to carry
crook data, is an OPTIONAL VETO on top of that inference, never its source.

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
    the `"crooked"` map (`{instrument: [crook, ...]}`) the OPTIONAL veto
    reads (`_roster_contradicts`); every other roster field is filled with
    a plausible, admissible (`source_kind: "catalog"`) minimum. Omitting
    it entirely (the default) is the REAL, current shape of every roster
    this repo has gathered.

    ⚠️ `OMR_SLOT_CONSTRAINTS=0` FOR THE DURATION OF THE BUILD, restored
    after. The constraint channels (`_apply_constraints`, order/family/
    clef) are a SEPARATE, earlier-roadmap mechanism this file is not
    testing, and left enabled they can independently narrow or decide an
    unnamed staff before this rule ever runs on some shapes. Isolating the
    flag here, rather than shrinking the reference further, keeps the
    reference wide enough to hold the roadmap 2.26b shape (an INTERIOR
    bare-crook staff, never the trailing one `_place_in_family_block`
    already owns).
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
    def test_the_real_Brahms_label_strings_place_Horn_Es(self):
        """⚠️ THE POSITIVE CASE, roster SILENT (the real shape: real
        Brahms's catalog names no crook at all). Placed from the plate's
        own convention alone -- the reference brace repeats `Horn` with
        `Es` among its crooks, and nothing else in the document attaches
        `Es` to a different instrument."""
        log = _document([REFERENCE, SHORT_ES])
        got = _slots(log, 1, 4)
        self.assertEqual(got[2], 2)   # slot 2 = "Hr. (Es)" in the reference
        v = _slot_verdict(log, 0, 1, 2)
        self.assertEqual(v.reason, "paired_by_bare_crook")
        self.assertEqual(v.detail["instrument"], "Horn")
        self.assertEqual(v.detail["document_owners"], ["Horn"])

    def test_roster_SILENT_still_places(self):
        """Same as the positive case, restated: a roster present but with
        no `"crooked"` field at all (an admissible `catalog` row that
        simply has nothing to say) must not block the plate's own
        evidence -- silence is not a veto."""
        log = _document([REFERENCE, SHORT_ES], roster={})
        v = _slot_verdict(log, 0, 1, 2)
        self.assertEqual(v.reason, "paired_by_bare_crook")

    def test_the_OTHER_crook_picks_the_OTHER_slot(self):
        log = _document([REFERENCE, SHORT_C])
        got = _slots(log, 1, 4)
        self.assertEqual(got[2], 1)   # slot 1 = "(C) Hr." in the reference
        v = _slot_verdict(log, 0, 1, 2)
        self.assertEqual(v.reason, "paired_by_bare_crook")

    def test_a_document_where_C_labels_both_Horn_and_Trumpet_abstains(self):
        """⚠️ THE CONTROL THIS REDESIGN EXISTS FOR. A THIRD system, anywhere
        in the document, prints `"(C) Tr."` -- so `"C"` is attached to TWO
        instruments across the plate's own labelled lineup, and the
        engraver's convention this rule leans on is exactly the one THIS
        document violates. Must refuse, not pick the reference's own
        answer as though the rest of the document did not exist."""
        third = ["Flauti", "(C) Tr.", "Fagotti"]
        log = _document([REFERENCE, SHORT_C, third])
        v = _slot_verdict(log, 0, 1, 2)
        self.assertNotEqual(v.reason, "paired_by_bare_crook")
        self.assertIsNot(v.outcome, Outcome.DECIDED)

    def test_a_roster_CONTRADICTING_the_document_abstains(self):
        """⚠️ THE VETO, EXERCISED. The document's OWN labelled lineup
        uniquely attaches `Es` to `Horn` -- (a) and the document check both
        pass -- but the roster (where it happens to carry crook data at
        all) names `Clarinet` for `Es` instead. The veto fires: a
        contradiction from an admissible, independent-of-the-page source
        outranks the plate's own convention."""
        log = _document([REFERENCE, SHORT_ES], roster={"Clarinet": ["ES"]})
        v = _slot_verdict(log, 0, 1, 2)
        self.assertNotEqual(v.reason, "paired_by_bare_crook")
        self.assertIsNot(v.outcome, Outcome.DECIDED)

    def test_a_roster_that_AGREES_still_places(self):
        """The mirror of the veto test: a roster that names the SAME
        instrument for the crook is not a contradiction and must not block
        what the document already established."""
        log = _document([REFERENCE, SHORT_ES], roster={"Horn": ["C", "ES"]})
        v = _slot_verdict(log, 0, 1, 2)
        self.assertEqual(v.reason, "paired_by_bare_crook")

    def test_a_crook_the_reference_brace_never_carries_still_abstains(self):
        """Neither reference slot of the Horn brace prints `"D"` -- (a)
        fails, refuse, roster or not."""
        log = _document([REFERENCE, ["Flauti", "(C) Hr.", "(D)", "Fagotti"]])
        v = _slot_verdict(log, 0, 1, 2)
        self.assertNotEqual(v.reason, "paired_by_bare_crook")
        self.assertIsNot(v.outcome, Outcome.DECIDED)

    def test_a_single_crook_instrument_is_not_a_brace(self):
        """`Bassoon` (`Fagotti`) is not REPEATED in the reference, so it is
        not a braced pair and carries no crook to disambiguate at all --
        matching its own bare crook by coincidence must not resolve."""
        ref = ["Flauti", "(C) Hr.", "Hr. (Es)", "Fagotti (D)", "Oboi"]
        log = _document([ref, ["Flauti", "(C) Hr.", "(D)", "Oboi"]])
        v = _slot_verdict(log, 0, 1, 2)
        self.assertNotEqual(v.reason, "paired_by_bare_crook")
        self.assertIsNot(v.outcome, Outcome.DECIDED)

    def test_the_full_system_is_UNCHANGED(self):
        """The equal-count population never enters the short-system branch
        at all and must not move."""
        log = _document([REFERENCE, REFERENCE])
        for s in (0, 1):
            self.assertEqual(_slots(log, s, len(REFERENCE)), [0, 1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
