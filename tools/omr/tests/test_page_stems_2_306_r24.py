"""ROADMAP 2.306 r24 (round 8) -- heads the old cell join still decided, read by the page stem reader from the ink (STAGED GATHER, inside
`OMR_PAGE_STEMS`, default OFF). Sean 2026-11-25 on the 36 tiles of these heads: "Aside from tile 5 that is boxing an ff the rest are all easily
seen as noteheads with stems" (`out/print/2.306-r24-old-join/answers.json`). Which stem each head is on is OUR look at the print.

Controls are REAL page windows cut from the reader's exact inputs pickled during an r23 gather (`benchmarks/page-ledger-2026-11/2306/
r23_cut_window.py`); each is shown failing with its rule switched off (CLAUDE rule 7), and the "never" side is real heads that must stay unresolved.

(1) A HEAD ON ITS CHORD PARTNER'S STEM (`_chord_stem`). Two half notes a third apart on one stem (Sean today, on the same figure: "two half notes,
    a third apart"): the partner stands on the long stroke and reads it the same way; the other stroke is the rings' side, running from this head
    to the partner, or shorter than a stem. Never where the other stroke is a stem's length leaving the pair (two voices).
(2) A STEM ENDS AT A NOTE (`_heads_a_stroke_can_end_at`). A stroke a stem's length that stops at a box with no head ink (on the beam, at the
    tip) is not that box's outline.
(3) A NOTE'S INK HOLDS ITS STROKE OVER A BOX AT THE TIP (`_free_from_tip_boxes`). Never for a head with no head ink of its own (tile 5, the ff).
(4) THE STROKE IT TOUCHES (`TOUCHED_HOW`): a stem joins the head whose ink it touches (Sean 2026-11-18); where the other stroke touches nothing
    of the head, holds no head and is shorter than a stem, the touched one is the stem. Never where the untouched stroke is a stem's length.
"""
import json
import os

import pytest

from tools.omr.staged import page_stems as PS

HERE = os.path.dirname(__file__)
WIN = os.path.join(HERE, "fixtures", "page_stems_2_306_r24.json")


def _read(name):
    w = json.load(open(WIN))[name]
    heads = [dict(h, box=tuple(h["box"])) for h in w["heads"]]
    verts = [dict(v, box=tuple(v["box"])) for v in w["verticals"]]
    cross = [dict(c, box=tuple(c["box"])) for c in w["crossers"]]
    strokes = {int(k): dict(v, box=tuple(v["box"])) for k, v in w["strokes"].items()}
    held = {int(k): v for k, v in w["held"].items()}
    return w, PS.read(heads, verts, held, crossers=cross, strokes=strokes)["heads"][w["head"]]


def _off(monkeypatch, *names):
    for n in names:
        monkeypatch.setattr(PS, n, False)


CHORD = ["chord_up_litolff_2_1_2_11_1", "chord_down_litolff_8_1_0_1_4", "chord_up_litolff_10_1_2_1_3", "chord_down_litolff_10_1_1_9_10",
         "chord_down_litolff_4_0_4_11_7"]


@pytest.mark.parametrize("name", CHORD)
def test_a_head_stands_on_the_stem_its_chord_partner_stands_on(name):
    """Our look (tiles 2, 9, 11, 10, 27 of `out/print/2.306-r24-old-join`): hollow heads a third apart on one stem; 4/0/4/11/7 the top head of a
    three-note chord on a down stem. The other stroke is the rings' side between the two heads (2.0-2.15 spaces: just past the r19 outline cut,
    which is left where it is -- the partner's own reading is the witness here, not a length)."""
    w, got = _read(name)
    assert got["state"] == "one" and got["how"] == PS.CHORD_HOW and got["direction"] == w["expect"], got


@pytest.mark.parametrize("name", CHORD)
def test_chord_rule_off_the_head_is_left_to_the_old_join(name, monkeypatch):
    _off(monkeypatch, "R24_CHORD_PARTNER")
    w, got = _read(name)
    assert got["state"] == "two_voices" and got["how"] == "two_voices", got


def test_a_stem_running_to_its_beam_does_not_end_at_the_box_there():
    """Litolff 2/0/7/1/5 (tile 1): a D5 eighth whose down stem runs 3.5 spaces to the beam, where a box with no head ink sits; the short up stroke
    at its right is the upper neighbour's ring side. Read down. Fails with the rule off (both strokes 'end at a head')."""
    w, got = _read("note_end_down_litolff_2_0_7_1_5")
    assert got["state"] == "one" and got["direction"] == "down", got


@pytest.mark.parametrize("name", ["note_end_unison_litolff_6_0_3_7_1", "note_end_unison_brahms_5_1_5_0_7"])
def test_a_note_shared_by_two_voices_whose_stem_runs_to_a_box_on_its_beam(name):
    """Litolff 6/0/3/7/1 (tile 6): bassoon eighths beamed above on up stems and below on down stems; Brahms 5/1/5/0/7 (tile 14): a C4 eighth
    with a stem each way. Two voices sharing the note (page-facts, Sean 2026-10-10)."""
    w, got = _read(name)
    assert got["how"] == PS.UNISON_HOW and set(got["voices"]) == {"up", "down"}, got


@pytest.mark.parametrize("name", ["chord_up_litolff_2_1_2_11_1", "note_end_down_litolff_2_0_7_1_5", "note_end_unison_litolff_6_0_3_7_1",
                                  "note_end_unison_brahms_5_1_5_0_7"])
def test_stem_end_rule_off(name, monkeypatch):
    if name.startswith("chord"):
        pytest.skip("read by the chord rule")
    _off(monkeypatch, "R24_STEM_ENDS_AT_A_NOTE")
    w, got = _read(name)
    assert got["how"] == "two_voices" and got.get("why") == "ends_at_another_head", got


def test_a_notes_ink_holds_its_stem_over_a_box_at_the_beam(monkeypatch):
    """Litolff 6/0/8/12/1 (tile 8): a D4 eighth whose down stem runs to the beam; a box there with no head ink read the stroke as its own up
    stem. The note (its own oval) touches the stroke: it holds it. Fails with the rule off."""
    w, got = _read("tip_box_down_litolff_6_0_8_12_1")
    assert got["state"] == "one" and got["direction"] == "down", got
    _off(monkeypatch, "R24_NOTE_BEFORE_TIP_BOX")
    w, got = _read("tip_box_down_litolff_6_0_8_12_1")
    assert got["state"] != "one", got


@pytest.mark.parametrize("name", ["never_ff_litolff_4_1_7_4_18", "never_two_voices_brahms_8_0_3_1_10", "never_column_brahms_0_0_11_1_13"])
def test_never(name):
    """The other side. Litolff 4/1/7/4/18 (tile 5): Sean -- "boxing an ff", not a notehead; it has no head ink and must take no stem. Brahms
    8/0/3/1/10 (tile 34): two voices, the upper black quarter's up stem and this dotted half's down stem (the map misses the down stem's
    contact): the up stroke is the partner's, but the other stroke is a stem's length -- never a chord. Brahms 0/0/11/1/13 (tile 25): two voices
    in one column; left unresolved."""
    w, got = _read(name)
    assert got["state"] not in ("one", "second") and got["how"] != PS.UNISON_HOW, got


@pytest.mark.parametrize("name", ["touched_up_litolff_6_1_3_1_1", "touched_up_litolff_10_1_10_11_1"])
def test_the_stroke_the_head_touches_when_the_other_is_too_short_to_be_a_stem(name, monkeypatch):
    """Litolff 6/1/3/1/1 (tile 30, an A3 eighth, up stem to the beam; the untouched stroke at its left 2.3 spaces) and 10/1/10/11/1 (tile 33,
    an Ab2 eighth on the bottom line, up stem to the beam; a 1.8-space piece below). Fails with the rule off (r23 left both `one_touches`)."""
    w, got = _read(name)
    assert got["state"] == "one" and got["how"] == PS.TOUCHED_HOW and got["direction"] == w["expect"], got
    _off(monkeypatch, "R24_ONLY_THE_TOUCHED")
    w, got = _read(name)
    assert got["state"] == "two_voices" and got.get("why") == "one_touches", got


def test_never_when_the_untouched_stroke_is_a_stems_length():
    """Litolff 8/1/2/1/1: a half note the old join wrote as two voices; the stroke it does not touch is a stem's length (3.4 spaces) -- it may
    be the second voice's stem whose contact the map missed. Left unresolved."""
    w, got = _read("never_untouched_is_a_stem_litolff_8_1_2_1_1")
    assert got["state"] == "two_voices" and got.get("why") == "one_touches", got
