"""ROADMAP 2.26 — a tied name pairing settled by the CROOK the name reduced.

⚠️ THE SHAPE, MEASURED ON A REAL DOCUMENT (Brahms 1/i, Breitkopf 317803,
whole movement). The reference lineup prints `Horn` TWICE (`"(C) Hr."` and
`"Hr. (Es)"`, both reduced to the bare family name by `adjudicate_instrument`'s
`hr` alias), so a short system that reads only `"(C) Hr."` on its one visible
Horn staff cannot be forced-paired by NAME alone — `_forced_pairing`'s own
docstring already predicted this exact case and had measured it dormant on
Litolff (`"the only name repeated in that reference is Violin, and no short
system ever reads a violin label"`, `identity.py`). Brahms DOES label Horn on
short systems, so the guard fires for the first time: 22 of 42
`staff_not_identified` staves on that document, `benchmarks/
omr-staff-identity-2026-09/FINDINGS.md`.

The crook that WOULD disambiguate the two Horn slots is not thrown away by
this fix's own logic — it is already on `Q.MARGIN_LABEL`'s raw text, on the
very same subject, and simply never reached `_forced_pairing`'s reduced name
table. Matching it against the reference's OWN raw text is a connection, not
a guess: it can only ever settle a tie `_forced_pairing` already found,
never invent one, and it refuses the moment either the tie has no crook to
read or the crook does not disambiguate cleanly.

⚠️ THE POSITIVE CONTROL IS IN THE SAME CLASS AS THE REFUSALS, for the same
reason `test_staged_slot_by_name.py` keeps one: a rule that "abstains
unconditionally" reads green against every refusal test here too.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  -- registers them
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators.identity import _crook_tokens
from tools.omr.staged.record import Log, Outcome, Q, READERS


def _document(systems, page=0):
    """`systems` is a list of `[(margin_text_or_None, ordinal_ignored), ...]`
    label lists, one per system, mirroring
    `test_staged_slot_by_name.py`'s own `_document` but carrying the RAW
    margin text (which may differ from what the lexicon resolves it to)
    rather than a name already in reference form."""
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
    adjudicate.run(log)
    return log


def _slot_verdict(log, page, system, i):
    return log.verdict(Q.SLOT_INDEX, R.staff(page, system, i))


def _slots(log, system, n, page=0):
    out = []
    for i in range(n):
        v = _slot_verdict(log, page, system, i)
        out.append(v.value if v.outcome is Outcome.DECIDED else v.reason)
    return out


# The Brahms shape, cut down to what matters: a 3-staff reference where the
# generic instrument name is printed TWICE, distinguished only by a crook
# neither of `adjudicate_instrument`'s aliases carries forward.
REFERENCE = ["Flauti", "(C) Hr.", "Hr. (Es)"]


class TestCrookTokens(unittest.TestCase):
    def test_extracts_the_parenthetical_only(self):
        self.assertEqual(_crook_tokens("(C) Hr."), frozenset({"C"}))
        self.assertEqual(_crook_tokens("Hr. (Es)"), frozenset({"ES"}))

    def test_case_and_whitespace_do_not_matter(self):
        self.assertEqual(_crook_tokens("(  es )"), frozenset({"ES"}))

    def test_no_parenthetical_is_empty(self):
        self.assertEqual(_crook_tokens("Hr."), frozenset())
        self.assertEqual(_crook_tokens(None), frozenset())


class TestTheDecision(unittest.TestCase):
    def test_a_tied_name_is_settled_by_a_MATCHING_crook(self):
        """⚠️ THE POSITIVE CASE. Real text off the real record."""
        log = _document([REFERENCE, ["Flauti", "(C) Hr."]])
        got = _slots(log, 1, 2)
        self.assertEqual(got, [0, 1])   # slot 1 = "(C) Hr." in the reference
        v = _slot_verdict(log, 0, 1, 1)
        self.assertEqual(v.reason, "paired_by_crook")
        self.assertEqual(v.detail["crook"], ["C"])

    def test_the_OTHER_crook_picks_the_OTHER_slot(self):
        log = _document([REFERENCE, ["Flauti", "Hr. (Es)"]])
        got = _slots(log, 1, 2)
        self.assertEqual(got, [0, 2])   # slot 2 = "Hr. (Es)" in the reference
        v = _slot_verdict(log, 0, 1, 1)
        self.assertEqual(v.reason, "paired_by_crook")

    def test_a_bare_crook_with_no_root_word_is_UNTOUCHED(self):
        """⚠️⚠️ THE HALF THIS FIX DOES NOT CLAIM. `"(Es)"` alone never
        reaches `adjudicate_instrument`'s lexicon at all (`not_in_lexicon`),
        so `mine[here]` is `None` here, not a tied name -- it never reaches
        this rule's branch (`mine[here] in ref_names` requires a NAME) at
        all. This is `unnamed_in_short_system`'s population (real Brahms
        text, `benchmarks/omr-staff-identity-2026-09/`) -- roadmap 2.26's
        crops ask Sean about it, and this rule must never silently resolve
        it. Whether the OTHER, unnamed-block machinery (`_place_in_family_
        block`, unaffected by this change) narrows or abstains it is not
        this test's question; only that this rule's own OUTPUT
        (`paired_by_crook`, a DECIDED value) never appears."""
        log = _document([REFERENCE, ["Flauti", "(Es)"]])
        v = _slot_verdict(log, 0, 1, 1)
        self.assertNotEqual(v.reason, "paired_by_crook")
        self.assertIsNot(v.outcome, Outcome.DECIDED)

    def test_no_crook_at_all_still_abstains(self):
        """The name is tied and neither side carries a crook to read --
        the ORIGINAL refusal, unmoved."""
        log = _document([["Flauti", "Hr.", "Hr."], ["Flauti", "Hr."]])
        got = _slots(log, 1, 2)
        self.assertEqual(got[1], "ambiguous_pairing")

    def test_an_AMBIGUOUS_crook_still_abstains(self):
        """⚠️ IT MAY ONLY DECIDE A CLEAN MATCH. Both reference candidates
        share the read crook (a malformed or duplicated print) -- refuse,
        never pick the first."""
        log = _document([["Flauti", "(C) Hr.", "(C) Hr."], ["Flauti", "(C) Hr."]])
        got = _slots(log, 1, 2)
        self.assertEqual(got[1], "ambiguous_pairing")

    def test_a_crook_matching_NEITHER_candidate_still_abstains(self):
        log = _document([REFERENCE, ["Flauti", "(D) Hr."]])
        got = _slots(log, 1, 2)
        # "(D) Hr." still resolves to the bare name "Horn" (alias "hr"), tied
        # against both reference slots, and "D" matches neither's crook.
        self.assertEqual(got[1], "ambiguous_pairing")

    def test_a_non_ambiguous_tied_name_case_is_UNCHANGED(self):
        """⚠️ THE EXISTING CONTROL, RE-RUN. `_forced_pairing`'s OWN
        "unpaired" refusal (not a duplicate name) must not be touched by
        this rule -- `"Violino I"` is unique in the reference, so
        `cand_slots` here has length 1 and the crook branch never fires."""
        log = _document(
            [["Flauti", "Violino I", "Violino II"], ["Tuba", "Violino I"]])
        got = _slots(log, 1, 2)
        self.assertEqual(got, ["not_in_reference", "ambiguous_pairing"])

    def test_the_full_system_is_UNCHANGED(self):
        """The equal-count population never enters the short-system branch
        at all and must not move."""
        log = _document([REFERENCE, REFERENCE])
        for s in (0, 1):
            self.assertEqual(_slots(log, s, len(REFERENCE)), [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
