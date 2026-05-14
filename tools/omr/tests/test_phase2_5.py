"""Phase 2.5 annotation framework tests.

Covers:
    - parse_verdict_markdown: detection lines, FN lines, wrong-pitch lines,
      pending detections, mixed verdicts.
    - score_cell / _aggregate: precision / recall / F1 math on synthetic
      ParsedVerdictFile inputs.

Marked `omr_phase2_5`. No PDFs or external assets required.

    pytest tools/omr/tests/test_phase2_5.py -v
    pytest -m omr_phase2_5 -v
"""

from __future__ import annotations

import pytest

from tools.omr.annotate.score import (
    DetectionVerdict,
    MissedNotehead,
    ParsedVerdictFile,
    _aggregate,
    parse_verdict_markdown,
    score_cell,
)


pytestmark = pytest.mark.omr_phase2_5


# ---------------------------------------------------------------------------
# parse_verdict_markdown
# ---------------------------------------------------------------------------


VERDICT_SAMPLE = """# Cell foo-p1-sys0-s0-m0 — verdicts

**Image:** ![overlay](../overlays/foo-p1-sys0-s0-m0.png)
**Clef assumed:** treble
**Staff lines (canonical y):** 100, 120, 140, 160, 180

## Detections

- [x] D0  noteheadBlack (notehead) at (x=10, y=150) → C4  conf=0.90
       verdict: TP
- [x] D1  noteheadBlack (notehead) at (x=20, y=160) → D4  conf=0.85
       verdict: FP barline-mistake
- [x] D2  noteheadBlack (notehead) at (x=30, y=170) → E4  conf=0.80
       verdict: WRONG_PITCH
- [x] D3  rest8th (rest) at (x=40, y=140)  conf=0.70
       verdict: __________
- [x] D4  barlineHeavy (barline) at (x=50, y=130)  conf=1.00
       verdict: unsure

## Missed noteheads (FN)

FN1 at (x=200, y=155) → pitch=G4
FN2 at (x=210, y=160) → pitch=A4
- FN at (x=__, y=__) → pitch=__

## Wrong-pitch corrections

D2 → correct pitch is F4
"""


def test_parse_basic_counts():
    parsed = parse_verdict_markdown(VERDICT_SAMPLE)
    assert parsed.cell_id == "foo-p1-sys0-s0-m0"
    assert len(parsed.detections) == 5
    assert len(parsed.missed_noteheads) == 2
    assert parsed.wrong_pitch_corrections == {"D2": "F4"}


def test_parse_detection_fields():
    parsed = parse_verdict_markdown(VERDICT_SAMPLE)
    by_id = {d.id: d for d in parsed.detections}

    d0 = by_id["D0"]
    assert d0.smufl_name == "noteheadBlack"
    assert d0.category == "notehead"
    assert d0.x == 10 and d0.y == 150
    assert d0.pitch == "C4"
    assert d0.confidence == pytest.approx(0.90)
    assert d0.verdict == "tp"
    assert d0.classification == "tp"

    d1 = by_id["D1"]
    assert d1.classification == "fp"
    assert d1.reason == "barline-mistake"

    d2 = by_id["D2"]
    assert d2.classification == "wrong_pitch"

    d3 = by_id["D3"]
    # The underscore placeholder must be treated as pending.
    assert d3.classification == "pending"
    assert d3.is_pending

    d4 = by_id["D4"]
    # Explicit "unsure" is pending.
    assert d4.classification == "pending"


def test_parse_fn_skips_placeholders():
    parsed = parse_verdict_markdown(VERDICT_SAMPLE)
    coords = [(fn.x, fn.y, fn.pitch) for fn in parsed.missed_noteheads]
    # The "FN at (x=__, y=__) → pitch=__" line must NOT be parsed as a real FN.
    assert (200, 155, "G4") in coords
    assert (210, 160, "A4") in coords
    assert len(coords) == 2


def test_parse_handles_zero_detection_cell():
    text = """# Cell empty-cell — verdicts

## Detections

_(matcher returned zero detections — fill out FN below.)_

## Missed noteheads (FN)

FN1 at (x=5, y=10) → pitch=C4
"""
    parsed = parse_verdict_markdown(text)
    assert parsed.cell_id == "empty-cell"
    assert parsed.detections == []
    assert len(parsed.missed_noteheads) == 1


def test_parse_cell_id_fallback_to_filename():
    text = """## Detections

- [x] D0  noteheadBlack (notehead) at (x=1, y=2) → C4  conf=0.5
       verdict: TP
"""
    parsed = parse_verdict_markdown(text, cell_id="explicit-id")
    assert parsed.cell_id == "explicit-id"


# ---------------------------------------------------------------------------
# score_cell + _aggregate
# ---------------------------------------------------------------------------


def _make_det(id_: str, verdict: str, category: str = "notehead",
              pitch: str | None = "C4") -> DetectionVerdict:
    """Helper to build a DetectionVerdict directly."""
    return DetectionVerdict(
        id=id_, smufl_name="noteheadBlack", category=category,
        x=0, y=0, pitch=pitch, confidence=0.9,
        verdict=verdict.lower(), reason="",
    )


def test_score_cell_basic_pr():
    """4 TP, 1 FP, 2 FN → P = 4/5 = 0.8, R = 4/6 ≈ 0.667, F1 ≈ 0.727."""
    parsed = ParsedVerdictFile(
        cell_id="cell-A",
        detections=[
            _make_det("D0", "tp"),
            _make_det("D1", "tp"),
            _make_det("D2", "tp"),
            _make_det("D3", "tp"),
            _make_det("D4", "fp"),
        ],
        missed_noteheads=[
            MissedNotehead(x=1, y=1, pitch="C4"),
            MissedNotehead(x=2, y=2, pitch="D4"),
        ],
    )
    cs = score_cell(parsed, source_tag="cell")
    assert cs.n_loc_tp == 4
    assert cs.n_fp == 1
    assert cs.n_fn == 2
    assert cs.precision == pytest.approx(4 / 5)
    assert cs.recall == pytest.approx(4 / 6)
    assert cs.f1 == pytest.approx(2 * (4 / 5) * (4 / 6) / ((4 / 5) + (4 / 6)))


def test_score_cell_wrong_pitch_is_location_tp_but_pitch_wrong():
    parsed = ParsedVerdictFile(
        cell_id="cell-B",
        detections=[
            _make_det("D0", "tp"),
            _make_det("D1", "wrong_pitch"),
        ],
    )
    cs = score_cell(parsed)
    # Both count as location-TP.
    assert cs.n_loc_tp == 2
    assert cs.precision == pytest.approx(1.0)
    # Pitch accuracy: 1 correct, 1 wrong = 50%.
    assert cs.n_pitch_correct == 1
    assert cs.n_pitch_wrong == 1
    assert cs.notehead_pitch_accuracy == pytest.approx(0.5)


def test_score_cell_pending_excluded_from_pr():
    parsed = ParsedVerdictFile(
        cell_id="cell-C",
        detections=[
            _make_det("D0", "tp"),
            _make_det("D1", ""),         # pending
            _make_det("D2", "unsure"),   # pending
        ],
    )
    cs = score_cell(parsed)
    assert cs.n_loc_tp == 1
    assert cs.n_fp == 0
    assert cs.n_pending == 2
    # Precision: 1/(1+0) = 1.0; recall undefined with no FN.
    assert cs.precision == pytest.approx(1.0)


def test_score_cell_all_pending_returns_none_pr():
    parsed = ParsedVerdictFile(
        cell_id="cell-D",
        detections=[_make_det("D0", "")],
    )
    cs = score_cell(parsed)
    assert cs.precision is None
    assert cs.recall is None
    assert cs.f1 is None


def test_per_category_counts():
    parsed = ParsedVerdictFile(
        cell_id="cell-E",
        detections=[
            _make_det("D0", "tp", category="notehead"),
            _make_det("D1", "fp", category="notehead"),
            _make_det("D2", "tp", category="rest"),
            _make_det("D3", "fp", category="barline"),
        ],
    )
    cs = score_cell(parsed)
    assert cs.per_category["notehead"]["tp"] == 1
    assert cs.per_category["notehead"]["fp"] == 1
    assert cs.per_category["rest"]["tp"] == 1
    assert cs.per_category["rest"]["fp"] == 0
    assert cs.per_category["barline"]["fp"] == 1


def test_aggregate_sums_across_cells():
    """Two cells: 3 TP / 1 FP / 0 FN and 2 TP / 2 FP / 1 FN.
    Aggregate: 5 TP / 3 FP / 1 FN → P = 5/8, R = 5/6.
    """
    cell_a = score_cell(ParsedVerdictFile(
        cell_id="A",
        detections=[
            _make_det("D0", "tp"), _make_det("D1", "tp"),
            _make_det("D2", "tp"), _make_det("D3", "fp"),
        ],
    ))
    cell_b = score_cell(ParsedVerdictFile(
        cell_id="B",
        detections=[
            _make_det("D0", "tp"), _make_det("D1", "tp"),
            _make_det("D2", "fp"), _make_det("D3", "fp"),
        ],
        missed_noteheads=[MissedNotehead(x=1, y=1, pitch="C4")],
    ))
    agg = _aggregate([cell_a, cell_b])
    assert agg["n_tp"] == 5
    assert agg["n_fp"] == 3
    assert agg["n_fn"] == 1
    assert agg["precision"] == pytest.approx(5 / 8)
    assert agg["recall"] == pytest.approx(5 / 6)


def test_aggregate_empty_returns_none():
    agg = _aggregate([])
    assert agg["n_tp"] == 0
    assert agg["precision"] is None
    assert agg["recall"] is None
    assert agg["f1"] is None


# ---------------------------------------------------------------------------
# end-to-end parse → score on a single round-trip
# ---------------------------------------------------------------------------


def test_end_to_end_parse_and_score():
    parsed = parse_verdict_markdown(VERDICT_SAMPLE)
    cs = score_cell(parsed, source_tag="foo-p1")
    # From the sample: D0 TP, D1 FP, D2 WRONG_PITCH (loc TP), D3+D4 pending.
    # FN: 2 missed noteheads.
    assert cs.n_loc_tp == 2          # D0 + D2 (D2 is wrong_pitch -> loc TP)
    assert cs.n_fp == 1              # D1
    assert cs.n_fn == 2
    assert cs.n_pending == 2         # D3 + D4
    assert cs.precision == pytest.approx(2 / 3)
    assert cs.recall == pytest.approx(2 / 4)
    # Pitch acc: D0 right pitch (notehead TP) = 1 correct,
    #           D2 wrong_pitch (notehead) = 1 wrong → 1/2 = 0.5.
    assert cs.notehead_pitch_accuracy == pytest.approx(0.5)
