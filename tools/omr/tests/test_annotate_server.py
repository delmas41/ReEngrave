"""Tests for tools/omr/annotate/server.py and the JSON-aware scorer.

These tests build a tiny synthetic bench dir under a tmp_path so they don't
touch the real benchmarks/omr-phase2.5 tree.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Skip the whole module if Flask isn't installed.
pytest.importorskip("flask")

from tools.omr.annotate.server import create_app
from tools.omr.annotate.score import run_scorer, parse_verdict_json


# ---------------------------------------------------------------------------
# Test bench fixture
# ---------------------------------------------------------------------------


def _make_png(path: Path, width: int = 32, height: int = 16) -> None:
    """Write a tiny valid PNG so endpoints serving it return image/png."""
    try:
        import cv2  # type: ignore
        import numpy as np

        img = np.full((height, width, 3), 255, dtype=np.uint8)
        cv2.imwrite(str(path), img)
    except ImportError:
        # Fallback: a hand-built 1x1 PNG.
        # (Tests don't actually inspect the bytes, only that the endpoint
        # returns 200 + image/png.)
        path.write_bytes(bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
            "53de0000000c4944415478da636400000000050001a5f645b40000000049"
            "454e44ae426082"
        ))


@pytest.fixture
def bench_dir(tmp_path: Path) -> Path:
    """Build a minimal Phase 2.5-shaped bench under tmp_path."""
    root = tmp_path / "bench"
    (root / "cells").mkdir(parents=True)
    (root / "detections").mkdir()
    (root / "overlays").mkdir()
    (root / "verdicts").mkdir()

    manifest = [
        {
            "cell_id": "synth-c0",
            "pdf": "synthetic.pdf",
            "page": 0,
            "system_index": 0,
            "staff_index": 0,
            "measure_index": 0,
            "cell_png_path": "cells/synth-c0.png",
            "nostaff_png_path": None,
            "staff_line_ys_canonical": [10, 20, 30, 40, 50],
            "clef": "treble",
            "source_tag": "synth",
            "cell_canonical_w": 100,
            "cell_canonical_h": 60,
        },
        {
            "cell_id": "synth-c1",
            "pdf": "synthetic.pdf",
            "page": 0,
            "system_index": 0,
            "staff_index": 0,
            "measure_index": 1,
            "cell_png_path": "cells/synth-c1.png",
            "nostaff_png_path": None,
            "staff_line_ys_canonical": [10, 20, 30, 40, 50],
            "clef": "treble",
            "source_tag": "synth",
            "cell_canonical_w": 100,
            "cell_canonical_h": 60,
        },
    ]
    (root / "cells.json").write_text(json.dumps(manifest, indent=2))

    detections_c0 = {
        "cell_id": "synth-c0",
        "detections": [
            {"id": "D0", "smufl_name": "noteheadBlack", "category": "notehead",
             "x": 10, "y": 25, "w": 8, "h": 8, "x_center": 14, "y_center": 29,
             "confidence": 0.9, "pitch": "C4"},
            {"id": "D1", "smufl_name": "rest8th", "category": "rest",
             "x": 30, "y": 20, "w": 6, "h": 12, "x_center": 33, "y_center": 26,
             "confidence": 0.7, "pitch": None},
        ],
    }
    detections_c1 = {
        "cell_id": "synth-c1",
        "detections": [
            {"id": "D0", "smufl_name": "noteheadBlack", "category": "notehead",
             "x": 10, "y": 25, "w": 8, "h": 8, "x_center": 14, "y_center": 29,
             "confidence": 0.8, "pitch": "D4"},
        ],
    }
    (root / "detections" / "synth-c0.json").write_text(
        json.dumps(detections_c0, indent=2))
    (root / "detections" / "synth-c1.json").write_text(
        json.dumps(detections_c1, indent=2))

    _make_png(root / "overlays" / "synth-c0.png")
    _make_png(root / "overlays" / "synth-c1.png")

    return root


@pytest.fixture
def client(bench_dir: Path):
    app = create_app(bench_dir)
    app.config["TESTING"] = True
    return app.test_client()


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.omr_annotate
def test_index_renders(client) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "synth-c0" in body
    assert "synth-c1" in body
    # Both cells start empty.
    assert body.count("empty") >= 2


@pytest.mark.omr_annotate
def test_cell_detail_renders(client) -> None:
    resp = client.get("/cells/synth-c0")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "synth-c0" in body
    # The two detections should show up.
    assert "D0" in body
    assert "D1" in body
    # Radio buttons present.
    assert 'value="TP"' in body
    assert 'value="FP"' in body
    assert 'value="unsure"' in body


@pytest.mark.omr_annotate
def test_cell_detail_unknown_cell_is_404(client) -> None:
    resp = client.get("/cells/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.omr_annotate
def test_overlay_png_served(client) -> None:
    resp = client.get("/cells/synth-c0/overlay.png")
    assert resp.status_code == 200
    assert resp.content_type.startswith("image/")


@pytest.mark.omr_annotate
def test_verdict_get_empty_initially(client) -> None:
    resp = client.get("/cells/synth-c0/verdict.json")
    assert resp.status_code == 200
    state = resp.get_json()
    assert state["cell_id"] == "synth-c0"
    assert len(state["verdicts"]) == 2
    assert all(v["verdict"] == "" for v in state["verdicts"])
    assert state["fn_noteheads"] == []


@pytest.mark.omr_annotate
def test_verdict_post_persists(client, bench_dir: Path) -> None:
    payload = {
        "cell_id": "synth-c0",
        "verdicts": [
            {"detection_id": "D0", "smufl_name": "noteheadBlack",
             "verdict": "TP"},
            {"detection_id": "D1", "smufl_name": "rest8th",
             "verdict": "FP"},
        ],
        "fn_noteheads": [
            {"id": "FN1", "x_canonical": 50, "y_canonical": 30, "pitch": "G4"},
        ],
    }
    resp = client.post("/cells/synth-c0/verdict.json", json=payload)
    assert resp.status_code == 200
    out = resp.get_json()
    assert out["ok"] is True
    assert out["errors"] == []

    # Persisted to disk?
    saved = json.loads(
        (bench_dir / "verdicts" / "synth-c0.verdict.json").read_text())
    assert saved["cell_id"] == "synth-c0"
    assert saved["verdicts"][0]["verdict"] == "TP"
    assert saved["verdicts"][1]["verdict"] == "FP"
    assert len(saved["fn_noteheads"]) == 1
    assert saved["fn_noteheads"][0]["pitch"] == "G4"

    # GET reads it back.
    resp2 = client.get("/cells/synth-c0/verdict.json")
    assert resp2.status_code == 200
    state = resp2.get_json()
    assert state["verdicts"][0]["verdict"] == "TP"
    assert state["fn_noteheads"][0]["x_canonical"] == 50


@pytest.mark.omr_annotate
def test_verdict_post_validates_bad_verdict_string(client, bench_dir: Path) -> None:
    payload = {
        "cell_id": "synth-c0",
        "verdicts": [
            {"detection_id": "D0", "smufl_name": "noteheadBlack",
             "verdict": "nonsense"},
        ],
        "fn_noteheads": [],
    }
    resp = client.post("/cells/synth-c0/verdict.json", json=payload)
    assert resp.status_code == 200
    out = resp.get_json()
    assert out["ok"] is True
    assert any("bad verdict" in e for e in out["errors"])
    # Bad verdict was coerced to empty.
    assert out["state"]["verdicts"][0]["verdict"] == ""


@pytest.mark.omr_annotate
def test_verdict_post_cell_id_mismatch_reports_error(client) -> None:
    payload = {
        "cell_id": "wrong-id",
        "verdicts": [],
        "fn_noteheads": [],
    }
    resp = client.post("/cells/synth-c0/verdict.json", json=payload)
    assert resp.status_code == 200
    out = resp.get_json()
    assert any("cell_id mismatch" in e for e in out["errors"])


@pytest.mark.omr_annotate
def test_verdict_post_unknown_cell_is_404(client) -> None:
    resp = client.post(
        "/cells/missing/verdict.json",
        json={"cell_id": "missing", "verdicts": [], "fn_noteheads": []},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Scorer-reads-JSON tests
# ---------------------------------------------------------------------------


@pytest.mark.omr_annotate
def test_parse_verdict_json_basic() -> None:
    detections_by_id = {
        "D0": {"id": "D0", "smufl_name": "noteheadBlack", "category": "notehead",
               "x_center": 14, "y_center": 29, "confidence": 0.9, "pitch": "C4"},
        "D1": {"id": "D1", "smufl_name": "rest8th", "category": "rest",
               "x_center": 33, "y_center": 26, "confidence": 0.7, "pitch": None},
    }
    payload = {
        "cell_id": "synth-c0",
        "verdicts": [
            {"detection_id": "D0", "smufl_name": "noteheadBlack",
             "verdict": "TP"},
            {"detection_id": "D1", "smufl_name": "rest8th",
             "verdict": "FP"},
        ],
        "fn_noteheads": [
            {"id": "FN1", "x_canonical": 50, "y_canonical": 30, "pitch": "G4"},
        ],
    }
    parsed = parse_verdict_json(payload, detections_by_id, cell_id="synth-c0")
    assert parsed.cell_id == "synth-c0"
    assert len(parsed.detections) == 2
    assert parsed.detections[0].classification == "tp"
    assert parsed.detections[1].classification == "fp"
    assert len(parsed.missed_noteheads) == 1
    assert parsed.missed_noteheads[0].pitch == "G4"


@pytest.mark.omr_annotate
def test_parse_verdict_json_wrong_pitch_routes_to_corrections() -> None:
    detections_by_id = {
        "D0": {"id": "D0", "smufl_name": "noteheadBlack", "category": "notehead",
               "x_center": 14, "y_center": 29, "confidence": 0.9, "pitch": "C4"},
    }
    payload = {
        "cell_id": "synth-c0",
        "verdicts": [
            {"detection_id": "D0", "smufl_name": "noteheadBlack",
             "verdict": "TP", "wrong_pitch": "D4"},
        ],
        "fn_noteheads": [],
    }
    parsed = parse_verdict_json(payload, detections_by_id, cell_id="synth-c0")
    assert parsed.detections[0].classification == "wrong_pitch"
    assert parsed.wrong_pitch_corrections["D0"] == "D4"


@pytest.mark.omr_annotate
def test_scorer_reads_verdict_json(bench_dir: Path) -> None:
    # Write a .verdict.json for c0 and an .md for c1; both should be picked up.
    verdicts_dir = bench_dir / "verdicts"
    (verdicts_dir / "synth-c0.verdict.json").write_text(json.dumps({
        "cell_id": "synth-c0",
        "verdicts": [
            {"detection_id": "D0", "smufl_name": "noteheadBlack",
             "verdict": "TP"},
            {"detection_id": "D1", "smufl_name": "rest8th",
             "verdict": "FP"},
        ],
        "fn_noteheads": [],
    }))
    (verdicts_dir / "synth-c1.md").write_text(
        "# Cell synth-c1 — verdicts\n"
        "- [x] D0  noteheadBlack (notehead) at (x=14, y=29) → D4  conf=0.80\n"
        "       verdict: TP\n"
    )

    out_dir = bench_dir / "results"
    overall = run_scorer(
        verdicts_dir=verdicts_dir,
        out_dir=out_dir,
        detections_dir=bench_dir / "detections",
        manifest_path=bench_dir / "cells.json",
    )
    # 2 TP (one per cell), 1 FP from c0, 0 FN.
    assert overall["n_tp"] == 2
    assert overall["n_fp"] == 1
    assert overall["n_fn"] == 0
    # Precision 2/(2+1) = 0.667
    assert abs(overall["precision"] - (2 / 3)) < 1e-6


@pytest.mark.omr_annotate
def test_scorer_prefers_json_over_md(bench_dir: Path) -> None:
    verdicts_dir = bench_dir / "verdicts"
    # MD says everything is TP.
    (verdicts_dir / "synth-c0.md").write_text(
        "# Cell synth-c0 — verdicts\n"
        "- [x] D0  noteheadBlack (notehead) at (x=14, y=29) → C4  conf=0.90\n"
        "       verdict: TP\n"
        "- [x] D1  rest8th (rest) at (x=33, y=26)  conf=0.70\n"
        "       verdict: TP\n"
    )
    # JSON says one is TP, one is FP. JSON should win.
    (verdicts_dir / "synth-c0.verdict.json").write_text(json.dumps({
        "cell_id": "synth-c0",
        "verdicts": [
            {"detection_id": "D0", "smufl_name": "noteheadBlack",
             "verdict": "TP"},
            {"detection_id": "D1", "smufl_name": "rest8th",
             "verdict": "FP"},
        ],
        "fn_noteheads": [],
    }))

    out_dir = bench_dir / "results"
    overall = run_scorer(
        verdicts_dir=verdicts_dir,
        out_dir=out_dir,
        detections_dir=bench_dir / "detections",
        manifest_path=bench_dir / "cells.json",
    )
    # If MD had won we'd see TP=2, FP=0. JSON winning gives TP=1, FP=1.
    assert overall["n_tp"] == 1
    assert overall["n_fp"] == 1


@pytest.mark.omr_annotate
def test_score_endpoint_runs(client) -> None:
    resp = client.get("/score")
    assert resp.status_code == 200
    body = resp.data.decode()
    # The page renders a report whether or not any verdicts exist.
    assert "scoring report" in body.lower() or "scorer failed" not in body.lower()
