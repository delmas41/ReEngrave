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
    # `staff_index` runs across the PAGE, as transcribe numbers it: the
    # second system continues where the first stopped.
    return {"pages": [
        {"page_index": 1, "systems": [
            {"system_index": 0, "staves": [_staff(0, 4, "Flute"), _staff(1, 4, "Horn"),
                                            _staff(2, 4, "Horn"), _staff(3, 4, "Violin")]},
            {"system_index": 1, "staves": [_staff(4, 3, "Flute"), _staff(5, 3, "Violin"),
                                            _staff(6, 3, None)]},
        ]},
        {"page_index": 2, "systems": [
            {"system_index": 0, "staves": [_staff(0, 5, "Flute"), _staff(1, 6, "Violin"),
                                            _staff(2, 6, "Horn")]},
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
    # 4 bars in the top system + 3 in the bottom = 7 bars: 8..14. The two
    # systems' different counts are NOT a disagreement.
    assert (w1["first_ref_measure"], w1["last_ref_measure"]) == (8, 14)
    assert not any("reads" in c for c in rows[0]["check"])
    assert w2["first_ref_measure"] == 15
    sys0 = rows[0]["systems"]["0"]
    assert [s["parts"] for s in sys0] == [[0, 1], [2, 3], [4, 5], [6]]
    sys1 = rows[0]["systems"]["1"]
    assert [s["parts"] for s in sys1] == [[0, 1], [6], []]
    assert any("no instrument read" in c for c in rows[0]["check"])
    # Page 2: one staff reads 5 where its system reads 6 — flagged, the
    # system's count wins (bars 15..20).
    assert w2["last_ref_measure"] == 20
    assert any("staff 0 reads 5 bars, its system 6" in c for c in rows[1]["check"])
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


def test_full_lineup_pairs_by_position_and_cross_checks_the_reader() -> None:
    # Five staves against a five-entry base row: positional. The reader
    # calls the Kontrafagott staff "Bassoon" and the pairing does not move.
    base = dict(BASE, staves=[{"name": "2 Floten", "parts": [0, 1]},
                             {"name": "2 Fagotte", "parts": [6, 7]},
                             {"name": "Kontrafagott", "parts": [8]},
                             {"name": "1. Violine", "parts": [16]},
                             {"name": "2. Violine", "parts": [17]}])
    tr = {"pages": [{"page_index": 1, "systems": [{"system_index": 0, "staves": [
        _staff(0, 7, "Flute"), _staff(1, 7, "Bassoon"), _staff(2, 7, "Bassoon"),
        _staff(3, 7, "Violin"), _staff(4, 7, "Trumpet")]}]}]}
    rows = dw.draft(tr, base)
    specs = rows[0]["systems"]["0"]
    assert [s["parts"] for s in specs] == [[0, 1], [6, 7], [8], [16], [17]]
    assert all(s["paired_by"] == "position" for s in specs)
    # Only the staves whose read instrument contradicts their position are
    # flagged: the Kontrafagott read as a bassoon, and the second violin
    # read as a trumpet. The reader's word never moves a staff.
    flagged = [c for c in rows[0]["check"] if "placed as" in c]
    assert len(flagged) == 2
    assert "Kontrafagott" in flagged[0] and "Bassoon" in flagged[0]
    assert "Trumpet" in flagged[1]
