"""ROADMAP 2.35 -- the rest beat-slot connection, the two forced sub-rules.

Sean, 2026-09-29 (quoted in full in `consequences.py`'s own module note):
*"based upon the other notes in a measure there will be a limited space
geometrically where the rest can be."* `Q.EVENT`, `Q.VOICES` and `Q.DURATION`
are all decided AFTER `Q.REST_IS_NOT_A_REST` in `adjudicate.ORDER`, so the two
pieces of this convention that FOLLOW without guessing are built as an
EVALUATE consequence (`consequences.rest_beat_slot`) that supersedes the
ADJUDICATE verdict, exactly as `apply_printed_accidental` already supersedes
`Q.ACCIDENTAL`:

  (A) a non-whole rest whose own box shares horizontal space with another
      event of its OWN VOICE -- no gap exists there -- is refused
      (`rest_shares_a_beat_slot`).
  (B) a non-whole rest whose voice's events strictly before it (by print
      position) already sum, in DECIDED beats, to the bar's own meter is
      refused (`rest_after_the_bar_ends`) -- there is no time left in the
      bar for it, which is what "the onset order its events imply" forces.

`rest_beat_slot` did not exist before this item: every test below is RED on
the unrepaired tree in the literal sense that `consequences.rest_beat_slot`
raises `AttributeError` there, and RED in the functional sense that commenting
out either check (confirmed by hand while writing this file) makes its own
test fail while leaving the other three classes (controls, abstentions,
already-refused) green.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import consequences
from tools.omr.staged import record as R
from tools.omr.staged.record import Candidate, Log, Outcome, Q, Verdict

CELL = R.cell(0, 0, 1, 3)
SYSTEM = R.system(0, 0)


def _v(log, sub, q, outcome, value, reason="t", detail=None, candidates=()):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome,
        value=value, decider="test", reason=reason, detail=detail or {},
        candidates=candidates))


def _box(log, gi, x0, w=20, y=0, h=16, cls="restQuarter"):
    """A `Q.GLYPH_BOX` OBSERVATION -- GATHER, not a verdict -- at (x0, y, w,
    h) in the cell's own canonical frame."""
    sub = R.glyph(0, 0, 1, 3, gi)
    log.observe(sub, Q.GLYPH_BOX, (cls, x0, y, w, h), reader="detector",
               frame="cell:3", score=0.9)
    return sub


def _rest(log, gi, x0, cls="restQuarter", w=20, refused=False,
         refuse_reason="rest_has_a_stem"):
    """A rest glyph: `Q.REST` observed, a box, and the ADJUDICATE-stage
    `Q.REST_IS_NOT_A_REST` verdict `size_measure_rest`'s own tests always
    seed by hand (`_whole_rest` in the sibling test file does the same)."""
    sub = _box(log, gi, x0, w=w, cls=cls)
    log.observe(sub, Q.REST, cls, reader="detector", frame="cell:3", score=0.9)
    _v(log, sub, Q.REST_IS_NOT_A_REST, Outcome.DECIDED,
       True if refused else False, reason=refuse_reason if refused else "rest")
    return sub


def _note(log, gi, x0, w=20, cls="noteheadBlack", beats=1.0, decided=True):
    sub = _box(log, gi, x0, w=w, cls=cls)
    if decided:
        _v(log, sub, Q.DURATION, Outcome.DECIDED,
           {"beats": beats, "written": beats, "dots": 0},
           reason="head_and_marks")
    else:
        _v(log, sub, Q.DURATION, Outcome.NARROWED, None, reason="beams_ambiguous",
           candidates=(Candidate({"beats": beats}, 2.0),
                       Candidate({"beats": beats / 2.0}, 1.0)))
    return sub


def _events(log, *entries):
    """`entries` is `(glyphs, x, kind)`. One DECIDED `Q.EVENT` for `CELL`."""
    return _v(log, CELL, Q.EVENT, Outcome.DECIDED,
             {"events": [{"glyphs": list(g), "x": x, "kind": k}
                        for g, x, k in entries]})


def _voices(log, streams):
    return _v(log, CELL, Q.VOICES, Outcome.DECIDED,
             {"n_voices": len(streams), "voices": [list(s) for s in streams],
              "rests_in_every_voice": [], "rests_displaced_by_position": {}})


def _meter(log, num=2, den=4):
    return _v(log, SYSTEM, Q.METER, Outcome.DECIDED,
             {"numerator": num, "denominator": den, "raw": f"{num}/{den}"})


def _fire(log, glyph, voices):
    return consequences.rest_beat_slot(log, glyph, voices)


class TestCheckA_Overlap(unittest.TestCase):
    """(A) -- RED on the unrepaired tree (the function does not exist)."""

    def test_a_rest_boxed_ON_TOP_OF_another_events_ink_is_refused(self):
        log = Log()
        note = _note(log, 0, x0=10, w=20)      # box [10, 30)
        rest = _rest(log, 1, x0=10, w=20)      # box [10, 30) -- SAME span
        _events(log, ([0], 20.0, "chord"), ([1], 20.0, "rest"))
        voices = _voices(log, [[0, 1]])
        out = _fire(log, rest, voices)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].value, True)
        self.assertEqual(out[0].reason, "rest_shares_a_beat_slot")
        self.assertEqual(out[0].supersedes,
                         log.verdicts(Q.REST_IS_NOT_A_REST, rest)[0].id)
        now = log.verdict(Q.REST_IS_NOT_A_REST, rest)
        self.assertIs(now.outcome, Outcome.DECIDED)
        self.assertTrue(now.value)


class TestCheckB_OnsetOverflow(unittest.TestCase):
    """(B) -- RED on the unrepaired tree."""

    def test_a_rest_after_its_voice_ALREADY_FILLED_THE_BAR_is_refused(self):
        log = Log()
        # 2/4: one note alone already uses the whole bar (2.0 beats).
        note = _note(log, 0, x0=0, w=20, beats=2.0)     # box [0, 20)
        rest = _rest(log, 1, x0=30, w=20)               # box [30, 50) -- clear
        _events(log, ([0], 10.0, "chord"), ([1], 40.0, "rest"))
        _meter(log, 2, 4)
        voices = _voices(log, [[0, 1]])
        out = _fire(log, rest, voices)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].reason, "rest_after_the_bar_ends")
        self.assertEqual(out[0].detail.get("onset_before_rest"), 2.0)
        self.assertEqual(out[0].detail.get("bar_beats"), 2.0)


class TestPositiveControls(unittest.TestCase):
    """Sean's own two: a legitimate rest is left standing."""

    def test_a_rest_in_a_REAL_GAP_with_room_left_in_the_bar_is_KEPT(self):
        log = Log()
        _meter(log, 2, 4)
        note = _note(log, 0, x0=0, w=20, beats=1.0)     # box [0, 20)
        rest = _rest(log, 1, x0=30, w=20)               # box [30, 50) -- gap
        _events(log, ([0], 10.0, "chord"), ([1], 40.0, "rest"))
        voices = _voices(log, [[0, 1]])
        self.assertEqual(_fire(log, rest, voices), [])
        self.assertFalse(log.verdict(Q.REST_IS_NOT_A_REST, rest).value)

    def test_a_DISPLACED_VOICE_2_rest_beside_a_voice_1_note_is_KEPT(self):
        """Two voices, and the rest's box touches the note's -- exactly the
        shape (A) would condemn in a single-voice bar. ROADMAP 2.27c's own
        convention (`Q.VOICES` itself) owns this case; this connection is
        scoped to a single voice and must not re-adjudicate it."""
        log = Log()
        _meter(log, 2, 4)
        note = _note(log, 0, x0=10, w=20, beats=1.0)    # box [10, 30)
        rest = _rest(log, 1, x0=10, w=20)               # box [10, 30) -- touches
        _events(log, ([0], 20.0, "chord"), ([1], 20.0, "rest"))
        voices = _voices(log, [[0], [1]])               # TWO voices
        self.assertEqual(_fire(log, rest, voices), [])
        self.assertFalse(log.verdict(Q.REST_IS_NOT_A_REST, rest).value)


class TestAbstains(unittest.TestCase):
    """Rule 8: voice membership or onsets not DECIDED -- never an answer."""

    def test_an_ABSTAINED_Q_VOICES_is_left_alone(self):
        log = Log()
        _meter(log, 2, 4)
        note = _note(log, 0, x0=0, w=20, beats=1.0)
        rest = _rest(log, 1, x0=10, w=20)                # would overlap IF read
        _events(log, ([0], 10.0, "chord"), ([1], 20.0, "rest"))
        undecided = _v(log, CELL, Q.VOICES, Outcome.ABSTAINED, None,
                       reason="no_voice_convention_fits")
        self.assertEqual(_fire(log, rest, undecided), [])
        self.assertFalse(log.verdict(Q.REST_IS_NOT_A_REST, rest).value)

    def test_a_NARROWED_neighbour_duration_leaves_the_onset_UNKNOWN(self):
        """No overlap (so (A) is silent); the note before the rest is
        NARROWED, so (B) cannot sum the bar and must not guess."""
        log = Log()
        _meter(log, 2, 4)
        note = _note(log, 0, x0=0, w=20, beats=1.0, decided=False)  # NARROWED
        rest = _rest(log, 1, x0=30, w=20)
        _events(log, ([0], 10.0, "chord"), ([1], 40.0, "rest"))
        voices = _voices(log, [[0, 1]])
        self.assertEqual(_fire(log, rest, voices), [])
        self.assertFalse(log.verdict(Q.REST_IS_NOT_A_REST, rest).value)

    def test_NO_METER_leaves_the_onset_UNKNOWN(self):
        log = Log()
        note = _note(log, 0, x0=0, w=20, beats=1.0)
        rest = _rest(log, 1, x0=30, w=20)
        _events(log, ([0], 10.0, "chord"), ([1], 40.0, "rest"))
        voices = _voices(log, [[0, 1]])
        undecided_meter = _v(log, SYSTEM, Q.METER, Outcome.ABSTAINED, None,
                             reason="carry_not_corroborated")
        self.assertEqual(_fire(log, rest, voices), [])
        self.assertFalse(log.verdict(Q.REST_IS_NOT_A_REST, rest).value)


class TestScopeAndSupersession(unittest.TestCase):
    """Never re-decides one already refused; a whole-bar rest is out of
    scope; the basis names the contest."""

    def test_an_ALREADY_REFUSED_rest_is_left_alone(self):
        log = Log()
        _meter(log, 2, 4)
        note = _note(log, 0, x0=0, w=20, beats=2.0)
        rest = _rest(log, 1, x0=0, w=20, refused=True,
                    refuse_reason="rest_has_a_stem")   # already refused
        _events(log, ([0], 10.0, "chord"), ([1], 10.0, "rest"))
        voices = _voices(log, [[0, 1]])
        self.assertEqual(_fire(log, rest, voices), [])
        self.assertEqual(log.verdict(Q.REST_IS_NOT_A_REST, rest).reason,
                         "rest_has_a_stem")

    def test_a_WHOLE_REST_is_OUT_OF_SCOPE_even_when_it_would_overlap(self):
        """ROADMAP 2.33 already owns `restWhole` (`rest_off_center`); this
        connection must not double-condemn it under a different reason."""
        log = Log()
        _meter(log, 2, 4)
        note = _note(log, 0, x0=0, w=20, beats=2.0)
        rest = _rest(log, 1, x0=0, w=20, cls="restWhole")   # overlaps `note`
        _events(log, ([0], 10.0, "chord"), ([1], 10.0, "rest"))
        voices = _voices(log, [[0, 1]])
        self.assertEqual(_fire(log, rest, voices), [])

    def test_the_basis_NAMES_the_contest(self):
        log = Log()
        note = _note(log, 0, x0=10, w=20)
        rest = _rest(log, 1, x0=10, w=20)
        events = _events(log, ([0], 20.0, "chord"), ([1], 20.0, "rest"))
        voices = _voices(log, [[0, 1]])
        out = _fire(log, rest, voices)
        self.assertEqual(len(out), 1)
        self.assertIn(voices.id, out[0].basis)
        self.assertIn(events.id, out[0].basis)
        prior = log.verdicts(Q.REST_IS_NOT_A_REST, rest)[0]
        self.assertIn(prior.id, out[0].basis)


if __name__ == "__main__":
    unittest.main()
