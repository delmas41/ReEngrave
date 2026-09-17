"""Unit tests for tools/omr/oemer_second_opinion.py.

Pure-function coverage of the ABC (LEGATO) summariser, the .omr.json
summariser, and the clef/time-signature diff — no PDFs, models, or GPU.
"""

from __future__ import annotations

from tools.omr.oemer_second_opinion import (
    _clef_token_from_abc,
    _extract_abc_from_predictions,
    _ts_token_from_abc,
    diff_summaries,
    summarize_abc,
    summarize_omr_json,
)


def test_extract_abc_from_predictions_real_schema():
    # scripts/inference.py writes {"abc_transcription": [<abc>], "tokens": ...}
    data = {"abc_transcription": ["X:1\nM:4/4\nK:C\nV:1 clef=treble\n"], "tokens": [[1, 2]]}
    assert _extract_abc_from_predictions(data).startswith("X:1")


# --------------------------------------------------------------------------- #
# ABC token normalisation
# --------------------------------------------------------------------------- #
def test_ts_token_from_abc():
    assert _ts_token_from_abc("C") == "4/4"
    assert _ts_token_from_abc("C|") == "2/2"
    assert _ts_token_from_abc("3/4") == "3/4"
    assert _ts_token_from_abc("12/8") == "12/8"
    assert _ts_token_from_abc("nonsense") is None


def test_clef_token_from_abc():
    assert _clef_token_from_abc("treble") == "treble"
    assert _clef_token_from_abc("bass") == "bass"
    assert _clef_token_from_abc("alto") == "alto"
    assert _clef_token_from_abc("tenor") == "tenor"
    assert _clef_token_from_abc("treble-8") == "treble_8vb"
    assert _clef_token_from_abc("G2") == "treble"   # case-insensitive + sign/line form
    assert _clef_token_from_abc("none") is None
    assert _clef_token_from_abc("") is None


# --------------------------------------------------------------------------- #
# ABC summariser
# --------------------------------------------------------------------------- #
_ABC = """X:1
M:4/4
L:1/8
K:D
V:1 clef=treble name="Fl."
V:2 clef=bass name="Fag."
V:3 clef=alto name="Vla."
[V:1] A2 B2 c2 d2 | e4 f4 |
[V:2] A,,4 B,,4 | C,4 D,4 |
"""


def test_summarize_abc_voices_and_meter():
    s = summarize_abc(_ABC)
    assert s.n_parts == 3
    assert [p.initial_clef for p in s.parts] == ["treble", "bass", "alto"]
    assert s.global_time_changes() == [(1, "4/4")]


def test_summarize_abc_bare_clef_form():
    # LEGATO emits the bare form `V:1 treble`, not `V:1 clef=treble`.
    abc = ('X:1\nM:3/4\nK:E\n'
           'V:1 treble nm="Fl."\nV:2 bass nm="Fag."\n'
           'V:8 alto nm="Vla."\nV:4 perc nm="Timp."\n'
           '[V:1] E2 F2 G2 |\n')
    s = summarize_abc(abc)
    assert [p.initial_clef for p in s.parts] == ["treble", "bass", "alto", "percussion"]
    assert s.global_time_changes() == [(1, "3/4")]


def test_summarize_abc_accepts_predictions_json():
    # The GPU round-trip returns LEGATO's predictions JSON; --legato-abc should
    # accept it directly (not just pre-extracted ABC text).
    import json as _json
    payload = _json.dumps({"abc_transcription": [
        'X:1\nM:3/4\nK:C\nV:1 clef=treble\nV:2 clef=bass\n[V:1] c2 c c |\n'],
        "tokens": []})
    s = summarize_abc(payload)
    assert s.n_parts == 2
    assert [p.initial_clef for p in s.parts] == ["treble", "bass"]
    assert s.global_time_changes() == [(1, "3/4")]


def test_summarize_abc_common_time_and_inline_change():
    abc = 'X:1\nM:C\nK:C\nV:1 clef=treble\n[V:1] c4 c4 | [M:3/4] c3 |\n'
    s = summarize_abc(abc)
    changes = s.global_time_changes()
    assert changes[0][1] == "4/4"          # C -> 4/4
    assert ("3/4" in [t for _m, t in changes])  # inline [M:3/4] captured


# --------------------------------------------------------------------------- #
# .omr.json summariser: role grouping + null-meter carry-forward + clef change
# --------------------------------------------------------------------------- #
def _omr(clef_a="treble", clef_b_last="treble"):
    return {"pages": [{"systems": [{"system_index": 0, "staves": [
        {"staff_index": 0, "clef": clef_a,
         "time_signature": {"numerator": 4, "denominator": 4, "raw": "4/4"},
         "measures": [
             {"measure_index": 0, "clef": clef_a,
              "time_signature": {"numerator": 4, "denominator": 4, "raw": "4/4"}},
             {"measure_index": 1, "clef": clef_a, "time_signature": None},
         ]},
        {"staff_index": 1, "clef": "bass", "time_signature": None,
         "measures": [
             {"measure_index": 0, "clef": "bass", "time_signature": None},
             {"measure_index": 1, "clef": clef_b_last, "time_signature": None},
         ]},
    ]}]}]}


def test_summarize_omr_json_carry_forward_and_change():
    s = summarize_omr_json(_omr(clef_b_last="treble"), page=0)
    assert s.n_parts == 2
    # meter seen only at m1 then null -> single change, carried forward
    assert s.parts[0].time_changes == [(1, "4/4")]
    # staff 1 changes bass -> treble at its 2nd measure
    assert s.parts[1].clef_changes == [(1, "bass"), (2, "treble")]


# --------------------------------------------------------------------------- #
# Diff: an engine supplies what the pipeline missed
# --------------------------------------------------------------------------- #
def test_diff_engine_supplies_meter_and_clefs():
    # Pipeline: all treble, no meter (the orchestral failure mode).
    pipeline_json = {"pages": [{"systems": [{"system_index": 0, "staves": [
        {"staff_index": i, "clef": "treble", "time_signature": None,
         "measures": [{"measure_index": 0, "clef": "treble", "time_signature": None}]}
        for i in range(4)
    ]}]}]}
    pipeline = summarize_omr_json(pipeline_json, page=0)
    legato = summarize_abc(
        'X:1\nM:4/4\nK:C\nV:1 clef=treble\nV:2 clef=bass\nV:3 clef=alto\n'
        '[V:1] c4 c4 |\n')
    report = diff_summaries(pipeline, legato)

    assert report["engine"] == "legato"
    # Meter: pipeline none, legato 4/4 -> only_oemer verdict (engine supplies it).
    assert report["time_signature"]["verdict"] == "only_oemer"
    assert report["time_signature"]["oemer_initial"] == "4/4"
    # Clef presence: legato saw bass + alto the pipeline missed.
    assert set(report["clef_presence"]["only_oemer"]) == {"bass", "alto"}
    assert report["summary"]["clef_supplied_by_oemer"] == 2
    assert report["summary"]["time_sig_agree"] is False
