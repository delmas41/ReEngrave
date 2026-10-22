"""ROADMAP 2.179 -- `stem_end_heads`: a head looked for again at the end of a stem that has none (flag OMR_STEM_END_HEADS, default ON)."""
from dataclasses import dataclass

import pytest

from tools.omr.staged import stem_end_heads as SEH


@dataclass
class D:
    smufl_name: str
    x_canonical: float
    y_canonical: float
    width_canonical: float
    height_canonical: float
    confidence: float = 0.5
    category: str = "notehead"


GRID = (100.0, 50.0)          # top line y=100, half step 50 -> staff space 100


def stem(x, y0, y1):
    return D("stem", x - 6, y0, 12, y1 - y0, 1.0, "stem")


def head(x, y, name="noteheadBlackInSpace", conf=0.5):
    """a 130x100 head centred at (x, y)"""
    return D(name, x - 65, y - 50, 130, 100, conf)


def test_flag_default_on(monkeypatch):
    monkeypatch.delenv(SEH.STEM_END_HEADS_ENV, raising=False)
    assert SEH.enabled() is True
    for v in ("0", "false", "no", "off", "OFF"):
        monkeypatch.setenv(SEH.STEM_END_HEADS_ENV, v)
        assert SEH.enabled() is False
    monkeypatch.setenv(SEH.STEM_END_HEADS_ENV, "1")
    assert SEH.enabled() is True


def test_stem_with_a_head_is_not_an_orphan():
    s = stem(300, 0, 350)                         # stem up, head at the bottom end, left of the stem
    assert not SEH.is_orphan(s, [SEH._box(head(245, 350))], 100.0)
    assert SEH.is_orphan(s, [SEH._box(head(800, 350))], 100.0)


def test_sub_floor_head_at_the_bottom_left_of_an_up_stem_is_kept():
    s = stem(300, 0, 350)
    kept, refused, n = SEH.candidates_for_cell([s], [], [head(245, 350, conf=0.12)], GRID)
    assert n == 1 and len(kept) == 1 and not refused
    assert kept[0]["end"] == "bottom" and kept[0]["read_from"] == "noteheadBlackInSpace"


def test_wrong_side_is_not_taken():
    """an up-stem's head is at its LEFT (stem at the head's right); a blot at the bottom RIGHT is not its head"""
    s = stem(300, 0, 350)
    kept, _r, _n = SEH.candidates_for_cell([s], [], [head(380, 350, conf=0.12)], GRID)
    assert kept == []


def test_top_end_right_side_for_a_down_stem():
    s = stem(300, 250, 600)                       # head at the top end, stem at the head's LEFT
    kept, _r, _n = SEH.candidates_for_cell([s], [], [head(355, 250, conf=0.1)], GRID)
    assert len(kept) == 1 and kept[0]["end"] == "top"


def test_no_orphan_no_candidates_and_a_seen_head_is_not_added_again():
    s = stem(300, 0, 350)
    existing = [head(245, 350, conf=0.8)]
    kept, refused, n = SEH.candidates_for_cell([s], existing, [head(245, 350, conf=0.1)], GRID)
    assert (kept, refused, n) == ([], [], 0)


def test_block_rest_at_a_stem_end_is_re_read_as_a_black_head():
    s = stem(300, 0, 300)                         # bottom end at y=300: a line (steps 4 -> on a line)
    rest = D("restWhole", 190, 260, 110, 60, 0.33, "rest")
    kept, _r, _n = SEH.candidates_for_cell([s], [rest], [], GRID)
    assert len(kept) == 1
    assert kept[0]["read_from"] == "restWhole" and kept[0]["from_record"] is True
    assert kept[0]["det"].smufl_name == "noteheadBlackOnLine" and kept[0]["det"].category == "notehead"
    assert rest.smufl_name == "restWhole"         # the production box itself is never changed


def test_a_stronger_box_of_another_family_blocks_the_candidate():
    s = stem(300, 0, 350)
    sharp = D("accidentalSharp", 190, 300, 110, 100, 0.6, "accidental")
    kept, refused, _n = SEH.candidates_for_cell([s], [sharp], [head(245, 350, conf=0.12)], GRID)
    assert kept == [] and refused and refused[0]["why"] == "another_mark_stronger"


def test_one_ink_at_two_stem_ends_is_kept_once():
    s1, s2 = stem(300, 0, 350), stem(310, 0, 350)
    kept, _r, _n = SEH.candidates_for_cell([s1, s2], [], [head(250, 350, conf=0.2)], GRID)
    assert len(kept) == 1


@pytest.mark.parametrize("cy,want", [(100, "noteheadBlackOnLine"), (150, "noteheadBlackInSpace"), (300, "noteheadBlackOnLine")])
def test_black_head_class_by_position(cy, want):
    assert SEH.black_head_class(cy, *GRID) == want


def test_a_rests_own_upright_is_not_an_orphan_stem():
    """the body of a Breitkopf quarter rest reads as a stem; inside the rest's box it is the rest's, never a note's"""
    s = stem(300, 100, 400)
    rest = D("restQuarter", 230, 80, 140, 340, 0.6, "rest")
    kept, _r, n = SEH.candidates_for_cell([s], [rest], [head(250, 400, conf=0.15)], GRID)
    assert n == 0 and kept == []


def test_a_candidate_beside_a_seen_head_is_never_added():
    """one ink boxed again half a space off, or the slot the stacked fit gives one head: the production head must not be overturned"""
    s = stem(300, 0, 470)
    seen = head(245, 340, conf=0.8)               # centre 130 above the stem's bottom end: the stem still reads as an orphan
    kept, refused, n = SEH.candidates_for_cell([s], [seen], [head(245, 440, conf=0.13)], GRID)
    assert n == 1 and kept == [] and refused[0]["why"] == "beside_a_seen_head"


def test_a_whole_class_box_at_a_stem_end_is_not_taken():
    s = stem(300, 0, 350)
    kept, _r, _n = SEH.candidates_for_cell([s], [], [head(245, 350, name="noteheadWholeOnLine", conf=0.2)], GRID)
    assert kept == []
