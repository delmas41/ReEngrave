"""The end-to-end fixtures must say what they claim to say.

These check the TRUTH side only — that the authored scores contain the notes
the benchmark believes they contain. They need no LilyPond and no PDF, so they
run in the normal suite; the rendering and scoring half needs `lilypond` and
`musicxml2ly` and lives in `tools/omr/training/end_to_end_eval.py`.

Worth having because the whole benchmark rests on the fixtures being right: if
the truth is wrong, every number derived from it is wrong in a way no amount of
staring at the pipeline would reveal.
"""

from __future__ import annotations

import pytest

from music21 import spanner

from tools.omr.training.e2e_fixtures import (
    FIXTURES, build_ensemble, build_keyboard, build_systems,
)


EXPECTED_NOTES = {"melody": 24, "keyboard": 27, "ensemble": 45, "systems": 73}
EXPECTED_PARTS = {"melody": 1, "keyboard": 2, "ensemble": 4, "systems": 4}


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_fixture_note_count(name):
    score = FIXTURES[name]()
    pitches = sum(len(n.pitches) for n in score.flatten().notes)
    assert pitches == EXPECTED_NOTES[name]


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_fixture_part_count(name):
    assert len(list(FIXTURES[name]().parts)) == EXPECTED_PARTS[name]


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_every_measure_is_a_full_bar(name):
    """Four quarter notes to the bar, everywhere. A short bar would make the
    duration score meaningless."""
    for part in FIXTURES[name]().parts:
        for measure in part.getElementsByClass("Measure"):
            total = sum(n.duration.quarterLength for n in measure.notes)
            assert total == pytest.approx(4.0), f"{name}: bar {measure.number} = {total}"


def test_eighths_are_beamed():
    """Unbeamed eighths would never exercise the beam path — and one fixture
    silently lost its beams when the meter sat at part level instead of in the
    first measure."""
    for name in ("melody", "keyboard", "ensemble"):
        eighths = [n for n in FIXTURES[name]().flatten().notes
                   if n.duration.quarterLength == 0.5]
        assert eighths, f"{name} has no eighth notes"
        beamed = [n for n in eighths if n.beams and n.beams.beamsList]
        assert len(beamed) == len(eighths), f"{name}: {len(beamed)}/{len(eighths)} beamed"


def test_ensemble_is_open_score_not_a_grand_staff():
    """The point of `ensemble` is four independent staves — barline detection
    behaves differently there than on a braced pair."""
    assert len(list(build_ensemble().parts)) == 4
    assert len(list(build_keyboard().parts)) == 2


def test_ensemble_carries_a_c_clef():
    from music21 import clef
    clefs = [c for p in build_ensemble().parts for c in p.flatten().getElementsByClass(clef.Clef)]
    assert any(isinstance(c, clef.AltoClef) for c in clefs)


class TestSystemsFixture:
    """`systems` is the only fixture with a system break, and the only place a
    cross-system slur can be measured at all. If its slurs stop crossing
    barlines it silently stops testing the thing it exists for."""

    def test_it_is_eight_bars_so_the_page_takes_two_systems(self):
        for part in build_systems().parts:
            assert len(list(part.getElementsByClass("Measure"))) == 8

    def test_two_parts_are_slurred_ACROSS_THE_SYSTEM_BREAK(self):
        """Bar 4 is the last of system 1 and bar 5 the first of system 2, so a
        (3 -> 4) span in 0-indexed bars is the case this fixture exists for.
        Two parts carry one so a single detection failure does not empty the
        measurement."""
        score = build_systems()
        crossing = 0
        for part in list(score.parts)[:2]:
            bars = list(part.getElementsByClass("Measure"))
            for slur in part.getElementsByClass(spanner.Slur):
                first, last = slur.getSpannedElements()[0], slur.getSpannedElements()[-1]
                # IDENTITY, not `in`: music21 compares notes by value, so two
                # same-pitch notes in different bars are equal and `in` finds
                # the wrong bar.
                b0 = next(i for i, b in enumerate(bars)
                          if any(n is first for n in b.notes))
                b1 = next(i for i, b in enumerate(bars)
                          if any(n is last for n in b.notes))
                if (b0, b1) == (3, 4):
                    crossing += 1
        assert crossing == 2

    def test_the_notes_either_side_of_the_break_are_half_notes(self):
        """Unbeamable by construction. With quarter notes there the slur arc
        was read as a beam and the bars stopped summing to four, which made the
        fixture measure rhythm rather than slurs — musicdiff prices a slur by
        the duration it SPANS, so a misread note is charged as a wrong slur."""
        for part in list(build_systems().parts)[:2]:
            bars = list(part.getElementsByClass("Measure"))
            assert list(bars[3].notes)[-1].quarterLength == 2.0
            assert list(bars[4].notes)[0].quarterLength == 2.0

    def test_the_bass_carries_no_cross_barline_slur(self):
        """A part that must NOT gain one, so a rule that over-merges shows up."""
        part = list(build_systems().parts)[3]
        bars = list(part.getElementsByClass("Measure"))
        for slur in part.getElementsByClass(spanner.Slur):
            first, last = slur.getSpannedElements()[0], slur.getSpannedElements()[-1]
            b0 = next(i for i, b in enumerate(bars)
                      if any(n is first for n in b.notes))
            b1 = next(i for i, b in enumerate(bars)
                      if any(n is last for n in b.notes))
            assert b0 == b1

    def test_the_staves_are_bracketed_with_barlines_run_through(self):
        """System grouping decides what belongs to one system by CONNECTIVITY.
        Without the StaffGroup LilyPond draws each staff its own barlines and
        the second system came back as four one-staff systems."""
        from music21 import layout
        groups = list(build_systems().getElementsByClass(layout.StaffGroup))
        assert len(groups) == 1
        assert groups[0].barTogether is True
