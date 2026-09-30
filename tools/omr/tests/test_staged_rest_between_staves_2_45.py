"""ROADMAP 2.45 -- a rest refused on BOTH staves it was detected on belongs
to the staff whose voice would otherwise be missing.

Sean, DECISIONS 2026-09-30, on three printed eighth rests between staves 2
and 3 of Brahms 1/i Breitkopf p1 system 0 bar 5 (`glyph/1/0/2/5/{0,3,10}` =
`glyph/1/0/3/5/{1,0,2}`, all six refused `rest_outside_its_staff` by
`family_precision._rest_vertical_window_refusal`, so all three physical
rests were lost):

    "They belong to the lower staff. I was able to determine that based on
    the amount of voices in each of the staffs. The one above has 2 voices
    and both the voices are accounted for. The one below has a voice that
    crosses as they both jump up higher. If the 8th note rests didn't belong
    to the lower staff then it would be missing a voice."

`consequences.reinstate_rest_between_staves` (EVALUATE, cause `Q.METER`,
effect `Q.REST_IS_NOT_A_REST`) reinstates the ONE twin whose own staff's bar
is short exactly this rest's own length, once every currently-refused glyph
is excluded (`_bar_total_excluding_refused`, built from `reconcile_duration`'s
own `_standing`/`_left_the_bar`/`_event_totals` preamble) -- provided every
OTHER contested staff is already complete without it. This is a bar-sum
reading, not `Q.VOICES` itself: `adjudicate_event` reads `Q.REST`, never
`Q.REST_IS_NOT_A_REST`, so a rest's ADJUDICATE-time refusal never removes it
from `Q.EVENT`/`Q.VOICES` at all and that quantity's OUTCOME cannot tell a
staff that needs the rest from one that does not.

The fixtures below construct TWO cells at the same (page, system, cell) --
different staves, matching CLAUDE.md's "a bar is keyed on (page, system,
cell)" -- each with its own `Q.DURATION`/`Q.EVENT`, a `Q.METER` at the shared
system, and a `Q.GLYPH_BAND_DISTANCE` contest linking the two staves' own
copies of the same ink, exactly as `gather._gather_owner_candidates` already
writes it (this rule reads that row; nothing in GATHER changed). This is
entirely new behaviour, so RED is simply the function's absence on the
unrepaired tree -- confirmed by moving `reinstate_rest_between_staves` and
its helper aside and re-running: `AttributeError`, all 12 tests below fail to
collect. Restoring the file returns every test to green.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import consequences
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict

PAGE, SYSTEM, CELL_IDX = 1, 0, 5
LOWER_STAFF, UPPER_STAFF = 3, 2
LOWER_CELL = R.cell(PAGE, SYSTEM, LOWER_STAFF, CELL_IDX)
UPPER_CELL = R.cell(PAGE, SYSTEM, UPPER_STAFF, CELL_IDX)
LOWER_KEY = R.staff(PAGE, SYSTEM, LOWER_STAFF).to_key()
UPPER_KEY = R.staff(PAGE, SYSTEM, UPPER_STAFF).to_key()


def _v(log, sub, q, outcome, value, *, reason="t", detail=None):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome,
        value=value, decider="test", reason=reason, detail=detail or {}))


def _dur(beats):
    return {"beats": beats, "written": beats, "dots": 0, "beam_levels": 0}


def _decided_duration(log, staff, gi, beats):
    sub = R.glyph(PAGE, SYSTEM, staff, CELL_IDX, gi)
    _v(log, sub, Q.DURATION, Outcome.DECIDED, _dur(beats),
       reason="head_and_marks")
    return sub


def _events(log, cell, *glyph_groups):
    _v(log, cell, Q.EVENT, Outcome.DECIDED,
       {"events": [{"glyphs": list(g)} for g in glyph_groups]})


def _meter(log, num=2, den=4):
    return _v(log, R.system(PAGE, SYSTEM), Q.METER, Outcome.DECIDED,
              {"numerator": num, "denominator": den, "raw": f"{num}/{den}"})


def _refused_rest(log, staff, gi, beats, *, other_staff_key, own_key,
                  reason="rest_outside_its_staff"):
    """One rest glyph, DECIDED `rest_outside_its_staff`, with its own
    `Q.DURATION` and a `Q.GLYPH_BAND_DISTANCE` contest row naming the
    neighbour staff -- exactly what `gather._gather_owner_candidates`
    already writes for a cross-staff rest contest."""
    sub = R.glyph(PAGE, SYSTEM, staff, CELL_IDX, gi)
    _v(log, sub, Q.DURATION, Outcome.DECIDED, _dur(beats),
       reason="head_and_marks")
    _v(log, sub, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, True, reason=reason)
    log.observe(sub, Q.GLYPH_BAND_DISTANCE, 3.2, reader=READERS.GEOMETRY,
                frame="page", candidate=other_staff_key, own=False)
    log.observe(sub, Q.GLYPH_BAND_DISTANCE, 3.2, reader=READERS.GEOMETRY,
                frame="page", candidate=own_key, own=True)
    return sub


def _fire(log, glyph, meter):
    return consequences.reinstate_rest_between_staves(log, glyph, meter)


class TestSeansCase(unittest.TestCase):
    """RED on the unrepaired tree (the rule does not exist at all)."""

    def _build(self, *, lower_note_beats=1.5, upper_notes=(1.0, 1.0),
              rest_beats=0.5):
        log = Log()
        meter = _meter(log)
        # Lower staff: one decided note short of 2/4 by exactly the rest.
        n = _decided_duration(log, LOWER_STAFF, 0, lower_note_beats)
        rest_lower = _refused_rest(log, LOWER_STAFF, 1, rest_beats,
                                   other_staff_key=UPPER_KEY, own_key=LOWER_KEY)
        _events(log, LOWER_CELL, [n], [rest_lower])
        # Upper staff: two decided notes that already sum to 2/4, plus its
        # own independently-detected (and independently refused) copy of
        # the SAME physical ink.
        u0 = _decided_duration(log, UPPER_STAFF, 0, upper_notes[0])
        u1 = _decided_duration(log, UPPER_STAFF, 1, upper_notes[1])
        rest_upper = _refused_rest(log, UPPER_STAFF, 2, rest_beats,
                                   other_staff_key=LOWER_KEY, own_key=UPPER_KEY)
        _events(log, UPPER_CELL, [u0], [u1], [rest_upper])
        return log, meter, rest_lower, rest_upper

    def test_the_lower_staffs_own_copy_is_reinstated_RED(self):
        log, meter, rest_lower, _ = self._build()
        out = _fire(log, rest_lower, meter)
        self.assertEqual(len(out), 1)
        v = out[0]
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest_reinstated_missing_voice")
        self.assertEqual(v.supersedes,
                         log.verdicts(Q.REST_IS_NOT_A_REST, rest_lower)[0].id)
        # The record now reads it as live, not refused.
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, rest_lower).value,
                     False)

    def test_the_upper_staffs_own_copy_stays_refused_RED(self):
        """The control this rule must NOT trip: the upper staff is already
        complete without the rest (2.0 == target), so ITS OWN copy's
        shortfall is zero, not 0.5, and nothing fires for it."""
        log, meter, _, rest_upper = self._build()
        out = _fire(log, rest_upper, meter)
        self.assertEqual(out, [])
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, rest_upper).value,
                     True)


class TestControls(unittest.TestCase):
    """GREEN before and after -- every shape this rule must leave alone."""

    def test_not_refused_at_all_is_untouched(self):
        log = Log()
        meter = _meter(log)
        sub = R.glyph(PAGE, SYSTEM, LOWER_STAFF, CELL_IDX, 0)
        _v(log, sub, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, False,
           reason="rest")
        self.assertEqual(_fire(log, sub, meter), [])

    def test_refused_for_a_DIFFERENT_reason_is_untouched(self):
        """A stem, a duplicate box, an off-centre whole rest -- none of
        these is the between-staves case and this rule has no opinion."""
        log = Log()
        meter = _meter(log)
        sub = R.glyph(PAGE, SYSTEM, LOWER_STAFF, CELL_IDX, 0)
        _v(log, sub, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, True,
           reason="rest_has_a_stem")
        log.observe(sub, Q.GLYPH_BAND_DISTANCE, 3.2, reader=READERS.GEOMETRY,
                   frame="page", candidate=UPPER_KEY, own=False)
        self.assertEqual(_fire(log, sub, meter), [])

    def test_no_contest_at_all_is_untouched(self):
        """Refused `rest_outside_its_staff` with no twin on any neighbour
        staff -- an ordinary off-staff rest, not this case."""
        log = Log()
        meter = _meter(log)
        sub = R.glyph(PAGE, SYSTEM, LOWER_STAFF, CELL_IDX, 0)
        _v(log, sub, Q.DURATION, Outcome.DECIDED, _dur(0.5))
        _v(log, sub, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, True,
           reason="rest_outside_its_staff")
        self.assertEqual(_fire(log, sub, meter), [])

    def test_both_staves_already_complete_is_untouched(self):
        """A duplicate detection of a rest that genuinely belongs to ONE
        staff which already accounts for it in full: neither staff is short,
        so this is not a missing-voice case and nothing should be guessed."""
        log = Log()
        meter = _meter(log)
        n = _decided_duration(log, LOWER_STAFF, 0, 2.0)   # already complete
        rest_lower = _refused_rest(log, LOWER_STAFF, 1, 0.5,
                                   other_staff_key=UPPER_KEY, own_key=LOWER_KEY)
        _events(log, LOWER_CELL, [n], [rest_lower])
        u = _decided_duration(log, UPPER_STAFF, 0, 2.0)   # also complete
        rest_upper = _refused_rest(log, UPPER_STAFF, 1, 0.5,
                                   other_staff_key=LOWER_KEY, own_key=UPPER_KEY)
        _events(log, UPPER_CELL, [u], [rest_upper])
        self.assertEqual(_fire(log, rest_lower, meter), [])
        self.assertEqual(_fire(log, rest_upper, meter), [])

    def test_both_staves_missing_something_is_untouched(self):
        """Neither candidate is complete: the shortfall on one staff matches
        the rest's own length, but the OTHER staff is not itself whole, so
        this is genuinely ambiguous and rule 8 applies."""
        log = Log()
        meter = _meter(log)
        n = _decided_duration(log, LOWER_STAFF, 0, 1.5)
        rest_lower = _refused_rest(log, LOWER_STAFF, 1, 0.5,
                                   other_staff_key=UPPER_KEY, own_key=LOWER_KEY)
        _events(log, LOWER_CELL, [n], [rest_lower])
        u = _decided_duration(log, UPPER_STAFF, 0, 1.0)   # short by 1.0, not
        rest_upper = _refused_rest(log, UPPER_STAFF, 1, 0.5,           # 0.5
                                   other_staff_key=LOWER_KEY, own_key=UPPER_KEY)
        _events(log, UPPER_CELL, [u], [rest_upper])
        self.assertEqual(_fire(log, rest_lower, meter), [])

    def test_shortfall_does_not_match_the_rests_own_length(self):
        """The own staff IS short, but not by exactly this rest's length --
        something else is wrong in the bar, and this rule only ever closes
        the ONE gap its own missing ink explains."""
        log = Log()
        meter = _meter(log)
        n = _decided_duration(log, LOWER_STAFF, 0, 1.0)   # short by 1.0
        rest_lower = _refused_rest(log, LOWER_STAFF, 1, 0.5,     # not 0.5
                                   other_staff_key=UPPER_KEY, own_key=LOWER_KEY)
        _events(log, LOWER_CELL, [n], [rest_lower])
        u = _decided_duration(log, UPPER_STAFF, 0, 2.0)
        rest_upper = _refused_rest(log, UPPER_STAFF, 1, 0.5,
                                   other_staff_key=LOWER_KEY, own_key=UPPER_KEY)
        _events(log, UPPER_CELL, [u], [rest_upper])
        self.assertEqual(_fire(log, rest_lower, meter), [])

    def test_candidate_staffs_own_bar_is_undecided(self):
        """The neighbour staff has no standing `Q.EVENT` at all -- an
        undecided candidate is not evidence either way (rule 8)."""
        log = Log()
        meter = _meter(log)
        n = _decided_duration(log, LOWER_STAFF, 0, 1.5)
        rest_lower = _refused_rest(log, LOWER_STAFF, 1, 0.5,
                                   other_staff_key=UPPER_KEY, own_key=LOWER_KEY)
        _events(log, LOWER_CELL, [n], [rest_lower])
        # No Q.EVENT / Q.DURATION at all on UPPER_CELL.
        self.assertEqual(_fire(log, rest_lower, meter), [])

    def test_no_meter_is_untouched(self):
        log = Log()
        n = _decided_duration(log, LOWER_STAFF, 0, 1.5)
        rest_lower = _refused_rest(log, LOWER_STAFF, 1, 0.5,
                                   other_staff_key=UPPER_KEY, own_key=LOWER_KEY)
        _events(log, LOWER_CELL, [n], [rest_lower])
        undecided = _v(log, R.system(PAGE, SYSTEM), Q.METER,
                       Outcome.ABSTAINED, None, reason="carry_not_corroborated")
        self.assertEqual(_fire(log, rest_lower, undecided), [])

    def test_a_whole_rest_twin_kept_on_its_own_staff_is_untouched(self):
        """One copy KEPT (not refused) on the staff it truly belongs to, the
        other copy refused on the neighbour -- but the neighbour's own bar
        is already complete without it (the true owner's copy already
        carries the duration), so the refused twin's shortfall is zero and
        nothing fires. Mirrors 2.33b's '8 whole rests kept on their own
        staff' shape."""
        log = Log()
        meter = _meter(log)
        kept = R.glyph(PAGE, SYSTEM, LOWER_STAFF, CELL_IDX, 0)
        _v(log, kept, Q.DURATION, Outcome.DECIDED, _dur(2.0))
        _v(log, kept, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, False,
           reason="rest")
        _events(log, LOWER_CELL, [kept])
        n = _decided_duration(log, UPPER_STAFF, 0, 2.0)  # already whole
        ghost = _refused_rest(log, UPPER_STAFF, 1, 2.0,
                              other_staff_key=LOWER_KEY, own_key=UPPER_KEY)
        _events(log, UPPER_CELL, [n], [ghost])
        self.assertEqual(_fire(log, ghost, meter), [])

    def test_rest_duration_not_decided_is_untouched(self):
        log = Log()
        meter = _meter(log)
        n = _decided_duration(log, LOWER_STAFF, 0, 1.5)
        sub = R.glyph(PAGE, SYSTEM, LOWER_STAFF, CELL_IDX, 1)
        _v(log, sub, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, True,
           reason="rest_outside_its_staff")
        log.observe(sub, Q.GLYPH_BAND_DISTANCE, 3.2, reader=READERS.GEOMETRY,
                   frame="page", candidate=UPPER_KEY, own=False)
        # No Q.DURATION for `sub` at all.
        _events(log, LOWER_CELL, [n], [sub])
        u = _decided_duration(log, UPPER_STAFF, 0, 2.0)
        _events(log, UPPER_CELL, [u])
        self.assertEqual(_fire(log, sub, meter), [])


if __name__ == "__main__":
    unittest.main()
