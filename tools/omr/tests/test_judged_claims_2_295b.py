"""ROADMAP 2.295b: the two checking tools (`claim_readout ink`, `judged_claims`) SEE claims filed as page-stroke ids.

The rows are REAL: `fixtures/judged_claims_2295b_brahms_p14_r3.json` is cut from the 2.288 r3 gather of Brahms p14 (tree f4a59088c, `OMR_PAGE_CLAIM_RESTS=1`): the
`page_boxes` rest claim on stroke 2494 (a READ whole rest filed on Sean's EIGHTH NOTE, 2.288 r3 tile 4), the one on stroke 4478 (a real whole rest, tile 2, that
the cell settle owns as a beam), and one claim of each other page-stroke owner (arc, tremolo, own-ink accidental). Only the dark pixels are drawn (a solid mark on
each real stroke box): nothing here reads `library/`, so the file is in the fast tier."""
import json
import pathlib

import numpy as np
import pytest

from tools.omr.staged import claim_readout as CR
from tools.omr.staged import judged_claims as JC

FX = json.loads((pathlib.Path(__file__).parent / "fixtures" / "judged_claims_2295b_brahms_p14_r3.json").read_text())
ROWS = {"observations": FX["claim_rows"] + FX["page_stroke_rows"]}
TILE4 = FX["tiles"]["r3_tile4_eighth_note"]        # Sean: "eighth note"
TILE2 = FX["tiles"]["r3_tile2_whole_rest"]         # Sean: "whole rest"
PAD = 60


def _window(tile):
    """The page window round one tile: (x0, y0, w, h); everything below is drawn in window coordinates (a 7000 x 5000 canvas would be a gigabyte)."""
    return tile[0] - PAD, tile[1] - PAD, (tile[2] - tile[0]) + 2 * PAD, (tile[3] - tile[1]) + 2 * PAD


def _shift(box, win):
    return [box[0] - win[0], box[1] - win[1], box[2] - win[0], box[3] - win[1]]


def _tile(kind, box, words, win):
    return {"id": "2.288 r3 #x", "lane": "2.288 r3", "plate": "brahms", "page": 14, "box": _shift(box, win), "words": words, "kind": kind}


def _canvas(tile, cell_kind=None, stroke_claims=True, open_tile=False, rows=ROWS):
    """A finished LedgerInk of the window round `tile`: ink = every real page-stroke box of the fixture there; `cell_kind` = what the cell settle names over the
    tile (inside a cell); page-stroke claims from the REAL rows through the shared reader and the bbox resolver."""
    win = _window(tile)
    boxes = {i: _shift(b, win) for i, b in CR.page_stroke_boxes(rows).items()}
    ink = np.zeros((win[3], win[2]), bool)
    for b in boxes.values():
        ink[max(0, b[1]):max(0, b[3]), max(0, b[0]):max(0, b[2])] = True
    c = CR.LedgerInk(ink)
    c.incell[:] = True
    x0, y0, x1, y1 = _shift(tile, win)
    if cell_kind:
        c.fam[y0:y1, x0:x1] |= CR.FINE_BIT[cell_kind]
    if open_tile:
        c.open[y0:y1, x0:x1] = True
    if stroke_claims:
        cl = CR.page_stroke_claims(rows)
        ys, xs, ids = CR.stroke_ids_on_ink(c.ink, boxes, sorted({i for k in cl for i in k["ids"]}))
        c.add_page_strokes(cl, ys, xs, ids, "bbox_approximation (test)")
    c.finish()
    return c


def test_the_shared_reader_finds_every_page_stroke_owner_in_the_real_rows():
    cl = CR.page_stroke_claims(ROWS)
    by = {(k["source"], k["kind"]): k for k in cl}
    assert ("page_boxes", "rest") in by and ("system_arc", "arc") in by and ("page_tremolo", "tremolo") in by
    assert ("page_accidental_ink", "accidental") in by          # `accidental_ink` is mapped (it was filed under `other`)
    assert CR.fine_of("accidental_ink") == "accidental"
    assert sorted(i for k in cl if k["source"] == "page_boxes" for i in k["ids"]) == [2494, 4478]
    assert all(not k["weak"] for k in cl)


def test_a_claim_naming_a_stroke_an_earlier_claim_holds_keeps_only_the_first_and_a_bool_is_not_an_id():
    rest = [o for o in FX["claim_rows"] if o["detail"].get("source") == "page_boxes" and 2494 in o["detail"]["page_strokes"]][0]
    late = {"id": "late", "subject": "page/14", "quantity": "claimed_area", "value": [0, 0], "detail": {"owner": "dynamic", "page_strokes": [2494, 99999]}}
    bad = {"id": "bad", "subject": "page/14", "quantity": "claimed_area", "value": [0, 0], "detail": {"owner": "dynamic", "page_strokes": [True, 5]}}
    got = CR.page_stroke_claims({"observations": [rest, late, bad]})
    assert [(k["owner"], k["ids"]) for k in got] == [("whole_rest", [2494]), ("dynamic", [99999])]


def test_REAL_CATCH_the_r3_whole_rest_claimed_on_Seans_eighth_note_CONTRADICTS_and_names_the_page_stroke_claim():
    c = _canvas(TILE4, "notehead")
    r = JC.judge_tile(c, _tile("notehead", TILE4, "eighth note", _window(TILE4)))
    assert r["verdict"] == "contradicts" and r["twice"]
    assert r["sources"]["rest"] == {"page-stroke claim": 1.0}
    assert r["sources"]["notehead"] == {"cell settle": 1.0}
    assert r["wrong_any"] >= 0.9


def test_the_control_fails_where_it_must_without_the_page_stroke_claim_the_same_tile_AGREES_the_blindness_of_2_295():
    c = _canvas(TILE4, "notehead", stroke_claims=False)
    r = JC.judge_tile(c, _tile("notehead", TILE4, "eighth note", _window(TILE4)))
    assert r["verdict"] == "agrees" and not r["twice"]


def test_the_real_whole_rest_the_cell_settle_owns_as_a_beam_reads_claimed_twice_rest_and_beam_not_beam_100():
    c = _canvas(TILE2, "beam")
    r = JC.judge_tile(c, _tile("rest:whole", TILE2, "whole rest", _window(TILE2)))
    assert (r["verdict"], r["twice"]) == ("contradicts", True)
    assert r["sources"]["rest"] == {"page-stroke claim": 1.0} and r["sources"]["beam"] == {"cell settle": 1.0}
    assert r["right"] >= 0.9                                    # his kind DOES own it, by the page-stroke claim


def test_a_page_stroke_claim_of_the_same_kind_as_the_cell_settle_is_one_owner_not_two():
    c = _canvas(TILE2, "rest")
    r = JC.judge_tile(c, _tile("rest:whole", TILE2, "whole rest", _window(TILE2)))
    assert r["verdict"] == "agrees" and r["wrong_any"] == 0.0
    assert c.tally()["twice"]["page_not_consulted_px"] == 0


def test_ink_the_cell_settle_left_open_between_kinds_is_not_a_standing_wrong_claim():
    c = _canvas(TILE2, "beam", stroke_claims=False, open_tile=True)
    x0, y0, x1, y1 = _shift(TILE2, _window(TILE2))
    c.fam[y0:y1, x0:x1] |= CR.FINE_BIT["rest"]
    c.finish()
    r = JC.judge_tile(c, _tile("rest:whole", TILE2, "whole rest", _window(TILE2)))
    assert r["verdict"] == "agrees" and r["open_share"] >= 0.9


def test_the_readout_counts_the_gap_as_its_own_subline_by_pair_and_the_four_lines_still_sum_to_the_ink():
    for tile, kind, pair in ((TILE4, "notehead", "page rest / cell notehead"), (TILE2, "beam", "page rest / cell beam")):
        t = _canvas(tile, kind).tally()                         # verify_tally ran inside: it raises if a line or a sub-line does not add up
        assert sum(t["lines"].values()) == t["ink_px"]
        tw = t["twice"]
        assert tw["page_not_consulted_px"] > 0 and sum(tw["page_not_consulted_pairs"].values()) == tw["page_not_consulted_px"]
        assert pair in tw["page_not_consulted_pairs"]
        assert tw["twin_px"] + tw["twin_views_px"] + tw["two_kinds_px"] + tw["views_disagree_px"] + tw["page_not_consulted_px"] == tw["px"]
        assert any("PAGE-STROKE claim the cell settle did not consult" in x for x in CR.render_ink_number("t", t))


def test_a_page_stroke_claim_is_a_ledger_claim_and_alone_on_a_pixel_it_is_one_owner():
    t = _canvas(TILE2).tally()
    assert t["twice"]["page_not_consulted_px"] == 0
    assert t["one"]["by_kind_ledger"].get("rest", 0) > 0 and t["one"]["by_kind_cell"].get("rest", 0) == 0


def test_a_GUESSED_page_stroke_claim_is_weak_not_a_READ_owner():
    weak_rows = json.loads(json.dumps(ROWS))
    for o in weak_rows["observations"]:
        if (o.get("detail") or {}).get("source") == "page_boxes":
            o["detail"]["standing"] = "GUESSED"
    c = _canvas(TILE2, rows=weak_rows)
    r = JC.judge_tile(c, _tile("rest:whole", TILE2, "whole rest", _window(TILE2)))
    assert r["verdict"] == "unclaimed" and r["weak_kinds"].get("rest", 0) > 0.9


def test_area_claims_skip_a_resolved_row_and_a_value_that_is_its_own_stroke_ids():
    four = {"id": "t4", "subject": "page/14", "quantity": "claimed_area", "value": [1, 2, 3, 4],
            "detail": {"owner": "tremolo", "unit": "page_ink", "standing": "READ", "page_strokes": [1, 2, 3, 4]}}
    rect = {"id": "ac", "subject": "page/14", "quantity": "claimed_area", "value": [10.0, 20.0, 30.0, 40.0],
            "detail": {"owner": "accidental_ink", "unit": "page_ink", "standing": "READ", "page_strokes": [7, 8]}}
    assert CR.area_claims_fine({"observations": [four, rect]}) == [{"rect": [10.0, 20.0, 30.0, 40.0], "kind": "accidental", "owner": "accidental_ink", "weak": False}]
    assert CR.area_claims_fine({"observations": [four, rect]}, skip_rows=["ac"]) == []


def test_the_bbox_resolver_gives_a_pixel_to_the_smallest_stroke_box_that_holds_it():
    ink = np.ones((20, 20), bool)
    boxes = {0: [0, 0, 20, 20], 1: [5, 5, 10, 10]}
    ys, xs, ids = CR.stroke_ids_on_ink(ink, boxes, [0, 1])
    assert {i: int((ids == i).sum()) for i in (0, 1)} == {1: 25, 0: 400 - 25}


def test_the_exact_path_refuses_a_page_map_that_differs_from_the_record(monkeypatch):
    class Stroke:
        box = (0, 0, 5, 5)

    class PM:
        strokes = [Stroke()]
    from tools.omr.staged import page_strokes as PS
    monkeypatch.setattr(PS, "map_page", lambda *a, **k: PM())
    labels, why = CR.exact_stroke_labels({"observations": FX["page_stroke_rows"]}, None, [], {}, {}, {})
    assert labels is None and why.startswith("page_map_differs_from_record")
