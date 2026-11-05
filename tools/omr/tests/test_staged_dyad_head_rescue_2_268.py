"""ROADMAP 2.268 -- `dyad_head_rescue`: a chord's other head from the detector's own sub-cut candidate (flag OMR_DYAD_HEAD_RESCUE, default ON, deny-list)."""
from dataclasses import dataclass

from tools.omr.staged import dyad_head_rescue as DHR


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


def head(x, y, name="noteheadHalfInSpace", conf=0.5):
    """a 130x100 head centred at (x, y)"""
    return D(name, x - 65, y - 50, 130, 100, conf)


def test_flag_default_on(monkeypatch):
    monkeypatch.delenv(DHR.ENV, raising=False)
    assert DHR.enabled() is True
    for v in ("1", "on", ""):
        monkeypatch.setenv(DHR.ENV, v)
        assert DHR.enabled() is True
    for v in ("0", "false", "no", "off", "OFF"):
        monkeypatch.setenv(DHR.ENV, v)
        assert DHR.enabled() is False


def test_a_third_along_a_shared_stem_is_kept():
    s = stem(300, 0, 500)                                   # stem up; boxed head at its bottom (left), the other a space above it
    existing = [head(235, 450)]
    kept, refused = DHR.candidates_for_cell([s], existing, [head(235, 350, conf=0.1)], GRID)
    assert len(kept) == 1 and kept[0]["partner"] == 0 and kept[0]["stem_index"] == 0 and not refused


def test_a_displaced_second_is_kept():
    s = stem(300, 0, 500)                                   # the second stands a step up on the OTHER side of the stem
    existing = [head(235, 450)]
    kept, _r = DHR.candidates_for_cell([s], existing, [head(365, 400, conf=0.1)], GRID)
    assert len(kept) == 1


def test_no_shared_stem_is_not_kept():
    existing = [head(235, 450)]
    kept, refused = DHR.candidates_for_cell([stem(900, 0, 500)], existing, [head(235, 350, conf=0.1)], GRID)
    assert kept == [] and refused and refused[0]["why"] == "no_stem_through_a_boxed_head"
    kept, _r = DHR.candidates_for_cell([], existing, [head(235, 350, conf=0.1)], GRID)
    assert kept == []


def test_a_stem_no_boxed_head_touches_is_not_kept():
    """the stem-end rescue's case (an orphan stem), not this one: the stem here has no boxed head"""
    s = stem(300, 0, 500)
    existing = [head(900, 450)]
    kept, _r = DHR.candidates_for_cell([s], existing, [head(235, 350, conf=0.1)], GRID)
    assert kept == []


def test_already_covered_is_not_kept():
    s = stem(300, 0, 500)
    existing = [head(235, 450), head(235, 350, conf=0.7)]
    kept, _r = DHR.candidates_for_cell([s], existing, [head(240, 355, conf=0.1)], GRID)
    assert kept == []


def test_the_boxed_heads_own_ink_boxed_again_is_not_kept():
    """less than a step from the boxed head: that head's own ink, not another note"""
    s = stem(300, 0, 500)
    existing = [head(235, 450)]
    kept, _r = DHR.candidates_for_cell([s], existing, [head(235, 420, conf=0.1)], GRID)
    assert kept == []


def test_another_marks_confident_box_holds_the_ink():
    s = stem(300, 0, 500)
    existing = [head(235, 450), D("accidentalFlat", 170, 300, 70, 100, 0.8, "accidental")]
    kept, refused = DHR.candidates_for_cell([s], existing, [head(205, 350, conf=0.1)], GRID)
    assert kept == [] and refused[0]["why"] == "another_mark_holds_it"


def test_one_candidate_per_ink_highest_score():
    s = stem(300, 0, 500)
    existing = [head(235, 450)]
    kept, _r = DHR.candidates_for_cell([s], existing, [head(235, 350, conf=0.05), head(237, 352, conf=0.2)], GRID)
    assert len(kept) == 1 and kept[0]["score"] == 0.2


def test_no_boxed_head_in_the_cell_nothing_is_kept():
    kept, refused = DHR.candidates_for_cell([stem(300, 0, 500)], [], [head(235, 350, conf=0.1)], GRID)
    assert kept == [] and refused == []


def test_is_dyad_reads_only_its_own_source():
    assert DHR.is_dyad({"source": "dyad_head_rescue"})
    assert not DHR.is_dyad({"source": "stem_end_head"}) and not DHR.is_dyad(None)
