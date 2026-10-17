"""ROADMAP 2.165 -- the ONE shared override check (`OMR_ONE_OVERRIDE_CHECK`, default OFF; Sean 2026-10-17).

`staged/override_check.py` + its call in `record.Log.record`: *may this step change that verdict?*, answered by ONE
table keyed by (stage, reading-order step) of the new verdict and of the one it supersedes or overturns. And the
shared-stem rule (Sean 2026-10-17): two heads whose own fills disagree -> the stem value UNDECIDED; three or more with
one dissent -> GUESSED to the majority, the dissent marked.

Controls that can fail: every test that asserts a refusal is paired with the same write under the flag OFF, where it
goes through (`TestRemovingTheGuardFails`); the site list is READ FROM THE CODE (`supersede_sites`, an `ast` walk),
so a new `supersedes=` site with no row fails `test_every_supersedes_site_has_a_row`.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import consequences, evaluate  # noqa: F401  (registers the rules)
from tools.omr.staged import override_check as OC
from tools.omr.staged import record as R
from tools.omr.staged.record import Candidate, Log, Outcome, Q, Verdict
from tools.omr.tests.test_staged_stem_value import Stem, _dur

G = R.glyph(0, 0, 0, 0, 0)
ON = {OC.FLAG: "1"}
OFF = {OC.FLAG: "0"}


def _rec(log, sub, q, outcome, value, *, decider="adjudicate_duration", reason="head_and_marks", candidates=(),
         detail=None, supersedes=None, basis=(), single=False):
    return log.record(Verdict(id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome, value=value,
                              decider=decider, reason=reason, candidates=tuple(candidates), detail=detail or {},
                              basis=tuple(basis), supersedes=supersedes, single_pass_revision=single))


def _quarter():
    return _dur(1.0)


def _eighth():
    return _dur(0.5, 0, 1)


class TestTheTable(unittest.TestCase):

    def test_every_supersedes_site_has_a_row(self):
        """Derived from the code: every `supersedes=` call site's decider has a key, and that key has a row."""
        sites = OC.supersede_sites()
        self.assertGreaterEqual(len(sites), 18, sites)       # the audit counted 18 on 2320c2ea; 2.162 adds one
        new_keys = {k[0] for k in OC.TABLE}
        for path, line, decider in sites:
            if decider == "infer:*":
                keys = {(OC.I, "collapse"), (OC.I, "bar_sum")}
            elif decider == "spec.name":                     # adjudicate_one's `revises` path (A1, dead)
                keys = {(OC.A, "own_reading"), (OC.A, "reading")}
            else:
                self.assertIn(decider, OC.DECIDER_KEY, f"{path}:{line} decider {decider!r} has no key")
                keys = {OC.DECIDER_KEY[decider]}
            for k in keys:
                self.assertIn(k, new_keys, f"{path}:{line} ({decider}) has no row for {k}")

    def test_an_unknown_pair_RAISES_in_tests(self):
        with self.assertRaises(OC.UnguardedOverride):
            OC.lookup((OC.E, "rest_convention"), (OC.I, "collapse"))

    def test_an_unknown_decider_superseding_RAISES(self):
        with mock.patch.dict(os.environ, ON):
            log = Log()
            prior = _rec(log, G, Q.DURATION, Outcome.DECIDED, _quarter())
            with self.assertRaises(OC.UnguardedOverride):
                _rec(log, G, Q.DURATION, Outcome.DECIDED, _eighth(), decider="a_new_rule_nobody_guarded",
                     supersedes=prior.id)

    def test_the_audit_violations_are_rows(self):
        covers = " ".join(r.covers for r in OC.TABLE.values())
        for n in (1, 2, 4, 5, 6, 7):
            self.assertIn(f"violation {n}", covers)


class _On(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, ON)
        p.start()
        self.addCleanup(p.stop)
        self.log = Log()


class TestBarSumConfirmsOnly(_On):
    """Audit violation 1 (E5b/E5c): the bar never moves a DECIDED value; 2.154: it confirms a bare stem only."""

    def test_a_decided_quarter_is_not_made_an_eighth_by_the_bar(self):
        prior = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _quarter())
        got = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _eighth(), decider="reconcile_duration",
                   reason="meter_reconciliation", supersedes=prior.id, basis=(prior.id,), single=True)
        self.assertIs(got, prior)
        self.assertIs(self.log.verdict(Q.DURATION, G), prior)
        nm = self.log.near_misses()
        self.assertEqual([(m["row"], m["why"]) for m in nm], [("bar_sum_confirms_only", "bar_sum_moves_a_decided_value")])
        self.assertEqual(nm[0]["attempted"]["value"]["beam_levels"], 1)
        self.assertEqual(self.log.to_json()["counts"]["near_misses"], 1)

    def test_a_bare_stem_may_be_confirmed_at_its_unbeamed_value(self):
        prior = _rec(self.log, G, Q.DURATION, Outcome.NARROWED, None, reason="beam_discounted_uncertain",
                     candidates=(Candidate(_quarter(), 2.0), Candidate(_eighth(), 1.0)),
                     detail={"beam_evidence": "none_over_this_note"})
        got = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _quarter(), decider="reconcile_duration",
                   reason="meter_reconciliation", supersedes=prior.id, basis=(prior.id,), single=True)
        self.assertIsNot(got, prior)
        self.assertEqual(self.log.near_misses(), [])

    def test_the_bar_never_lands_the_bare_stems_eighth_nor_picks_another_narrowing(self):
        prior = _rec(self.log, G, Q.DURATION, Outcome.NARROWED, None, reason="beam_discounted_uncertain",
                     candidates=(Candidate(_quarter(), 2.0), Candidate(_eighth(), 1.0)),
                     detail={"beam_evidence": "none_over_this_note"})
        _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _eighth(), decider="reconcile_duration",
             reason="meter_reconciliation", supersedes=prior.id, single=True)
        g2 = R.glyph(0, 0, 0, 0, 1)
        p2 = _rec(self.log, g2, Q.DURATION, Outcome.NARROWED, None, reason="beams_ambiguous",
                  candidates=(Candidate(_quarter(), 2.0), Candidate(_eighth(), 1.0)))
        _rec(self.log, g2, Q.DURATION, Outcome.DECIDED, _quarter(), decider="reconcile_duration",
             reason="meter_reconciliation", supersedes=p2.id, single=True)
        self.assertEqual([m["why"] for m in self.log.near_misses()],
                         ["bar_sum_picks_from_a_narrowing", "bar_sum_picks_from_a_narrowing"])


class TestInfer(_On):
    def test_infer_never_overturns_decided(self):
        prior = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _quarter())
        got = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _eighth(), decider="infer:collapse_duration_by_column",
                   reason="the_neighbours_name_this_gap", supersedes=prior.id, detail={"inferred": True})
        self.assertIs(got, prior)
        self.assertEqual(self.log.near_misses()[0]["why"], "infer_never_overturns_decided")

    def test_the_bar_in_infer_is_only_sean_s_exceptions(self):
        prior = _rec(self.log, G, Q.DURATION, Outcome.NARROWED, None, reason="beams_ambiguous",
                     candidates=(Candidate(_quarter(), 2.0), Candidate(_eighth(), 1.0)))
        got = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _quarter(), decider="infer:collapse_narrowed_by_bar",
                   reason="some_new_bar_reason", supersedes=prior.id, detail={"inferred": True})
        self.assertIs(got, prior)
        self.assertEqual(self.log.near_misses()[0]["why"], "bar_sum_may_only_confirm")
        ok = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _quarter(), decider="infer:collapse_narrowed_by_bar",
                  reason="lone_event_fills_bar", supersedes=prior.id, detail={"inferred": True})
        self.assertIsNot(ok, prior)

    def test_an_inference_must_be_labelled(self):
        prior = _rec(self.log, G, Q.DURATION, Outcome.NARROWED, None, reason="beams_ambiguous",
                     candidates=(Candidate(_quarter(), 2.0), Candidate(_eighth(), 1.0)))
        got = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _quarter(), decider="infer:collapse_duration_by_column",
                   reason="the_neighbours_name_this_gap", supersedes=prior.id)
        self.assertIs(got, prior)
        self.assertEqual(self.log.near_misses()[0]["why"], "an_inference_must_be_guessed")


class TestLaterStepsOnlyWiden(_On):
    def test_the_dot_join_may_widen_a_decided_value(self):
        prior = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _dur(2.0))
        got = _rec(self.log, G, Q.DURATION, Outcome.NARROWED, None, decider="reconcile_unjoined_dots",
                   reason="dot_seen_beside_a_plain_note", supersedes=prior.id,
                   candidates=(Candidate(_dur(2.0), 2.0), Candidate(_dur(3.0, 1), 1.0)))
        self.assertIsNot(got, prior)
        self.assertEqual(self.log.near_misses(), [])

    def test_the_dot_join_may_not_replace_a_decided_value(self):
        prior = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _dur(2.0))
        got = _rec(self.log, G, Q.DURATION, Outcome.NARROWED, None, decider="reconcile_unjoined_dots",
                   reason="dot_seen_beside_a_plain_note", supersedes=prior.id,
                   candidates=(Candidate(_dur(3.0, 1), 2.0), Candidate(_dur(1.5, 1), 1.0)))
        self.assertIs(got, prior)
        self.assertEqual(self.log.near_misses()[0]["why"], "not_a_widening")

    def test_the_stem_never_overwrites_a_decided_fill(self):
        prior = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _quarter())
        got = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, {**_dur(2.0), "head_fill": "half"},
                   decider="share_stem_value", reason="stem_value_follows", supersedes=prior.id, single=True)
        self.assertIs(got, prior)
        self.assertEqual(self.log.near_misses()[0]["why"], "shared_stem_overwrites_a_decided_fill")

    def test_the_stem_may_give_a_head_its_tip_beams(self):
        """Sean's 2.78 tile 1: the far head saw strokes between the heads (16th); the tip reads one beam (8th)."""
        prior = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _dur(0.25, 0, 2))
        got = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _eighth(), decider="share_stem_value",
                   reason="stem_value_follows", supersedes=prior.id, single=True)
        self.assertIsNot(got, prior)

    def test_a_whole_class_head_on_a_stem_takes_the_half(self):
        prior = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _dur(4.0))
        got = _rec(self.log, G, Q.DURATION, Outcome.DECIDED, _dur(2.0), decider="share_stem_value",
                   reason="stem_value_follows", supersedes=prior.id, single=True)
        self.assertIsNot(got, prior)

    def test_a_flag_never_reopens_an_open_head(self):
        """Audit violation 6: the step-3 narrowing is refused; the head keeps its step-1 open value."""
        got = _rec(self.log, G, Q.DURATION, Outcome.NARROWED, None, reason="open_head_flag_contradiction",
                   candidates=(Candidate(_dur(2.0), 2.0), Candidate(_dur(1.0, 0, 1), 1.0)),
                   detail={"open_on_stem": {"ink_filled": False}})
        self.assertIs(got.outcome, Outcome.DECIDED)
        self.assertEqual(got.value["written"], 2.0)
        self.assertEqual(got.reason, "open_head_kept_over_a_flag")
        self.assertEqual(got.detail["flag_on_an_open_head"], [1])
        self.assertEqual(self.log.near_misses()[0]["row"], "flag_never_reopens_an_open_head")

    def test_a_flag_on_a_head_whose_ink_reads_filled_still_narrows(self):
        got = _rec(self.log, G, Q.DURATION, Outcome.NARROWED, None, reason="open_head_flag_contradiction",
                   candidates=(Candidate(_dur(2.0), 2.0), Candidate(_dur(1.0, 0, 1), 1.0)),
                   detail={"open_on_stem": {"ink_filled": True}})
        self.assertIs(got.outcome, Outcome.NARROWED)

    def test_the_meter_s_bars_are_summed_by_2_162s_helper(self):
        """Audit violation 2: under the guard a bar holding a narrowed note has no known length."""
        self.assertTrue(consequences.narrowed_bar_length_unknown())

    def test_a_rest_is_not_reinstated_in_a_bar_of_unknown_length(self):
        """Audit violation 7: `reinstate_rest_between_staves` in a bar holding a narrowed note."""
        cellsub = R.cell(0, 0, 0, 0)
        ev = _rec(self.log, cellsub, Q.EVENT, Outcome.DECIDED, {"events": [{"glyphs": [0]}]}, decider="adjudicate_event",
                  reason="t")
        self.assertIsNotNone(ev)
        _rec(self.log, G, Q.DURATION, Outcome.NARROWED, None, reason="beams_ambiguous",
             candidates=(Candidate(_quarter(), 2.0), Candidate(_eighth(), 1.0)))
        rest = R.glyph(0, 0, 0, 0, 1)
        refusal = _rec(self.log, rest, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, True,
                       decider="adjudicate_rest_is_not_a_rest", reason="t")
        got = _rec(self.log, rest, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, False,
                   decider="reinstate_rest_between_staves", reason="rest_reinstated_missing_voice",
                   supersedes=refusal.id)
        self.assertIs(got, refusal)
        self.assertEqual(self.log.near_misses()[0]["why"], "bar_length_unknown")

    def test_export_rows_refuse(self):
        self.assertFalse(OC.export_may("chord_value", (OC.A, "shared_stem")).allowed)
        self.assertFalse(OC.export_may("carried_meter", (OC.A, "bar_sum")).allowed)


class TestRemovingTheGuardFails(unittest.TestCase):
    """The same writes with the flag OFF all go through: the refusals above are the guard's, nothing else's."""

    def test_off_the_bar_moves_the_decided_quarter(self):
        with mock.patch.dict(os.environ, OFF):
            log = Log()
            prior = _rec(log, G, Q.DURATION, Outcome.DECIDED, _quarter())
            got = _rec(log, G, Q.DURATION, Outcome.DECIDED, _eighth(), decider="reconcile_duration",
                       reason="meter_reconciliation", supersedes=prior.id, basis=(prior.id,), single=True)
            self.assertIsNot(got, prior)
            self.assertEqual(log.near_misses(), [])
            self.assertNotIn("near_misses", log.to_json())

    def test_off_infer_and_the_stem_overwrite_go_through(self):
        with mock.patch.dict(os.environ, OFF):
            log = Log()
            prior = _rec(log, G, Q.DURATION, Outcome.DECIDED, _quarter())
            got = _rec(log, G, Q.DURATION, Outcome.DECIDED, _dur(2.0), decider="share_stem_value",
                       reason="stem_value_follows", supersedes=prior.id, single=True)
            self.assertIsNot(got, prior)

    def test_off_the_open_head_narrows(self):
        with mock.patch.dict(os.environ, OFF):
            log = Log()
            got = _rec(log, G, Q.DURATION, Outcome.NARROWED, None, reason="open_head_flag_contradiction",
                       candidates=(Candidate(_dur(2.0), 2.0), Candidate(_dur(1.0, 0, 1), 1.0)),
                       detail={"open_on_stem": {"ink_filled": False}})
            self.assertIs(got.outcome, Outcome.NARROWED)

    def test_guard_patched_out_lets_the_move_through(self):
        """The guard removed (its `check` always allows) with the flag ON: the refusal test's assertion fails."""
        with mock.patch.dict(os.environ, ON), mock.patch.object(OC, "check", lambda *a, **k: OC.Decision(True)):
            log = Log()
            prior = _rec(log, G, Q.DURATION, Outcome.DECIDED, _quarter())
            got = _rec(log, G, Q.DURATION, Outcome.DECIDED, _eighth(), decider="reconcile_duration",
                       reason="meter_reconciliation", supersedes=prior.id, basis=(prior.id,), single=True)
            self.assertIsNot(got, prior)


# ─────────────────────────────────────────────────────────────────────────────
# (c) shared stem, Sean 2026-10-17
# ─────────────────────────────────────────────────────────────────────────────

def _stem_with(fills, *, decider="adjudicate_duration"):
    s = Stem()
    ys = [60, 40, 20, 0]
    for gi, w in enumerate(fills):
        cls = "noteheadHalfInSpace" if w == 2.0 else "noteheadBlackInSpace"
        s.head(gi, cls, ys[gi], decided=(w, 0, 0))
    # the fixture's heads carry decider "test": re-file them as the reader's so the guard can key them
    for gi in range(len(fills)):
        v = s.log.verdict(Q.DURATION, s.heads[gi])
        object.__setattr__(v, "decider", decider)
    return s


class TestSharedStem(_On):

    def test_two_heads_that_disagree_leave_the_stem_UNDECIDED(self):
        s = _stem_with([2.0, 1.0]).run()
        for gi in (0, 1):
            v = s.value(gi)
            self.assertIs(v.outcome, Outcome.NARROWED, (v.reason, v.detail))
            self.assertEqual(v.reason, "stem_heads_disagree")
        evaluate.run(s.log)
        self.assertEqual(s.log.verdict(Q.DURATION, s.heads[1]).value["written"], 1.0)   # no fill overwritten
        self.assertEqual(s.log.verdict(Q.DURATION, s.heads[0]).value["written"], 2.0)

    def test_three_heads_one_dissent_GUESS_the_majority(self):
        s = _stem_with([2.0, 2.0, 1.0]).run()
        v = s.value(2)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "stem_heads_one_dissent")
        self.assertTrue(v.detail["guessed"])
        self.assertEqual(v.detail["likely_misreading"], s.heads[2].to_key())
        self.assertEqual(v.value["written"], 2.0)
        self.assertEqual(sorted(c.value["written"] for c in v.candidates), [1.0, 2.0])
        evaluate.run(s.log)
        d = s.log.verdict(Q.DURATION, s.heads[2])
        self.assertEqual(d.value["written"], 2.0)
        self.assertTrue(d.detail["guessed"])
        self.assertTrue(d.detail["likely_misreading"])
        agree = s.log.verdict(Q.DURATION, s.heads[0])
        self.assertTrue(agree.detail.get("guessed"))            # the whole chord is blue
        self.assertFalse(agree.detail.get("likely_misreading"))
        self.assertTrue(OC.is_guess(d))

    def test_three_heads_two_different_dissents_leave_it_UNDECIDED(self):
        s = _stem_with([2.0, 1.0, 4.0])
        # the whole-class box casts no vote; make the third a decided whole on a non-whole-class box
        s.run()
        self.assertEqual(s.value(0).reason, "stem_heads_disagree")
        self.assertIs(s.value(0).outcome, Outcome.NARROWED)

    def test_two_against_two_is_UNDECIDED(self):
        s = _stem_with([2.0, 2.0, 1.0, 1.0]).run()
        self.assertEqual(s.value(0).reason, "stem_heads_disagree")

    def test_heads_that_agree_are_untouched(self):
        s = _stem_with([2.0, 2.0, 2.0]).run()
        self.assertEqual(s.value(0).reason, "stem_agrees")

    def test_off_the_hollow_head_still_wins(self):
        """The control: with the flag OFF the 2.78 rule stands -- a hollow head makes the stem a half."""
        with mock.patch.dict(os.environ, OFF):
            s = _stem_with([2.0, 1.0]).run()
            self.assertIs(s.value(1).outcome, Outcome.DECIDED)
            self.assertEqual(s.value(1).value["written"], 2.0)


if __name__ == "__main__":
    unittest.main()
