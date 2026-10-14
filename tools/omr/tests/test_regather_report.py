"""ROADMAP 2.118: the detailed re-gather report, on a small synthetic record.

RED-first controls: a funnel that balances, an imbalance that is REPORTED
(never hidden), a guessed symbol with its margin band, bars by state.
"""
from tools.omr.staged import regather_report as RR


def _vid():
    n = [0]

    def f():
        n[0] += 1
        return f"vrd:{n[0]:06d}"
    return f


def _record():
    """Six notehead boxes on staff 0 of system 0 (cells 0..5):
    g0 refused as too narrow, g1 and g2 decided, g3 narrowed then settled by
    INFER (a guess), g4 abstained, g5 kept with no duration verdict at all."""
    vid = _vid()
    obs, vs = [], []
    for g in range(6):
        obs.append({"id": f"obs:{g}", "subject": f"glyph/1/0/0/{g}/0", "quantity": "glyph_box",
                    "value": ["noteheadBlack", 10, 10, 8, 8], "reader": "detector"})

    def v(sub, q, outcome, value, decider, reason, **kw):
        row = {"id": vid(), "subject": sub, "quantity": q, "outcome": outcome, "value": value,
               "decider": decider, "reason": reason, "candidates": [], "supersedes": None,
               "margin": None, "detail": {}, "basis": [], "used": []}
        row.update(kw)
        vs.append(row)
        return row
    S = lambda g: f"glyph/1/0/0/{g}/0"
    v(S(0), "notehead_is_not_a_notehead", "decided", True, "adjudicate_notehead_is_not_a_notehead", "too_narrow",
      margin=-0.2, detail={"margin_unit": "staff_spaces"})
    for g in (1, 2, 3, 4, 5):
        v(S(g), "notehead_is_not_a_notehead", "decided", False, "adjudicate_notehead_is_not_a_notehead", "notehead")
    dur = {"beats": 1.0, "written": 1.0, "dots": 0, "beam_levels": 0}
    v(S(1), "duration", "decided", dur, "adjudicate_duration", "head_and_marks")
    v(S(2), "duration", "decided", dur, "adjudicate_duration", "head_and_marks")
    nar = v(S(3), "duration", "narrowed", None, "adjudicate_duration", "beams_ambiguous",
            candidates=[{"value": dur, "support": 2.0}, {"value": dict(dur, beats=0.5), "support": 1.0}],
            margin=-0.1, detail={"margin_unit": "ratio"})
    v(S(3), "duration", "decided", dur, "infer:collapse_narrowed_by_bar", "the_bar_names_it",
      supersedes=nar["id"], candidates=nar["candidates"])
    v(S(4), "duration", "abstained", None, "adjudicate_duration", "owned_by_another_staff",
      margin=-0.9, detail={"margin_unit": "ratio"})
    return {"record": {"observations": obs, "abstentions": [], "verdicts": vs, "counts": {}},
            "provenance": {"commit": "abc", "dirty": False}, "adjudication": {}}


def _funnel(facts, name):
    return next(f for f in facts["funnels"] if f["name"] == name)


def test_funnel_balances_and_counts_every_box():
    f = _funnel(RR.extract_facts(_record()), "noteheads: how long")
    assert (f["boxes"], f["refused_total"], f["decided"], f["narrowed"],
            f["abstained"], f["no_verdict"]) == (6, 1, 3, 0, 1, 1)
    assert f["balance"]["balanced"] and f["balance"]["imbalance"] == 0
    assert f["stage_balance"]["balanced"]


def test_stage_flow_shows_who_settled_what():
    f = _funnel(RR.extract_facts(_record()), "noteheads: how long")
    assert f["adjudicate_said"] == {"decided": 2, "narrowed": 1, "abstained": 1}
    assert f["then"]["settled by INFER"] == 1 and f["then"]["stays"] == 3
    assert f["guessed_at_glyph_level"] == 1          # the INFER collapse


def test_an_imbalance_is_reported_not_hidden():
    bad = RR._balance("x", 10, {"a": 3, "b": 4})
    assert not bad["balanced"] and bad["imbalance"] == 3
    facts = RR.extract_facts(_record())
    facts["funnels"][0]["balance"] = bad
    rep = RR.build_report(facts, {"families": []}, None, "t")
    md = RR.render_md(rep)
    assert "IMBALANCE +3" in md
    # the control can fail: a balanced ledger prints no such word
    cov = {"families": [], "notes_not_written": {"not_a_notehead:too_narrow": 1}}
    clean = RR.render_md(RR.build_report(RR.extract_facts(_record()), cov, None, "t"))
    assert "IMBALANCE" not in clean.split("## 9.")[1]
    # and the exporter dropping a different number than the record refused IS a finding
    cov["notes_not_written"]["not_a_notehead:too_narrow"] = 0
    off = RR.render_md(RR.build_report(RR.extract_facts(_record()), cov, None, "t"))
    assert "IMBALANCE" in off.split("## 9.")[1]


def test_margin_bands_and_missing_margins_are_counted():
    m = RR.extract_facts(_record())["margins"]
    assert m["refusals_total"] == 2 and m["with_a_margin"] == 2
    b = RR._margin_bands([-0.1, -0.5, -0.9, -2.0, -5.0, -9.0])
    assert (b["near"], b["middle"], b["far"]) == (2, 2, 2)
    assert RR._margin_bands([]) == {}


def test_guess_rules_and_candidates_are_reported():
    g = RR.extract_facts(_record())["guessed"]
    assert g["by_infer_rule"] == {"collapse_narrowed_by_bar": 1}
    assert g["candidates_per_infer_guess"] == {"2": 1}
    assert g["support_gap_of_infer_guess"] == {"gap 1": 1}


def test_bars_by_state():
    cov = {"partial_bars": {"written": 1, "bars": [
               {"part": "P1", "measure": 2, "status": "partial"},
               {"part": "P1", "measure": 3, "status": "held", "why": "voice_overfull"}]},
           "bars_held_out_sum": {"bars": 2, "held": [{"part": "P2", "measure": 1},
                                                    {"part": "P1", "measure": 3}]},
           "unread_bar_marks": {"unread": 1}}
    cells = {"P1|1": dict(notes=2, rests=0, blue_notes=0, blue_other=0, red=0, unread_words=0),
             "P1|2": dict(notes=3, rests=0, blue_notes=2, blue_other=0, red=1, unread_words=1),
             "P1|3": dict(notes=0, rests=0, blue_notes=0, blue_other=0, red=1, unread_words=1),
             "P1|4": dict(notes=0, rests=1, blue_notes=0, blue_other=0, red=1, unread_words=1),
             "P2|1": dict(notes=0, rests=0, blue_notes=0, blue_other=0, red=1, unread_words=1),
             "P2|2": dict(notes=4, rests=0, blue_notes=1, blue_other=0, red=0, unread_words=0)}
    st = RR.bar_states(cov, {"parts": {"P1": "Flute", "P2": "Oboe"}, "cells": cells})
    assert st["states"] == {"written plain": 1, "partial": 1, "held out": 2,
                            "unread, empty": 1, "written with guesses": 1}
    assert st["total"] == 6
    assert all(c["agrees"] for c in st["checks"])
    # a control that can fail: the exporter claims a different number
    cov["bars_held_out_sum"]["bars"] = 5
    st2 = RR.bar_states(cov, {"parts": {}, "cells": cells})
    assert any(not c["agrees"] for c in st2["checks"])


def test_every_family_refusal_has_a_row_or_is_listed():
    from tools.omr.staged.adjudicators.family_precision import FAMILY_REFUSALS
    shown = {f[2] for f in RR.FUNNELS if f[2]}
    missing = [q for q in FAMILY_REFUSALS if q not in shown and q not in RR.REFUSALS_NOT_SHOWN_AS_ROWS]
    assert not missing, missing


def test_movers_rank_the_biggest_relative_changes():
    cur = {"a": 1000, "b": 90, "c": 5, "d": 400}
    prev = {"a": 1010, "b": 20, "c": 1, "d": 400}
    rows = RR.movers(cur, prev, n=3)
    assert [r["row"] for r in rows] == ["b", "a"]       # c is too small, d unchanged


def test_render_with_previous_shows_deltas():
    facts = RR.extract_facts(_record())
    rep = RR.build_report(facts, {"families": []}, None, "now")
    prev = RR.build_report(facts, {"families": []}, None, "before")
    md = RR.render_md(rep, prev)
    assert "Balance ledger" in md and "One screen" in md


def test_a_repeated_bar_number_is_two_bars_named_by_ordinal(tmp_path):
    xml = """<score-partwise><part-list><score-part id="P1"><part-name>Flute</part-name></score-part></part-list>
    <part id="P1">
      <measure number="1"><note><rest/></note></measure>
      <measure number="2"><direction><direction-type><words>unread</words></direction-type></direction></measure>
      <measure number="2"><note color="#1F6FEB"><pitch/></note></measure>
    </part></score-partwise>"""
    f = tmp_path / "x.musicxml"
    f.write_text(xml)
    mx = RR.read_musicxml(f)
    assert set(mx["cells"]) == {"P1|1", "P1|2", "P1|3"}        # the repeat does not overwrite
    assert [mx["cells"][k]["number"] for k in ("P1|1", "P1|2", "P1|3")] == [1, 2, 2]
    # the exporter names the unread bar by ORDINAL: the FIRST "2", not the second
    cov = {"unread_bar_marks": {"unread": 1},
           "unread_empty_bars": {"list": [{"part": "P1", "ordinal": 2, "measure": 2}]}}
    st = RR.bar_states(cov, mx)
    assert st["total"] == 3 and st["bars_on_repeated_numbers"] == 1
    assert st["repeated_bar_numbers"] == [2]
    assert {k: v for k, v in st["states"].items() if v} == {
        "written plain": 1, "unread, empty": 1, "written with guesses": 1}
    assert all(c["agrees"] for c in st["checks"])


def test_the_refusal_crosscheck_counts_a_box_read_as_a_rest():
    facts = {"funnels": [{"meaning": "duration", "family": "note",
                          "refused": {"too_narrow": 5}}]}
    cov = {"notes_not_written": {"not_a_notehead:too_narrow": 3},
           "part_join": {"refusals_reinstated": {"refused_then_read_as_rest": {
               "not_a_notehead:too_narrow": 2}}}}
    row = RR._refusal_crosscheck(facts, cov)[0]
    assert row["agrees"] and row["export_read_as_rest"] == 2
    cov["part_join"]["refusals_reinstated"]["refused_then_read_as_rest"]["not_a_notehead:too_narrow"] = 1
    assert not RR._refusal_crosscheck(facts, cov)[0]["agrees"]      # a control that can fail


def test_the_overnight_compare_writes_the_report_as_a_last_harmless_step():
    from pathlib import Path
    sh = (Path(__file__).resolve().parents[3] / "benchmarks/acceptance/overnight/compare_20261009.sh").read_text()
    assert "tools.omr.staged.regather_report night" in sh
    tail = sh.split("tools.omr.staged.regather_report night")[1]
    assert "||" in tail.split("\n\n")[0] or "|| echo" in tail      # a failure only adds a README line
    assert sh.rindex("regather_report night") > sh.rindex("acceptance --manifest")  # after the existing steps
