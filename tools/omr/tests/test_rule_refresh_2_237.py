"""ROADMAP 2.237: the rule-page refresh tools (fresh fire counts beside the 10-22 ones; parity with the stroke owner).

Pure: constructed verdict dumps, no record, no gather.  Controls that can fail: a box the owner OWNS must read `disagrees`, a box it
refuses must read `same`, a twin it merges must read `merged`, and a missing fresh file must print `-` rather than zero.
"""
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
RULE_DIR = ROOT / "benchmarks" / "rule-page"
sys.path.insert(0, str(RULE_DIR))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, RULE_DIR / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RP = _load("rule_parity")
REPLAY = _load("replay_slice")
B = _load("build_rule_page")


def _v(i, subject, quantity, reason, outcome="decided", value=True, margin=None, detail=None):
    return dict(id="vrd:%d" % i, subject=subject, quantity=quantity, outcome=outcome, value=value, decider="d", reason=reason,
                margin=margin, detail=detail or {}, supersedes=None)


def test_count_verdicts_counts_each_live_verdict_once():
    vs = [_v(1, "glyph/0/0/0/0/1", "notehead_is_not_a_notehead", "is_a_rest_twin"),
          _v(2, "glyph/0/0/0/0/2", "notehead_is_not_a_notehead", "is_a_rest_twin")]
    out = REPLAY.count_verdicts(vs)
    assert out["verdicts_total"] == 2
    assert out["rows"][0]["n"] == 2


def test_parity_same_disagrees_merged_silent(tmp_path):
    cell = "cell/0/0/0/0"
    q, r = "notehead_is_not_a_notehead", "is_a_rest_twin"
    rows = [
        _v(1, "glyph/0/0/0/0/1", q, r, margin=0.01),        # ownership refuses it   -> same
        _v(2, "glyph/0/0/0/0/2", q, r, margin=0.30),        # ownership decided it   -> disagrees
        _v(3, "glyph/0/0/0/0/3", q, r),                     # ownership merged it    -> merged
        _v(4, "glyph/0/0/0/0/4", q, r),                     # ownership says nothing -> silent
        _v(5, cell, "stroke_owner", "strokes_owned", value={}, detail={
            "boxes": {"glyph/0/0/0/0/1": ["refused", []]},
            "strokes": {"0": ["decided", "head", ["glyph/0/0/0/0/2"], "shape", []],
                        "1": ["merged", "head", ["glyph/0/0/0/0/3"], "shape", []]}}),
    ]
    (tmp_path / "litolff.verdicts.jsonl").write_text("\n".join(json.dumps(x) for x in rows))
    res = RP.run(str(tmp_path), 0.05)["litolff"]
    c = res["per"]["%s|%s" % (q, r)]
    assert (c["same"], c["disagrees"], c["merged"], c["silent"]) == (1, 1, 1, 1)
    assert (c["with_margin"], c["near"]) == (2, 1)       # 0.01 is inside the 0.05 noise, 0.30 is not
    assert res["ownership_only"] == {}                    # the one refused box WAS refused by a scoped rule


def test_ownership_only_boxes_are_counted(tmp_path):
    rows = [_v(1, "cell/0/0/0/0", "stroke_owner", "strokes_owned", value={}, detail={"boxes": {"glyph/0/0/0/0/9": ["contested", []]}})]
    (tmp_path / "brahms.verdicts.jsonl").write_text("\n".join(json.dumps(x) for x in rows))
    assert RP.run(str(tmp_path), 0.05)["brahms"]["ownership_only"] == {"contested": 1}


def test_stacked_duplicate_margin_is_the_ink_gap(tmp_path):
    d = {"stacked_head_this_ink": "0.78", "stacked_head_other_ink": "0.79"}
    rows = [_v(1, "glyph/0/0/0/0/1", "notehead_is_not_a_notehead", "stacked_head_duplicate", detail=d)]
    (tmp_path / "litolff.verdicts.jsonl").write_text("\n".join(json.dumps(x) for x in rows))
    c = RP.run(str(tmp_path), 0.05)["litolff"]["per"]["notehead_is_not_a_notehead|stacked_head_duplicate"]
    assert (c["with_margin"], c["near"]) == (1, 1)


def test_fresh_counts_absent_print_a_dash_not_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "HERE", tmp_path)
    assert B.load_fresh("nope") is None
    assert B.fresh_cell(None, "x", ["y"]) == "-"


def test_fresh_counts_load_and_sum(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "HERE", tmp_path)
    for plate, n in (("litolff", 3), ("brahms", 5)):
        (tmp_path / ("fires-%s-T.json" % plate)).write_text(json.dumps(
            {"verdicts_total": 9, "superseded": 0, "pages": [1],
             "rows": [{"decider": "dd", "outcome": "decided", "reason": "rr", "value": True, "n": n}]}))
    fresh = B.load_fresh("T")
    assert B.fresh_cell(fresh, "dd", ["rr"]) == "3 / 5"
    assert B.fresh_cell(fresh, "dd", ["other"]) == "0 / 0"      # a reason that did not fire is 0, a missing file is "-"
    assert B.fresh_total(fresh, "dd") == "3 / 5"
