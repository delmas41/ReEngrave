"""Tests for tools/omr/annotate/server.py (FastAPI labeling app) and the
schema-aware scoring helpers.

The server tests build a tiny synthetic bench under tmp_path so they
never touch the real benchmarks/. The scorer tests exercise
``tools/omr/annotate/score.py`` (unchanged in the server rewrite) and
guard the v1 markdown / .verdict.json parsing path against regressions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Skip the whole module if FastAPI isn't installed.
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

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
        path.write_bytes(bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
            "53de0000000c4944415478da636400000000050001a5f645b40000000049"
            "454e44ae426082"
        ))


@pytest.fixture
def bench_dir(tmp_path: Path) -> Path:
    """Build a minimal bench under tmp_path: manifest, 2 cells, detection JSON."""
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
            {"id": "D0", "smufl_name": "noteheadBlackOnLine", "category": "notehead",
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
            {"id": "D0", "smufl_name": "noteheadBlackOnLine", "category": "notehead",
             "x": 10, "y": 25, "w": 8, "h": 8, "x_center": 14, "y_center": 29,
             "confidence": 0.8, "pitch": "D4"},
        ],
    }
    (root / "detections" / "synth-c0.json").write_text(
        json.dumps(detections_c0, indent=2))
    (root / "detections" / "synth-c1.json").write_text(
        json.dumps(detections_c1, indent=2))

    # The new server serves the cell PNG (not the overlay) — but both
    # fixtures exist for compatibility with old tests.
    _make_png(root / "cells" / "synth-c0.png", width=100, height=60)
    _make_png(root / "cells" / "synth-c1.png", width=100, height=60)
    _make_png(root / "overlays" / "synth-c0.png")
    _make_png(root / "overlays" / "synth-c1.png")

    return root


@pytest.fixture
def client(bench_dir: Path) -> TestClient:
    app = create_app(bench_dir)  # accepts Path or Bench
    return TestClient(app)


# ---------------------------------------------------------------------------
# Endpoint tests (FastAPI app)
# ---------------------------------------------------------------------------


@pytest.mark.omr_annotate
def test_index_renders(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text
    # The index page is client-rendered — the cell list comes via /api/cells.
    # We just check that the page skeleton + script tag are present.
    assert "ReEngrave labeling" in body
    assert "/static/index.js" in body


@pytest.mark.omr_annotate
def test_cell_page_renders(client: TestClient) -> None:
    resp = client.get("/cells/synth-c0")
    assert resp.status_code == 200
    body = resp.text
    # The cell page is client-rendered — it ships only the skeleton plus
    # the verdict-button labels.
    assert "TP" in body and "FP" in body and "Fix class" in body
    assert "/static/cell.js" in body


@pytest.mark.omr_annotate
def test_cell_page_unknown_cell_is_404(client: TestClient) -> None:
    resp = client.get("/cells/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.omr_annotate
def test_api_cells_lists_both(client: TestClient) -> None:
    resp = client.get("/api/cells")
    assert resp.status_code == 200
    cells = resp.json()
    ids = [c["cell_id"] for c in cells]
    assert ids == ["synth-c0", "synth-c1"]
    # Both start unlabeled.
    for c in cells:
        assert c["has_verdict"] is False
        assert c["n_pending"] == c["n_detections"]


@pytest.mark.omr_annotate
def test_api_bench_summary(client: TestClient) -> None:
    resp = client.get("/api/bench")
    assert resp.status_code == 200
    info = resp.json()
    assert info["n_cells"] == 2
    assert info["n_classes"] == 168
    # All 9 picker categories should be available.
    assert set(info["categories"]) >= {
        "notehead", "rest", "clef", "accidental", "flag",
        "dynamic", "ornament", "structural", "time_sig",
    }


@pytest.mark.omr_annotate
def test_api_classes_includes_archetype_url(client: TestClient) -> None:
    resp = client.get("/api/classes")
    assert resp.status_code == 200
    classes = resp.json()
    by_name = {c["name"]: c for c in classes}
    assert "noteheadBlackOnLine" in by_name
    # Archetype URLs point at the static dir, regardless of whether the
    # PNG happens to exist in this test env.
    if by_name["noteheadBlackOnLine"]["has_archetype"]:
        assert by_name["noteheadBlackOnLine"]["archetype_url"].endswith(
            "/static/archetypes/noteheadBlackOnLine.png"
        )


@pytest.mark.omr_annotate
def test_cell_image_served(client: TestClient) -> None:
    resp = client.get("/api/cell/synth-c0/image")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/")


@pytest.mark.omr_annotate
def test_cell_crop_served(client: TestClient) -> None:
    resp = client.get(
        "/api/cell/synth-c0/crop",
        params={"x": 5, "y": 5, "w": 20, "h": 10, "pad": 2},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/")
    assert len(resp.content) > 60  # at least a valid PNG header


@pytest.mark.omr_annotate
def test_verdict_get_empty_initially_v2_shaped(client: TestClient) -> None:
    resp = client.get("/api/cell/synth-c0/verdict")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["source"] == "new"
    state = payload["state"]
    assert state["cell_id"] == "synth-c0"
    assert state["schema_version"] == 2
    assert len(state["detections"]) == 2
    assert state["added_detections"] == []
    for d in state["detections"]:
        assert d["verdict"] is None
        assert d["human_corrected_class"] is None
        assert d["human_bbox"] is None
        # Bbox + class come from the detections JSON.
        assert d["model_bbox"]["w"] > 0
        assert d["model_predicted_class"]


@pytest.mark.omr_annotate
def test_verdict_post_persists_v2(client: TestClient, bench_dir: Path) -> None:
    payload = {
        "cell_id": "synth-c0",
        "schema_version": 2,
        "detections": [
            {
                "id": "D0",
                "verdict": "TP",
                "model_predicted_class": "noteheadBlackOnLine",
                "model_predicted_category": "notehead",
                "human_corrected_class": None,
                "human_corrected_category": None,
                "model_bbox": {"x": 10, "y": 25, "w": 8, "h": 8},
                "human_bbox": None,
                "confidence": 0.9,
                "notes": "",
            },
            {
                "id": "D1",
                "verdict": "WRONG_CATEGORY",
                "model_predicted_class": "rest8th",
                "model_predicted_category": "rest",
                "human_corrected_class": "rest16th",
                "human_corrected_category": "rest",
                "model_bbox": {"x": 30, "y": 20, "w": 6, "h": 12},
                "human_bbox": None,
                "confidence": 0.7,
                "notes": "looks like 16th",
            },
        ],
        "added_detections": [
            {
                "id": "H0",
                "human_class": "fermataAbove",
                "human_category": "ornament",
                "bbox": {"x": 50, "y": 8, "w": 12, "h": 6},
                "notes": "",
            }
        ],
    }
    resp = client.post("/api/cell/synth-c0/verdict", json=payload)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    saved = json.loads(
        (bench_dir / "verdicts" / "synth-c0.verdict.json").read_text()
    )
    assert saved["schema_version"] == 2
    assert saved["labeled_at_utc"]  # populated by the server
    assert saved["detections"][0]["verdict"] == "TP"
    assert saved["detections"][1]["human_corrected_class"] == "rest16th"
    assert saved["added_detections"][0]["human_class"] == "fermataAbove"

    # GET reads it back as schema_v2 (source=v2).
    resp2 = client.get("/api/cell/synth-c0/verdict")
    state = resp2.json()
    assert state["source"] == "v2"
    assert state["state"]["detections"][0]["verdict"] == "TP"
    assert state["state"]["added_detections"][0]["bbox"]["x"] == 50


@pytest.mark.omr_annotate
def test_verdict_post_validates_bad_verdict(client: TestClient) -> None:
    payload = {
        "cell_id": "synth-c0",
        "schema_version": 2,
        "detections": [
            {
                "id": "D0",
                "verdict": "nonsense",
                "model_predicted_class": "noteheadBlackOnLine",
                "model_predicted_category": "notehead",
                "model_bbox": {"x": 10, "y": 25, "w": 8, "h": 8},
                "confidence": 0.9,
            }
        ],
        "added_detections": [],
    }
    resp = client.post("/api/cell/synth-c0/verdict", json=payload)
    # Schema validation fails the request rather than silently coercing —
    # cleaner than the old v1 behavior since the UI is the only writer.
    assert resp.status_code == 400


@pytest.mark.omr_annotate
def test_verdict_post_cell_id_mismatch(client: TestClient) -> None:
    payload = {
        "cell_id": "wrong-id",
        "schema_version": 2,
        "detections": [],
        "added_detections": [],
    }
    resp = client.post("/api/cell/synth-c0/verdict", json=payload)
    assert resp.status_code == 400
    assert "cell_id" in resp.json()["detail"]


@pytest.mark.omr_annotate
def test_verdict_post_unknown_cell_is_404(client: TestClient) -> None:
    resp = client.post(
        "/api/cell/missing/verdict",
        json={"cell_id": "missing", "schema_version": 2,
              "detections": [], "added_detections": []},
    )
    assert resp.status_code == 404


@pytest.mark.omr_annotate
def test_v1_verdict_file_migrates_to_v2_on_read(
    client: TestClient, bench_dir: Path
) -> None:
    # Drop a schema_v1 verdict file (no schema_version key, has fn_noteheads).
    v1 = {
        "cell_id": "synth-c0",
        "verdicts": [
            {"detection_id": "D0", "smufl_name": "noteheadBlackOnLine",
             "verdict": "TP"},
            {"detection_id": "D1", "smufl_name": "rest8th",
             "verdict": "FP", "actual_label": "rest16th"},
        ],
        "fn_noteheads": [
            {"id": "FN1", "x_canonical": 50, "y_canonical": 30,
             "pitch": "G4", "class_name": "noteheadBlackInSpace"},
        ],
    }
    (bench_dir / "verdicts" / "synth-c0.verdict.json").write_text(
        json.dumps(v1)
    )

    resp = client.get("/api/cell/synth-c0/verdict")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["source"] == "v1"
    state = payload["state"]
    assert state["schema_version"] == 2
    # FP with actual_label should turn into WRONG_CATEGORY in v2.
    by_id = {d["id"]: d for d in state["detections"]}
    assert by_id["D0"]["verdict"] == "TP"
    assert by_id["D1"]["verdict"] == "WRONG_CATEGORY"
    assert by_id["D1"]["human_corrected_class"] == "rest16th"
    # fn_noteheads should appear under added_detections with synthesized bbox.
    assert len(state["added_detections"]) == 1
    assert state["added_detections"][0]["human_class"] == "noteheadBlackInSpace"


# ---------------------------------------------------------------------------
# Scorer-reads-JSON tests (legacy v1 schema, kept unchanged)
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
    # Write a v1 .verdict.json for c0 and an .md for c1; both should be picked
    # up by the existing scoring code (unchanged in the UI rewrite).
    verdicts_dir = bench_dir / "verdicts"
    (verdicts_dir / "synth-c0.verdict.json").write_text(json.dumps({
        "cell_id": "synth-c0",
        "verdicts": [
            {"detection_id": "D0", "smufl_name": "noteheadBlackOnLine",
             "verdict": "TP"},
            {"detection_id": "D1", "smufl_name": "rest8th",
             "verdict": "FP"},
        ],
        "fn_noteheads": [],
    }))
    (verdicts_dir / "synth-c1.md").write_text(
        "# Cell synth-c1 — verdicts\n"
        "- [x] D0  noteheadBlackOnLine (notehead) at (x=14, y=29) → D4  conf=0.80\n"
        "       verdict: TP\n"
    )

    out_dir = bench_dir / "results"
    overall = run_scorer(
        verdicts_dir=verdicts_dir,
        out_dir=out_dir,
        detections_dir=bench_dir / "detections",
        manifest_path=bench_dir / "cells.json",
    )
    assert overall["n_tp"] == 2
    assert overall["n_fp"] == 1
    assert overall["n_fn"] == 0
    assert abs(overall["precision"] - (2 / 3)) < 1e-6


@pytest.mark.omr_annotate
def test_scorer_prefers_json_over_md(bench_dir: Path) -> None:
    verdicts_dir = bench_dir / "verdicts"
    (verdicts_dir / "synth-c0.md").write_text(
        "# Cell synth-c0 — verdicts\n"
        "- [x] D0  noteheadBlackOnLine (notehead) at (x=14, y=29) → C4  conf=0.90\n"
        "       verdict: TP\n"
        "- [x] D1  rest8th (rest) at (x=33, y=26)  conf=0.70\n"
        "       verdict: TP\n"
    )
    (verdicts_dir / "synth-c0.verdict.json").write_text(json.dumps({
        "cell_id": "synth-c0",
        "verdicts": [
            {"detection_id": "D0", "smufl_name": "noteheadBlackOnLine",
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
    # JSON wins over markdown: TP=1, FP=1.
    assert overall["n_tp"] == 1
    assert overall["n_fp"] == 1
