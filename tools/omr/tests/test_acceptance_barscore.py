"""Fast unit tests for `tools.omr.acceptance_barscore` (ROADMAP 1.6).

No score PDF, no shared record, no library file — every fixture is an
inline MusicXML `<part>` fragment built from a literal string. CLAUDE.md
§6c: a fast test file must not name a `library/`, `omr-weights` or a
venv/`.pdf"` path, or the whole file goes slow silently; there is nothing
of the kind here.

CLAUDE.md rule 7 ("a control must be able to fail"): the SELF control scores
a part against an unmodified copy of itself and must come back all
`matched_exact`; the CORRUPTED control shifts one bar's pitches a step and
must come back flagged `pitch_wrong` in EXACTLY that bar, nowhere else —
proving the scorer can and does fail where it should.
"""
import unittest
import xml.etree.ElementTree as ET
from fractions import Fraction

from tools.omr.acceptance_barscore import (
    Event, align_and_score, parse_part_bars, score_bar, sum_scores,
)


def _part(xml_fragment: str):
    return ET.fromstring(f"<part id='P1'>{xml_fragment}</part>")


def _note(step, alter, octave, duration, *, chord=False, voice="1", rest=False):
    chord_tag = "<chord/>" if chord else ""
    if rest:
        pitch = "<rest/>"
    else:
        alter_tag = f"<alter>{alter}</alter>" if alter else ""
        pitch = f"<pitch><step>{step}</step>{alter_tag}<octave>{octave}</octave></pitch>"
    return (f"<note>{chord_tag}{pitch}<duration>{duration}</duration>"
            f"<voice>{voice}</voice></note>")


TWO_BAR_PART = _part(f"""
<measure number="1">
  <attributes><divisions>4</divisions></attributes>
  {_note('C', 0, 4, 4)}
  {_note('E', 0, 4, 4)}
</measure>
<measure number="2">
  {_note('F', 0, 4, 2)}
  {_note('A', 0, 4, 2, chord=True)}
  {_note('G', 0, 4, 4)}
</measure>
""")


def _shift_pitch(events, from_bar, semitone_step_shift=1):
    """A copy of a bar->events dict with every pitch in `from_bar` moved up
    one diatonic step (C->D, E->F, F->G, G->A, A->B) — the corrupted
    control. Duration and onset are UNCHANGED, so the only thing that can
    flip is pitch_wrong."""
    ladder = {"C": "D", "D": "E", "E": "F", "F": "G", "G": "A", "A": "B", "B": "C"}
    out = dict(events)
    new_list = []
    for e in events[from_bar]:
        if e.pitch is None:
            new_list.append(e)
            continue
        step = e.pitch[0]
        rest = e.pitch[1:]
        new_list.append(Event(e.onset, e.duration, ladder[step] + rest, e.voice))
    out[from_bar] = new_list
    return out


class TestParsePartBars(unittest.TestCase):
    def test_onsets_and_chord(self):
        bars = parse_part_bars(TWO_BAR_PART)
        self.assertEqual(set(bars), {"1", "2"})
        b1 = bars["1"]
        self.assertEqual(len(b1), 2)
        self.assertEqual(b1[0].onset, Fraction(0))
        self.assertEqual(b1[1].onset, Fraction(1))  # quarter, divisions=4 -> 4/4=1
        b2 = bars["2"]
        # F (onset 0), A chord on F (onset 0 too), G (onset 1/2)
        self.assertEqual(b2[0].onset, Fraction(0))
        self.assertEqual(b2[1].onset, Fraction(0))
        self.assertEqual(b2[2].onset, Fraction(1, 2))

    def test_rest_has_no_pitch(self):
        part = _part(f"""<measure number="1">
          <attributes><divisions>4</divisions></attributes>
          {_note('', '', '', 4, rest=True)}
        </measure>""")
        bars = parse_part_bars(part)
        self.assertIsNone(bars["1"][0].pitch)


class TestScoreBarSelfControl(unittest.TestCase):
    """CLAUDE.md rule 7: score the reference against ITSELF first."""

    def test_identical_part_scores_all_matched(self):
        bars = parse_part_bars(TWO_BAR_PART)
        for bar_num, events in bars.items():
            score = score_bar(events, events)
            self.assertEqual(score.pitch_wrong, 0, bar_num)
            self.assertEqual(score.duration_wrong, 0, bar_num)
            self.assertEqual(score.missing, 0, bar_num)
            self.assertEqual(score.extra, 0, bar_num)
            n_notes = sum(1 for e in events if e.pitch is not None)
            self.assertEqual(score.matched_exact, n_notes, bar_num)
            self.assertEqual(score.ref_n, n_notes)
            self.assertEqual(score.our_n, n_notes)


class TestScoreBarCorruptedControl(unittest.TestCase):
    """The control that can FAIL: shift one bar's pitches a step and
    require the scorer to flag exactly that bar, and nothing else."""

    def test_shifted_bar_is_flagged_pitch_wrong_only_there(self):
        ref_bars = parse_part_bars(TWO_BAR_PART)
        corrupted_bars = _shift_pitch(ref_bars, "2")

        score_1 = score_bar(ref_bars["1"], corrupted_bars["1"])
        self.assertEqual(score_1.pitch_wrong, 0)
        self.assertEqual(score_1.matched_exact, 2)

        score_2 = score_bar(ref_bars["2"], corrupted_bars["2"])
        n_notes_bar2 = sum(1 for e in ref_bars["2"] if e.pitch is not None)
        self.assertEqual(score_2.matched_exact, 0)
        self.assertEqual(score_2.pitch_wrong, n_notes_bar2)
        self.assertEqual(score_2.missing, 0)
        self.assertEqual(score_2.extra, 0)
        self.assertEqual(score_2.duration_wrong, 0)

    def test_duration_only_change_is_duration_wrong_not_pitch_wrong(self):
        ref_bars = parse_part_bars(TWO_BAR_PART)
        our_events = [Event(e.onset, e.duration * 2, e.pitch, e.voice)
                     for e in ref_bars["1"]]
        score = score_bar(ref_bars["1"], our_events)
        self.assertEqual(score.duration_wrong, 2)
        self.assertEqual(score.pitch_wrong, 0)
        self.assertEqual(score.matched_exact, 0)

    def test_missing_and_extra(self):
        ref_events = [Event(Fraction(0), Fraction(1), "C+04", "1")]
        our_events: list = []
        score = score_bar(ref_events, our_events)
        self.assertEqual(score.missing, 1)
        self.assertEqual(score.extra, 0)

        score2 = score_bar([], ref_events)
        self.assertEqual(score2.missing, 0)
        self.assertEqual(score2.extra, 1)


class TestAlignAndScoreSkipsHeldBars(unittest.TestCase):
    """A bar the exporter held out, or that one side has no measure for at
    all (a condensed staff, a suppressed tacet staff), must be SKIPPED, not
    scored as a clean 0-for-0 — CLAUDE.md rule 8."""

    def test_held_out_bar_is_skipped_not_scored(self):
        ref_bars = parse_part_bars(TWO_BAR_PART)
        our_bars = parse_part_bars(TWO_BAR_PART)
        scores, skipped = align_and_score(
            ref_bars, our_bars, ["1", "2"], held_out={"2"})
        self.assertEqual(set(scores), {"1"})
        self.assertEqual(skipped, ["2"])

    def test_bar_absent_from_one_side_is_skipped(self):
        ref_bars = parse_part_bars(TWO_BAR_PART)
        our_bars = {"1": ref_bars["1"]}  # bar 2 never exported (e.g. a
                                        # suppressed staff / condensed part)
        scores, skipped = align_and_score(ref_bars, our_bars, ["1", "2"])
        self.assertEqual(set(scores), {"1"})
        self.assertEqual(skipped, ["2"])

    def test_bar_with_no_notes_on_either_side_is_skipped(self):
        ref_bars = {"1": [Event(Fraction(0), Fraction(4), None, "1")]}  # rest only
        our_bars = {"1": [Event(Fraction(0), Fraction(4), None, "1")]}
        scores, skipped = align_and_score(ref_bars, our_bars, ["1"])
        self.assertEqual(scores, {})
        self.assertEqual(skipped, ["1"])

    def test_bar_with_notes_on_only_one_side_is_scored_not_skipped(self):
        # a genuine miss (ref has a note, ours has none at all) must SHOW UP
        # as missing, never be swallowed as "not comparable"
        ref_bars = {"1": [Event(Fraction(0), Fraction(4), "C+04", "1")]}
        our_bars = {"1": [Event(Fraction(0), Fraction(4), None, "1")]}  # rest
        scores, skipped = align_and_score(ref_bars, our_bars, ["1"])
        self.assertEqual(skipped, [])
        self.assertEqual(scores["1"].missing, 1)


class TestSumScores(unittest.TestCase):
    def test_sums_every_field(self):
        a = score_bar([Event(Fraction(0), Fraction(1), "C+04", "1")],
                      [Event(Fraction(0), Fraction(1), "C+04", "1")])
        b = score_bar([Event(Fraction(0), Fraction(1), "C+04", "1")], [])
        total = sum_scores([a, b])
        self.assertEqual(total.ref_n, 2)
        self.assertEqual(total.our_n, 1)
        self.assertEqual(total.matched_exact, 1)
        self.assertEqual(total.missing, 1)


if __name__ == "__main__":
    unittest.main()
