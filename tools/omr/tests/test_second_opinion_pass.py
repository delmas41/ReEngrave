"""Unit tests for tools/omr/second_opinion_pass.py — routing + the gate."""

from __future__ import annotations

from tools.omr.oemer_second_opinion import summarize_abc, summarize_omr_json
from tools.omr.second_opinion_pass import (
    clef_detection_rate,
    gate_flags,
    page_staff_count,
    route_engine,
)


def test_route_engine():
    assert route_engine(1) == "oemer"
    assert route_engine(2) == "oemer"
    assert route_engine(3) == "legato"
    assert route_engine(26) == "legato"


def _all_treble_no_meter(n=4):
    return {"pages": [{"systems": [{"system_index": 0, "staves": [
        {"staff_index": i, "clef": "treble", "time_signature": None,
         "measures": [{"measure_index": 0, "clef": "treble",
                       "time_signature": None, "detections": []}]}
        for i in range(n)]}]}]}


def test_gate_flags_meter_suggestion_and_clefs_defaulted():
    # The Mahler failure: all-treble, meter abstained, ~0 clefs detected.
    pipe = summarize_omr_json(_all_treble_no_meter(4), page=0)
    leg = summarize_abc("X:1\nM:3/4\nK:E\nV:1 treble\nV:2 bass\nV:3 alto\n[V:1] E2 |\n")
    g = gate_flags(pipe, leg, clef_rate=0.0)
    assert g["meter"]["flag"] == "meter_suggestion"
    assert g["meter"]["suggested"] == "3/4"
    assert g["clefs"]["flag"] == "clefs_defaulted"
    assert set(g["clefs"]["only_engine"]) == {"bass", "alto"}
    assert len(g["flags"]) == 2


def test_gate_no_clef_flag_when_clefs_well_detected():
    # Same clef disagreement, but the pipeline actually detected its clefs
    # (rate high) -> don't flag; a disagreement there is likelier an engine error.
    pipe = summarize_omr_json(_all_treble_no_meter(2), page=0)
    leg = summarize_abc("X:1\nM:3/4\nK:C\nV:1 treble\nV:2 bass\n[V:1] c |\n")
    g = gate_flags(pipe, leg, clef_rate=1.0)
    assert g["clefs"]["flag"] is None
    # meter still flagged (pipeline abstained)
    assert g["meter"]["flag"] == "meter_suggestion"


def test_gate_meter_agree_no_flag():
    pj = {"pages": [{"systems": [{"system_index": 0, "staves": [
        {"staff_index": 0, "clef": "treble",
         "time_signature": {"numerator": 3, "denominator": 4, "raw": "3/4"},
         "measures": [{"measure_index": 0, "clef": "treble",
                       "time_signature": {"numerator": 3, "denominator": 4, "raw": "3/4"},
                       "detections": []}]}]}]}]}
    pipe = summarize_omr_json(pj, page=0)
    leg = summarize_abc("X:1\nM:3/4\nK:C\nV:1 treble\n[V:1] c |\n")
    g = gate_flags(pipe, leg, clef_rate=1.0)
    assert g["meter"]["flag"] is None
    assert g["flags"] == []


def test_page_facts():
    omr = {"pages": [{"systems": [{"system_index": 0, "staves": [
        {"staff_index": 0, "clef": "treble",
         "measures": [{"clef": "treble", "detections": [{"category": "clef"}]}]},
        {"staff_index": 1, "clef": "treble",
         "measures": [{"clef": "treble", "detections": []}]},
    ]}]}]}
    assert page_staff_count(omr, 0) == 2
    assert clef_detection_rate(omr, 0) == 0.5   # 1 of 2 staves had a detected clef
