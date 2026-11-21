"""ROADMAP 2.319 (STAGED ADJUDICATE + EXPORT): ONE READER DECIDES BEAMS END TO END.

The rule, as a musician says it: a beam joins the stems whose ink it meets; the notes whose stems hang on one beam are one group, and a flag
hangs on its own stem and is never in a beam group. Both sides of each boundary are pinned on REAL stroke rows (`fixtures/one_beam_reader_2_319`,
the cells of the frozen-sample records of 2026-11-21; truth is the print at 600 dpi, our look) and on Sean's 24 judged beam tiles plus Litolff
p2 bar 13 (`fixtures/one_beam_count_2_318`, his 2.317 answers):

* a stem ends at its beam even where the scan runs its ink on into an `ff` the letter's claim refused (Litolff p16 1/7/2, middle chord);
* a stem piece an `ff`'s box took, touching none of the letter's ink and running to the beam, is the stem's (p16 1/7/2, first chord) -- never a
  piece that touches the letter's ink;
* a line that runs out of the bar at both ends is never a beam (Brahms p25 0/2/1: flagged eighths over the next staff's top line) -- never a
  stroke that ends inside the bar;
* notes share a group only where their stems share beam ink (p16 0/8/15: a flagged eighth, then three beamed); a flagged note carries none.

`TestTheControlCanFail` switches each 2.319 rule off and shows its note read wrong."""
from __future__ import annotations

import json
import pathlib
from unittest import mock

import pytest

from tools.omr.staged import beam_strokes as BS
from tools.omr.staged import export as E

HERE = pathlib.Path(__file__).parent / "fixtures"
NOTES = json.loads((HERE / "one_beam_reader_2_319" / "controls.json").read_text())["notes"]
SEAN = json.loads((HERE / "one_beam_count_2_318" / "controls.json").read_text())["notes"]


def views(note):
    ow = note["owner"] or {}
    mask = {int(o): "owned" for o in ow.get("owned", ())}
    mask.update({int(o): "contested" for o in ow.get("contested", ())})
    out = []
    for s in note["strokes"]:
        b = s["box"]
        if not b or len(b) < 4:
            continue
        out.append(BS.StrokeView(
            ordinal=s["ord"], kind=mask.get(s["ord"], str(s["kind"])), box=tuple(float(v) for v in b[:4]), length=float(s["len"] or 0),
            thickness=float(s["th"] or 0), sagitta=s["sag"], angle=float(s["ang"] or 0),
            touches=tuple((int(a), float(c)) for a, c in (s["touches"] or ())), space_px=float(s["sp"] or 0), row_id=s["id"],
            profile=tuple(int(v) for v in (s["prof"] or ())), ends=tuple(float(v) for v in (s["ends"] or ())[:4]),
            end_steps=tuple(float(v) for v in (s.get("steps") or ())[:2]), cut=str(s.get("cut") or ""), family=str(s.get("fam") or "")))
    return out


def count(note):
    vs = views(note)
    roles = BS.roles(vs, face_join=True, trough=True, one_count=True)
    return BS.beam_count(vs, roles, tuple(float(x) for x in note["head"]), note["side"] if note["side"] in ("up", "down") else None)


def ink(note):
    """The beam ink the note's stem hangs on, by stroke row id (what `rhythm._one_beam_count` files as `beam_strokes`)."""
    got = count(note)
    by = {s["ord"]: s["id"] for s in note["strokes"]}
    return frozenset(by[o] for st in got["stems"] for o in st.get("beam_ink") or ())


@pytest.mark.parametrize("glyph", sorted(NOTES))
def test_the_count_reads_the_print(glyph):
    got = count(NOTES[glyph])
    assert got["state"] == "read" and got["certain"] == NOTES[glyph]["truth"], (glyph, got["state"], got["certain"], got["possible"])


@pytest.mark.parametrize("glyph", sorted(NOTES))
def test_a_note_carries_beam_ink_exactly_when_it_is_beamed(glyph):
    assert bool(ink(NOTES[glyph])) == (NOTES[glyph]["group"] != "-")


def _in_order(prefix):
    keys = [g for g in NOTES if g.startswith(prefix)]
    return sorted(keys, key=lambda g: NOTES[g]["head"][0])


def test_the_three_chords_over_the_ff_are_one_group():
    # one head per chord, left to right (7, 3, 1; their partners 10, 5, 6 share the stem)
    chords = ["glyph/16/1/7/2/7", "glyph/16/1/7/2/3", "glyph/16/1/7/2/1"]
    inks = [ink(NOTES[g]) for g in chords]
    assert E.groups_sharing_beam_ink([1, 1, 1], inks) == [[0, 1, 2]]
    for a, b in (("glyph/16/1/7/2/7", "glyph/16/1/7/2/10"), ("glyph/16/1/7/2/3", "glyph/16/1/7/2/5"), ("glyph/16/1/7/2/1", "glyph/16/1/7/2/6")):
        assert ink(NOTES[a]) == ink(NOTES[b])          # every head on one stem hangs on the same beam


def test_a_flagged_eighth_before_three_beamed_stays_out_of_the_group():
    order = _in_order("glyph/16/0/8/15/")
    assert order[0] == "glyph/16/0/8/15/2"             # the flagged one is first on the page
    inks = [ink(NOTES[g]) for g in order]
    assert E.groups_sharing_beam_ink([1] * len(order), inks) == [[1, 2, 3]]


def test_flagged_eighths_over_the_next_staffs_line_make_no_group():
    order = _in_order("glyph/25/0/2/1/")
    assert E.groups_sharing_beam_ink([1] * len(order), [ink(NOTES[g]) for g in order]) == []


def test_sean_bar_13_four_eighths_are_one_group():
    order = sorted((g for g in SEAN if g.startswith("glyph/2/1/7/13/")), key=lambda g: SEAN[g]["head"][0])
    assert len(order) == 4
    assert E.groups_sharing_beam_ink([1] * 4, [ink(SEAN[g]) for g in order]) == [[0, 1, 2, 3]]


@pytest.mark.parametrize("glyph", sorted(g for g in SEAN if SEAN[g]["truth"] == 0))
def test_sean_quarters_carry_no_beam_ink(glyph):
    assert not ink(SEAN[glyph]), glyph


@pytest.mark.parametrize("glyph", sorted(g for g in SEAN if (SEAN[g]["truth"] or 0) >= 1))
def test_sean_beamed_notes_hang_on_beam_ink(glyph):
    got = count(SEAN[glyph])
    if got["certain"] >= 1:
        assert ink(SEAN[glyph]), glyph


def test_groups_never_join_across_a_flag_or_a_rest_and_never_a_lone_note():
    a, b = frozenset({"s1"}), frozenset({"s2"})
    assert E.groups_sharing_beam_ink([1, 1, 1, 1], [a, frozenset(), a, a]) == [[2, 3]]          # a flagged note (no ink) breaks the run
    assert E.groups_sharing_beam_ink([1, 0, 1], [a, a, a]) == []                                # a rest breaks it; runs of one are no group
    assert E.groups_sharing_beam_ink([1, 1, 1, 1], [a, a, b, b]) == [[0, 1], [2, 3]]            # two beams side by side: two groups
    assert E.groups_sharing_beam_ink([2, 1, 1], [a, a | b, b]) == [[0, 1, 2]]                   # ink shared neighbour to neighbour


class TestTheControlCanFail:
    def test_without_the_letter_step_the_middle_chord_reads_no_beam(self):
        with mock.patch.object(BS, "LETTER_INK_ONE_STEP", False):
            assert count(NOTES["glyph/16/1/7/2/3"])["certain"] == 0

    def test_without_reading_through_the_letters_claim_the_first_chord_reads_no_beam(self):
        with mock.patch.object(BS, "STEM_PIECE_A_LETTER_TOOK", False):
            assert count(NOTES["glyph/16/1/7/2/7"])["certain"] == 0

    def test_without_the_bar_rule_the_flagged_eighths_read_a_beam_and_group(self):
        with mock.patch.object(BS, "BEAM_WITHIN_ONE_BAR", False):
            order = _in_order("glyph/25/0/2/1/")
            assert count(NOTES["glyph/25/0/2/1/0"])["certain"] == 1
            assert E.groups_sharing_beam_ink([1] * len(order), [ink(NOTES[g]) for g in order]) != []

    def test_a_piece_that_touches_the_letters_ink_is_never_read_as_the_stem(self):
        note = NOTES["glyph/16/1/7/2/7"]
        vs = views(note)
        piece = next(v for v in vs if v.ordinal == 19)
        letter = next(v for v in vs if v.kind == "owned" and v.family == "dynamic" and v.ordinal != 19)
        touched = piece.__class__(**{**piece.__dict__, "touches": piece.touches + ((letter.ordinal, 1.0),)})
        vs2 = [touched if v.ordinal == 19 else v for v in vs]
        assert not BS._stem_piece_a_letter_took(vs2, touched, "down")
        assert BS._stem_piece_a_letter_took(vs, piece, "down")
