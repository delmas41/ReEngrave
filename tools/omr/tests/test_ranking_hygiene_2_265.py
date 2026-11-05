"""ROADMAP 2.265 -- ranking hygiene: the COUNTED view of a record (`benchmarks/acceptance/overnight/ranking/counted_view.py`) and the
rank table that reads it. Counting only: no reader, no record row. Synthetic records, no gather, no OCR."""
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
RANK = ROOT / "benchmarks" / "acceptance" / "overnight" / "ranking"
sys.path.insert(0, str(RANK))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, RANK / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CV = _load("counted_view")
RT = _load("rank_table")

from tools.omr.staged import export as E, stroke_map  # noqa: E402


def _obs(q, sub, value=None, detail=None, oid=None):
    return {"id": oid or "obs:%s:%s" % (q, sub), "subject": sub, "quantity": q, "value": value, "detail": detail or {}}


def _dot(sub, area_wh=(0.4, 0.3, 1.0), role=("abstained", "dot_role_ambiguous")):
    """A dot-class box `sub` with a MARK_SHAPE row of `w x h x fill` and a standing dot-role verdict."""
    w, h, f = area_wh
    rows = [_obs("aug_dot", sub, [1, 1]), _obs("mark_shape", sub, 0.5, {"w_spaces": w, "h_spaces": h, "fill": f})]
    v = {"id": "vrd:" + sub, "subject": sub, "quantity": "dot_role", "outcome": role[0], "reason": role[1], "value": None}
    return rows, v


def test_the_floor_is_the_stroke_maps_own_not_a_new_number():
    assert CV.SPECK_FLOOR_SP2 == stroke_map.MIN_AREA_SP2


def test_dot_specks_only_boxes_under_the_floor_with_a_shape_row_on_counted_pages():
    obs, vrd = [], []
    for sub, shape in (("glyph/2/0/0/0/1", (0.2, 0.2, 1.0)),      # 0.04 sp2: a speck
                       ("glyph/2/0/0/0/2", (0.4, 0.3, 1.0)),      # 0.12 sp2: a dot
                       ("glyph/2/0/0/0/3", (0.25, 0.2, 1.0)),     # 0.05 exactly: at the floor, not under it
                       ("glyph/1/0/0/0/4", (0.2, 0.2, 1.0))):     # a speck on the CONTEXT page: not counted
        o, v = _dot(sub, shape)
        obs += o
        vrd.append(v)
    obs.append(_obs("aug_dot", "glyph/2/0/0/0/5", [1, 1]))         # no shape row: cannot tell, never a speck
    vrd.append({"id": "vrd:5", "subject": "glyph/2/0/0/0/5", "quantity": "dot_role", "outcome": "abstained",
                "reason": "dot_role_ambiguous", "value": None})
    rec = E.Record({"record": {"observations": obs, "verdicts": vrd, "abstentions": []}})
    specks = CV.dot_specks(rec, {2})
    assert [s["subject"] for s in specks] == ["glyph/2/0/0/0/1"]
    assert CV.specks_in_row(specks) == 1


def test_specks_in_row_counts_only_the_row_the_ranking_prints():
    sp = [dict(outcome="abstained", reason="dot_role_ambiguous"), dict(outcome="abstained", reason="on_a_stroke"),
          dict(outcome="decided", reason="centred_and_offset_from_a_head")]
    assert CV.specks_in_row(sp) == 1


def test_drop_context_marks_leaves_the_counted_page_and_other_families_alone():
    rec = {"observations": [_obs("arc_box", "glyph/1/0/0/0/1"), _obs("arc_box", "glyph/2/0/0/0/1"), _obs("aug_dot", "glyph/1/0/0/0/2"),
                            _obs("glyph_box", "glyph/1/0/0/0/1"), _obs("cell_box", "cell/1/0/0/0")],
           "abstentions": [{"id": "abs:1", "subject": "glyph/1/0/0/0/1", "quantity": "arc_kind"}],
           "verdicts": [{"id": "v1", "subject": "glyph/1/0/0/0/1", "quantity": "tie_pair"},
                        {"id": "v2", "subject": "glyph/2/0/0/0/1", "quantity": "tie_pair"},
                        {"id": "v3", "subject": "glyph/1/0/0/0/1", "quantity": "duration"}]}
    gone = CV.drop_context_marks(rec, {1})
    assert [o["subject"] for o in rec["observations"] if o["quantity"] == "arc_box"] == ["glyph/2/0/0/0/1"]
    assert not [o for o in rec["observations"] if o["quantity"] == "aug_dot"]
    assert {o["quantity"] for o in rec["observations"]} >= {"glyph_box", "cell_box", "arc_box"}     # other families stay
    assert [v["id"] for v in rec["verdicts"]] == ["v2", "v3"]                                      # the page-1 tie_pair went, its duration stayed
    assert rec["abstentions"] == []
    assert gone["observations:arc_box"] == 1 and gone["verdicts:tie_pair"] == 1
    assert CV.drop_context_marks(rec, set()) == {}


def test_drop_context_marks_changes_what_a_family_count_sees():
    """The control that can fail: the exporter counts `Q.AUG_DOT` rows; with the context page's row left in the count is 2, left out it is 1."""
    rec = {"observations": [_obs("aug_dot", "glyph/1/0/0/0/1"), _obs("aug_dot", "glyph/2/0/0/0/1")], "abstentions": [], "verdicts": []}
    assert len(E.Record({"record": rec}).obs_of("aug_dot")) == 2
    CV.drop_context_marks(rec, {1})
    assert len(E.Record({"record": rec}).obs_of("aug_dot")) == 1


def test_counted_symbols_filters_hosts_red_bars_and_notes_not_written_by_page():
    hosts = [{"page": 1, "blue": True}, {"page": 2, "blue": True}, {"page": 2, "blue": False}, {"page": None, "blue": False}]
    loose = [{"page": 1}, {"page": 2}]
    report = {"bars_written_red": {"bars_list": [{"page": 1}, {"page": 2}, {"page": 2}]},
              "notes_not_written_by_system": {"1/0": {"no_pitch": 5}, "2/0": {"no_pitch": 2, "duration_abstained": 1}, "2/1": {"no_pitch": 4}}}
    h, lo, red, blue, nnw = CV.counted_symbols(hosts, loose, report, {2})
    assert (len(h), len(lo), red, blue, nnw) == (3, 1, 2, 1, 7)        # the page-less host stays; page 1 is context


def test_rank_table_dots_row_is_the_ambiguous_count_less_the_specks(tmp_path):
    def rank(raw, specks):
        return {"rows": {}, "totals_over_loaded_pages": {"arcs_not_written": {}, "dot_role_not_placed": {"abstained_dot_role_ambiguous": raw},
                                                           "dot_specks_in_the_dots_row": specks}}
    p = tmp_path / "x.rank.json"
    p.write_text(json.dumps(rank(68, 17)))
    assert RT.kinds(str(p))[RT.DOTS_KIND] == 51
    p.write_text(json.dumps({"rows": {}, "totals_over_loaded_pages": {"arcs_not_written": {}, "dot_role_not_placed": {"abstained_dot_role_ambiguous": 68}}}))
    assert RT.kinds(str(p))[RT.DOTS_KIND] == 68                         # a pre-2.265 rank file: the raw count, never a guess
