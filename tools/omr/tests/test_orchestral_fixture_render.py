"""The fixture render must carry what the truth claims — `_restore_rest_fermatas`.

`musicxml2ly` drops every fermata that sits on a rest, and on the Beethoven
excerpt that left 22 of the truth's 36 fermatas off the page — 105 edits
charged against ink that was never printed, to a perfect reader too. The
fixture pipeline now splits the generated `R2*8` runs at the fermata bars and
attaches `\\fermata` there. These tests pin the splitting itself, because its
one real hazard is silent: a fermata placed on the WRONG bar still renders,
still counts, and still scores — it just measures a different page than the
truth describes.
"""
import pytest

from tools.omr.training.orchestral_eval import (
    _patch_block,
    _restore_rest_fermatas,
)

# The shape musicxml2ly actually generates: a bar check at the end of the
# HEADER, labelled `% 1`, before any music has sounded. A counter that
# advances on every `|` reads the whole block one measure late — the
# regression that put Flute 1's fermata on bar 1.
HEADER = '\\clef "treble" \\time 2/4 \\key es \\major | % 1\n    '


def test_fermatas_split_a_full_block_run():
    body = HEADER + "R2*8 }"[:-1]
    out = _patch_block(body, [2, 5])
    assert "R2 R2\\fermata R2*2 R2\\fermata R2*3" in out


def test_header_bar_check_does_not_shift_the_count():
    # Bar 1 holds a note; the fermata belongs to bar 2. Without anchoring on
    # the `% n` comments, the header `|` pushes every ordinal up by one and
    # the fermata lands on the note bar's rest run at the wrong offset.
    body = HEADER + "c2 | % 2\n    R2*7 "
    out = _patch_block(body, [2])
    assert "R2\\fermata R2*6" in out


def test_markup_stays_on_the_first_piece():
    # Flute 1's `R2*8` carries the tempo markup; after the split it must stay
    # with bar 1, not drift to the last piece.
    body = HEADER + "R2*8 ^\\markup{ \\bold {Allegro con brio} } "
    out = _patch_block(body, [2, 5])
    assert ("R2 ^\\markup{ \\bold {Allegro con brio} } "
            "R2\\fermata R2*2 R2\\fermata R2*3") in out


def test_mixed_notes_and_runs_track_the_bar_comments():
    body = HEADER + ("R2*2 | % 3\n    c2 | % 4\n    d2 | % 5\n    R2*4 ")
    out = _patch_block(body, [2, 5])
    assert "R2 R2\\fermata |" in out
    assert "R2\\fermata R2*3" in out


def test_fraction_multiplier_survives_the_split():
    body = '\\time 5/8 | % 1\n    R1*5/8*4 '
    out = _patch_block(body, [2])
    assert "R1*5/8 R1*5/8\\fermata R1*5/8*2" in out


def test_a_target_outside_every_run_raises():
    body = HEADER + "c2 | % 2\n    d2 | % 3\n    R2*6 "
    with pytest.raises(RuntimeError, match="could not place"):
        _patch_block(body, [1])


def test_drifted_bar_comment_raises():
    # A missed bar check means every later ordinal is wrong; the comment
    # disagreeing with the counter is the only visible symptom.
    body = HEADER + "c2 d2 | % 3\n    R2*6 "
    with pytest.raises(RuntimeError, match="drifted"):
        _patch_block(body, [4])


def test_no_comments_at_all_refuses_to_guess():
    with pytest.raises(RuntimeError, match="anchor"):
        _patch_block("R2*8 ", [2])


def test_restore_addresses_blocks_by_part_order():
    ly = (
        "PartPOneVoiceOne =  \\relative c' {\n    " + HEADER + "R2*4 }\n\n"
        "PartPOneVoiceOneLyricsOne =  \\lyricmode { la la }\n\n"
        "PartPTwoVoiceOne =  \\relative c' {\n    " + HEADER + "R2*4 }\n"
    )
    out = _restore_rest_fermatas(ly, {1: [3]}, n_parts=2)
    one, two = out.split("PartPTwoVoiceOne")
    assert "\\fermata" not in one          # part 0 untouched, lyrics untouched
    assert "R2*2 R2\\fermata R2" in two    # part 1, bar 3


def test_restore_refuses_a_block_count_mismatch():
    ly = "PartPOneVoiceOne =  \\relative c' {\n    " + HEADER + "R2*4 }\n"
    with pytest.raises(RuntimeError, match="part blocks"):
        _restore_rest_fermatas(ly, {0: [2]}, n_parts=2)
