"""ROADMAP 2.215: a changed dynamic is boxed on its own letters; a bar-check word has no ink and no tile box."""
from tools.omr.staged import lane_report as L


def test_own_direction_box():
    boxes = {"glyph/1/0/2/3/0": dict(page=1, box=[10, 10, 20, 30], cls="dynamicM"),
             "glyph/1/0/2/3/1": dict(page=1, box=[22, 12, 40, 32], cls="dynamicP"),
             "glyph/1/0/2/3/9": dict(page=1, box=[0, 0, 5, 5], cls="noteheadBlack")}
    d = dict(kind="dynamic", value="mp", rg="glyph/1/0/2/3/9", page=1, box=[0, 0, 5, 5])
    assert L.own_direction_box(d, boxes) == [10, 10, 40, 32]
    w = dict(kind="words", value="does not add up: should hold 4", rg="glyph/1/0/2/3/9", page=1, box=[0, 0, 5, 5])
    assert L.own_direction_box(w, boxes) is None and w["no_ink"]
    o = dict(kind="words", value="dolce", rg="glyph/1/0/2/3/9", page=1, box=[0, 0, 5, 5])
    assert L.own_direction_box(o, boxes) == [0, 0, 5, 5] and o["box_is_host"]
