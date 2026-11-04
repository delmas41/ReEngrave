"""ROADMAP 2.258 (OMR_ARC_ONE_CURVE): the binder's junction guard asks the TRACE. Each guard has a twin that fails without it."""
from tools.omr.staged import arc_claim as AC


class _Row:
    def __init__(self, value=None, detail=None):
        self.value, self.detail = value, detail or {}


class _Ev:
    """boxes `{key: [x0, y0, x1, y1]}`, cell boxes `{cell index: [x0, y0, x1, y1]}`"""

    def __init__(self, boxes, cells):
        self.boxes, self.cells = boxes, cells

    def rows(self, q, subject=None, **kw):
        from tools.omr.staged.record import Q
        if q is Q.ARC_BOX:
            b = self.boxes.get(subject.to_key())
            return [_Row(detail={"bbox_page_px": b})] if b else []
        if q is Q.CELL_BOX:
            c = self.cells.get(subject.cell)
            return [_Row(value=c)] if c else []
        return []


def _guard(boxes, cells, joins=None):
    from tools.omr.staged.adjudicators.ownership import _joins_not_at_a_barline
    return _joins_not_at_a_barline(_Ev(boxes, cells), sorted(boxes), 10.0, joins)


def test_twin_boxes_in_one_cell_are_one_stroke_only_where_the_trace_says_so():
    k1, k2 = "glyph/0/0/0/3/0", "glyph/0/0/0/3/1"
    boxes = {k1: [100, 0, 160, 5], k2: [120, 0, 190, 5]}
    cells = {3: [90, 0, 200, 50]}
    assert _guard(boxes, cells) == [k1 + ">" + k2]                      # OFF: same cell, never a barline
    agree = [dict(a=k1, b=k2, agree_cols=30, a_x0=100, a_x1=160, b_x0=120, b_x1=190)]
    assert _guard(boxes, cells, agree) == []                              # the traces agree over 3 sp: one stroke
    meet = [dict(a=k1, b=k2, agree_cols=3, a_x0=100, a_x1=160, b_x0=155, b_x1=190)]
    assert _guard(boxes, cells, meet) == [k1 + ">" + k2]                  # two arcs meeting at a note: the guard stands


def test_a_barline_crossing_whose_second_box_starts_inside_its_cell():
    k1, k2 = "glyph/0/0/0/10/0", "glyph/0/0/0/11/0"
    boxes = {k1: [100, 0, 200, 5], k2: [235, 0, 300, 5]}
    cells = {10: [50, 0, 200, 50], 11: [200, 0, 350, 50]}
    assert _guard(boxes, cells) == [k1 + ">" + k2]                       # the right box begins 3.5 sp inside its cell
    cross = [dict(a=k1, b=k2, agree_cols=27, a_x0=100, a_x1=232, b_x0=205, b_x1=300)]
    assert _guard(boxes, cells, cross) == []                              # both traces ink the stroke over 2.7 sp: one stroke
    meet = [dict(a=k1, b=k2, agree_cols=0, a_x0=100, a_x1=200, b_x0=203, b_x1=300)]
    assert _guard(boxes, cells, meet) == [k1 + ">" + k2]                  # end meets start only: a tie then a slur at one note


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv(AC.ENV_ONE_CURVE, raising=False)
    assert not AC.one_curve_enabled()
    monkeypatch.setenv(AC.ENV_ONE_CURVE, "1")
    assert AC.one_curve_enabled()
