"""ROADMAP 2.241 -- the claim-order check. Pure canvas tests (no PDF, no record): the layers, the classes, the planted controls that must be
able to fail. The real-page runs are in benchmarks/capture-readout-2026-10/FINDINGS.md (2.241 section)."""
import numpy as np

from tools.omr.staged import claim_order as CO
from tools.omr.staged import claim_readout as CR
from tools.omr.staged import stroke_owner as SO
from tools.omr.staged.claim_order import OrderCanvas, OrderInfo

H, W = 60, 120
L = {n: i for i, n in enumerate(CO.LAYER_NAMES)}


def test_every_family_the_stroke_owner_names_has_a_layer():
    fams = {f for t in SO.TIERS for f in t} | set(SO.CONSUMERS)
    missing = sorted(f for f in fams if CO.layer_of(f) is None)
    assert missing == []


def test_the_order_is_the_plans():
    names = CO.LAYER_NAMES
    # staff, structure, header, words, arcs, (whole rest), heads, stems, accidentals, rests, dots
    assert names.index("barline_bracket") < names.index("clef_key_meter") < names.index("word_dynamic") < names.index("arc_hairpin")
    assert names.index("arc_hairpin") < names.index("head") < names.index("stem_beam_flag") < names.index("accidental")
    assert names.index("accidental") < names.index("rest") < names.index("dot_mark")
    assert names.index("whole_rest") < names.index("head")          # DECISIONS 2026-10-29: a whole rest claims before heads


def _canvas(ink_boxes):
    ink = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in ink_boxes:
        ink[y0:y1, x0:x1] = True
    return CR.PageInk(ink)


def _labels(boxes):
    lab = np.zeros((H, 60), np.int16)
    for i, (x0, y0, x1, y1) in boxes.items():
        lab[y0:y1, x0:x1] = i
    return lab


def _run(ink_boxes, label_boxes, info):
    base = _canvas(ink_boxes)
    oc = OrderCanvas(base)
    base.add_cell((0, 0, 60, H), _labels(label_boxes), {i: CR.StrokeClaims(kinds={"head"}, n_box=1) for i in label_boxes})
    oc.add_cell((0, 0, 60, H), _labels(label_boxes), info)
    base.finish()
    oc.finish()
    return oc


def _px(oc, cls):
    return int(((oc.cls == CO.CLASSES.index(cls)) & oc.mask).sum())


def test_classify_the_five_cases():
    r = lambda *ls: sum(1 << L[l] for l in ls)
    assert CO.classify(0, CO.NO_OWNER, False)[0] == CO.C_NONE
    assert CO.classify(r("word_dynamic", "head"), L["word_dynamic"], False)[0] == CO.C_OK
    assert CO.classify(r("head"), L["head"], False)[0] == CO.C_SOLE
    c, pair = CO.classify(r("word_dynamic", "head"), L["head"], False)
    assert (c, pair) == (CO.C_VIOL, (L["word_dynamic"], L["head"]))
    assert CO.classify(r("word_dynamic", "head"), CO.NO_OWNER, False)[0] == CO.C_OPEN
    assert CO.classify(r("head"), L["head"], True)[0] == CO.C_SPLIT


def test_a_head_that_owns_ink_a_word_read_is_a_violation_word_to_head():
    oc = _run([(10, 10, 20, 20)], {1: (10, 10, 20, 20)}, {1: OrderInfo(read={L["word_dynamic"], L["head"]}, owner=L["head"])})
    t = oc.tally()
    assert t["class_px"]["ORDER-VIOLATION"] == 100
    assert t["by_pair"]["ORDER-VIOLATION"] == {"word_dynamic->head": 100}


def test_the_earliest_reader_owning_it_is_ok_and_a_sole_reader_is_earlier_unread():
    oc = _run([(10, 10, 20, 20), (30, 10, 40, 20)], {1: (10, 10, 20, 20), 2: (30, 10, 40, 20)},
              {1: OrderInfo(read={L["word_dynamic"], L["head"]}, owner=L["word_dynamic"]), 2: OrderInfo(read={L["head"]}, owner=L["head"])})
    t = oc.tally()
    assert t["class_px"]["ORDER-OK"] == 100 and t["class_px"]["EARLIER-UNREAD"] == 100 and t["class_px"]["ORDER-VIOLATION"] == 0
    assert t["by_pair"]["EARLIER-UNREAD"] == {"head": 100}


def test_read_by_two_and_owned_by_nobody_is_open_and_unread_ink_is_no_reader():
    oc = _run([(10, 10, 20, 20), (30, 10, 40, 20)], {1: (10, 10, 20, 20), 2: (30, 10, 40, 20)},
              {1: OrderInfo(read={L["arc_hairpin"], L["head"]}, owner=None, open=True), 2: OrderInfo()})
    t = oc.tally()
    assert t["class_px"]["OPEN"] == 100 and t["class_px"]["NO-READER"] == 100
    assert t["by_pair"]["OPEN"] == {"arc_hairpin|head": 100}


def test_the_planted_head_over_words_control_can_fail_and_can_pass():
    mk = lambda: {1: OrderInfo(read={L["word_dynamic"]}, owner=L["word_dynamic"])}
    before = _run([(10, 10, 20, 20)], {1: (10, 10, 20, 20)}, mk()).tally()
    assert "word_dynamic->head" not in before["by_pair"].get("ORDER-VIOLATION", {})
    info = mk()
    assert CO.plant_head_over_words(info) == 1
    after = _run([(10, 10, 20, 20)], {1: (10, 10, 20, 20)}, info).tally()
    assert after["by_pair"]["ORDER-VIOLATION"] == {"word_dynamic->head": 100}
    # a page with no word-owned stroke: the plant touches nothing, so the control would FAIL there (it must be able to)
    none = {1: OrderInfo(read={L["head"]}, owner=L["head"])}
    assert CO.plant_head_over_words(none) == 0


def test_identical_rows_read_identically():
    mk = lambda: {1: OrderInfo(read={L["word_dynamic"], L["head"]}, owner=L["head"])}
    a = _run([(10, 10, 20, 20)], {1: (10, 10, 20, 20)}, mk()).tally()
    b = _run([(10, 10, 20, 20)], {1: (10, 10, 20, 20)}, mk()).tally()
    assert a == b


def test_a_clef_cut_into_pieces_is_split_across_claim_and_the_largest_piece_is_not():
    base = _canvas([(10, 10, 30, 40), (10, 41, 30, 50)])           # one clef claim [5, 5, 35, 55]: a 20x30 body and a 20x9 tip below it
    oc = OrderCanvas(base)
    oc.set_areas([{"rect": [5, 5, 35, 55], "owner": "clef", "kind": "clef_key_meter", "weak": False}])
    lab = _labels({1: (10, 10, 30, 40), 2: (10, 41, 30, 50)})
    info = {1: OrderInfo(read={L["clef_key_meter"]}, owner=L["clef_key_meter"]), 2: OrderInfo(read={L["clef_key_meter"]}, owner=L["clef_key_meter"])}
    base.add_cell((0, 0, 60, H), lab, {i: CR.StrokeClaims(kinds={"clef_key_meter"}) for i in (1, 2)})
    oc.add_cell((0, 0, 60, H), lab, info)
    base.finish()
    oc.finish()
    t = oc.tally()
    assert t["class_px"]["SPLIT-ACROSS-CLAIM"] == 180             # the 20x9 tip, not the 600 px body
    assert t["by_pair"]["SPLIT-ACROSS-CLAIM"] == {"clef_key_meter": 180}
    assert len(oc.split_pieces) == 1 and oc.split_pieces[0]["box"] == [10, 41, 30, 50]
    # a clef held in ONE stroke is not split
    base2 = _canvas([(10, 10, 30, 50)])
    oc2 = OrderCanvas(base2)
    oc2.set_areas([{"rect": [5, 5, 35, 55], "owner": "clef", "kind": "clef_key_meter", "weak": False}])
    lab2 = _labels({1: (10, 10, 30, 50)})
    base2.add_cell((0, 0, 60, H), lab2, {1: CR.StrokeClaims(kinds={"clef_key_meter"})})
    oc2.add_cell((0, 0, 60, H), lab2, {1: OrderInfo(read={L["clef_key_meter"]}, owner=L["clef_key_meter"])})
    base2.finish()
    oc2.finish()
    assert oc2.tally()["class_px"]["SPLIT-ACROSS-CLAIM"] == 0


def test_a_word_box_reads_a_stroke_only_when_half_the_stroke_is_inside_it():
    base = _canvas([(10, 10, 20, 20), (30, 10, 50, 20)])
    oc = OrderCanvas(base)
    oc.add_reader_boxes([[8, 8, 35, 22]], L["word_dynamic"])       # holds all of stroke 1, a quarter of stroke 2 (x 30..35 of 30..50)
    lab = _labels({1: (10, 10, 20, 20), 2: (30, 10, 50, 20)})
    base.add_cell((0, 0, 60, H), lab, {i: CR.StrokeClaims(kinds={"head"}) for i in (1, 2)})
    oc.add_cell((0, 0, 60, H), lab, {i: OrderInfo(read={L["head"]}, owner=L["head"]) for i in (1, 2)})
    base.finish()
    oc.finish()
    assert oc.tally()["by_pair"]["ORDER-VIOLATION"] == {"word_dynamic->head": 100}      # stroke 1 only


def test_order_for_cell_reads_candidates_the_shape_did_not_refuse_and_lets_a_consumer_take_an_unclaimed_stroke():
    class S:  # a stroke stand-in
        kind = "vertical"
    verdict = {"strokes": {
        "0": ["decided", "head", ["g"], "shape", [["g", "head", "noteheadBlack", "clear", "", "cover"], ["h", "dynamic", "dynamicF", "could", "", "cover"]]],
        "1": ["refused_claims", None, [], "shape", [["g", "head", "noteheadBlack", "no", "", "cover"]]],
        "2": ["contested", None, [], "", [["g", "head", "x", "could", "", "cover"], ["h", "accidental", "y", "could", "", "cover"]]],
    }}
    info = CO.order_for_cell([S(), S(), S()], verdict, {1: ["stem"]}, {})
    assert info[1].read == {L["head"], L["word_dynamic"]} and info[1].owner == L["head"]
    assert info[2].read == {L["stem_beam_flag"]} and info[2].owner == L["stem_beam_flag"]        # the refused head is not a read; the stem box takes it
    assert info[3].open and info[3].owner is None and info[3].read == {L["head"], L["accidental"]}


def test_a_flag_off_arm_drops_only_the_claim_rows_not_the_readers_rows():
    rows = {"observations": [
        {"quantity": "claimed_area", "detail": {"owner": "word"}}, {"quantity": "claimed_area", "detail": {"owner": "clef"}},
        {"quantity": "direction_word", "detail": {"bbox_page_px": [1, 2, 3, 4]}}], "abstentions": [], "verdicts": []}
    off = CO.apply_flag_arm(rows, {"OMR_CLAIM_WORDS_FIRST": "0"})
    assert [r["quantity"] for r in off["observations"]] == ["claimed_area", "direction_word"]
    assert off["observations"][0]["detail"]["owner"] == "clef"
    assert CO.apply_flag_arm(rows, {}) is rows
    assert CO.reader_boxes(off) == [[1.0, 2.0, 3.0, 4.0]]


def test_code_agrees_tells_where_the_codes_own_tier_order_differs_from_the_plan():
    assert CO.code_agrees(L["arc_hairpin"], L["head"]) is False       # the code lists heads (tier 2) before arcs (tier 4); the plan, arcs first
    assert CO.code_agrees(L["word_dynamic"], L["arc_hairpin"]) is False  # dynamic boxes are tier 5, after arcs
    # heads are tier 2, accidentals tier 3, dots tier 5 in `stroke_owner.TIERS`; the consumers come last in the code, so stem -> accidental differs
    assert CO.code_agrees(L["head"], L["accidental"]) is True
    assert CO.code_agrees(L["stem_beam_flag"], L["accidental"]) is False


def test_choose_tiles_takes_the_biggest_pairs_round_robin_and_keeps_tiles_apart():
    mk = lambda pair, px, x: {"page": "p", "box": [x, 0, x + 10, 10], "ink_px": px, "pair": pair}
    pool = [mk("a->b", 900, 0), mk("a->b", 800, 500), mk("c->d", 100, 1000), mk("e->f", 50, 1500), mk("a->b", 700, 2000)]
    got = CO.choose_tiles(pool, 4)
    assert [g["pair"] for g in got] == ["a->b", "c->d", "e->f", "a->b"]
    assert CO.choose_tiles([mk("a->b", 900, 0), mk("a->b", 800, 50)], 4)[0]["ink_px"] == 900 and len(CO.choose_tiles([mk("a->b", 900, 0), mk("a->b", 800, 50)], 4)) == 1
