"""ROADMAP 2.36 -- a chord's members share one stem and one duration.

`consequences.reconcile_chord_duration`: a NARROWED `Q.DURATION` verdict
whose own `used` names the exact SAME `Q.STEM` observation id as another
glyph's DECIDED duration in the same cell is settled to that mate's value --
but ONLY where the mate's beam level is one of the narrowing's OWN
candidates. Never a guess past what the reader already offered (rule 6),
and never touched where the evidence is ambiguous (rule 8).

⚠️ WHY `used`, TESTED DIRECTLY (`test_a_shared_ANCESTOR_stem_list_does_not_
count`): `adjudicate_duration` reads EVERY stem in the cell into
`considered`/`basis` (`ev.rows(Q.STEM, scope=SELF_AND_ANCESTORS, ...)`), so
two unrelated notes in the same bar share that whole list -- only `used`
(`rhythm._stem_joined`'s own overlap test between THIS head's box and the
stem rows) narrows to the note's OWN stem.

Reach, measured against both 2026-09-29 acceptance records (read-only,
`benchmarks/omr-duration-narrowed-2026-09/chord_reach.py`, no re-gather):
32 of 1,149 narrowed Litolff notes, 37 of 3,200 narrowed Brahms notes --
modest, and reported as such rather than assumed.

RED against the unrepaired tree: `consequences.reconcile_chord_duration`
does not exist there at all (`AttributeError`), confirmed by copying this
module's pre-2.36 content aside and running this file against it.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import consequences
from tools.omr.staged import record as R
from tools.omr.staged.record import Candidate, Log, Outcome, Q, READERS, Verdict

CELL = R.cell(0, 0, 1, 3)


def _v(log, sub, q, outcome, value, *, reason="t", used=(), candidates=()):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome,
        value=value, decider="test", reason=reason, used=tuple(used),
        candidates=candidates))


def _dur(beats, levels):
    return {"beats": beats, "written": beats, "dots": 0, "beam_levels": levels}


def _stem(log, *, x=90, y=0, w=4, h=60):
    """One `Q.STEM` observation -- the real row shape (`rhythm._stem` in
    `test_staged_duration.py`)."""
    return log.observe(CELL, Q.STEM, (x, y, w, h), reader=READERS.CV_LINES,
                       frame="cell:0", x0=x, x1=x + w, y_center=y + h / 2.0,
                       image="no_staff", staff_lines_erased=True)


def _decided(log, g, beats, levels=0, *, used=()):
    sub = R.glyph(0, 0, 1, 3, g)
    v = _v(log, sub, Q.DURATION, Outcome.DECIDED, _dur(beats, levels),
          reason="head_and_marks", used=used)
    return sub, v


def _narrowed(log, g, *options, used=()):
    sub = R.glyph(0, 0, 1, 3, g)
    v = _v(log, sub, Q.DURATION, Outcome.NARROWED, None,
          reason="beams_ambiguous", used=used,
          candidates=tuple(Candidate(_dur(b, lv), 2.0 - i)
                           for i, (b, lv) in enumerate(options)))
    return sub, v


def _meter(log, num=2, den=4):
    return _v(log, R.system(0, 0), Q.METER, Outcome.DECIDED,
              {"numerator": num, "denominator": den, "raw": f"{num}/{den}"})


def _fire(log, meter):
    return consequences.reconcile_chord_duration(log, CELL, meter)


class TestAChordMateSettlesIt(unittest.TestCase):
    """RED on the unrepaired tree (the function does not exist)."""

    def test_a_chord_mate_settles_it_RED(self):
        """A shares stem S and is DECIDED one beam level (an eighth); B
        shares the SAME stem S and is NARROWED {quarter(0), eighth(1)} --
        its own candidates already admit level 1, so the mate settles it."""
        log = Log()
        s = _stem(log)
        _decided(log, 0, 0.5, levels=1, used=(s.id,))
        b, before = _narrowed(log, 1, (1.0, 0), (0.5, 1), used=(s.id,))
        out = _fire(log, _meter(log))
        self.assertEqual(len(out), 1)
        now = log.verdict(Q.DURATION, b)
        self.assertIs(now.outcome, Outcome.DECIDED)
        self.assertEqual(now.value["beats"], 0.5)
        self.assertTrue(now.value["reconciled_by_chord_mate"])
        self.assertEqual(now.reason, "chord_mate_shares_the_stem")
        self.assertEqual(now.supersedes, before.id)

    def test_the_candidate_ORDER_is_irrelevant_only_MEMBERSHIP_matters(self):
        """The mate's level (0) is the narrowing's SECOND-listed candidate,
        not its top one -- membership decides, not rank."""
        log = Log()
        s = _stem(log)
        _decided(log, 0, 1.0, levels=0, used=(s.id,))
        b, _ = _narrowed(log, 1, (0.5, 1), (1.0, 0), used=(s.id,))
        out = _fire(log, _meter(log))
        self.assertEqual(len(out), 1)
        self.assertEqual(log.verdict(Q.DURATION, b).value["beats"], 1.0)


class TestControls(unittest.TestCase):
    """Every one of these must stay NARROWED -- a positive result here is
    the guard failing to guard."""

    def test_no_shared_stem_stays_NARROWED(self):
        """Two separate notes, two separate stems: the classic case this
        must NOT touch -- an ordinary bar with one settled note and one
        genuinely ambiguous one that happens to sit near it."""
        log = Log()
        s1 = _stem(log, x=90)
        s2 = _stem(log, x=200)
        _decided(log, 0, 0.5, levels=1, used=(s1.id,))
        b, _ = _narrowed(log, 1, (1.0, 0), (0.5, 1), used=(s2.id,))
        self.assertEqual(_fire(log, _meter(log)), [])
        self.assertIs(log.verdict(Q.DURATION, b).outcome, Outcome.NARROWED)

    def test_no_stem_at_all_stays_NARROWED(self):
        """A narrowing with an empty `used` (no stem attached) has nothing
        to match against -- the common case for most `beams_ambiguous`
        rows, and the reason this connection's reach is modest."""
        log = Log()
        s = _stem(log)
        _decided(log, 0, 0.5, levels=1, used=(s.id,))
        b, _ = _narrowed(log, 1, (1.0, 0), (0.5, 1), used=())
        self.assertEqual(_fire(log, _meter(log)), [])
        self.assertIs(log.verdict(Q.DURATION, b).outcome, Outcome.NARROWED)

    def test_two_DECIDED_stem_mates_that_DISAGREE_refuse(self):
        """A three-note chord where two DECIDED members disagree about
        their own beam level: which one is this note's own is no longer a
        single fact, so rule 8 refuses rather than picking either."""
        log = Log()
        s = _stem(log)
        _decided(log, 0, 0.5, levels=1, used=(s.id,))
        _decided(log, 2, 1.0, levels=0, used=(s.id,))
        b, _ = _narrowed(log, 1, (1.0, 0), (0.5, 1), used=(s.id,))
        self.assertEqual(_fire(log, _meter(log)), [])
        self.assertIs(log.verdict(Q.DURATION, b).outcome, Outcome.NARROWED)

    def test_a_level_the_narrowing_never_offered_refuses(self):
        """The mate reads TWO beams; the narrowing only ever offered 0 or
        1 -- the mate's answer is not among what THIS note's own ink
        admitted, so this must not invent a THIRD candidate."""
        log = Log()
        s = _stem(log)
        _decided(log, 0, 0.25, levels=2, used=(s.id,))
        b, _ = _narrowed(log, 1, (1.0, 0), (0.5, 1), used=(s.id,))
        self.assertEqual(_fire(log, _meter(log)), [])
        self.assertIs(log.verdict(Q.DURATION, b).outcome, Outcome.NARROWED)

    def test_a_head_fill_narrowing_with_THREE_same_level_candidates_refuses(self):
        """`head_fill_from_ink` narrows across black/half/whole, and every
        one of those candidates carries `beam_levels: 0` (ROADMAP 2.23) --
        so a beam_levels-0 mate admits THREE candidates, not one, and this
        must refuse rather than guess which fill the mate implies. The
        mate speaks to BEAM COUNT, not to notehead fill."""
        log = Log()
        s = _stem(log)
        _decided(log, 0, 1.0, levels=0, used=(s.id,))
        sub = R.glyph(0, 0, 1, 3, 1)
        _v(log, sub, Q.DURATION, Outcome.NARROWED, None,
          reason="head_fill_from_ink", used=(s.id,),
          candidates=(Candidate({**_dur(1.0, 0), "head_fill": "black"}, 1.0),
                      Candidate({**_dur(2.0, 0), "head_fill": "half"}, 2.0),
                      Candidate({**_dur(4.0, 0), "head_fill": "whole"}, 1.0)))
        self.assertEqual(_fire(log, _meter(log)), [])
        self.assertIs(log.verdict(Q.DURATION, sub).outcome, Outcome.NARROWED)

    def test_a_narrowed_REST_is_not_touched(self):
        """A rest carries no stem, and `_is_rest` excludes it structurally
        even where a fixture hands it one -- this is the guard, tested
        directly, not a change to any rest-reading rule."""
        log = Log()
        s = _stem(log)
        _decided(log, 0, 0.5, levels=1, used=(s.id,))
        sub = R.glyph(0, 0, 1, 3, 1)
        _v(log, sub, Q.DURATION, Outcome.NARROWED, None, reason="rest_value",
          used=(s.id,),
          candidates=(Candidate({**_dur(1.0, 0), "is_rest": True}, 2.0),
                      Candidate({**_dur(0.5, 1), "is_rest": True}, 1.0)))
        self.assertEqual(_fire(log, _meter(log)), [])
        self.assertIs(log.verdict(Q.DURATION, sub).outcome, Outcome.NARROWED)

    def test_no_decided_note_in_the_cell_at_all(self):
        log = Log()
        s = _stem(log)
        b, _ = _narrowed(log, 1, (1.0, 0), (0.5, 1), used=(s.id,))
        self.assertEqual(_fire(log, _meter(log)), [])
        self.assertIs(log.verdict(Q.DURATION, b).outcome, Outcome.NARROWED)

    def test_the_superseded_reading_stays_on_the_record(self):
        log = Log()
        s = _stem(log)
        _decided(log, 0, 0.5, levels=1, used=(s.id,))
        b, before = _narrowed(log, 1, (1.0, 0), (0.5, 1), used=(s.id,))
        _fire(log, _meter(log))
        self.assertIsNotNone(log.row(before.id))
        self.assertEqual(log.verdict(Q.DURATION, b).supersedes, before.id)


class TestItIsRegistered(unittest.TestCase):
    def test_it_is_a_live_downhill_bounded_rule(self):
        from tools.omr.staged import evaluate
        names = [r.fn.__name__ for r in evaluate.RULES]
        self.assertIn("reconcile_chord_duration", names)
        r = [r for r in evaluate.RULES
            if r.fn.__name__ == "reconcile_chord_duration"][0]
        evaluate.check_downhill(r.cause, r.effect)
        self.assertGreater(len(r.bound), 40)

    def test_it_runs_before_reconcile_duration_in_the_same_pass(self):
        """Same `cause` (METER): file order is the tie-break, and a chord
        fix must land BEFORE the bar-sum search reads `_standing` so a
        newly-decided chord member can feed it."""
        from tools.omr.staged import evaluate
        cause_metered = [r.fn.__name__ for r in evaluate.RULES
                        if r.cause == Q.METER]
        self.assertLess(cause_metered.index("reconcile_chord_duration"),
                        cause_metered.index("reconcile_duration"))


if __name__ == "__main__":
    unittest.main()
