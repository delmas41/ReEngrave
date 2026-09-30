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

⚠️⚠️ MANAGER CORRECTION 2026-09-30 to the first build of this file, which
fired ZERO times on Sean's own shape. Fixed here:

  1. A staff's expected total is VOICES x bar length, not one bar length --
     `_voice_count` reads `Q.VOICES` where decided, else counts DECIDED
     `Q.STEM_DIRECTION`s exactly as `adjudicate_voices` (2.21) counts them
     at its own first rule.
  2. The three contested rests are ONE GROUP per bar against one neighbour
     staff (`_contest_group`), not three independent 0.5-beat tests -- a
     staff's shortfall must equal the GROUP's own total length.
  3. The meter read is whatever `Q.METER` DECIDED, never a better guess.
     `benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` SS21c names the
     real blocker on the actual Brahms p1 record (a persisting 2.12h
     mis-metering on this exact bar); these fixtures inject a CORRECT
     meter directly, per Sean's 2026-09-29 process convention (microscopic
     tests, no re-gather), to prove the mechanism itself.

RED is the function's total absence on the unrepaired tree (confirmed by
moving `reinstate_rest_between_staves`/`_bar_total_excluding`/
`_contest_group`/`_group_length`/`_voice_count` out of `consequences.py`
and re-running: `AttributeError`, every test below fails to collect;
restoring returns every test to green).
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


def _meter(log, num=6, den=8):
    return _v(log, R.system(PAGE, SYSTEM), Q.METER, Outcome.DECIDED,
              {"numerator": num, "denominator": den, "raw": f"{num}/{den}"})


def _voices(log, cell, n):
    _v(log, cell, Q.VOICES, Outcome.DECIDED,
       {"n_voices": n, "voices": [], "rests_in_every_voice": [],
        "rests_displaced_by_position": {}})


def _stem_dir(log, staff, gi, direction):
    sub = R.glyph(PAGE, SYSTEM, staff, CELL_IDX, gi)
    _v(log, sub, Q.STEM_DIRECTION, Outcome.DECIDED, direction)
    return sub


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
    """Sean's own shape: 2 voices per staff, 6/8, one group of 3 eighth
    rests. RED on the unrepaired tree."""

    def _build(self):
        log = Log()
        meter = _meter(log, 6, 8)                      # bar_len = 3.0
        _voices(log, LOWER_CELL, 2)                     # expected 6.0
        _voices(log, UPPER_CELL, 2)                     # expected 6.0

        # Lower staff: one decided note (4.5) + the 3-rest group (1.5) =
        # 6.0 once the group is reinstated; 4.5 while it is excluded.
        n_lo = _decided_duration(log, LOWER_STAFF, 0, 4.5)
        lo_rests = [
            _refused_rest(log, LOWER_STAFF, gi, 0.5,
                         other_staff_key=UPPER_KEY, own_key=LOWER_KEY)
            for gi in (1, 2, 3)]
        _events(log, LOWER_CELL, [n_lo], *([r] for r in lo_rests))

        # Upper staff: already complete at 6.0 without its own (spurious)
        # copies of the same three rests.
        n_up = _decided_duration(log, UPPER_STAFF, 0, 6.0)
        up_rests = [
            _refused_rest(log, UPPER_STAFF, gi, 0.5,
                         other_staff_key=LOWER_KEY, own_key=UPPER_KEY)
            for gi in (11, 12, 13)]
        _events(log, UPPER_CELL, [n_up], *([r] for r in up_rests))

        return log, meter, lo_rests, up_rests

    def test_the_whole_group_reinstates_on_the_lower_staff_RED(self):
        log, meter, lo_rests, up_rests = self._build()
        for r in lo_rests:
            out = _fire(log, r, meter)
            self.assertEqual(len(out), 1, msg=f"{r.to_key()} did not fire")
            v = out[0]
            self.assertIs(v.outcome, Outcome.DECIDED)
            self.assertIs(v.value, False)
            self.assertEqual(v.reason, "rest_reinstated_missing_voice")
            self.assertAlmostEqual(v.detail["group_len_beats"], 1.5)
            self.assertEqual(v.detail["own_voices"], 2)
            self.assertEqual(v.detail["candidate_voices"], 2)
        for r in lo_rests:
            self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, r).value, False)

    def test_the_upper_staffs_own_copies_stay_refused_RED(self):
        """The control this rule must NOT trip: the upper staff is already
        complete (6.0 == 2 voices x 3.0) without the group, so its own
        shortfall is zero, not 1.5, and nothing fires for it."""
        log, meter, _, up_rests = self._build()
        for r in up_rests:
            self.assertEqual(_fire(log, r, meter), [])
            self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, r).value, True)

    def test_voice_count_by_stem_direction_when_Q_VOICES_is_undecided(self):
        """The same mechanism, but neither cell has a `Q.VOICES` verdict at
        all -- the own staff's voice count comes from two DECIDED, opposite
        `Q.STEM_DIRECTION`s (2.21's own first rule), the candidate's from a
        single direction (one voice)."""
        log = Log()
        meter = _meter(log, 2, 4)                       # bar_len = 2.0
        _stem_dir(log, LOWER_STAFF, 50, "up")
        _stem_dir(log, LOWER_STAFF, 51, "down")          # own: 2 voices
        _stem_dir(log, UPPER_STAFF, 60, "up")            # candidate: 1 voice

        n_lo = _decided_duration(log, LOWER_STAFF, 0, 3.5)  # short by 0.5
        rest = _refused_rest(log, LOWER_STAFF, 1, 0.5,
                             other_staff_key=UPPER_KEY, own_key=LOWER_KEY)
        _events(log, LOWER_CELL, [n_lo], [rest])

        n_up = _decided_duration(log, UPPER_STAFF, 0, 2.0)  # complete at 2.0
        ghost = _refused_rest(log, UPPER_STAFF, 1, 0.5,
                              other_staff_key=LOWER_KEY, own_key=UPPER_KEY)
        _events(log, UPPER_CELL, [n_up], [ghost])

        out = _fire(log, rest, meter)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].detail["own_voices"], 2)
        self.assertEqual(out[0].detail["candidate_voices"], 1)


class TestControls(unittest.TestCase):
    """GREEN before and after -- every shape this rule must leave alone."""

    def _two_voice_66_build(self):
        log = Log()
        meter = _meter(log, 6, 8)
        _voices(log, LOWER_CELL, 2)
        _voices(log, UPPER_CELL, 2)
        return log, meter

    def test_not_refused_at_all_is_untouched(self):
        log, meter = self._two_voice_66_build()
        sub = R.glyph(PAGE, SYSTEM, LOWER_STAFF, CELL_IDX, 0)
        _v(log, sub, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, False,
           reason="rest")
        self.assertEqual(_fire(log, sub, meter), [])

    def test_refused_for_a_DIFFERENT_reason_is_untouched(self):
        log, meter = self._two_voice_66_build()
        sub = R.glyph(PAGE, SYSTEM, LOWER_STAFF, CELL_IDX, 0)
        _v(log, sub, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, True,
           reason="rest_has_a_stem")
        log.observe(sub, Q.GLYPH_BAND_DISTANCE, 3.2, reader=READERS.GEOMETRY,
                   frame="page", candidate=UPPER_KEY, own=False)
        self.assertEqual(_fire(log, sub, meter), [])

    def test_no_contest_at_all_is_untouched(self):
        log, meter = self._two_voice_66_build()
        sub = R.glyph(PAGE, SYSTEM, LOWER_STAFF, CELL_IDX, 0)
        _v(log, sub, Q.DURATION, Outcome.DECIDED, _dur(0.5))
        _v(log, sub, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, True,
           reason="rest_outside_its_staff")
        self.assertEqual(_fire(log, sub, meter), [])

    def test_voice_count_undecided_is_untouched(self):
        """No `Q.VOICES` and no `Q.STEM_DIRECTION` at all on the own staff:
        rule 8 -- never assume a voice count nobody gave."""
        log = Log()
        meter = _meter(log, 6, 8)
        n = _decided_duration(log, LOWER_STAFF, 0, 4.5)
        rest = _refused_rest(log, LOWER_STAFF, 1, 0.5,
                             other_staff_key=UPPER_KEY, own_key=LOWER_KEY)
        _events(log, LOWER_CELL, [n], [rest])
        _voices(log, UPPER_CELL, 2)
        self.assertEqual(_fire(log, rest, meter), [])

    def test_both_staves_already_complete_is_untouched(self):
        """A duplicate detection of a rest that genuinely belongs to ONE
        staff which already accounts for it in full at its own voice count:
        neither staff is short, so nothing should be guessed."""
        log, meter = self._two_voice_66_build()
        n_lo = _decided_duration(log, LOWER_STAFF, 0, 6.0)   # complete
        lo_rest = _refused_rest(log, LOWER_STAFF, 1, 0.5,
                                other_staff_key=UPPER_KEY, own_key=LOWER_KEY)
        _events(log, LOWER_CELL, [n_lo], [lo_rest])
        n_up = _decided_duration(log, UPPER_STAFF, 0, 6.0)   # complete
        up_rest = _refused_rest(log, UPPER_STAFF, 1, 0.5,
                                other_staff_key=LOWER_KEY, own_key=UPPER_KEY)
        _events(log, UPPER_CELL, [n_up], [up_rest])
        self.assertEqual(_fire(log, lo_rest, meter), [])
        self.assertEqual(_fire(log, up_rest, meter), [])

    def test_both_staves_missing_something_is_untouched(self):
        """The lower staff's own shortfall matches the group's length, but
        the candidate (upper) staff is NOT itself complete -- genuinely
        ambiguous, rule 8."""
        log, meter = self._two_voice_66_build()
        n_lo = _decided_duration(log, LOWER_STAFF, 0, 4.5)   # short by 1.5
        lo_rest = _refused_rest(log, LOWER_STAFF, 1, 0.5,
                                other_staff_key=UPPER_KEY, own_key=LOWER_KEY)
        _events(log, LOWER_CELL, [n_lo], [lo_rest])
        n_up = _decided_duration(log, UPPER_STAFF, 0, 5.0)   # short by 1.0,
        up_rest = _refused_rest(log, UPPER_STAFF, 1, 0.5,            # not 0
                                other_staff_key=LOWER_KEY, own_key=UPPER_KEY)
        _events(log, UPPER_CELL, [n_up], [up_rest])
        self.assertEqual(_fire(log, lo_rest, meter), [])

    def test_shortfall_does_not_match_the_groups_own_length(self):
        """The own staff IS short, but not by exactly the group's own
        length -- something else is wrong in the bar, and this rule only
        ever closes the gap its own missing ink explains."""
        log, meter = self._two_voice_66_build()
        n_lo = _decided_duration(log, LOWER_STAFF, 0, 4.0)   # short by 2.0,
        lo_rest = _refused_rest(log, LOWER_STAFF, 1, 0.5,       # not 0.5
                                other_staff_key=UPPER_KEY, own_key=LOWER_KEY)
        _events(log, LOWER_CELL, [n_lo], [lo_rest])
        n_up = _decided_duration(log, UPPER_STAFF, 0, 6.0)
        up_rest = _refused_rest(log, UPPER_STAFF, 1, 0.5,
                                other_staff_key=LOWER_KEY, own_key=UPPER_KEY)
        _events(log, UPPER_CELL, [n_up], [up_rest])
        self.assertEqual(_fire(log, lo_rest, meter), [])

    def test_candidate_staffs_own_bar_is_undecided(self):
        log, meter = self._two_voice_66_build()
        n_lo = _decided_duration(log, LOWER_STAFF, 0, 4.5)
        lo_rest = _refused_rest(log, LOWER_STAFF, 1, 0.5,
                                other_staff_key=UPPER_KEY, own_key=LOWER_KEY)
        _events(log, LOWER_CELL, [n_lo], [lo_rest])
        # No Q.EVENT / Q.DURATION at all on UPPER_CELL.
        self.assertEqual(_fire(log, lo_rest, meter), [])

    def test_no_meter_is_untouched(self):
        log = Log()
        _voices(log, LOWER_CELL, 2)
        _voices(log, UPPER_CELL, 2)
        n_lo = _decided_duration(log, LOWER_STAFF, 0, 4.5)
        lo_rest = _refused_rest(log, LOWER_STAFF, 1, 0.5,
                                other_staff_key=UPPER_KEY, own_key=LOWER_KEY)
        _events(log, LOWER_CELL, [n_lo], [lo_rest])
        undecided = _v(log, R.system(PAGE, SYSTEM), Q.METER,
                       Outcome.ABSTAINED, None, reason="carry_not_corroborated")
        self.assertEqual(_fire(log, lo_rest, undecided), [])

    def test_a_whole_rest_twin_kept_on_its_own_staff_is_untouched(self):
        """One copy KEPT (not refused) on the staff it truly belongs to, the
        other copy refused on the neighbour -- but the neighbour's own bar
        is already complete without it, so nothing fires. Mirrors 2.33b's
        '8 whole rests kept on their own staff' shape."""
        log, meter = self._two_voice_66_build()
        kept = R.glyph(PAGE, SYSTEM, LOWER_STAFF, CELL_IDX, 0)
        _v(log, kept, Q.DURATION, Outcome.DECIDED, _dur(6.0))
        _v(log, kept, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, False,
           reason="rest")
        _events(log, LOWER_CELL, [kept])
        n_up = _decided_duration(log, UPPER_STAFF, 0, 6.0)  # already whole
        ghost = _refused_rest(log, UPPER_STAFF, 1, 6.0,
                              other_staff_key=LOWER_KEY, own_key=UPPER_KEY)
        _events(log, UPPER_CELL, [n_up], [ghost])
        self.assertEqual(_fire(log, ghost, meter), [])

    def test_rest_duration_not_decided_is_untouched(self):
        log, meter = self._two_voice_66_build()
        n_lo = _decided_duration(log, LOWER_STAFF, 0, 4.5)
        sub = R.glyph(PAGE, SYSTEM, LOWER_STAFF, CELL_IDX, 1)
        _v(log, sub, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, True,
           reason="rest_outside_its_staff")
        log.observe(sub, Q.GLYPH_BAND_DISTANCE, 3.2, reader=READERS.GEOMETRY,
                   frame="page", candidate=UPPER_KEY, own=False)
        # No Q.DURATION for `sub` at all.
        _events(log, LOWER_CELL, [n_lo], [sub])
        n_up = _decided_duration(log, UPPER_STAFF, 0, 6.0)
        _events(log, UPPER_CELL, [n_up])
        self.assertEqual(_fire(log, sub, meter), [])


if __name__ == "__main__":
    unittest.main()
