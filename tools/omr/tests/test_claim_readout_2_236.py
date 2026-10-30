"""ROADMAP 2.236 -- the capture readout. Pure canvas tests (no PDF, no record): the de-dup in page pixels, the states, the truth classes and the
controls that must be able to fail. The real-page runs are in benchmarks/capture-readout-2026-10/FINDINGS.md."""
import numpy as np

from tools.omr.staged import claim_readout as CR
from tools.omr.staged.claim_readout import PageInk, StrokeClaims

H, W = 60, 120


def _canvas(ink_boxes):
    ink = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in ink_boxes:
        ink[y0:y1, x0:x1] = True
    return PageInk(ink)


def _labels(h, w, boxes):
    """A stroke label image (frame of the cell, 1 px per page px here): {label: (x0, y0, x1, y1)}."""
    lab = np.zeros((h, w), np.int16)
    for i, (x0, y0, x1, y1) in boxes.items():
        lab[y0:y1, x0:x1] = i
    return lab


def _claims(**kw):
    out = {}
    for lab, (kinds, nbox, shape) in kw.items():
        out[int(lab[1:])] = StrokeClaims(shape=shape, kinds=set(kinds), n_box=nbox)
    return out


def test_same_ink_in_two_overlapping_cells_is_one_ink():
    # one stroke at x 40..50 seen by cell A (x 0..60) and by cell B (x 30..90): page ink is 10x20 = 200 px, counted once
    c = _canvas([(40, 10, 50, 30)])
    lab_a = _labels(H, 60, {1: (40, 10, 50, 30)})
    lab_b = _labels(H, 60, {1: (10, 10, 20, 30)})        # cell B's frame starts at page x 30
    c.add_cell((0, 0, 60, H), lab_a, _claims(c1=(("head",), 1, "blob")))
    c.add_cell((30, 0, 90, H), lab_b, _claims(c1=(("head",), 1, "blob")))
    c.finish()
    t = c.tally()
    assert t["ink_px"] == 200
    assert t["stroke_px_deduped"] == 200                  # NOT 400
    assert t["naive_stroke_px"] == 400                    # what a per-cell sum would have said
    assert t["claimed_px_by_kind"] == {"head": 200}


def test_the_same_kind_from_two_boxes_is_a_twin_not_contested():
    c = _canvas([(40, 10, 50, 30)])
    c.add_cell((0, 0, 60, H), _labels(H, 60, {1: (40, 10, 50, 30)}), _claims(c1=(("head",), 1, "blob")))
    c.add_cell((30, 0, 90, H), _labels(H, 60, {1: (10, 10, 20, 30)}), _claims(c1=(("head",), 1, "blob")))
    c.finish()
    sp = c.tally()["state_px"]
    assert sp.get("twin") == 200 and "one" not in sp and not any(k.startswith("contested") for k in sp)


def test_states_one_contested_unclaimed():
    c = _canvas([(5, 5, 15, 15), (25, 5, 35, 15), (45, 5, 55, 15)])
    lab = _labels(H, W, {1: (5, 5, 15, 15), 2: (25, 5, 35, 15), 3: (45, 5, 55, 15)})
    claims = _claims(c1=(("head",), 1, "blob"), c2=(("head", "rest"), 2, "blob"), c3=((), 0, "vertical"))
    claims[2].open = True
    c.add_cell((0, 0, W, H), lab, claims)
    c.finish()
    sp = c.tally()["state_px"]
    assert sp["one"] == 100 and sp["contested_open"] == 100 and sp["unclaimed:vertical"] == 100
    assert ("unclaimed:vertical", 100) in CR.todo_list(c.tally())


def test_a_planted_double_claim_shows_as_contested_and_a_refused_claim_is_not_a_claim():
    c0 = _canvas([(5, 5, 15, 15)])
    claims = _claims(c1=(("head",), 1, "blob"))
    c0.add_cell((0, 0, W, H), _labels(H, W, {1: (5, 5, 15, 15)}), claims)
    c0.finish()
    assert not any(k.startswith("contested") for k in c0.tally()["state_px"])
    c1 = _canvas([(5, 5, 15, 15)])
    claims = _claims(c1=(("head",), 1, "blob"))
    assert CR.plant_double_claim(claims, "head", "rest") == [1]
    c1.add_cell((0, 0, W, H), _labels(H, W, {1: (5, 5, 15, 15)}), claims)
    c1.finish()
    assert c1.tally()["state_px"]["contested_settled"] == 100
    # a claim whose shape did not fit (`fit: no`) stands for nothing: the ink is "refused", not claimed
    class St:
        kind = "vertical"
    cl = CR.claims_for_cell([St()], {"strokes": {"0": ["refused_claims", None, [], "", [["glyph/0/0/0/0/1", "head", "noteheadBlackInSpace", "no", "x", "cover"]]]}}, {}, {})
    assert cl[1].kinds == set() and cl[1].refused


def test_claims_for_cell_counts_boxes_register_and_reads():
    class St:
        kind = "blob"
    verdict = {"strokes": {"0": ["decided", "arc_trace", ["obs:1"], "area", [["obs:1", "arc_trace", "arc", "clear", "area", "area"],
                                                                         ["glyph/0/0/0/0/3", "arc", "slur", "clear", "x", "cover"]]],
                           "1": ["decided", "head", ["glyph/0/0/0/0/4"], "single", [["glyph/0/0/0/0/4", "head", "noteheadBlackInSpace", "clear", "x", "cover"],
                                                                                  ["glyph/0/0/0/0/5", "head", "noteheadBlackInSpace", "clear", "x", "cover"]]]}}
    cl = CR.claims_for_cell([St(), St(), St()], verdict, {2: ["stem"]}, {2: ["beam"], 0: ["stem"]})
    assert cl[1].kinds == {"arc"} and cl[1].register == {"arc"} and cl[1].n_box == 1      # trace + a slur box: one kind, one box
    assert cl[2].kinds == {"head"} and cl[2].n_box == 2                                # two boxes: a twin
    assert cl[3].kinds == {"stem"} and cl[3].n_box == 1                                # the cv_lines read is ignored beside a box
    cl2 = CR.claims_for_cell([St()], {}, {}, {0: ["beam"]})
    assert cl2[1].kinds == {"beam"} and cl2[1].n_box == 0                              # a read claims ink nothing else does


def test_truth_classes_and_the_register_view():
    c = _canvas([(5, 5, 15, 15), (25, 5, 35, 15), (45, 5, 55, 15), (65, 5, 75, 15)])
    lab = _labels(H, W, {1: (5, 5, 15, 15), 2: (25, 5, 35, 15), 3: (45, 5, 75, 15)})
    # stroke 3 covers two truth boxes: half head, half unclaimed is NOT possible per stroke, so split by a second stroke
    lab[5:15, 65:75] = 4
    cl = _claims(c1=(("head",), 1, "blob"), c2=(("stem",), 1, "blob"), c3=(("head",), 1, "blob"), c4=((), 0, "blob"))
    cl[3].register = {"head"}
    c.add_cell((0, 0, W, H), lab, cl)
    c.finish()
    assert c.judge_box((5, 5, 15, 15), ("head",))["verdict"] == "right"
    assert c.judge_box((25, 5, 35, 15), ("head",))["verdict"] == "wrong_kind"
    assert c.judge_box((65, 5, 75, 15), ("head",))["verdict"] == "nothing"
    assert c.judge_box((25, 5, 75, 15), ("head",))["verdict"] == "split"
    assert c.judge_box((100, 40, 110, 50), ("head",))["verdict"] == "no_ink"
    assert c.judge_box((45, 5, 55, 15), ("head",), "register")["verdict"] == "right"
    assert c.judge_box((5, 5, 15, 15), ("head",), "register")["verdict"] == "nothing"      # claimed by a box, not by the register
    assert CR.TRUTH_KINDS["tie"] == ("arc",) and CR.TRUTH_KINDS["noteheadBlackOnLine"] == ("head",)


def test_staff_line_debris_and_outside_cells_are_named_not_claimed():
    c = _canvas([(5, 5, 15, 7), (30, 30, 40, 32), (90, 40, 100, 50), (100, 5, 110, 15)])
    lab = np.zeros((H, 80), np.int16)
    er = np.zeros((H, 80), bool)
    er[5:7, 5:15] = True                                  # the eraser took this raw ink: a staff line
    c.add_cell((0, 0, 80, H), lab, {}, er)
    c.add_area((98, 3, 112, 17), "word_dynamic")           # a READ margin word outside every cell
    c.finish()
    sp = c.tally()["state_px"]
    assert sp["staff_line"] == 20 and sp["debris"] == 20 and sp["outside_cells"] == 100 and sp["one"] == 100


def test_a_weak_area_is_reported_on_its_own():
    c = _canvas([(5, 5, 15, 15)])
    c.add_cell((0, 0, W, H), _labels(H, W, {1: (5, 5, 15, 15)}), _claims(c1=((), 0, "blob")))
    c.add_area((0, 0, 20, 20), "word_dynamic", weak=True)
    c.finish()
    assert c.tally()["state_px"] == {"weak_claim": 100}


def test_two_identical_inputs_give_identical_readouts():
    def build():
        c = _canvas([(5, 5, 15, 15), (40, 10, 50, 30)])
        c.add_cell((0, 0, 60, H), _labels(H, 60, {1: (5, 5, 15, 15), 2: (40, 10, 50, 30)}), _claims(c1=(("head",), 1, "blob"), c2=((), 0, "vertical")))
        c.finish()
        return c.tally()
    import json
    assert json.dumps(build(), sort_keys=True) == json.dumps(build(), sort_keys=True)


def test_resolve_source_refuses_the_big_record(tmp_path):
    big = tmp_path / "x.record.json"
    big.write_bytes(b"{}")
    import os
    os.truncate(big, CR.BIG_RECORD_BYTES + 1)
    try:
        CR.resolve_source(str(big))
    except SystemExit as e:
        assert "never loaded whole" in str(e)
    else:
        raise AssertionError("a record over 5 GB must be refused")


def test_nothing_in_it_names_a_pipeline_quantity_it_writes():
    import pathlib
    src = pathlib.Path(CR.__file__).read_text()
    assert "log.observe" not in src and "log.abstain" not in src


def test_unclaimed_line_shaped_ink_on_a_staff_line_is_residue_but_a_stem_crossing_it_is_not():
    c = _canvas([(5, 20, 60, 22), (30, 5, 32, 45)])
    lab = _labels(H, W, {1: (5, 20, 60, 22), 2: (30, 5, 32, 45)})
    c.add_cell((0, 0, W, H), lab, _claims(c1=((), 0, "horizontal"), c2=((), 0, "vertical")), None, [10.0, 15.0, 21.0, 26.0, 31.0])
    c.finish()
    sp = c.tally()["state_px"]
    assert sp.get("residue:horizontal", 0) > 0 and "residue:vertical" not in sp and sp["unclaimed:vertical"] > 0
