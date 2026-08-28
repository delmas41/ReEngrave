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

from tools.omr.training.e2e_fixtures import FIXTURES, build_ensemble, build_keyboard


EXPECTED_NOTES = {"melody": 24, "keyboard": 27, "ensemble": 45}
EXPECTED_PARTS = {"melody": 1, "keyboard": 2, "ensemble": 4}


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
