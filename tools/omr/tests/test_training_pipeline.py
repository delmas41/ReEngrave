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


# ---------------------------------------------------------------------------
# Class-name vocabulary (committed 208-name snapshot)
# ---------------------------------------------------------------------------


def test_committed_208_vocab_loads_without_weights():
    """The committed JSON snapshot must resolve the full trained vocabulary
    even when torch / the gitignored weights are unavailable."""
    from tools.omr.training.verdicts_to_yolo_labels import (
        DEEPSCORES_208_JSON,
        load_base_class_names,
        load_class_names,
    )

    assert DEEPSCORES_208_JSON.exists()
    base = load_base_class_names(None, DEEPSCORES_208_JSON)
    assert len(base) == 208
    assert base[0] == "brace"
    assert "noteheadBlackOnLine" in base
    full = load_class_names(None, DEEPSCORES_208_JSON)
    assert len(full) == 214
    assert full[:208] == base
    assert full[208] == "barlineSingle"


def test_load_base_class_names_errors_with_no_sources(tmp_path: Path):
    """No weights + no fallback JSON must be a hard error, not a silent
    fall-through to the 146-name dataset snapshot (which disagrees with
    the trained vocabulary on 141/146 slots)."""
    from tools.omr.training.verdicts_to_yolo_labels import load_base_class_names

    with pytest.raises(SystemExit):
        load_base_class_names(None, tmp_path / "missing.json")


# ---------------------------------------------------------------------------
# build_catalog_yaml — nc capping
# ---------------------------------------------------------------------------


def _make_catalog_root(tmp_path: Path) -> Path:
    """A minimal version dir: one cell with a base-class box and a
    custom-class box, one cell with only base-class boxes. Includes the
    membership manifest — a catalog root without one is refused."""
    root = tmp_path / "user-labeled"
    v1 = root / "v1-2026-01-01-test"
    (v1 / "images").mkdir(parents=True)
    (v1 / "labels").mkdir(parents=True)
    (v1 / "images" / "mixed.png").write_bytes(_MINIMAL_PNG)
    (v1 / "labels" / "mixed.txt").write_text(
        "0 0.5 0.5 0.1 0.1\n208 0.2 0.2 0.1 0.1\n"
    )
    (v1 / "images" / "clean.png").write_bytes(_MINIMAL_PNG)
    (v1 / "labels" / "clean.txt").write_text("5 0.5 0.5 0.1 0.1\n")
    (root / "catalog-versions.txt").write_text("v1-2026-01-01-test\n")
    return root


def test_cap_labels_to_nc_redirects_only_offending_cells(tmp_path: Path):
    from tools.omr.training.build_catalog_yaml import _cap_labels_to_nc

    root = _make_catalog_root(tmp_path)
    imgs = [
        root / "v1-2026-01-01-test" / "images" / "mixed.png",
        root / "v1-2026-01-01-test" / "images" / "clean.png",
    ]
    out, dropped = _cap_labels_to_nc(root, imgs, 208)
    assert dict(dropped) == {208: 1}
    # clean.png untouched, mixed.png redirected into the capped tree
    assert out[1] == imgs[1]
    assert "_nc208" in str(out[0])
    assert out[0].exists()  # symlink resolves back to the original image
    capped_label = out[0].parent.parent / "labels" / "mixed.txt"
    assert capped_label.read_text() == "0 0.5 0.5 0.1 0.1\n"
    # the version dir itself is untouched
    assert "208 0.2 0.2 0.1 0.1" in (
        root / "v1-2026-01-01-test" / "labels" / "mixed.txt"
    ).read_text()


def test_build_catalog_cli_caps_nc_by_default(tmp_path: Path):
    root = _make_catalog_root(tmp_path)
    cmd = [
        sys.executable, "-m", "tools.omr.training.build_catalog_yaml",
        "--root", str(root), "--val-fraction", "0",
        "--weights", str(tmp_path / "no-weights.pt"),
        "--emit-full-catalog",
    ]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    cat = yaml.safe_load((root / "catalog.yaml").read_text())
    assert cat["nc"] == 208
    assert len(cat["names"]) == 208
    train_paths = [
        Path(p) for p in (root / "_catalog_train.txt").read_text().splitlines()
    ]
    assert len(train_paths) == 2
    for img in train_paths:
        label = img.parent.parent / "labels" / f"{img.stem}.txt"
        ids = [int(l.split()[0]) for l in label.read_text().splitlines() if l.strip()]
        assert all(i < 208 for i in ids), f"{label}: {ids}"

    full = yaml.safe_load((root / "catalog-214.yaml").read_text())
    assert full["nc"] == 214
    full_train = (root / "_catalog_full_train.txt").read_text()
    assert "_nc208" not in full_train


def test_build_catalog_cli_keep_custom_classes(tmp_path: Path):
    root = _make_catalog_root(tmp_path)
    cmd = [
        sys.executable, "-m", "tools.omr.training.build_catalog_yaml",
        "--root", str(root), "--val-fraction", "0",
        "--weights", str(tmp_path / "no-weights.pt"),
        "--keep-custom-classes",
    ]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    cat = yaml.safe_load((root / "catalog.yaml").read_text())
    assert cat["nc"] == 214
    assert "_nc208" not in (root / "_catalog_train.txt").read_text()


# ---------------------------------------------------------------------------
# build_catalog_yaml — version membership (catalog-versions.txt)
# ---------------------------------------------------------------------------
#
# Which versions the catalog unions is a recorded training decision, not a
# directory listing: the committed catalog deliberately excludes the
# clef-heavy v5/v6 batches (they narrow the density prior — the mechanism
# that collapsed dense-page noteheads 2506 -> 114; PROJECT_STATUS.md open
# decision #13). Until 2026-09-02 that exclusion survived only as long as
# nobody re-ran the documented command. These tests pin the guard: a
# default run reproduces the manifest's membership exactly or refuses —
# it never silently widens.


def _add_version(root: Path, name: str) -> Path:
    v = root / name
    (v / "images").mkdir(parents=True)
    (v / "labels").mkdir(parents=True)
    (v / "images" / f"{name}-cell.png").write_bytes(_MINIMAL_PNG)
    (v / "labels" / f"{name}-cell.txt").write_text("0 0.5 0.5 0.1 0.1\n")
    return v


def _run_catalog_builder(root: Path, *extra: str) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable, "-m", "tools.omr.training.build_catalog_yaml",
        "--root", str(root), "--val-fraction", "0",
        "--weights", str(root / "no-weights.pt"),
        *extra,
    ]
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)


def test_catalog_refuses_without_manifest_or_versions(tmp_path: Path):
    """No manifest + no --versions = refuse, pointing at the decision
    record — never a silent union of what happens to be on disk."""
    root = tmp_path / "user-labeled"
    _add_version(root, "v1-2026-01-01-a")
    _add_version(root, "v2-2026-01-02-b")
    result = _run_catalog_builder(root)
    assert result.returncode != 0
    assert "catalog-versions.txt" in result.stderr
    assert "decision #13" in result.stderr
    # The refusal lists what IS on disk, so writing the manifest is easy.
    assert "v2-2026-01-02-b" in result.stderr
    assert not (root / "catalog.yaml").exists()


def test_catalog_unions_only_manifest_members(tmp_path: Path):
    """A version on disk but not in the manifest stays out of the catalog,
    and the exclusion is reported rather than silent."""
    root = tmp_path / "user-labeled"
    _add_version(root, "v1-2026-01-01-a")
    _add_version(root, "v2-2026-01-02-b")
    (root / "catalog-versions.txt").write_text(
        "# membership record\nv1-2026-01-01-a\n"
    )
    result = _run_catalog_builder(root)
    assert result.returncode == 0, result.stderr

    train = (root / "_catalog_train.txt").read_text()
    assert "v1-2026-01-01-a" in train
    assert "v2-2026-01-02-b" not in train
    assert "v2-2026-01-02-b" in result.stdout          # named as excluded
    assert "decision #13" in result.stdout

    summary = json.loads((root / "_catalog_summary.json").read_text())
    assert [v["name"] for v in summary["versions"]] == ["v1-2026-01-01-a"]
    assert summary["versions_excluded_on_disk"] == ["v2-2026-01-02-b"]
    assert summary["membership_source"].endswith("catalog-versions.txt")


def test_catalog_refuses_manifest_entry_missing_on_disk(tmp_path: Path):
    """A manifest naming a version that isn't there cannot be reproduced —
    refuse rather than build a smaller catalog quietly."""
    root = tmp_path / "user-labeled"
    _add_version(root, "v1-2026-01-01-a")
    (root / "catalog-versions.txt").write_text(
        "v1-2026-01-01-a\nv9-2026-01-09-ghost\n"
    )
    result = _run_catalog_builder(root)
    assert result.returncode != 0
    assert "v9-2026-01-09-ghost" in result.stderr


def test_catalog_refuses_duplicate_manifest_entries(tmp_path: Path):
    root = tmp_path / "user-labeled"
    _add_version(root, "v1-2026-01-01-a")
    (root / "catalog-versions.txt").write_text(
        "v1-2026-01-01-a\nv1-2026-01-01-a\n"
    )
    result = _run_catalog_builder(root)
    assert result.returncode != 0
    assert "more than once" in result.stderr


def test_catalog_versions_flag_overrides_manifest(tmp_path: Path):
    """--versions is the deliberate one-off path: it names its membership
    on the command line and is recorded as the source in the summary."""
    root = tmp_path / "user-labeled"
    _add_version(root, "v1-2026-01-01-a")
    _add_version(root, "v2-2026-01-02-b")
    (root / "catalog-versions.txt").write_text("v1-2026-01-01-a\n")
    result = _run_catalog_builder(root, "--versions", "v2-2026-01-02-b")
    assert result.returncode == 0, result.stderr
    train = (root / "_catalog_train.txt").read_text()
    assert "v2-2026-01-02-b" in train
    assert "v1-2026-01-01-a/images" not in train
    summary = json.loads((root / "_catalog_summary.json").read_text())
    assert summary["membership_source"] == "--versions"
    assert [v["name"] for v in summary["versions"]] == ["v2-2026-01-02-b"]


def test_committed_catalog_membership_is_v1_through_v4():
    """Pin the committed membership AND that the manifest reproduces the
    committed catalog exactly.

    If this fails because you changed data/user-labeled/catalog-versions.txt
    on purpose: that is a training decision — update PROJECT_STATUS.md open
    decision #13, rebuild the catalog so _catalog_summary.json matches, and
    update this pin, all in the same commit. If you did NOT change the
    manifest on purpose, put it back.
    """
    from tools.omr.training.build_catalog_yaml import (
        read_versions_manifest,
        select_versions,
    )

    root = REPO_ROOT / "data" / "user-labeled"
    committed = [
        "v1-2026-05-18-orchestral",
        "v2-2026-06-08-beet5",
        "v3-2026-06-09-mahler5",
        "v4-2026-06-10-la-mer",
    ]
    assert read_versions_manifest(root) == committed

    # The manifest and the generated catalog must agree — editing one
    # without rebuilding the other is exactly the drift this guards.
    summary = json.loads((root / "_catalog_summary.json").read_text())
    assert [v["name"] for v in summary["versions"]] == committed

    # A default run resolves to the same membership (read-only check;
    # nothing is written).
    members, excluded, source = select_versions(root, None)
    assert [d.name for d in members] == committed
    assert source.endswith("catalog-versions.txt")
    # The recorded exclusions are on disk and stay out (PROJECT_STATUS.md
    # #13 for v5/v6; the hollow batch's entry is an open training-time
    # decision — benchmarks/omr-labeling-hollow-2026-08/AUDIT.md).
    for parked in ("v5-2026-07-12-clef", "v6-2026-07-13-clef-diverse",
                   "v7-2026-09-02-hollow"):
        assert (root / parked).is_dir()
        assert parked in excluded


# ---------------------------------------------------------------------------
# train_yolo — nc consistency guard
# ---------------------------------------------------------------------------


def _nc_check_fixture(tmp_path: Path, nc: int) -> tuple[Path, Path]:
    data_yaml = tmp_path / "data.yaml"
    data_yaml.write_text(yaml.safe_dump({"nc": nc, "names": ["x"] * nc}))
    weights = tmp_path / "ckpt.pt"
    weights.write_bytes(b"not a real checkpoint")
    return data_yaml, weights


def test_nc_guard_blocks_mismatch(tmp_path: Path, monkeypatch):
    from tools.omr.training import train_yolo

    data_yaml, weights = _nc_check_fixture(tmp_path, 214)
    monkeypatch.setattr(train_yolo, "_read_checkpoint_num_classes",
                        lambda p: 208)
    assert train_yolo._check_nc_consistency(
        data_yaml, str(weights), allow_expansion=False) is not None


def test_nc_guard_passes_on_match(tmp_path: Path, monkeypatch):
    from tools.omr.training import train_yolo

    data_yaml, weights = _nc_check_fixture(tmp_path, 208)
    monkeypatch.setattr(train_yolo, "_read_checkpoint_num_classes",
                        lambda p: 208)
    assert train_yolo._check_nc_consistency(
        data_yaml, str(weights), allow_expansion=False) is None


def test_nc_guard_respects_allow_flag(tmp_path: Path, monkeypatch):
    from tools.omr.training import train_yolo

    data_yaml, weights = _nc_check_fixture(tmp_path, 214)
    monkeypatch.setattr(train_yolo, "_read_checkpoint_num_classes",
                        lambda p: 208)
    assert train_yolo._check_nc_consistency(
        data_yaml, str(weights), allow_expansion=True) is None


def test_nc_guard_skips_download_aliases(tmp_path: Path):
    from tools.omr.training import train_yolo

    data_yaml, _ = _nc_check_fixture(tmp_path, 214)
    # Non-existent path = ultralytics auto-download alias — nothing
    # fine-tuned to protect, so the guard must not block.
    assert train_yolo._check_nc_consistency(
        data_yaml, "yolov8m.pt", allow_expansion=False) is None
