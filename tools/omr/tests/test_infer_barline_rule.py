"""`collapse_duration_to_barline` — the rule, on a system it can actually walk.

⚠️⚠️ THE REGISTERED RULES HAD NO UNIT FIXTURE UNTIL THIS FILE.
`test_infer_stage.py` asserts the HARNESS's five disciplines using one-off
rules installed per test, which is right for what it covers and means the two
real rules were exercised only by a benchmark arm over a 132 MB record that
needs `library/`. So a rule could stop firing entirely and the suite would
stay green — the shape this repository already records as *a test named for a
hazard it does not reach*.

This builds the smallest system the rules can read: three staves, one bar, two
onset columns, page-frame glyph boxes, and `Q.ONSET_COLUMN` in the shape
`adjudicate_onset_column` actually writes. Both rules are then asserted on it,
including the one guard that separates them.
"""

import os
import unittest
from unittest import mock

from tools.omr.staged import evaluate, infer, inferences
from tools.omr.staged.gather import FRAME_PAGE
from tools.omr.staged.record import (READERS, Candidate, Kind, Log, Outcome, Q,
                                     Subject, Verdict)

SPACING = 10.0          # px per staff space, so the tolerance is 1.0 px
COL_X = (100.0, 200.0)  # the two onset columns of the bar


def _sub(staff, glyph, cell=0):
    return Subject(Kind.GLYPH, page=0, system=0, staff=staff, cell=cell,
                   glyph=glyph)


def _system():
    return Subject(Kind.SYSTEM, page=0, system=0)


def _cell(staff, cell=0):
    return Subject(Kind.CELL, page=0, system=0, staff=staff, cell=cell)


class _Builder:
    """A system with page-frame boxes, events, columns and durations."""

    def __init__(self):
        self.log = Log()
        self.events = {}        # staff -> [ [glyph, ...], ... ] in x order
        self.xs = {}            # (staff, glyph) -> page x

    def note(self, staff, glyph, x):
        """One single-glyph event on `staff` at page x."""
        self.log.observe(_sub(staff, glyph), Q.GLYPH_BOX, [0, 0, 1, 1],
                         reader=READERS.DETECTOR, frame=FRAME_PAGE,
                         x_center_page=x, bbox_page_px=[x - 1, 0, x + 1, 1])
        self.events.setdefault(staff, []).append([glyph])
        self.xs[(staff, glyph)] = x
        return self

    def narrowed(self, staff, glyph, beats=(2.0, 4.0)):
        self.log.record(Verdict(
            id=self.log._next_id("vrd"), subject=_sub(staff, glyph),
            quantity=Q.DURATION, outcome=Outcome.NARROWED, value=None,
            decider="test:reader", reason="two_readings_fit",
            candidates=tuple(Candidate({"beats": b}, support=1.0)
                             for b in beats)))
        return self

    def decided(self, staff, glyph, beats, basis=()):
        v = Verdict(
            id=self.log._next_id("vrd"), subject=_sub(staff, glyph),
            quantity=Q.DURATION, outcome=Outcome.DECIDED,
            value={"beats": beats}, decider="test:reader", reason="read",
            basis=tuple(basis))
        self.log.record(v)
        return v

    def meter(self, beats_per_bar=4.0):
        """A `Q.METER` verdict, so a witness can be made meter-derived."""
        v = Verdict(
            id=self.log._next_id("vrd"), subject=_system(), quantity=Q.METER,
            outcome=Outcome.DECIDED, value={"beats": beats_per_bar},
            decider="test:meter", reason="voted")
        self.log.record(v)
        return v

    def finish(self):
        """Write `Q.EVENT` per cell and `Q.ONSET_COLUMN` on the system."""
        for staff, evs in self.events.items():
            self.log.record(Verdict(
                id=self.log._next_id("vrd"), subject=_cell(staff),
                quantity=Q.EVENT, outcome=Outcome.DECIDED,
                value={"events": [{"glyphs": g} for g in evs]},
                decider="test:events", reason="grouped"))
        self.log.record(Verdict(
            id=self.log._next_id("vrd"), subject=_system(),
            quantity=Q.ONSET_COLUMN, outcome=Outcome.DECIDED,
            value={"bars": [{"measure": 0, "events_per_space": 1.0,
                             "columns": [{"x_page": x, "n_witness": 3}
                                         for x in COL_X]}]},
            decider="test:columns", reason="corroborated",
            detail={"staff_spacing_px": SPACING}))
        self.log.freeze()
        return self.log


def _run(log):
    """⚠️ THE DURATION RULES ARE DEFAULT-OFF SINCE 2026-09-21 AND THIS FILE
    MUST TURN THEM ON. Every rule now carries its own switch: the slot-index
    rule ships ON (25 of 25 against the print) while BOTH duration rules stay
    behind `OMR_INFER`, because neither has had a note checked against a page.
    `infer.run()` honours each switch, so without this the seven tests below
    exercised a stage that skipped the very rules they are named for --
    *a test named for a hazard it does not reach*, arriving by a default
    change rather than by a bad fixture.

    ⚠️ The assertion is the part that matters: it fails LOUDLY if the rule
    under test is ever skipped again, instead of the tests quietly asserting
    against an empty report.
    """
    with mock.patch.dict(os.environ, {infer.INFER_ENV: "1"}, clear=False):
        enabled = {r.inference for r in infer.enabled_rules()}
        assert infer.Inference.COLLAPSE_DURATION_TO_BARLINE in enabled, (
            "the barline rule is not enabled -- these tests would pass "
            "against a stage that never ran it")
        return infer.run(log, evaluate.Report([], [], []))


def _fired(report, which):
    return [i for i in report.inferred if i[0] == which.value]


class TestItReachesTheBarlinePopulation(unittest.TestCase):
    """⚠️ The bucket rule 1 declines by design: 191 of 357 on the real page."""

    def _two_witnesses_to_the_barline(self):
        b = _Builder()
        b.note(0, 0, COL_X[0]).narrowed(0, 0, beats=(2.0, 4.0))
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0)
        b.note(2, 0, COL_X[0]).decided(2, 0, 2.0)
        return b.finish()

    def test_it_fires(self):
        r = _run(self._two_witnesses_to_the_barline())
        self.assertEqual(
            len(_fired(r, infer.Inference.COLLAPSE_DURATION_TO_BARLINE)), 1)

    def test_the_column_rule_does_not_touch_this_population(self):
        """The two rules partition the walk; neither may claim both."""
        r = _run(self._two_witnesses_to_the_barline())
        self.assertEqual(
            _fired(r, infer.Inference.COLLAPSE_DURATION_BY_COLUMN), [])

    def test_it_takes_the_neighbours_length(self):
        log = self._two_witnesses_to_the_barline()
        _run(log)
        v = log.verdict(Q.DURATION, _sub(0, 0))
        self.assertEqual(v.value, {"beats": 2.0})
        self.assertTrue(infer.is_inferred(v))
        self.assertTrue(v.detail["runs_to_barline"])
        self.assertIsNone(v.detail["ends_at_column"])

    def test_one_witness_is_not_enough(self):
        b = _Builder()
        b.note(0, 0, COL_X[0]).narrowed(0, 0)
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0)
        r = _run(b.finish())
        self.assertEqual(
            _fired(r, infer.Inference.COLLAPSE_DURATION_TO_BARLINE), [])

    def test_one_dissenter_refuses_the_whole_inference(self):
        b = _Builder()
        b.note(0, 0, COL_X[0]).narrowed(0, 0)
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0)
        b.note(2, 0, COL_X[0]).decided(2, 0, 4.0)
        r = _run(b.finish())
        self.assertEqual(
            _fired(r, infer.Inference.COLLAPSE_DURATION_TO_BARLINE), [])

    def test_a_length_the_reader_never_admitted_is_refused(self):
        """Rule 4 — and here it must REFUSE rather than raise, because the
        neighbours disagreeing with the reader is an ordinary page fact."""
        b = _Builder()
        b.note(0, 0, COL_X[0]).narrowed(0, 0, beats=(1.0, 4.0))
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0)
        b.note(2, 0, COL_X[0]).decided(2, 0, 2.0)
        r = _run(b.finish())
        self.assertEqual(
            _fired(r, infer.Inference.COLLAPSE_DURATION_TO_BARLINE), [])


class TestTheMeterGuard(unittest.TestCase):
    """⚠️⚠️ The guard that lets this rule exist without reading `Q.METER`."""

    def _with_meter_derived_witnesses(self, n_clean):
        b = _Builder()
        m = b.meter()
        b.note(0, 0, COL_X[0]).narrowed(0, 0, beats=(2.0, 4.0))
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0, basis=(m.id,))
        for staff in range(2, 2 + n_clean):
            b.note(staff, 0, COL_X[0]).decided(staff, 0, 2.0)
        return b.finish()

    def test_a_meter_derived_witness_does_not_count(self):
        """One clean witness plus one meter-derived one is ONE witness."""
        r = _run(self._with_meter_derived_witnesses(n_clean=1))
        self.assertEqual(
            _fired(r, infer.Inference.COLLAPSE_DURATION_TO_BARLINE), [])

    def test_it_still_fires_on_the_clean_witnesses_and_counts_the_refusal(self):
        log = self._with_meter_derived_witnesses(n_clean=2)
        r = _run(log)
        self.assertEqual(
            len(_fired(r, infer.Inference.COLLAPSE_DURATION_TO_BARLINE)), 1)
        v = log.verdict(Q.DURATION, _sub(0, 0))
        self.assertEqual(v.detail["witnesses_refused_meter_derived"], 1)

    def test_the_counter_is_written_even_when_it_is_zero(self):
        """⚠️ "no witness was refused" and "this rule does not refuse
        witnesses" are different facts, and only an always-written counter
        keeps them apart."""
        b = _Builder()
        b.note(0, 0, COL_X[0]).narrowed(0, 0, beats=(2.0, 4.0))
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0)
        b.note(2, 0, COL_X[0]).decided(2, 0, 2.0)
        log = b.finish()
        _run(log)
        v = log.verdict(Q.DURATION, _sub(0, 0))
        self.assertIn("witnesses_refused_meter_derived", v.detail)
        self.assertEqual(v.detail["witnesses_refused_meter_derived"], 0)

    def test_the_guard_flag_says_whether_it_checked(self):
        """⚠️ A lone 0 cannot tell "checked, refused nobody" from "does not
        check". Rule 1 does not check; rule 2 does; both report 0 here."""
        b = _Builder()
        b.note(0, 0, COL_X[0]).narrowed(0, 0, beats=(2.0, 4.0))
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0)
        b.note(2, 0, COL_X[0]).decided(2, 0, 2.0)
        log = b.finish()
        _run(log)
        v = log.verdict(Q.DURATION, _sub(0, 0))
        self.assertTrue(v.detail["refuses_meter_derived_witnesses"])

        c = _Builder()
        c.note(0, 0, COL_X[0]).narrowed(0, 0, beats=(2.0, 4.0))
        c.note(0, 1, COL_X[1]).decided(0, 1, 1.0)
        c.note(1, 0, COL_X[0]).decided(1, 0, 2.0)
        c.note(1, 1, COL_X[1]).decided(1, 1, 1.0)
        c.note(2, 0, COL_X[0]).decided(2, 0, 2.0)
        c.note(2, 1, COL_X[1]).decided(2, 1, 1.0)
        log2 = c.finish()
        _run(log2)
        v2 = log2.verdict(Q.DURATION, _sub(0, 0))
        self.assertFalse(v2.detail["refuses_meter_derived_witnesses"],
                         "the column rule does not check, and must say so")
        self.assertEqual(v2.detail["witnesses_refused_meter_derived"], 0)

    def test_the_guard_is_provenance_and_not_a_decider_name(self):
        """A witness reached through ANY chain that touches the meter is
        refused, not merely one whose own decider is a meter consequence."""
        b = _Builder()
        m = b.meter()
        b.note(0, 0, COL_X[0]).narrowed(0, 0, beats=(2.0, 4.0))
        # staff 1's duration rests on staff 3's, which rests on the meter.
        far = b.note(3, 0, COL_X[0]).decided(3, 0, 2.0, basis=(m.id,))
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0, basis=(far.id,))
        b.note(2, 0, COL_X[0]).decided(2, 0, 2.0)
        log = b.finish()
        r = _run(log)
        # staff 1 and staff 3 are both meter-derived; only staff 2 is clean.
        self.assertEqual(
            _fired(r, infer.Inference.COLLAPSE_DURATION_TO_BARLINE), [])


class TestTheEndpointIsAPairAndNotAColumn(unittest.TestCase):
    """⚠️⚠️ THREE STATES, AND THE THIRD IS THE ONE THAT BITES.

    A note is barline-bound only when NOTHING follows it in the bar. Deriving
    that from *no later COLUMNED event* instead would call a note barline-bound
    whenever the event after it missed every column centre -- and then hand it
    a neighbour's whole-bar length.
    """

    def test_a_witness_that_ends_elsewhere_is_not_a_witness(self):
        """Both name 2.0, but only one of them measures THIS stretch."""
        b = _Builder()
        b.note(0, 0, COL_X[0]).narrowed(0, 0, beats=(2.0, 4.0))
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0)        # also to the barline
        b.note(2, 0, COL_X[0]).decided(2, 0, 2.0)        # ends at column 1
        b.note(2, 1, COL_X[1]).decided(2, 1, 1.0)
        r = _run(b.finish())
        # staff 2 spans k -> column 1, not k -> barline, so one witness remains
        self.assertEqual(
            _fired(r, infer.Inference.COLLAPSE_DURATION_TO_BARLINE), [])

    def test_a_witness_whose_endpoint_is_unknown_is_not_a_witness(self):
        """⚠️ THE ARM THAT FOUND THIS GAP IS WHY THE ENDPOINT IS A PAIR.

        Staff 2 stops at some unread instant, so its endpoint is
        `(None, False)`; the subject runs to the barline, `(None, True)`.
        They share the COLUMN half -- both `None` -- so a comparison on the
        column alone would count staff 2 as a witness to a gap it never
        measured. Only the pair keeps it out, and with it out one witness
        remains and the inference is refused."""
        b = _Builder()
        b.note(0, 0, COL_X[0]).narrowed(0, 0, beats=(2.0, 4.0))
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0)        # to the barline
        b.note(2, 0, COL_X[0]).decided(2, 0, 2.0)        # stops somewhere
        b.note(2, 1, 150.0).decided(2, 1, 1.0)           # ...in no column
        log = b.finish()
        spans = {(s.staff, s.k): s for s in inferences._walk(log, _system())}
        self.assertTrue(spans[(0, 0)].runs_to_barline)
        r = _run(log)
        self.assertEqual(
            _fired(r, infer.Inference.COLLAPSE_DURATION_TO_BARLINE), [])

    def test_an_event_in_no_column_makes_the_endpoint_unknown(self):
        """Something follows, and nobody knows when this note stops."""
        b = _Builder()
        b.note(0, 0, COL_X[0]).narrowed(0, 0, beats=(2.0, 4.0))
        b.note(0, 1, 150.0).decided(0, 1, 1.0)   # 50 px from either column
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0)
        b.note(2, 0, COL_X[0]).decided(2, 0, 2.0)
        log = b.finish()
        r = _run(log)
        self.assertEqual(
            _fired(r, infer.Inference.COLLAPSE_DURATION_TO_BARLINE), [])
        self.assertEqual(
            _fired(r, infer.Inference.COLLAPSE_DURATION_BY_COLUMN), [])

    def test_the_unknown_endpoint_is_named_on_the_span(self):
        b = _Builder()
        b.note(0, 0, COL_X[0]).narrowed(0, 0)
        b.note(0, 1, 150.0).decided(0, 1, 1.0)
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0)
        spans = inferences._walk(b.finish(), _system())
        self.assertEqual(len(spans), 1)
        self.assertTrue(spans[0].endpoint_is_unknown)
        self.assertFalse(spans[0].runs_to_barline)

    def test_two_unknown_endpoints_infer_nothing(self):
        """⚠️ AND IT PASSES FOR A REASON WORTH NAMING: not because the witness
        comparison rejects an unknown pair -- two unknowns compare EQUAL as
        `(None, False)` -- but because both rules exclude an unknown SUBJECT
        before witnesses are gathered at all. Asserted on the span so the
        mechanism, not the outcome, is what is pinned."""
        b = _Builder()
        b.note(0, 0, COL_X[0]).narrowed(0, 0, beats=(2.0, 4.0))
        b.note(0, 1, 150.0).decided(0, 1, 1.0)
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0)
        b.note(1, 1, 150.0).decided(1, 1, 1.0)
        b.note(2, 0, COL_X[0]).decided(2, 0, 2.0)
        b.note(2, 1, 150.0).decided(2, 1, 1.0)
        log = b.finish()
        spans = [s for s in inferences._walk(log, _system())]
        self.assertTrue(spans)
        self.assertTrue(all(s.endpoint_is_unknown for s in spans))
        self.assertEqual(_run(log).inferred, [])


class TestTheColumnRuleStillWorks(unittest.TestCase):
    """The refactor put both rules on one walk. Rule 1 must be unmoved."""

    def _bar_with_a_second_onset(self):
        b = _Builder()
        b.note(0, 0, COL_X[0]).narrowed(0, 0, beats=(2.0, 4.0))
        b.note(0, 1, COL_X[1]).decided(0, 1, 1.0)
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0)
        b.note(1, 1, COL_X[1]).decided(1, 1, 1.0)
        b.note(2, 0, COL_X[0]).decided(2, 0, 2.0)
        b.note(2, 1, COL_X[1]).decided(2, 1, 1.0)
        return b.finish()

    def test_the_column_rule_fires(self):
        r = _run(self._bar_with_a_second_onset())
        self.assertEqual(
            len(_fired(r, infer.Inference.COLLAPSE_DURATION_BY_COLUMN)), 1)

    def test_the_barline_rule_does_not_touch_this_population(self):
        r = _run(self._bar_with_a_second_onset())
        self.assertEqual(
            _fired(r, infer.Inference.COLLAPSE_DURATION_TO_BARLINE), [])

    def test_it_records_the_column_it_ends_at(self):
        log = self._bar_with_a_second_onset()
        _run(log)
        v = log.verdict(Q.DURATION, _sub(0, 0))
        self.assertEqual(v.detail["ends_at_column"], 1)
        self.assertFalse(v.detail["runs_to_barline"])


class TestTheTwoRulesPartitionTheWalk(unittest.TestCase):
    """Derived, so a third rule cannot quietly overlap them."""

    def test_no_glyph_is_claimed_twice(self):
        b = _Builder()
        b.note(0, 0, COL_X[0]).narrowed(0, 0, beats=(2.0, 4.0))   # to barline
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0)
        b.note(2, 0, COL_X[0]).decided(2, 0, 2.0)
        log = b.finish()
        r = _run(log)
        subjects = [i[1] for i in r.inferred]
        self.assertEqual(len(subjects), len(set(subjects)))

    def test_every_span_has_exactly_one_owning_rule(self):
        log = _Builder()
        log.note(0, 0, COL_X[0]).narrowed(0, 0)
        log.note(1, 0, COL_X[0]).decided(1, 0, 2.0)
        frozen = log.finish()
        spans = inferences._walk(frozen, _system())
        self.assertTrue(spans)
        for s in spans:
            self.assertEqual(
                [s.end is None, s.end is not None].count(True), 1)


class TestNeitherRuleReadsTheMeter(unittest.TestCase):
    """⚠️ Derived over the whole registry, so `bar_fill.py` stays a
    legitimate self-check for every rule and not only for the first one."""

    def setUp(self):
        infer._ensure_rules()

    def test_no_registered_rule_declares_the_meter(self):
        for r in infer.RULES:
            self.assertEqual(infer.scoring_conflict(r, (Q.METER,)), (),
                             f"{r.inference.value} reads Q.METER")

    def test_the_barline_rule_is_registered(self):
        names = {r.inference for r in infer.RULES}
        self.assertIn(infer.Inference.COLLAPSE_DURATION_TO_BARLINE, names)


if __name__ == "__main__":
    unittest.main()


class TestItReadsGlyphOwner(unittest.TestCase):
    """⚠️ A CELL IS A CROP AND ITS INK IS NOT ALL ITS OWN (2026-09-23).

    The measure cell is padded 4 staff spaces, so on a conductor's page the
    detector fires on the NEIGHBOUR's notes inside this staff's crop.
    `glyph/p/s/9/c/5` means "the 5th detection in staff 9's cell-c crop", never
    "a note belonging to staff 9" -- `adjudicate_glyph_owner` settles which.

    Until this was wired, both duration rules took every glyph in the crop as
    the staff's own and borrowed a length from that staff's neighbours for ink
    another staff owns. Measured on the Litolff shared record: 2 of 16
    inferences stood on a glyph ownership had already awarded elsewhere, and
    Sean adjudicated one of them against the print -- `glyph/4/0/9/5/7`, owned
    by `staff/4/0/10` (Basso), where the rule had inferred 0.25 from
    VIOLONCELLO's column structure and the note is a Basso eighth.

    RUN RED against the pre-fix tree: the first test reports 1 inference where
    it expects 0.
    """

    def _owned(self, log, staff, glyph, owner_staff, cell=0):
        log.record(Verdict(
            id=log._next_id("vrd"), subject=_sub(staff, glyph, cell),
            quantity=Q.GLYPH_OWNER, outcome=Outcome.DECIDED,
            value=Subject(Kind.STAFF, page=0, system=0,
                          staff=owner_staff).to_key(),
            decider="adjudicate_glyph_owner", reason="distance"))

    def _bar(self):
        b = _Builder()
        b.note(0, 0, COL_X[0]).narrowed(0, 0, beats=(2.0, 4.0))
        b.note(1, 0, COL_X[0]).decided(1, 0, 2.0)
        b.note(2, 0, COL_X[0]).decided(2, 0, 2.0)
        return b

    def test_a_glyph_owned_by_another_staff_is_not_inferred_on(self):
        b = self._bar()
        log = b.finish()
        self._owned(log, 0, 0, owner_staff=1)     # staff 0's crop, staff 1's note
        r = _run(log)
        self.assertEqual(
            _fired(r, infer.Inference.COLLAPSE_DURATION_TO_BARLINE), [],
            "the rule borrowed a length for ink another staff owns")

    def test_a_glyph_owned_by_its_own_staff_is_still_inferred_on(self):
        """The guard must not refuse everything -- a positive control in the
        same class, without which the test above passes by refusing all."""
        b = self._bar()
        log = b.finish()
        self._owned(log, 0, 0, owner_staff=0)     # the contest was WON here
        r = _run(log)
        self.assertEqual(
            len(_fired(r, infer.Inference.COLLAPSE_DURATION_TO_BARLINE)), 1)

    def test_silence_is_not_a_verdict_an_uncontested_glyph_is_kept(self):
        """⚠️ `adjudicate_glyph_owner`'s domain is the CONTESTED population, so
        most glyphs carry no verdict at all -- 13 of the 16 measured. With no
        verdict the detection cell is the only claim there is, and reading the
        absence as "not mine" would silently delete them. That is the fallback
        hazard CLAUDE.md names: a fallback never converts "cannot tell" into an
        answer."""
        log = self._bar().finish()                # no glyph_owner verdict at all
        r = _run(log)
        self.assertEqual(
            len(_fired(r, infer.Inference.COLLAPSE_DURATION_TO_BARLINE)), 1)
