"""ROADMAP 2.273 -- the staff-row arc strip: its pure rules, and that the flag defaults OFF (fast tier; no detector, no weights)."""
import os

from tools.omr.staged import arc_strip as S


def _cut(side="r"):
    # a box 40..100 wide cut at the cell's right edge x=100, one staff space = 10 px
    return {"box": (40.0, 10.0, 100.0, 30.0), "side": side, "bar": 100.0, "sp": 10.0}


def test_flag_default_on(monkeypatch):
    monkeypatch.delenv(S.ENV, raising=False)
    assert S.enabled()                                   # default ON since 2026-11-06 (deny-list)
    for off in ("0", "false", "no", "off"):
        monkeypatch.setenv(S.ENV, off)
        assert not S.enabled()
    monkeypatch.setenv(S.ENV, "1")
    assert S.enabled()


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
    assert S.turns(_arch(1), 10.0) <= 1                                # one arc: its apex
    assert S.turns(_arch(3), 10.0) > 1                                 # three arcs meeting at notes


def _passes(f):
    return f["cross"] <= S.FAR_CROSS_MAX_SPACES and f["end"] <= S.FAR_END_MAX_SPACES and f["cover"] >= S.FAR_COVER_MIN


def test_guard_cutoffs_are_the_page_traces_own():
    from tools.omr.staged import arcs_system as AS
    assert (S.FAR_CROSS_MAX_SPACES, S.FAR_END_MAX_SPACES, S.FAR_COVER_MIN) == (AS.GAP_MAX_SPACES, AS.CUT_EXTEND_SPACES, AS.MIN_COVER)


def test_far_part_guard_passes_one_arc_and_fails_where_it_must():
    sp = 10.0
    box = (0.0, 80.0, 400.0, 105.0)
    bar = 100.0
    # a far half: the stroke runs from the barline to the box's far edge
    one = {x: (90, 93) for x in range(100, 400)}
    assert _passes(S.far_part(one, "r", bar, box, sp))
    # CONTROL 1 (must fail): a box over two arcs with a gap between -- the stroke on the far side begins 19 sp after the barline
    two = {x: (90, 93) for x in range(290, 400)}
    assert not _passes(S.far_part(two, "r", bar, box, sp))
    # CONTROL 2 (must fail): a box that runs on far past the arc's end (a staff-wide box)
    short = {x: (90, 93) for x in range(100, 160)}
    assert not _passes(S.far_part(short, "r", bar, box, sp))
    # CONTROL 3 (must fail): a box on empty ink
    assert not _passes(S.far_part({}, "r", bar, box, sp))
    # CONTROL 4 (must fail): a sparse trace (a few columns of a 300-column far part)
    sparse = {x: (90, 93) for x in range(100, 400, 25)}
    assert not _passes(S.far_part(sparse, "r", bar, box, sp))
    # the mirror: an arc that ENDS in this cell, cut at its left edge (bar = 300): the far part is to the left
    left = {x: (90, 93) for x in range(0, 300)}
    assert _passes(S.far_part(left, "l", 300.0, box, sp))
    assert not _passes(S.far_part({x: (90, 93) for x in range(0, 40)}, "l", 300.0, box, sp))


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
