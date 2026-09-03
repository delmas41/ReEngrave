"""Drafting window rows from a transcription and a base row: the measure
window chains, staves pair by instrument in order, gaps are flagged."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.omr.training import draft_windows as dw
from tools.omr.training import mxl_verdicts as mv

pytestmark = pytest.mark.omr_training


def _staff(i: int, n: int, instrument: str | None) -> dict:
    return {"staff_index": i, "n_measures": n, "measures": [{"measure_index": k} for k in range(n)],
            "instrument": instrument, "instrument_source": "label" if instrument else None}


def _transcription() -> dict:
    return {"pages": [
        {"page_index": 1, "systems": [
            {"system_index": 0, "staves": [_staff(0, 4, "Flute"), _staff(1, 4, "Horn"),
                                            _staff(2, 4, "Horn"), _staff(3, 4, "Violin")]},
            {"system_index": 1, "staves": [_staff(0, 3, "Flute"), _staff(1, 3, "Violin"),
                                            _staff(2, 3, None)]},
        ]},
        {"page_index": 2, "systems": [
            {"system_index": 0, "staves": [_staff(0, 5, "Flute"), _staff(1, 6, "Violin")]},
        ]},
    ]}


BASE = {"row_id": "fx-p0", "work_id": "x--y",
        "edition": {"catalog_path": "e.pdf"}, "reference": {"catalog_path": "r.mxl"},
        "page": {"pdf_page_index": 0}, "window": {"first_ref_measure": 1, "last_ref_measure": 7},
        "staves": [{"name": "2 Floten", "parts": [0, 1]},
                   {"name": "4 Horner in C 1./2.", "parts": [2, 3]},
                   {"name": "4 Horner in Es 3./4.", "parts": [4, 5]},
                   {"name": "1. Violine", "parts": [6]},
                   {"name": "2. Violine", "parts": [7]}]}


def test_windows_chain_and_staves_pair_by_instrument(tmp_path: Path) -> None:
    rows = dw.draft(_transcription(), BASE)
    assert [r["page"]["pdf_page_index"] for r in rows] == [1, 2]
    w1, w2 = rows[0]["window"], rows[1]["window"]
    assert (w1["first_ref_measure"], w1["last_ref_measure"]) == (8, 14)   # 4 + 3 measures
    assert w2["first_ref_measure"] == 15
    sys0 = rows[0]["systems"]["0"]
    assert [s["parts"] for s in sys0] == [[0, 1], [2, 3], [4, 5], [6]]
    sys1 = rows[0]["systems"]["1"]
    assert [s["parts"] for s in sys1] == [[0, 1], [6], []]
    assert any("no instrument read" in c for c in rows[0]["check"])
    # Page 2's staves disagree (5 vs 6): flagged, mode wins.
    assert any("different measure count" in c for c in rows[1]["check"])
    assert rows[1]["confidence"] == "draft"
    # And mxl_verdicts reads the result, per system.
    out = tmp_path / "w.json"
    out.write_text(json.dumps(rows))
    loaded = mv.load_windows(out)
    assert loaded[1].staves_for_system(1)[1].parts == [6]
    assert loaded[1].staves_for_system(0)[2].parts == [4, 5]


def test_first_measure_override_and_page_gap(tmp_path: Path) -> None:
    base = dict(BASE, page={"pdf_page_index": 5})
    with pytest.raises(SystemExit):
        dw.draft(_transcription(), base)
    rows = dw.draft(_transcription(), base, first_measure=100)
    assert rows[0]["window"]["first_ref_measure"] == 100


def test_cli_reads_the_benchmark_row(tmp_path: Path) -> None:
    tp = tmp_path / "t.json"
    tp.write_text(json.dumps({"pages": [{"page_index": 1, "systems": [
        {"system_index": 0, "staves": [_staff(0, 7, "Flute"), _staff(1, 7, "Violin")]}]}]}))
    out = tmp_path / "w.json"
    rc = dw.main(["--transcription", str(tp), "--base", "benchmarks/omr-scan-e2e-2026-09/works.json",
                  "--row-id", "brahms-sym1-mvt1-317803-p1", "--out", str(out)])
    assert rc == 0
    rows = json.loads(out.read_text())
    assert rows[0]["window"]["first_ref_measure"] == 8
    assert rows[0]["systems"]["0"][0]["parts"] == [0, 1]      # 2 Floten
    assert rows[0]["systems"]["0"][1]["parts"] == [16]        # 1. Violine
