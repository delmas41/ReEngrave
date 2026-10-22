"""Unit tests for the column-aggregated rhythm-sum verifier
(`transcribe._annotate_column_rhythm_warnings`).

This is the notation-math check reshaped to aggregate per measure-COLUMN across
a system's staves, so a resting/sparse staff never false-flags against a meter
force-filled onto it (by beat-sum inference here, or a dossier on the
verification track — the verifier is meter-source-agnostic). Ported alongside
the function from the dossier track so the shared implementation is tested in
one place; over-sum = high (fused/extra beats), under-sum = low (only when the
column's fullest voice is short), all-resting columns skipped.
"""

from __future__ import annotations

from tools.omr.transcribe import (
    _annotate_column_rhythm_warnings,
    _measure_rhythm_sum_warning,
)


_TS34 = {"numerator": 3, "denominator": 4, "raw": "3/4"}


def _det(x, beats):
    """A pitched, durationed notehead detection at canonical x."""
    return {
        "category": "notehead", "pitch": "C4", "bbox": [x, 0, 10, 10],
        "duration_beats": beats, "duration_type": "quarter", "dots": 0,
    }


def _quarters(n):
    """`n` distinct quarter-note detections -> a measure of length `n` beats."""
    return [_det(x, 1.0) for x in range(0, n * 20, 20)]


def _measure(idx, detections, ts=None, phase1=False):
    md = {"measure_index": idx, "time_signature": ts, "detections": detections}
    if phase1:
        md["phase1_warning"] = "fused"
    return md


def _system(staves):
    return {"system_index": 0, "n_staves": len(staves),
            "staves": [{"staff_index": i, "measures": ms} for i, ms in enumerate(staves)]}


def _page(systems):
    return {"page_index": 0, "n_systems": len(systems), "systems": systems}


def _warns(page):
    """All rhythm_sum_warnings in a page, keyed (staff_index, measure_index)."""
    out = {}
    for sys in page["systems"]:
        for st in sys["staves"]:
            for md in st["measures"]:
                if "rhythm_sum_warning" in md:
                    out[(st["staff_index"], md["measure_index"])] = md["rhythm_sum_warning"]
    return out


class TestColumnRhythmWarnings:
    def test_resting_staff_in_filled_column_does_not_flag(self):
        # THE precision win. Column 0: staff 0 plays a full 3/4 bar, staff 1 is
        # empty (resting). The naive per-staff check flags staff 1 {exp:3,
        # act:0}; the column verifier must NOT.
        page = _page([_system([
            [_measure(0, _quarters(3), ts=dict(_TS34))],   # full
            [_measure(0, [], ts=dict(_TS34))],             # resting
        ])])
        _annotate_column_rhythm_warnings(page)
        assert _warns(page) == {}  # neither staff flagged
        # ...and confirm the naive path WOULD have flagged the resting staff,
        # documenting exactly what the reshape fixes.
        assert _measure_rhythm_sum_warning([], _TS34) == {"expected_beats": 3.0,
                                                          "actual_beats": 0.0}

    def test_all_resting_column_skipped(self):
        page = _page([_system([
            [_measure(0, [], ts=dict(_TS34))],
            [_measure(0, [], ts=dict(_TS34))],
        ])])
        _annotate_column_rhythm_warnings(page)
        assert _warns(page) == {}

    def test_over_sum_is_high_confidence(self):
        # Staff 0's measure holds 6 quarters = 6 beats in a 3/4 bar.
        page = _page([_system([
            [_measure(0, _quarters(6), ts=dict(_TS34))],
            [_measure(0, _quarters(3), ts=dict(_TS34))],
        ])])
        _annotate_column_rhythm_warnings(page)
        w = _warns(page)
        assert (0, 0) in w
        assert w[(0, 0)]["kind"] == "over_sum"
        assert w[(0, 0)]["severity"] == "high"
        assert w[(0, 0)]["actual_beats"] == 6.0
        assert w[(0, 0)]["fused_suspected"] is False
        # staff 1 fills the bar exactly -> not flagged
        assert (1, 0) not in w

    def test_over_sum_flags_fused_suspected(self):
        page = _page([_system([
            [_measure(0, _quarters(6), ts=dict(_TS34), phase1=True)],
        ])])
        _annotate_column_rhythm_warnings(page)
        assert _warns(page)[(0, 0)]["fused_suspected"] is True

    def test_under_sum_is_low_confidence(self):
        # Fullest voice in the whole column is 2.0 < 3.0.
        page = _page([_system([
            [_measure(0, _quarters(2), ts=dict(_TS34))],
            [_measure(0, _quarters(1), ts=dict(_TS34))],
        ])])
        _annotate_column_rhythm_warnings(page)
        w = _warns(page)
        # Attached to the FULLEST measure (staff 0, 2.0), not the sparser one.
        assert set(w) == {(0, 0)}
        assert w[(0, 0)]["kind"] == "under_sum"
        assert w[(0, 0)]["severity"] == "low"
        assert w[(0, 0)]["actual_beats"] == 2.0

    def test_full_voice_suppresses_under_flag(self):
        # Staff 0 fills the bar (3.0); staff 1 is short (1.0). Because SOME
        # voice reaches the bar, the column is fine -> no flag anywhere.
        page = _page([_system([
            [_measure(0, _quarters(3), ts=dict(_TS34))],
            [_measure(0, _quarters(1), ts=dict(_TS34))],
        ])])
        _annotate_column_rhythm_warnings(page)
        assert _warns(page) == {}

    def test_over_sum_takes_priority_over_under(self):
        # One staff over (6.0), another short (1.0): the column flags over-sum
        # on the long staff and does NOT also under-flag.
        page = _page([_system([
            [_measure(0, _quarters(6), ts=dict(_TS34))],
            [_measure(0, _quarters(1), ts=dict(_TS34))],
        ])])
        _annotate_column_rhythm_warnings(page)
        w = _warns(page)
        assert set(w) == {(0, 0)}
        assert w[(0, 0)]["kind"] == "over_sum"

    def test_rest_only_measure_does_not_over_flag(self):
        # A whole rest fills any bar; if it happens to parse as 4 beats it must
        # NOT over-flag a 3/4 column (has_note=False guards it).
        rest4 = [{"category": "rest", "bbox": [0, 0, 10, 10],
                  "duration_beats": 4.0, "duration_type": "whole", "dots": 0}]
        page = _page([_system([[_measure(0, rest4, ts=dict(_TS34))]])])
        _annotate_column_rhythm_warnings(page)
        assert _warns(page) == {}

    def test_measure_without_meter_is_ignored(self):
        page = _page([_system([[_measure(0, _quarters(6), ts=None)]])])
        _annotate_column_rhythm_warnings(page)
        assert _warns(page) == {}

    def test_columns_are_independent(self):
        # Column 0 over-sums, column 1 is clean, column 2 under-sums.
        page = _page([_system([[
            _measure(0, _quarters(6), ts=dict(_TS34)),
            _measure(1, _quarters(3), ts=dict(_TS34)),
            _measure(2, _quarters(2), ts=dict(_TS34)),
        ]])])
        _annotate_column_rhythm_warnings(page)
        w = _warns(page)
        assert w[(0, 0)]["kind"] == "over_sum"
        assert (0, 1) not in w
        assert w[(0, 2)]["kind"] == "under_sum"
