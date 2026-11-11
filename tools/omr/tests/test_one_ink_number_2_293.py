"""ROADMAP 2.293 -- THE ONE INK NUMBER. Pure canvas tests (no PDF, no record): the four lines that add to 100% of the dark pixels, the claim source
(page ledger vs cell box), the ledger's own answer read from a stroke-owner verdict, and the three controls that must be able to fail."""
import copy

import numpy as np
import pytest

from tools.omr.staged import claim_readout as CR
from tools.omr.staged.claim_readout import FINE_BIT, InkPartitionError, LedgerInk, LedgerStroke

H, W = 80, 160


def _canvas(ink_boxes):
    ink = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in ink_boxes:
        ink[y0:y1, x0:x1] = True
    return LedgerInk(ink)


def _labels(boxes, h=H, w=W):
    lab = np.zeros((h, w), np.int16)
    for i, (x0, y0, x1, y1) in boxes.items():
        lab[y0:y1, x0:x1] = i
    return lab


def _ls(kinds=(), src="cell", **kw):
    s = LedgerStroke(shape=kw.pop("shape", "blob"), **kw)
    for k in kinds:
        s.kinds.add(k)
        s.src[k] = src
    return s


def _page():
    """Seven strokes of known size: head (200 px, cell box), barline (200, register), twin head (200), two-kind (200, open), unowned blob, weak text, staff."""
    boxes = {1: (0, 0, 10, 20), 2: (20, 0, 30, 20), 3: (40, 0, 50, 20), 4: (60, 0, 70, 20), 5: (80, 0, 90, 20)}
    c = _canvas(list(boxes.values()) + [(100, 0, 110, 20), (0, 40, 40, 42)])
    c.add_cell((0, 0, 100, H), _labels(boxes, H, 100), {
        1: _ls(["notehead"]), 2: _ls(["barline"], "ledger"), 3: _ls(["notehead"], twin=True),
        4: _ls(["notehead", "stem"], open=True), 5: _ls([], shape="blob")})
    c.add_area((100, 0, 110, 20), "word", weak=True)
    c.staff[40:42, 0:40] = True
    c.incell[40:42, 0:40] = True
    c.finish()
    return c


def test_the_four_lines_add_to_every_dark_pixel_and_each_stroke_lands_in_its_line():
    c = _page()
    t = c.tally()
    assert sum(t["lines"].values()) == t["ink_px"] == 5 * 200 + 200 + 80
    assert t["one"]["px"] == 200 + 200 + 80                     # head + barline + the staff-line ink
    assert t["one"]["by_kind"] == {"notehead": 200, "barline": 200, "staff_line": 80}
    assert t["twice"]["twin_px"] == 200 and t["twice"]["two_kinds_px"] == 200 and t["twice"]["px"] == 400
    assert t["weak"]["px"] == 200 and t["weak"]["by_kind"] == {"word": 200}
    assert t["none"]["px"] == 200


def test_ledger_and_cell_box_sublines_split_the_one_owner_ink_by_claim_source():
    t = _page().tally()
    o = t["one"]
    assert o["by_kind_ledger"] == {"barline": 200, "staff_line": 80}    # a page-wide register claim, and the staff geometry
    assert o["by_kind_cell"] == {"notehead": 200}                       # a detector box of one padded cell
    assert o["ledger_px"] + o["cell_px"] == o["px"]


def test_a_register_area_outside_every_cell_is_a_ledger_claim_and_a_weak_one_is_not_a_claim():
    c = _canvas([(0, 0, 10, 10), (20, 0, 30, 10)])
    c.add_area((0, 0, 10, 10), "bracket")
    c.add_area((20, 0, 30, 10), "word", weak=True)
    c.finish()
    t = c.tally()
    assert t["one"]["by_kind_ledger"] == {"bracket": 100} and t["weak"]["px"] == 100 and t["none"]["px"] == 0


def test_the_same_ink_in_two_cells_is_one_pixel_and_two_unlinked_views_of_one_kind_are_flagged():
    c = _canvas([(40, 10, 50, 30)])
    c.add_cell((0, 0, 60, H), _labels({1: (40, 10, 50, 30)}, H, 60), {1: _ls(["notehead"])})
    c.add_cell((30, 0, 90, H), _labels({1: (10, 10, 20, 30)}, H, 60), {1: _ls(["notehead"])})
    c.finish()
    t = c.tally()
    assert t["ink_px"] == 200 and t["twice"]["twin_views_px"] == 200       # one kind, named in two UNLINKED views
    c2 = _canvas([(40, 10, 50, 30)])
    c2.add_cell((0, 0, 60, H), _labels({1: (40, 10, 50, 30)}, H, 60), {1: _ls(["notehead"], linked=True)})
    c2.add_cell((30, 0, 90, H), _labels({1: (10, 10, 20, 30)}, H, 60), {1: _ls(["notehead"], linked=True)})
    c2.finish()
    assert c2.tally()["one"]["px"] == 200                                  # linked views are the ledger's one answer


def test_two_unlinked_views_that_name_different_kinds_are_claimed_twice_not_one_owner():
    c = _canvas([(40, 10, 50, 30)])
    c.add_cell((0, 0, 60, H), _labels({1: (40, 10, 50, 30)}, H, 60), {1: _ls(["notehead"])})
    c.add_cell((30, 0, 90, H), _labels({1: (10, 10, 20, 30)}, H, 60), {1: _ls(["stem"])})
    c.finish()
    t = c.tally()
    assert t["twice"]["views_disagree_px"] == 200 and t["twice"]["pairs"] == {"stem+notehead": 200} or t["twice"]["pairs"] == {"notehead+stem": 200}


def test_a_stroke_settled_over_a_rival_has_one_owner_and_the_rival_is_reported_on_a_subline():
    c = _canvas([(0, 0, 10, 20)])
    c.add_cell((0, 0, 20, H), _labels({1: (0, 0, 10, 20)}, H, 20), {1: _ls(["arc"], "ledger", rival=True)})
    c.finish()
    t = c.tally()
    assert t["one"]["by_kind"] == {"arc": 200} and t["one"]["over_rival_px"] == 200 and t["twice"]["px"] == 0


def test_no_owner_ink_is_ranked_by_a_shape_guess():
    boxes = {1: (0, 0, 2, 2), 2: (10, 0, 12, 90), 3: (30, 0, 54, 24), 4: (70, 0, 86, 8)}
    ink = np.zeros((100, 160), bool)
    for x0, y0, x1, y1 in boxes.values():
        ink[y0:y1, x0:x1] = True
    c = LedgerInk(ink)
    c.add_cell((0, 0, 100, 100), _labels(boxes, 100, 100), {i: _ls([]) for i in boxes})
    c.sp = 24.0
    c.bands = [(60.0, 60.0)]                 # a staff at y 60: the text-like piece at y 4 stands outside it
    c.finish()
    cls = c.tally()["none"]["by_class"]
    assert cls["specks"] == 4 and cls["long_thin_stroke"] == 2 * 90 and cls["note_like_blob"] == 24 * 24
    assert cls["text_like"] == 16 * 8
    assert sum(cls.values()) == c.tally()["none"]["px"]


def test_a_refused_claim_is_no_owner_and_is_named_as_a_fact_not_a_guess():
    c = _canvas([(0, 0, 10, 20)])
    c.add_cell((0, 0, 20, H), _labels({1: (0, 0, 10, 20)}, H, 20), {1: _ls([], refused=True, shape="vertical")})
    c.finish()
    assert c.tally()["none"]["by_class"] == {"refused_claim": 200}


# ── the ledger's own answer, read off a stroke-owner verdict ──
class _St:
    def __init__(self, kind="blob"):
        self.kind = kind


def _cand(key, fam, fit="clear", how="cover"):
    return [key, fam, fam, fit, "", how]


def test_claims_read_the_settle_as_the_ledger_answered_it():
    strokes = [_St() for _ in range(7)]
    verdict = {"strokes": {
        "0": ["decided", "barline", ["a"], "area", [_cand("a", "barline", how="area")]],
        "1": ["decided", "head", ["b"], "single", [_cand("b", "head")]],
        "2": ["merged", "head", ["b", "c"], "shape", [_cand("b", "head"), _cand("c", "head")]],
        "3": ["contested", None, [], "", [_cand("d", "head", "could"), _cand("e", "stem", "could")]],
        "4": ["refused_claims", None, [], "shape", [_cand("f", "head", "no")]],
        "5": ["decided", "arc_trace", ["g"], "area", [_cand("g", "arc_trace", how="area"), _cand("h", "head", "could")]],
    }}
    cl = CR.ledger_claims_for_cell(strokes, verdict, {6: ["stem"]}, {}, {0: [3, 1.0, 1.0, 0.0]})
    assert cl[1].kinds == {"barline"} and cl[1].src == {"barline": "ledger"} and cl[1].linked
    assert cl[2].kinds == {"notehead"} and cl[2].src == {"notehead": "cell"} and not cl[2].twin and not cl[2].linked
    assert cl[3].twin
    assert cl[4].open and cl[4].kinds == {"notehead", "stem"}
    assert cl[5].refused and not cl[5].kinds
    assert cl[6].kinds == {"arc"} and cl[6].rival and not cl[6].twin
    assert cl[7].kinds == {"stem"} and cl[7].src == {"stem": "cell"}             # a consumer box on a stroke the settle left unclaimed


def test_a_cv_read_claims_only_where_nothing_else_does_and_an_unknown_owner_keeps_its_own_name():
    cl = CR.ledger_claims_for_cell([_St(), _St()], {"strokes": {"0": ["decided", "head", ["b"], "single", [_cand("b", "head")]]}}, {}, {0: ["stem"], 1: ["beam"]}, {})
    assert cl[1].kinds == {"notehead"} and cl[2].kinds == {"beam"}
    assert CR.fine_of("tremolo") == "tremolo" and CR.fine_of("a_layer_nobody_listed") == "other" and CR.fine_of("whole_rest") == "rest"


def test_a_planted_second_box_marks_strokes_of_that_kind_only():
    verdict = {"strokes": {"0": ["decided", "head", ["b"], "single", [_cand("b", "head")]], "1": ["decided", "stem", ["c"], "single", [_cand("c", "stem")]]}}
    cl = CR.ledger_claims_for_cell([_St(), _St()], verdict, {}, {}, {}, plant=("twin", "notehead"))
    assert cl[1].twin and cl[1].planted and not cl[2].twin


def test_link_is_the_ledgers_own_rule():
    assert CR.link_is_linked([3, 0.95, 0.9, 0.0]) and not CR.link_is_linked([3, 0.5, 0.9, 0.0]) and not CR.link_is_linked(None)
    assert not CR.link_is_linked([3, 0.95, 0.3, 0.0])               # a piece holding a small share of its page stroke, no cell-edge cut: not a view
    assert CR.link_is_linked([3, 0.95, 0.3, 1.0])


# ── the controls that must be able to fail ──
def test_control_a_erasing_a_kind_moves_exactly_its_sole_ink_out_of_the_claimed_lines():
    c = _page()
    t0 = c.tally()
    sole = int(((c.fam_eff == FINE_BIT["notehead"]) & c.ink).sum())
    assert sole == 400                                              # the head (200) and the twin head (200)
    t1 = c.without_kind("notehead").tally()
    assert (t1["lines"]["weak"] + t1["lines"]["none"]) - (t0["lines"]["weak"] + t0["lines"]["none"]) == sole
    assert t1["one"]["by_kind"].get("notehead", 0) == 0 and t1["ink_px"] == t0["ink_px"]
    # the two-kind stroke (notehead+stem) is left with one owner, not lost
    assert t1["one"]["by_kind"].get("stem") == 200


def test_control_b_a_second_owner_raises_claimed_twice_by_exactly_the_ink_planted():
    c = _page()
    t0 = c.tally()
    c2 = _canvas([(0, 0, 10, 20), (20, 0, 30, 20)])
    c2.add_cell((0, 0, 100, H), _labels({1: (0, 0, 10, 20), 2: (20, 0, 30, 20)}, H, 100), {1: _ls(["notehead"]), 2: _ls(["notehead"], twin=True, planted=True)})
    c2.finish()
    t2 = c2.tally()
    assert t2["twice"]["px"] == 200 and t2["twice"]["planted_px"] == 200 and t2["one"]["px"] == 200
    assert t0["twice"]["planted_px"] == 0


def test_control_c_the_sum_check_trips_on_a_doctored_canvas_and_a_doctored_tally():
    t = _page().tally()
    CR.verify_tally(t)
    for path, bump in ((("lines", "none"), 1), (("one", "ledger_px"), 1), (("none", "px"), 1), (("twice", "px"), 1)):
        bad = copy.deepcopy(t)
        bad[path[0]][path[1]] += bump
        with pytest.raises(InkPartitionError):
            CR.verify_tally(bad)
    c = _page()
    c.state = c.state.copy()
    ys, xs = np.nonzero(c.ink)
    c.state[ys[0], xs[0]] = 255                                     # a dark pixel with no state
    with pytest.raises(InkPartitionError):
        CR.verify_tally(c.tally())


def test_pages_merge_by_exact_sums_and_the_headline_names_its_denominator():
    t = _page().tally()
    m = CR.merge_ink_tallies([t, t])
    assert m["ink_px"] == 2 * t["ink_px"] and m["lines"]["one"] == 2 * t["lines"]["one"]
    s = CR.ink_headline("brahms", m, [0, 4])
    assert "dark px" in s and "not staff line" in s
    text = "\n".join(CR.render_ink_number("TOTAL", m))
    assert "ONE OWNER" in text and "NOT on the page ledger" in text and "100.0%" in text
