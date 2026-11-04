"""ROADMAP 2.260b r2 (OMR_PAGE_CLAIMS): an end extends only along its own page stroke, and never moves an end that bound a head."""
import numpy as np

from tools.omr.staged import arc_claim as AC


class _PM:
    scale = 1.0

    def __init__(self, masks):
        self.masks = masks


def _head(key, cx, cy):
    return dict(key=key, cx=cx, cy=cy, w=20.0, h=15.0)


def test_extent_is_where_the_stroke_ink_ends():
    m = np.zeros((10, 100), bool)
    m[4, 10:90] = True
    ext = AC.page_stroke_extent(_PM([(m, 200, 300)]), [0])
    assert ext[0][0] == 210.5 and ext[1][0] == 289.5          # the stroke's own ink, no fixed distance
    assert AC.page_stroke_extent(_PM([]), []) is None


def test_stroke_end_binds_only_an_end_that_bound_nothing():
    sp = 15.0
    detail = dict(x_left_page=100, y_left_page=50, x_right_page=300, y_right_page=50, trace=[])
    heads = [_head("L", 40, 50), _head("R", 305, 50)]
    off = AC.bind_curve(detail, heads, sp)
    assert off["left"].get("unbound") == "no_head_at_end" and off["right"]["head"] == "R"
    on = AC.bind_curve(detail, heads, sp, alt_ends={"left": [55, 50], "right": [330, 50]})
    assert on["left"]["head"] == "L" and on["left"]["via_stroke_end"]         # the unbound end reached its head along the stroke
    assert on["right"] == off["right"]                                         # the end that bound a head is never moved


def test_flag_off(monkeypatch):
    monkeypatch.delenv(AC.ENV_PAGE_CLAIMS, raising=False)
    assert not AC.page_claims_enabled()
