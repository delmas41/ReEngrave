"""ROADMAP 2.273 -- the staff-row arc strip: its pure rules, and that the flag defaults OFF (fast tier; no detector, no weights)."""
import os

from tools.omr.staged import arc_strip as S


def _cut(side="r"):
    # a box 40..100 wide cut at the cell's right edge x=100, one staff space = 10 px
    return {"box": (40.0, 10.0, 100.0, 30.0), "side": side, "bar": 100.0, "sp": 10.0}


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv(S.ENV, raising=False)
    assert not S.enabled()
    monkeypatch.setenv(S.ENV, "1")
    assert S.enabled()
    monkeypatch.setenv(S.ENV, "0")
    assert not S.enabled()


def test_continues_far_half():
    assert S.continues(_cut(), (38.0, 8.0, 160.0, 30.0))              # starts with K, runs 6 sp past the bar
    assert not S.continues(_cut(), (38.0, 8.0, 104.0, 30.0))          # ends under 0.75 sp past the bar
    assert not S.continues(_cut(), (95.0, 8.0, 160.0, 30.0))          # starts after the bar-side half of K: a different arc
    assert not S.continues(_cut(), (38.0, 60.0, 160.0, 80.0))         # another y band


def test_continues_left_cut():
    k = {"box": (0.0, 10.0, 60.0, 30.0), "side": "l", "bar": 0.0, "sp": 10.0}
    assert S.continues(k, (-50.0, 8.0, 62.0, 30.0))
    assert not S.continues(k, (-5.0, 8.0, 62.0, 30.0))


def _arch(n, amp=20, width=60):
    """n arches in a row as traced points {x: (y0, y1)} (y grows downward: the apex is the smallest y)."""
    pts = {}
    for i in range(n):
        for t in range(width):
            x = i * width + t
            y = 100 - amp * 4 * (t / width) * (1 - t / width)
            pts[x] = (int(y), int(y) + 3)
    return pts


def test_turns_one_arc_is_one_chain_is_many():
    assert S.turns(_arch(1), 10.0) <= S.MAX_TURNS                      # the control that must pass
    assert S.turns(_arch(3), 10.0) > S.MAX_TURNS                       # the control that must FAIL: three arcs meeting at notes


def _a(x0, x1, cut_l=False, cut_r=False):
    return {"box": (x0, 10.0, x1, 30.0), "cut_l": cut_l, "cut_r": cut_r}


def test_whole_arcs_inside_counts_whole_not_pieces():
    box = (0.0, 5.0, 400.0, 35.0)
    # one arc in three pieces cut at two barlines is ONE arc (closed at both ends), not three
    assert S.whole_arcs_inside(box, [_a(0, 100, cut_r=True), _a(100, 200, True, True), _a(200, 300, cut_l=True)], 10.0) == (1, 1)
    # a piece still open at its left end (the arc started outside the candidate) is not a whole arc
    assert S.whole_arcs_inside(box, [_a(0, 100, cut_l=True, cut_r=True), _a(100, 200, cut_l=True)], 10.0) == (0, 1)
    # two arcs that each end on their own notes: two whole arcs
    assert S.whole_arcs_inside(box, [_a(10, 150), _a(150, 300)], 10.0)[0] == 2
