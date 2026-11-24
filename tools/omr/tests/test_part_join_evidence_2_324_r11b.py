"""ROADMAP 2.324 r11b -- the part join asks whether the short systems' slots REST ON EVIDENCE, not whether their numbers differ from
the staves' positions, STAGED ADJUDICATE (`adjudicators/identity._short_slots_rest_on_evidence`, `adjudicate_part_partition`).

Found on Litolff p12-14 once the viola's alto clef was read (2.324 r11): every 11-staff system's slots were paired on names, brace
blocks and clefs and came out 0..9 at their positions, so `_slots_are_ordinals` refused the join and the pages were written one part
per staff. The join had held before only because the viola, misread as bass, pushed two staves off their positions. The never kept:
a short system's staff is never joined to a part on its position alone (the 2026-09-11 Litolff p.1-4 case, `test_staged_part_join`,
`test_staged_slot_by_name.test_and_it_still_REFUSES_where_no_name_was_read`, both unchanged).

These are CONSTRUCTED documents (labels as the margin reader files them) for the rule's two sides; the real-record control is the
re-adjudicated Litolff p1+12-14 gather in the lane report.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged.adjudicators.identity import _short_slots_rest_on_evidence
from tools.omr.staged.record import Q
from tools.omr.staged import record as R
from tools.omr.tests.test_staged_slot_by_name import FULL, _document, _slots


class _V:
    def __init__(self, page, system, value, reason):
        self.subject = R.staff(page, system, 0) if reason is not None else R.system(page, system)
        self.value = value
        self.reason = reason


class TestShortSlotsRestOnEvidence(unittest.TestCase):
    COUNTS = [_V(0, 0, 4, None), _V(0, 1, 3, None)]

    def test_paired_short_system_rests_on_evidence(self):
        slots = [_V(0, 0, i, "named") for i in range(4)] + [_V(0, 1, i, "paired_by_name") for i in range(3)]
        self.assertTrue(_short_slots_rest_on_evidence(slots, self.COUNTS))

    def test_never_on_position_alone(self):
        slots = ([_V(0, 0, i, "named") for i in range(4)]
                 + [_V(0, 1, 0, "paired_by_name"), _V(0, 1, 1, "forced_by_constraints"), _V(0, 1, 2, "full_lineup")])
        self.assertFalse(_short_slots_rest_on_evidence(slots, self.COUNTS))

    def test_no_short_slot_is_no_evidence(self):
        slots = [_V(0, 0, i, "full_lineup") for i in range(4)]
        self.assertFalse(_short_slots_rest_on_evidence(slots, self.COUNTS))


class TestTheJoin(unittest.TestCase):
    def test_a_short_system_that_drops_only_its_last_staves_joins_when_its_names_were_read(self):
        """Slots 0..3 on a 4-staff system, each paired by its read name: contiguous, and before r11b refused as 'the ordinal'."""
        log = _document([FULL, FULL[:4]])
        self.assertEqual(_slots(log, 1, 4), [0, 1, 2, 3])
        v = log.verdict(Q.PART_PARTITION, R.DOCUMENT)
        self.assertEqual((v.reason, v.value["join"]), ("slot", "slot"))

    def test_control_the_old_numbers_only_question_refuses_it(self):
        """The change can fail: asked by the numbers alone (the evidence check off), the same document is refused."""
        import tools.omr.staged.adjudicators.identity as ID
        orig = ID._short_slots_rest_on_evidence
        ID._short_slots_rest_on_evidence = lambda *a, **k: False
        try:
            log = _document([FULL, FULL[:4]])
            v = log.verdict(Q.PART_PARTITION, R.DOCUMENT)
            self.assertEqual(v.value.get("reason"), "slots_are_ordinals")
        finally:
            ID._short_slots_rest_on_evidence = orig

    def test_unread_short_system_still_refuses(self):
        log = _document([[None] * len(FULL), [None] * 4])
        v = log.verdict(Q.PART_PARTITION, R.DOCUMENT)
        self.assertEqual(v.reason, "deduced_anchor")


if __name__ == "__main__":
    unittest.main()
