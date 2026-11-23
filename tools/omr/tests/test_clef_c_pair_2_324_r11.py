"""ROADMAP 2.324 r11 -- the opening C clef of a line read as a bass clef (overnight 20261122-night), STAGED GATHER (`clef_pagewide.c_bars`,
`_own_past_ink`, `read_header_ink`).

Sean 2026-11-23 (crops `out/print/overnight-1122-pitches/` B and C, nothing of ours drawn): "The first tile is all alto clef - The second
tile starts in tenor." B = Brahms p3 s1 staff 11 (viola), C = Brahms p17 s1 staff 3 (bassoon). Two more by our look (not judged): Brahms
p10 s1 staff 11 and Litolff p13 s0 staff 9 (violas, alto clef).

THE CAUSE. A C clef is two upright bars, a thick one and a thin one beside it, the same height, with two bowls right of them; a bass
clef is a ball and curve at the top line with two FREE dots in the two top spaces. Our C test refused the C clef's bars -- on Breitkopf a
scan nick in the thick bar's edge column took 1-2 columns off it, so it measured 1.8-2.2x its thin bar where the test asked 2.2x
(B, B2, C); on Litolff the ink past the staff that marks a treble clef's spine was another staff's treble tail above and the system's
thin barline below (D). With the C clef refused, its own UPPER BOWL fills both F-dot places (fills 0.96-1.0), and the F clef's never
"no F clef on a C clef's bar" looked only at bars the C test had accepted -- so B, B2 and D were read bass. C (tenor, a space higher)
failed the F body test and went unread; the staff was then decided bass downstream.

THE RULES (r11): a C clef's two bars stand side by side and run the same height, the thick one on the left -- never two strokes of
different heights, never a thick bar as thin as a barline. A treble clef's curl and tail are its own stroke, run on from its spine past
the staff -- never another staff's clef or a barline standing apart from it.

`data_clef_c_pair_2_324_r11.npz`: each place cut from the pipeline's own page binary (master cell map) at the call
`_gather_clef_header_by_ink` made to `read_header_ink`, with the lines and place it handed in, in crop pixels; `read_main_5634884a4` is
what main read there.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from tools.omr.staged import clef_pagewide as CP

DATA = pathlib.Path(__file__).with_name("data_clef_c_pair_2_324_r11.npz")
_Z = np.load(DATA)
META = json.loads(str(_Z["meta"]))
OPENING_C = ["alto_brahms_p3_s1_st11", "alto_brahms_p10_s1_st11", "tenor_brahms_p17_s1_st3", "alto_litolff_p13_s0_st9"]
JUDGED = ["alto_brahms_p3_s1_st11", "tenor_brahms_p17_s1_st3"]     # Sean 2026-11-23: the hard controls


def _case(name):
    m = META[name]
    ink = np.unpackbits(_Z[name])[: m["shape"][0] * m["shape"][1]].reshape(m["shape"]).astype(bool)
    return ink, m


def _read(name):
    ink, m = _case(name)
    return CP.read_header_ink(ink, m["place"], m["lines"], m["sp"])


@pytest.mark.parametrize("name", OPENING_C)
def test_the_opening_c_clef_is_read_c_of_its_kind(name):
    got = _read(name)
    assert got["passed"] and got["plain"] and (got["family"], got["kind"]) == ("C", META[name]["kind"]), got


@pytest.mark.parametrize("name", OPENING_C)
def test_control_main_before_r11_misreads_it(name, monkeypatch):
    """The control can fail: with r11 switched off the same pixels read what main read on the overnight (bass, or unread for C)."""
    monkeypatch.setenv(CP.ENV_C_PAIR, "0")
    got = _read(name)
    was = META[name]["read_main_5634884a4"]
    assert (bool(got["passed"]), got.get("family"), got.get("kind")) == (bool(was["passed"]), was.get("family"), was.get("kind"))
    assert got.get("kind") != META[name]["kind"]


@pytest.mark.parametrize("name", ["alto_brahms_p3_s1_st11", "alto_brahms_p10_s1_st11", "tenor_brahms_p17_s1_st3"])
def test_the_bars_are_a_pair_of_one_height(name):
    ink, m = _case(name)
    c = [c for c in CP.c_bars(ink, m["lines"], m["sp"], m["place"][0], m["place"][2]) if c["passed"]][0]
    assert c.get("bar_pair") and c["bar_width_spaces"] < CP.C_BAR_MIN_WIDTH_SPACES
    assert max(abs(v) for v in c["thin_beside_edges_spaces"]) <= 0.1      # measured: within 0.06 space


def test_never_a_pair_of_two_heights_a_g_clef_beside_a_barline():
    """The refusing side, real pixels (`data_clef_page_only_2_324.npz`, Litolff p8: a mid-staff G clef beside a barline, our look): its
    spine and the barline beside it run different heights (more than half a space apart at one end), so they are no C clef's pair,
    whatever the widths -- and it stays refused."""
    z = np.load(pathlib.Path(__file__).with_name("data_clef_page_only_2_324.npz"))
    m = json.loads(str(z["meta"]))["g_beside_barline_litolff_p8"]
    ink = np.unpackbits(z["g_beside_barline_litolff_p8"])[: m["shape"][0] * m["shape"][1]].reshape(m["shape"]).astype(bool)
    cands = CP.c_bars(ink, m["lines"], m["sp"], 0, ink.shape[1])
    assert not any(c["passed"] for c in cands) and not any(c.get("bar_pair") for c in cands)
    beside = [c for c in cands if c.get("thin_beside_edges_spaces")]
    assert beside and all(max(abs(v) for v in c["thin_beside_edges_spaces"]) > 0.5 for c in beside)


def test_never_a_thick_bar_as_thin_as_a_barline(monkeypatch):
    """The width never can fail: raise it past the thick bar Sean named (0.396 space) and the clef is lost."""
    monkeypatch.setattr(CP, "C_PAIR_MIN_WIDTH_SPACES", 0.40)
    assert _read("alto_brahms_p3_s1_st11").get("family") != "C"


def test_litolff_neighbours_ink_past_the_staff_is_not_this_clefs(monkeypatch):
    """D: the treble clef of the staff above hangs its tail into the band above the viola staff, the system's thin barline runs through
    the band below. Counted as the clef's own (no trace back to the bar), the alto clef's bar is refused as a treble clef's spine."""
    ink, m = _case("alto_litolff_p13_s0_st9")
    monkeypatch.setattr(CP, "_own_past_ink", lambda ink, lines, sp, ya, yb, xa, xb, b0, b1: ink[ya:yb, xa:xb])
    cands = CP.c_bars(ink, m["lines"], m["sp"], m["place"][0], m["place"][2])
    assert not any(c["passed"] for c in cands) and any(c["why"] == "g_clef_shape" for c in cands)


@pytest.mark.parametrize("name", OPENING_C)
def test_never_a_bass_clef_from_a_c_clefs_bowls(name):
    """The C clef's upper bowl fills both F-dot places; once its bars are read, the F never ('no F clef on a C clef's bar') holds."""
    ink, m = _case(name)
    pc = CP.glyph_piece(ink, m["place"], m["lines"], m["sp"])
    if pc is None:
        return
    f = CP.read_mid_f("clefF", pc["box"], ink, m["lines"], m["sp"], dots_beside_core=True)
    assert not f["passed"]


def test_control_with_half_a_space_the_f_never_misses_the_bars(monkeypatch):
    """Before r11 the F never looked half a space left of the piece it was handed (which began at the thin bar): Sean's p3 alto clef's
    upper bowl then passes as an F clef's two dots."""
    monkeypatch.setenv(CP.ENV_C_PAIR, "0")
    ink, m = _case("alto_brahms_p3_s1_st11")
    pc = CP.glyph_piece(ink, m["place"], m["lines"], m["sp"])
    f = CP.read_mid_f("clefF", pc["box"], ink, m["lines"], m["sp"], dots_beside_core=True)
    assert f["passed"] and f["kind"] == "bass" and min(f["dots"]["upper"], f["dots"]["lower"]) >= 0.96


@pytest.mark.parametrize("name", ["midf_bass_brahms_p25_s0_st3", "midf_bass_brahms_p26_s0_st5"])
def test_the_mid_line_bass_clefs_stay_read(name):
    """Brahms p25 s0 staff 3 (bassoon, bars 475-483) and p26 s0 staff 5 (horn, 497-502): mid-line bass clefs newly read on
    20261122-night, read on their `clefF` box (`place` is the box). The F never now looks a whole space left: they stay plain bass."""
    ink, m = _case(name)
    f = CP.read_mid_f("clefF", m["place"], ink, m["lines"], m["sp"])
    assert f["passed"] and f["plain"] and f["kind"] == "bass", f.get("why")


def test_the_timpani_bass_clef_read_by_its_ink_stays_bass():
    """Litolff p13 s0 staff 6 (Tp.): a header bass clef with no box, read by its own ink -- newly right on 20261122-night; r11 keeps it."""
    got = _read("bass_litolff_p13_s0_st6_timpani")
    assert got["passed"] and got["plain"] and (got["family"], got["kind"]) == ("F", "bass")
