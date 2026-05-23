"""DeepScoresV2 -> YOLOv8 training pipeline tests.

All tests run without the real dataset or a GPU. The conversion path is
exercised via the `--dry-run` mock; the trainer is exercised only via
`--help` (we don't actually fire ultralytics).

Marked `omr_training`. Run with:

    pytest tools/omr/tests/test_training_pipeline.py -v
    pytest -m omr_training -v
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tools.omr.training import deepscores_classes
from tools.omr.training.prepare_yolo_data import (
    bbox_to_yolo,
    convert_dataset,
    dry_run_conversion,
    load_deepscores_json,
    yolo_to_bbox,
    _build_mock_dataset_json,
    _MINIMAL_PNG,
)
from tools.omr.training.download_dataset import (
    DENSE_FILES,
    FULL_FILES,
    download_dataset,
)


pytestmark = pytest.mark.omr_training


REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# deepscores_classes — sanity checks
# ---------------------------------------------------------------------------


def test_deepscores_class_list_size_in_expected_range():
    """DeepScoresV2 ships ~135 classes; the embedded snapshot should be
    within plausible bounds. Strict equality is intentionally avoided —
    the dataset has shipped variants with 123 / 134 / 135 / 136 classes.
    """
    n = deepscores_classes.expected_class_count()
    assert 100 <= n <= 160, f"unexpected class count: {n}"


def test_deepscores_class_list_has_no_duplicates():
    names = deepscores_classes.DEEPSCORES_V2_CLASSES
    assert len(names) == len(set(names))


def test_deepscores_class_list_contains_known_landmarks():
    names = set(deepscores_classes.DEEPSCORES_V2_CLASSES)
    # A small set of class names we are confident exist in the dataset.
    # These are the ones the existing yolo_detector._CATEGORY_MAP keys
    # off of.
    for known in ("gClef", "fClef", "accidentalSharp", "accidentalFlat",
                  "accidentalNatural", "restQuarter", "rest8th",
                  "noteheadBlackOnLine", "stem"):
        assert known in names, f"missing landmark class {known!r}"


# ---------------------------------------------------------------------------
# bbox_to_yolo roundtrip
# ---------------------------------------------------------------------------


def test_bbox_to_yolo_roundtrip():
    """abs xyxy -> yolo cxcywh -> abs xyxy should be ~lossless."""
    img_w, img_h = 1960, 2772
    cases = [
        (100.0, 200.0, 150.0, 280.0),
        (10.5, 20.5, 13.5, 24.5),
        (0.0, 0.0, 100.0, 100.0),
        (1900.0, 2700.0, 1960.0, 2772.0),
    ]
    for xmin, ymin, xmax, ymax in cases:
        cx, cy, w, h = bbox_to_yolo(xmin, ymin, xmax, ymax,
                                    img_w=img_w, img_h=img_h)
        # Normalized values stay in [0..1]
        assert 0.0 <= cx <= 1.0
        assert 0.0 <= cy <= 1.0
        assert 0.0 <= w <= 1.0
        assert 0.0 <= h <= 1.0
        # Roundtrip back to absolute
        rx0, ry0, rx1, ry1 = yolo_to_bbox(cx, cy, w, h,
                                           img_w=img_w, img_h=img_h)
        assert abs(rx0 - xmin) < 1e-3
        assert abs(ry0 - ymin) < 1e-3
        assert abs(rx1 - xmax) < 1e-3
        assert abs(ry1 - ymax) < 1e-3


def test_bbox_to_yolo_clamps_overflow():
    """Annotations slightly past the image edge should be clipped to [0..1]
    rather than producing >1 normalized coords.
    """
    cx, cy, w, h = bbox_to_yolo(-10, -10, 110, 110, img_w=100, img_h=100)
    assert 0.0 <= cx <= 1.0
    assert 0.0 <= cy <= 1.0
    assert 0.0 <= w <= 1.0
    assert 0.0 <= h <= 1.0


# ---------------------------------------------------------------------------
# prepare_yolo_data --dry-run
# ---------------------------------------------------------------------------


def test_dry_run_conversion_produces_data_yaml(tmp_path: Path):
    report = dry_run_conversion(tmp_path / "out")
    yaml_path = Path(report["data_yaml"])
    assert yaml_path.exists()
    data = yaml.safe_load(yaml_path.read_text())
    assert data["nc"] == deepscores_classes.expected_class_count()
    assert isinstance(data["names"], list)
    assert len(data["names"]) == data["nc"]
    assert data["names"][:1] == [deepscores_classes.DEEPSCORES_V2_CLASSES[0]]


def test_dry_run_conversion_writes_label_files(tmp_path: Path):
    out = tmp_path / "out"
    dry_run_conversion(out)
    labels_dir = out / "labels" / "train"
    files = sorted(labels_dir.glob("*.txt"))
    assert len(files) == 2  # two mock images
    # Each line must have 5 whitespace-separated numeric tokens
    for f in files:
        for line in f.read_text().strip().splitlines():
            if not line.strip():
                continue
            parts = line.split()
            assert len(parts) == 5
            assert parts[0].isdigit()
            for tok in parts[1:]:
                v = float(tok)
                assert 0.0 <= v <= 1.0


def test_dry_run_via_subprocess(tmp_path: Path):
    """Exercise the CLI surface, not just the function. Catches argparse
    regressions.
    """
    cmd = [
        sys.executable, "-m", "tools.omr.training.prepare_yolo_data",
        "--dry-run", "--dst", str(tmp_path / "cli_out"),
    ]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "dry-run"
    assert payload["n_classes"] == deepscores_classes.expected_class_count()


# ---------------------------------------------------------------------------
# convert_split: round-trip with custom mock data
# ---------------------------------------------------------------------------


def test_convert_dataset_roundtrip_geometry(tmp_path: Path):
    """Build a mock dataset with a known annotation, run the converter,
    parse the resulting YOLO .txt back to absolute pixels, and assert
    the bbox geometry matches.
    """
    src = tmp_path / "src"
    images_dir = src / "images"
    images_dir.mkdir(parents=True)
    # Two mock PNGs (file existence required for symlink/copy step)
    for fname in ("mock_001.png", "mock_002.png"):
        (images_dir / fname).write_bytes(_MINIMAL_PNG)

    payload = _build_mock_dataset_json(deepscores_classes.DEEPSCORES_V2_CLASSES)
    (src / "deepscores_train.json").write_text(json.dumps(payload))
    (src / "deepscores_test.json").write_text(json.dumps(payload))

    dst = tmp_path / "yolo"
    report = convert_dataset(src=src, dst=dst, symlink_images=False)
    assert report["n_classes"] == deepscores_classes.expected_class_count()

    label = (dst / "labels" / "train" / "mock_001.txt").read_text().strip().splitlines()
    # First annotation in the mock: a_bbox=[10, 20, 30, 40] on a 100x100 image
    cls, cx, cy, w, h = label[0].split()
    assert int(cls) == 0  # 1-based cat_id "1" -> 0-based YOLO index 0
    img_w = img_h = 100
    rx0, ry0, rx1, ry1 = yolo_to_bbox(
        float(cx), float(cy), float(w), float(h), img_w=img_w, img_h=img_h,
    )
    assert abs(rx0 - 10) < 1e-3
    assert abs(ry0 - 20) < 1e-3
    assert abs(rx1 - 30) < 1e-3
    assert abs(ry1 - 40) < 1e-3


def test_load_deepscores_json_parses_mock(tmp_path: Path):
    payload = _build_mock_dataset_json(deepscores_classes.DEEPSCORES_V2_CLASSES)
    p = tmp_path / "mock.json"
    p.write_text(json.dumps(payload))
    classes, images, annotations = load_deepscores_json(p)
    assert len(classes) == deepscores_classes.expected_class_count()
    assert len(images) == 2
    assert len(annotations) == 3
    # All cat_ids are valid indices into the class list
    for a in annotations:
        assert 0 <= a.cat_id < len(classes)


# ---------------------------------------------------------------------------
# download_dataset --dry-run
# ---------------------------------------------------------------------------


def test_download_dry_run_lists_urls(tmp_path: Path, capsys):
    report = download_dataset(
        out_dir=tmp_path / "ds2",
        files=DENSE_FILES,
        dry_run=True,
    )
    assert report["files"]
    for entry in report["files"]:
        assert entry["status"] == "dry-run"
        assert entry["url"].startswith("https://")
        # No actual files written
        assert not Path(entry["dst"]).exists()


def test_download_dry_run_includes_full_set():
    """The FULL_FILES manifest must also be sane (no empty URL, sizes set)."""
    assert FULL_FILES
    for f in FULL_FILES:
        assert f.url.startswith("https://")
        assert f.expected_size_bytes > 0


def test_download_dry_run_subprocess(tmp_path: Path):
    cmd = [
        sys.executable, "-m", "tools.omr.training.download_dataset",
        "--dry-run", "--out", str(tmp_path / "ds2"),
    ]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    # The URL should appear in stderr (progress) and the JSON report in stdout
    assert "https://zenodo.org" in result.stderr
    report = json.loads(result.stdout)
    assert all(e["status"] == "dry-run" for e in report["files"])


# ---------------------------------------------------------------------------
# train_yolo --help
# ---------------------------------------------------------------------------


def test_train_yolo_help_works():
    """`--help` exits 0 even without ultralytics imported (it's lazy)."""
    cmd = [
        sys.executable, "-m", "tools.omr.training.train_yolo", "--help",
    ]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "--epochs" in result.stdout
    assert "--imgsz" in result.stdout
    assert "--smoke" in result.stdout


def test_train_yolo_fails_fast_on_missing_data(tmp_path: Path):
    """Without --smoke and with a bogus data path, the script should
    bail out before importing ultralytics or touching the GPU.
    """
    cmd = [
        sys.executable, "-m", "tools.omr.training.train_yolo",
        "--data", str(tmp_path / "does-not-exist.yaml"),
    ]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode != 0
    assert "data.yaml not found" in result.stderr


def test_eval_help_works():
    cmd = [
        sys.executable, "-m", "tools.omr.training.eval_on_score_cells",
        "--help",
    ]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "--weights" in result.stdout
    assert "--cells" in result.stdout
