"""ROADMAP 2.356 -- the process check: no EVALUATE rule may overturn a quantity its own CAUSE's decision reads, unless the
loop is named and broken (STAGED, static).

CAUSE (Brahms glyph/21/0/4/1/2, 2026-11-26): 2.346 let the meter's bar sum read the not-a-rest refusals (`Q.REST_IS_NOT_A_REST`),
and `reinstate_rest_between_staves` overturns exactly those refusals with the meter as its cause -- meter -> rest -> meter, which
`Log.record` refuses (`UphillConsequence`) and which stopped a whole-movement run. Nothing static said that the meter decision now
`wants` the effect of a meter-caused rule. This test says it: for every rule, the effect may not be among the quantities the
cause's decision reads (its `wants`, followed through the decisions it reads in turn), unless

* the rule is `single_pass=True` (a bounded loop Sean ruled on: `reconcile_duration`, 2026-09-09; `share_stem_value`), or
* it is listed in `LOOP_BROKEN_BY` with the mechanism that keeps the overturned rows out of the cause's basis.

A NEW rule of that shape -- or a decision that starts reading a quantity a rule caused by it rewrites -- fails here until someone
names how the loop is broken (or asks Sean for a single-pass ruling). It is a check on declarations, not a try/except around the
guard; the guard is untouched.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, consequences, evaluate  # noqa: F401  (consequences registers the rules)
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.record import Q

#: rule -> how its cause's decision is kept from reading the rows the rule overturns. Each entry has its own control.
LOOP_BROKEN_BY = {
    # `rhythm._bar_lengths_for`: a bar holding ANY whole rest never speaks for the meter, and the rest's duration is never asked
    # (`_corroborate`'s THE PROVENANCE note); control `test_staged_rest_meter_2_79` / the whole-rest tests.
    "size_measure_rest": "the meter's bar sum leaves out every bar holding a whole rest",
    # ROADMAP 2.356: a bar holding a rest contested with another staff never speaks for the meter, found from GATHER rows
    # (`rhythm._rest_contested_between_staves`); control `test_staged_uphill_rest_between_staves_2_356`.
    "reinstate_rest_between_staves": "the meter's bar sum leaves out every bar holding a rest contested with another staff",
    # ⚠️ NOT A MECHANISM, A GAP (2.356 finding): the verdict's basis names the narrowed note and its stem-mate only, never the
    # meter it is caused by, so the guard cannot see a loop through the meter at all. Listed so the check is honest about it.
    "reconcile_chord_duration": "UNBROKEN IN THE MODEL: the rule leaves its cause (the meter) out of its basis",
}


def _wants_closure(quantity: str) -> set:
    adjudicate._ensure_decisions()
    seen, stack = set(), [quantity]
    while stack:
        spec = adjudicate.REGISTRY.get(stack.pop())
        for w in (spec.wants if spec else ()):
            if w not in seen:
                seen.add(w)
                stack.append(w)
    return seen


def _loops():
    return {r.consequence.value: r for r in evaluate.RULES
            if not r.stub and r.effect in _wants_closure(r.cause)}


class TestCauseReadsEffect(unittest.TestCase):

    def test_every_rule_whose_cause_reads_its_effect_is_single_pass_or_named(self):
        unnamed = sorted(name for name, r in _loops().items() if not r.single_pass and name not in LOOP_BROKEN_BY)
        self.assertEqual(unnamed, [], "a rule overturns a quantity its cause's decision reads; break the loop at the cause "
                                      "(keep those rows out of its basis) and name it in LOOP_BROKEN_BY, or get a single-pass ruling")

    def test_the_named_list_has_no_stale_entry(self):
        loops = _loops()
        stale = sorted(n for n in LOOP_BROKEN_BY if n not in loops or loops[n].single_pass)
        self.assertEqual(stale, [])

    def test_the_check_can_fail(self):
        """Rule 7: the meter decision reads `Q.REST_IS_NOT_A_REST` (2.346), so without its entry the 2.356 rule is caught."""
        loops = _loops()
        self.assertIn("reinstate_rest_between_staves", loops)
        self.assertIn(Q.REST_IS_NOT_A_REST, _wants_closure(Q.METER))
        self.assertFalse(loops["reinstate_rest_between_staves"].single_pass)


if __name__ == "__main__":
    unittest.main()
