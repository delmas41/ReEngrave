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

from tools.omr.annotate.server import (
    _glyph_metrics,
    _parse_batch_config,
    click_box_px,
    create_app,
    snap_to_staff,
)
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
    # 208 DSv2 classes + 6 hand-labelled custom ones (5 barline/repeat +
    # textDynamic), less those whose category the picker doesn't display.
    # This read 168 — the count from before the custom classes were added
    # (af0d4c0, after this test was written) — and went stale unnoticed
    # because the whole module was erroring on a missing class list.
    assert info["n_classes"] == 174
    # The relationship worth pinning, rather than the magic number. DSv2
    # annotates no barlines at all, so the "barline" category exists only
    # because the custom classes were merged into the catalog — if they stop
    # reaching it, a labeller cannot mark a barline, and this says so.
    assert "barline" in info["categories"], (
        "custom barline/repeat classes are not reaching the class picker"
    )
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
# Verdicts accumulate across serving sessions
# ---------------------------------------------------------------------------
#
# This is what makes a multi-pass campaign safe: the same cells are labelled
# several times over, one symbol kind per sweep, and a later sweep must ADD
# to what an earlier one drew. If re-serving a batch reset the drawn boxes,
# every pass but the last would be lost silently — the boxes are irreplaceable
# human work and nothing downstream would report their absence.


@pytest.mark.omr_annotate
def test_added_detections_survive_a_new_serving_session(bench_dir: Path) -> None:
    """Re-serving a bench (a fresh create_app) must not reset drawn boxes."""
    first = create_app(bench_dir)
    c1 = TestClient(first)
    state = c1.get("/api/cell/synth-c0/verdict").json()["state"]
    state["added_detections"].append({
        "id": "H0", "human_class": "noteheadHalfOnLine",
        "human_category": "notehead",
        "bbox": {"x": 40, "y": 20, "w": 12, "h": 10}, "notes": "pass 1",
    })
    assert c1.post("/api/cell/synth-c0/verdict", json=state).status_code == 200

    # A second serving session over the same directory — this is literally
    # what happens when the labeler stops the server and starts it again.
    c2 = TestClient(create_app(bench_dir))
    reloaded = c2.get("/api/cell/synth-c0/verdict").json()
    assert reloaded["source"] == "v2"
    assert [h["id"] for h in reloaded["state"]["added_detections"]] == ["H0"]

    # Pass 2 appends rather than replacing.
    state2 = reloaded["state"]
    state2["added_detections"].append({
        "id": "H1", "human_class": "restWhole", "human_category": "rest",
        "bbox": {"x": 70, "y": 25, "w": 9, "h": 5}, "notes": "pass 2",
    })
    assert c2.post("/api/cell/synth-c0/verdict", json=state2).status_code == 200

    c3 = TestClient(create_app(bench_dir))
    final = c3.get("/api/cell/synth-c0/verdict").json()["state"]
    assert [h["id"] for h in final["added_detections"]] == ["H0", "H1"]
    assert [h["human_class"] for h in final["added_detections"]] == [
        "noteheadHalfOnLine", "restWhole"
    ]
    # And the pass-1 box is untouched, not merely present.
    assert final["added_detections"][0]["bbox"] == {"x": 40, "y": 20, "w": 12, "h": 10}


@pytest.mark.omr_annotate
def test_added_detections_survive_when_detections_are_emptied(
    bench_dir: Path
) -> None:
    """Drawn boxes outlive the model detections they were drawn beside.

    Blank-canvas batches empty `detections/` to stubs (that is how the hollow
    batch was labelled), and a coordinator may regenerate them between passes.
    Human boxes are keyed on nothing but themselves, so they survive; verdicts
    on MODEL detections are keyed by detection id and are dropped when that id
    is gone, which is the documented reconciliation behavior and is pinned
    here so a change to it is deliberate.
    """
    c1 = TestClient(create_app(bench_dir))
    state = c1.get("/api/cell/synth-c0/verdict").json()["state"]
    state["detections"][0]["verdict"] = "TP"
    state["added_detections"].append({
        "id": "H0", "human_class": "noteheadHalfInSpace",
        "human_category": "notehead",
        "bbox": {"x": 40, "y": 20, "w": 12, "h": 10}, "notes": "",
    })
    c1.post("/api/cell/synth-c0/verdict", json=state)

    (bench_dir / "detections" / "synth-c0.json").write_text(
        json.dumps({"cell_id": "synth-c0", "detections": []})
    )
    reloaded = TestClient(create_app(bench_dir)).get(
        "/api/cell/synth-c0/verdict").json()["state"]
    assert [h["id"] for h in reloaded["added_detections"]] == ["H0"]
    assert reloaded["detections"] == []


# ---------------------------------------------------------------------------
# Single-symbol pass mode
# ---------------------------------------------------------------------------


HOLLOW_PASS = {
    "pass_name": "hollow noteheads",
    "note": "every half or whole notehead the detector missed",
    "classes": [
        {
            "label": "half notehead",
            "on_line": "noteheadHalfOnLine",
            "in_space": "noteheadHalfInSpace",
            "click_box": True,
        },
        {
            "label": "whole notehead",
            "on_line": "noteheadWholeOnLine",
            "in_space": "noteheadWholeInSpace",
            "click_box": True,
        },
    ],
}


@pytest.fixture
def pass_client(bench_dir: Path):
    """A bench serving the hollow-notehead pass config."""
    (bench_dir / "batch_config.json").write_text(json.dumps(HOLLOW_PASS))
    return TestClient(create_app(bench_dir))


ALL_CLASSES = {"noteheadHalfOnLine", "noteheadHalfInSpace", "restWhole",
               "noteheadWholeOnLine", "noteheadWholeInSpace", "rest8th",
               "noteheadBlackOnLine"}


# --- config parsing --------------------------------------------------------


@pytest.mark.omr_annotate
def test_config_plain_class_list() -> None:
    cfg = _parse_batch_config(
        {"pass_name": "rests", "classes": ["restWhole", "rest8th"]}, ALL_CLASSES
    )
    assert cfg.pass_name == "rests"
    assert cfg.single is False
    assert [s.label for s in cfg.slots] == ["restWhole", "rest8th"]
    assert all(s.kind == "class" for s in cfg.slots)
    # A rests pass gets no click box: rest height varies with the value.
    assert all(s.click_box is None for s in cfg.slots)


@pytest.mark.omr_annotate
def test_config_single_class_is_flagged_single() -> None:
    cfg = _parse_batch_config({"classes": ["restWhole"]}, ALL_CLASSES)
    assert cfg.single is True
    assert cfg.slots[0].class_for("on_line") == "restWhole"


@pytest.mark.omr_annotate
def test_config_active_classes_alias_accepted() -> None:
    cfg = _parse_batch_config({"active_classes": ["restWhole"]}, ALL_CLASSES)
    assert [s.label for s in cfg.slots] == ["restWhole"]


@pytest.mark.omr_annotate
def test_config_position_pair_is_one_slot() -> None:
    cfg = _parse_batch_config(HOLLOW_PASS, ALL_CLASSES)
    assert len(cfg.slots) == 2
    slot = cfg.slots[0]
    assert slot.kind == "staff_position_pair"
    assert slot.label == "half notehead"
    assert slot.class_for("on_line") == "noteheadHalfOnLine"
    assert slot.class_for("in_space") == "noteheadHalfInSpace"
    assert slot.class_names == ["noteheadHalfOnLine", "noteheadHalfInSpace"]


@pytest.mark.omr_annotate
def test_config_unknown_class_is_dropped_with_a_warning() -> None:
    cfg = _parse_batch_config(
        {"classes": ["restWhole", "noSuchGlyph"]}, ALL_CLASSES
    )
    assert [s.label for s in cfg.slots] == ["restWhole"]
    assert any("noSuchGlyph" in w for w in cfg.warnings)
    # Slots are re-indexed over what survived, so the number keys stay 1..n.
    assert [s.index for s in cfg.slots] == [0]


@pytest.mark.omr_annotate
def test_config_with_no_usable_class_raises() -> None:
    # Serving the full picker to someone who asked for a pass is the quiet
    # failure; this is loud instead.
    with pytest.raises(ValueError):
        _parse_batch_config({"classes": ["noSuchGlyph"]}, ALL_CLASSES)
    with pytest.raises(ValueError):
        _parse_batch_config({"classes": []}, ALL_CLASSES)
    with pytest.raises(ValueError):
        _parse_batch_config({"pass_name": "x"}, ALL_CLASSES)


@pytest.mark.omr_annotate
def test_config_click_box_overrides_and_rejects_nonsense() -> None:
    cfg = _parse_batch_config(
        {"classes": [{"name": "noteheadHalfOnLine",
                      "click_box": {"height_spaces": 1.5}}]},
        ALL_CLASSES,
    )
    box = cfg.slots[0].click_box
    assert box["height_spaces"] == 1.5
    assert box["source"] == "config"
    # The aspect still comes from the measurement when it isn't overridden.
    assert box["aspect"] == pytest.approx(1.19, abs=0.05)
    for bad in ({"height_spaces": 0}, {"aspect": -1}, "yes"):
        with pytest.raises(ValueError):
            _parse_batch_config(
                {"classes": [{"name": "restWhole", "click_box": bad}]},
                ALL_CLASSES,
            )


@pytest.mark.omr_annotate
def test_corrupt_config_fails_at_startup(bench_dir: Path) -> None:
    (bench_dir / "batch_config.json").write_text("{not json")
    with pytest.raises(ValueError):
        create_app(bench_dir)


# --- measured geometry -----------------------------------------------------


@pytest.mark.omr_annotate
def test_glyph_metrics_are_measured_from_bravura() -> None:
    """A notehead is one staff space tall, and the templates say so.

    SMuFL's em box is four staff spaces, so a trimmed template's height over
    size_px/4 is its height in spaces. If this drifts, the click-box size is
    no longer the glyph's own size.
    """
    half = _glyph_metrics("noteheadHalfOnLine")
    assert half["source"] == "bravura"
    assert half["height_spaces"] == pytest.approx(1.0, abs=0.02)
    assert half["aspect"] == pytest.approx(1.19, abs=0.05)
    # The staff-position suffix is stripped, so both halves agree.
    assert _glyph_metrics("noteheadHalfInSpace") == half
    # A whole note is the same height and visibly wider — the width has to
    # come from the glyph, not from one number for all noteheads.
    whole = _glyph_metrics("noteheadWholeOnLine")
    assert whole["height_spaces"] == pytest.approx(1.0, abs=0.02)
    assert whole["aspect"] > half["aspect"] + 0.3
    # A class the library never rendered abstains into the fallback.
    assert _glyph_metrics("textDynamic")["source"] == "fallback"


@pytest.mark.omr_annotate
def test_snap_to_staff_lines_spaces_and_ledgers() -> None:
    ys = [10, 20, 30, 40, 50]
    # Every printed line is an even step and reads on_line.
    for i, y in enumerate(ys):
        got = snap_to_staff(ys, y)
        assert (got["step"], got["position"]) == (2 * i, "on_line")
        assert got["ledger"] is False
    # Every space between them is odd and reads in_space.
    for i in range(4):
        got = snap_to_staff(ys, ys[i] + 5)
        assert (got["step"], got["position"]) == (2 * i + 1, "in_space")
    # Off-grid clicks snap to the nearest position, not the nearest line.
    assert snap_to_staff(ys, 24)["position"] == "in_space"
    assert snap_to_staff(ys, 21)["position"] == "on_line"
    # Ledger territory keeps the parity going in both directions.
    above = snap_to_staff(ys, 0)
    assert (above["step"], above["position"], above["ledger"]) == (-2, "on_line", True)
    assert snap_to_staff(ys, 5)["position"] == "in_space"
    below = snap_to_staff(ys, 60)
    assert (below["step"], below["position"], below["ledger"]) == (10, "on_line", True)
    assert snap_to_staff(ys, 55)["position"] == "in_space"


@pytest.mark.omr_annotate
def test_snap_uses_the_staffs_own_line_positions() -> None:
    """Real staff lines are not evenly spaced, and the grid must not assume.

    These are the measured lines of beet5-p2-sys0-s2-m3: the gaps run
    102/101/95/102. Snapping off a single median from the top line would put
    the 3rd line 4 px out; snapping to the lines themselves cannot.
    """
    ys = [400, 502, 603, 698, 800]
    for i, y in enumerate(ys):
        got = snap_to_staff(ys, y)
        assert (got["step"], got["snapped_y"]) == (2 * i, float(y))
    assert snap_to_staff(ys, 552)["position"] == "in_space"
    assert snap_to_staff(ys, 100)["spacing"] == pytest.approx(101.5, abs=0.6)


@pytest.mark.omr_annotate
def test_snap_abstains_without_staff_geometry() -> None:
    assert snap_to_staff([], 20) is None
    assert snap_to_staff([30], 20) is None


@pytest.mark.omr_annotate
def test_click_box_px_is_centred_and_sized_in_spaces() -> None:
    box = click_box_px({"height_spaces": 1.0, "aspect": 1.2}, spacing=100,
                       x=200, y=400)
    assert (box["w"], box["h"]) == (120, 100)
    assert (box["x"] + box["w"] / 2, box["y"] + box["h"] / 2) == (200, 400)


# --- the palette endpoint --------------------------------------------------


@pytest.mark.omr_annotate
def test_api_pass_inactive_without_a_config(client: TestClient) -> None:
    body = client.get("/api/pass").json()
    assert body["active"] is False
    assert body["slots"] == []


@pytest.mark.omr_annotate
def test_api_pass_serves_the_restricted_palette(pass_client: TestClient) -> None:
    body = pass_client.get("/api/pass").json()
    assert body["active"] is True
    assert body["pass_name"] == "hollow noteheads"
    assert body["single"] is False
    assert len(body["slots"]) == 2
    slot = body["slots"][0]
    assert slot["kind"] == "staff_position_pair"
    assert [c["name"] for c in slot["classes"]] == [
        "noteheadHalfOnLine", "noteheadHalfInSpace"
    ]
    assert slot["by_position"]["in_space"]["name"] == "noteheadHalfInSpace"
    assert slot["click_box"]["height_spaces"] == pytest.approx(1.0, abs=0.02)
    # The palette is 4 classes, not the whole catalog. That is the point.
    palette = {c["name"] for s in body["slots"] for c in s["classes"]}
    assert len(palette) == 4


@pytest.mark.omr_annotate
def test_pass_does_not_shrink_the_class_catalog(pass_client: TestClient) -> None:
    """The pass is a palette, not a filter on /api/classes.

    The UI still needs every class by name — to render a model detection's own
    class, and for the explicit escape hatch to the full picker — so the
    catalog endpoints answer exactly as they do without a config.
    """
    assert len(pass_client.get("/api/classes").json()) == 174
    assert "barline" in pass_client.get("/api/categories").json()["order"]
    assert pass_client.get("/api/bench").json()["pass_name"] == "hollow noteheads"


@pytest.mark.omr_annotate
def test_bench_reports_no_pass_without_a_config(client: TestClient) -> None:
    assert client.get("/api/bench").json()["pass_name"] is None


# --- click-to-box, end to end through the API ------------------------------


@pytest.mark.omr_annotate
def test_snap_endpoint_places_a_sized_box_and_picks_the_variant(
    pass_client: TestClient
) -> None:
    # The synthetic cell's lines are at 10/20/30/40/50 — spacing 10.
    on_line = pass_client.get(
        "/api/cell/synth-c0/snap", params={"x": 50, "y": 30, "slot": 0}).json()
    assert on_line["available"] is True
    assert on_line["class"]["name"] == "noteheadHalfOnLine"
    assert on_line["position"] == "on_line"
    # One space tall, centred on the snapped line, wider than tall.
    assert on_line["bbox"]["h"] == 10
    assert on_line["bbox"]["w"] == 12
    assert on_line["bbox"]["y"] + on_line["bbox"]["h"] / 2 == 30

    in_space = pass_client.get(
        "/api/cell/synth-c0/snap", params={"x": 50, "y": 26, "slot": 0}).json()
    assert in_space["class"]["name"] == "noteheadHalfInSpace"
    assert in_space["bbox"]["y"] + in_space["bbox"]["h"] / 2 == 25


@pytest.mark.omr_annotate
def test_snap_endpoint_rederives_the_variant_when_a_box_moves(
    pass_client: TestClient
) -> None:
    """Moving a box across the grid changes what it IS, and must say so.

    The UI calls this with the moved box's centre; a box nudged from a line
    into the space above it is no longer the OnLine variant, and leaving the
    class behind would be a silent mislabel.
    """
    before = pass_client.get(
        "/api/cell/synth-c0/snap", params={"x": 50, "y": 40, "slot": 0}).json()
    after = pass_client.get(
        "/api/cell/synth-c0/snap", params={"x": 50, "y": 35, "slot": 0}).json()
    assert before["class"]["name"] == "noteheadHalfOnLine"
    assert after["class"]["name"] == "noteheadHalfInSpace"
    assert after["step"] == before["step"] - 1


@pytest.mark.omr_annotate
def test_snap_endpoint_uses_the_slots_own_glyph_width(
    pass_client: TestClient
) -> None:
    half = pass_client.get(
        "/api/cell/synth-c0/snap", params={"x": 50, "y": 30, "slot": 0}).json()
    whole = pass_client.get(
        "/api/cell/synth-c0/snap", params={"x": 50, "y": 30, "slot": 1}).json()
    assert whole["class"]["name"] == "noteheadWholeOnLine"
    assert whole["bbox"]["h"] == half["bbox"]["h"]
    assert whole["bbox"]["w"] > half["bbox"]["w"]


@pytest.mark.omr_annotate
def test_snap_endpoint_clamps_to_the_cell(pass_client: TestClient) -> None:
    at_edge = pass_client.get(
        "/api/cell/synth-c0/snap", params={"x": 0, "y": 10, "slot": 0}).json()
    assert at_edge["bbox"]["x"] >= 0
    assert at_edge["bbox"]["y"] >= 0
    assert at_edge["bbox"]["x"] + at_edge["bbox"]["w"] <= 100


@pytest.mark.omr_annotate
def test_snap_endpoint_abstains_without_staff_geometry(bench_dir: Path) -> None:
    manifest = json.loads((bench_dir / "cells.json").read_text())
    manifest[0]["staff_line_ys_canonical"] = []
    (bench_dir / "cells.json").write_text(json.dumps(manifest))
    (bench_dir / "batch_config.json").write_text(json.dumps(HOLLOW_PASS))
    c = TestClient(create_app(bench_dir))
    body = c.get("/api/cell/synth-c0/snap",
                 params={"x": 50, "y": 30, "slot": 0}).json()
    assert body["available"] is False
    assert "staff_line_ys" in body["reason"]


@pytest.mark.omr_annotate
def test_snap_endpoint_guards_its_inputs(pass_client: TestClient) -> None:
    assert pass_client.get(
        "/api/cell/nope/snap", params={"x": 1, "y": 1}).status_code == 404
    assert pass_client.get(
        "/api/cell/synth-c0/snap",
        params={"x": 1, "y": 1, "slot": 9}).status_code == 404


@pytest.mark.omr_annotate
def test_snap_endpoint_needs_a_pass(client: TestClient) -> None:
    # No pass configured: there is no palette to snap into. (Kept in its own
    # test — `client` and `pass_client` share one bench_dir, so a test asking
    # for both would serve the config to both.)
    assert client.get(
        "/api/cell/synth-c0/snap", params={"x": 1, "y": 1}).status_code == 409


@pytest.mark.omr_annotate
def test_pass_mode_does_not_change_the_verdict_schema(
    pass_client: TestClient, bench_dir: Path
) -> None:
    """A pass-drawn box is an ordinary added_detection.

    The only pass-specific field is `inspected_passes` (coverage provenance,
    which the YOLO converter ignores), so a batch labelled over several passes
    converts to training labels through the same path as any other — the box
    is a plain added_detection.
    """
    state = pass_client.get("/api/cell/synth-c0/verdict").json()["state"]
    snap = pass_client.get(
        "/api/cell/synth-c0/snap", params={"x": 50, "y": 30, "slot": 0}).json()
    state["added_detections"].append({
        "id": "H0", "human_class": snap["class"]["name"],
        "human_category": snap["class"]["category"],
        "bbox": snap["bbox"], "notes": "",
    })
    assert pass_client.post(
        "/api/cell/synth-c0/verdict", json=state).status_code == 200
    saved = json.loads(
        (bench_dir / "verdicts" / "synth-c0.verdict.json").read_text())
    assert set(saved) == {"cell_id", "schema_version", "labeled_at_utc",
                          "detections", "added_detections", "inspected_passes"}
    assert saved["added_detections"][0]["human_class"] == "noteheadHalfOnLine"


# ---------------------------------------------------------------------------
# Inspected-empty coverage marker
# ---------------------------------------------------------------------------
#
# A single-symbol sweep leaves many cells with nothing to draw — they hold
# none of the pass's symbols. Before this marker such a cell left NO file, so
# "swept and empty" was indistinguishable from "never opened" and pass
# coverage could not be read off the verdicts dir (the hollow batch was 48/48
# inspected but only 25 files). Navigating away in a pass now stamps the pass
# name into `inspected_passes` and saves, so the sweep is provable.


@pytest.mark.omr_annotate
def test_new_verdict_seeds_empty_inspected_passes(client: TestClient) -> None:
    state = client.get("/api/cell/synth-c0/verdict").json()["state"]
    assert state["inspected_passes"] == []


@pytest.mark.omr_annotate
def test_inspected_empty_is_written_and_distinct_from_never_opened(
    pass_client: TestClient, bench_dir: Path
) -> None:
    """The POST the client's navigate-away makes on a cell with no boxes."""
    listing = {c["cell_id"]: c for c in pass_client.get("/api/cells").json()}
    # synth-c1 is left untouched as the never-opened control.
    assert listing["synth-c1"]["has_verdict"] is False
    assert listing["synth-c1"]["inspected_passes"] == []
    assert not (bench_dir / "verdicts" / "synth-c1.verdict.json").exists()

    # Sweep synth-c0: no boxes, just the inspected stamp (added_detections []).
    state = pass_client.get("/api/cell/synth-c0/verdict").json()["state"]
    state["inspected_passes"].append("hollow noteheads")
    assert pass_client.post(
        "/api/cell/synth-c0/verdict", json=state).status_code == 200

    saved = json.loads(
        (bench_dir / "verdicts" / "synth-c0.verdict.json").read_text())
    assert saved["added_detections"] == []
    assert saved["inspected_passes"] == ["hollow noteheads"]

    # The two are now distinguishable in the listing.
    listing = {c["cell_id"]: c for c in pass_client.get("/api/cells").json()}
    assert listing["synth-c0"]["has_verdict"] is True
    assert listing["synth-c0"]["inspected_passes"] == ["hollow noteheads"]
    assert listing["synth-c1"]["has_verdict"] is False


@pytest.mark.omr_annotate
def test_inspected_empty_survives_a_restart(bench_dir: Path) -> None:
    (bench_dir / "batch_config.json").write_text(json.dumps(HOLLOW_PASS))
    c1 = TestClient(create_app(bench_dir))
    state = c1.get("/api/cell/synth-c0/verdict").json()["state"]
    state["inspected_passes"].append("hollow noteheads")
    c1.post("/api/cell/synth-c0/verdict", json=state)

    # A fresh serving session = the labeler restarting the server.
    reloaded = TestClient(create_app(bench_dir)).get(
        "/api/cell/synth-c0/verdict").json()
    assert reloaded["source"] == "v2"
    assert reloaded["state"]["inspected_passes"] == ["hollow noteheads"]
    assert reloaded["state"]["added_detections"] == []


@pytest.mark.omr_annotate
def test_inspected_empty_upgrades_to_boxed_on_a_later_pass(
    bench_dir: Path
) -> None:
    """Drawing a box later must not lose the sweep, nor the sweep the box."""
    (bench_dir / "batch_config.json").write_text(json.dumps(HOLLOW_PASS))
    c1 = TestClient(create_app(bench_dir))
    state = c1.get("/api/cell/synth-c0/verdict").json()["state"]
    state["inspected_passes"].append("hollow noteheads")
    c1.post("/api/cell/synth-c0/verdict", json=state)

    # A later visit draws a box and the sweep records a second pass.
    c2 = TestClient(create_app(bench_dir))
    st = c2.get("/api/cell/synth-c0/verdict").json()["state"]
    snap = c2.get("/api/cell/synth-c0/snap",
                  params={"x": 50, "y": 30, "slot": 0}).json()
    st["added_detections"].append({
        "id": "H0", "human_class": snap["class"]["name"],
        "human_category": snap["class"]["category"],
        "bbox": snap["bbox"], "notes": "",
    })
    st["inspected_passes"].append("whole noteheads")
    c2.post("/api/cell/synth-c0/verdict", json=st)

    final = TestClient(create_app(bench_dir)).get(
        "/api/cell/synth-c0/verdict").json()["state"]
    assert [h["id"] for h in final["added_detections"]] == ["H0"]
    assert final["inspected_passes"] == ["hollow noteheads", "whole noteheads"]


@pytest.mark.omr_annotate
def test_inspected_passes_deduped_and_coerced(client: TestClient) -> None:
    payload = {
        "cell_id": "synth-c0", "schema_version": 2,
        "detections": [], "added_detections": [],
        "inspected_passes": ["hollow", "hollow", "", 7, "rests", None],
    }
    assert client.post("/api/cell/synth-c0/verdict", json=payload).status_code == 200
    got = client.get("/api/cell/synth-c0/verdict").json()["state"]
    assert got["inspected_passes"] == ["hollow", "rests"]


@pytest.mark.omr_annotate
def test_a_plain_verdict_without_the_field_round_trips_empty(
    client: TestClient
) -> None:
    """A payload that omits inspected_passes (any non-pass save) is fine."""
    payload = {
        "cell_id": "synth-c0", "schema_version": 2,
        "detections": [], "added_detections": [],
    }
    assert client.post("/api/cell/synth-c0/verdict", json=payload).status_code == 200
    assert client.get(
        "/api/cell/synth-c0/verdict").json()["state"]["inspected_passes"] == []


@pytest.mark.omr_annotate
def test_inspected_empty_is_excluded_from_yolo_export() -> None:
    """The load-bearing converter contract: a coverage marker is not a label.

    An inspected-empty cell has added_detections [] and no decided detection,
    so `_is_filled` is False and the converter counts it n_empty and emits no
    label — it must never become a background-only training cell on the
    strength of a sweep alone. Adding one box flips it to filled. The
    converter never reads `inspected_passes`, so this needs no converter
    change; the test guards that it stays that way.
    """
    from tools.omr.training.verdicts_to_yolo_labels import _is_filled

    swept_empty = {
        "cell_id": "x", "schema_version": 2,
        "detections": [{"id": "D0", "verdict": None}],
        "added_detections": [],
        "inspected_passes": ["hollow noteheads"],
    }
    assert _is_filled(swept_empty) is False

    boxed = dict(swept_empty)
    boxed["added_detections"] = [{"id": "H0", "human_class": "noteheadHalfOnLine",
                                  "bbox": {"x": 1, "y": 1, "w": 2, "h": 2}}]
    assert _is_filled(boxed) is True


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
