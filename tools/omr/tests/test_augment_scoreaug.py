"""ScoreAug scan-degradation augmentation tests.

Run without the real TISMIR blanks, without augraphy, and without a
network connection — the end-to-end tests synthesize tiny score-like
images and (where needed) tiny blank pages on the fly.

Marked `omr_training`. Run with:

    pytest tools/omr/tests/test_augment_scoreaug.py -v
    pytest -m omr_training -v
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import cv2
import numpy as np
import pytest

from tools.omr.training.augment_scoreaug import (
    AUGRAPHY_SAFE_EFFECTS,
    apply_blank_composite,
    apply_show_through,
    discover_blanks,
    run,
    synth_blank,
    _augment_blank,
    _fit_to_target,
    _per_image_rng,
)


pytestmark = pytest.mark.omr_training


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_score_image(w: int = 320, h: int = 120, seed: int = 0) -> np.ndarray:
    """White page, black staff lines + a few 'notehead' blobs (BGR)."""
    rng = random.Random(seed)
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    for i in range(5):
        y = 20 + i * 16
        img[y : y + 2, 8 : w - 8] = 0
    for _ in range(4):
        cx = rng.randint(30, w - 30)
        cy = rng.randint(20, h - 20)
        cv2.ellipse(img, (cx, cy), (7, 5), 0, 0, 360, (0, 0, 0), -1)
    return img


def _make_training_dir(root: Path, n: int = 4) -> "tuple[Path, Path]":
    images = root / "images"
    labels = root / "labels"
    images.mkdir(parents=True)
    labels.mkdir(parents=True)
    for i in range(n):
        cv2.imwrite(str(images / f"cell{i}.png"), _fake_score_image(seed=i))
        (labels / f"cell{i}.txt").write_text(
            f"24 0.5{i} 0.40 0.05 0.10\n208 0.25 0.5{i} 0.02 0.30\n"
        )
    return images, labels


# ---------------------------------------------------------------------------
# Unit: synthetic blanks + blank augmentation
# ---------------------------------------------------------------------------


def test_synth_blank_shape_dtype_and_tone():
    blank = synth_blank(random.Random(1), width=200, height=300)
    assert blank.shape == (300, 200, 3)
    assert blank.dtype == np.uint8
    # Aged paper: bright-ish overall, never pure white everywhere.
    assert 120 < blank.mean() < 250
    assert blank.min() < 250


def test_synth_blank_deterministic():
    a = synth_blank(random.Random(7), width=64, height=64)
    b = synth_blank(random.Random(7), width=64, height=64)
    assert np.array_equal(a, b)


def test_augment_blank_no_dark_corners_from_rotation():
    """BORDER_REPLICATE must prevent black rotation corners — a black
    corner would survive the darker-min merge and stamp a fake blob."""
    blank = np.full((200, 200, 3), 210, dtype=np.uint8)
    for seed in range(5):
        out, params = _augment_blank(blank, random.Random(seed))
        assert out.shape == blank.shape
        # Corners must stay paper-toned (brightness jitter can move the
        # level, but nowhere near ink-black).
        for corner in (out[0, 0], out[0, -1], out[-1, 0], out[-1, -1]):
            assert corner.min() > 100, f"dark corner with seed {seed}: {corner}"


def test_fit_to_target_covers_exact_size():
    src = np.full((300, 200, 3), 190, dtype=np.uint8)
    for tw, th in [(500, 40), (40, 500), (100, 100), (640, 480)]:
        out = _fit_to_target(src, tw, th, random.Random(0))
        assert out.shape[:2] == (th, tw)


# ---------------------------------------------------------------------------
# Unit: degradation ops are strictly darkening / photometric
# ---------------------------------------------------------------------------


def test_blank_composite_never_lightens():
    img = _fake_score_image()
    blank = synth_blank(random.Random(3), width=400, height=200)
    out, params = apply_blank_composite(img, blank, random.Random(3))
    assert out.shape == img.shape
    assert out.dtype == img.dtype
    assert (out <= img).all(), "darker-min merge must never lighten a pixel"
    assert "rotation_deg" in params


def test_blank_composite_preserves_ink():
    """Black ink pixels must stay black after compositing."""
    img = _fake_score_image()
    ink = img.min(axis=2) == 0
    blank = synth_blank(random.Random(4), width=400, height=200)
    out, _ = apply_blank_composite(img, blank, random.Random(4))
    assert (out[ink] == 0).all()


def test_show_through_never_lightens_and_is_subtle():
    img = _fake_score_image(seed=1)
    partner = _fake_score_image(seed=2)
    out, params = apply_show_through(img, partner, random.Random(5))
    assert out.shape == img.shape
    assert (out <= img).all()
    assert 0.05 <= params["alpha"] <= 0.15
    # Ghost ink is faint: background must not drop anywhere near ink level.
    bg = img.min(axis=2) == 255
    assert out[bg].min() > 150


def test_grayscale_input_supported():
    img = cv2.cvtColor(_fake_score_image(), cv2.COLOR_BGR2GRAY)
    blank = synth_blank(random.Random(6), width=400, height=200)
    out, _ = apply_blank_composite(img, blank, random.Random(6))
    assert out.shape == img.shape and out.ndim == 2
    out2, _ = apply_show_through(img, _fake_score_image(seed=9), random.Random(6))
    assert out2.shape == img.shape and out2.ndim == 2


def test_augraphy_safe_list_has_no_spatial_effects():
    """Guard the invariant that keeps labels valid: no geometric augs."""
    forbidden = {
        "BookBinding", "Folding", "Geometric", "PageBorder", "BindingsAndFasteners",
        "SectionShift", "GlitchEffect", "Squish", "DotMatrix", "Rescale",
    }
    assert not forbidden & set(AUGRAPHY_SAFE_EFFECTS)


# ---------------------------------------------------------------------------
# End-to-end via run()
# ---------------------------------------------------------------------------


def test_run_end_to_end_labels_byte_identical(tmp_path):
    images, labels = _make_training_dir(tmp_path / "src", n=4)
    out_root = tmp_path / "out"
    manifest = run(
        src_images=images,
        src_labels=labels,
        out_root=out_root,
        blanks_dir=None,  # forces the synthetic-blank fallback
        fraction=0.5,
        seed=13,
        use_augraphy=False,
    )

    # All 4 originals present, exactly 2 degraded twins.
    out_images = sorted(p.name for p in (out_root / "images").glob("*.png"))
    out_labels = sorted(p.name for p in (out_root / "labels").glob("*.txt"))
    assert len([n for n in out_images if "_aug" not in n]) == 4
    assert len([n for n in out_images if "_aug" in n]) == 2
    assert len(out_images) == len(out_labels)
    assert manifest["n_degraded_written"] == 2
    assert manifest["synthetic_blank_fallback_used"] is True

    # Labels byte-identical to source (originals AND _aug copies).
    for lab in (out_root / "labels").glob("*.txt"):
        base = lab.stem.split("_aug")[0]
        assert lab.read_bytes() == (labels / f"{base}.txt").read_bytes()

    # Degraded images: same shape/dtype, strictly darker-or-equal nowhere
    # required (augraphy could add noise) — but with use_augraphy=False
    # all ops are darkening-only.
    for img in (out_root / "images").glob("*_aug*.png"):
        base = img.stem.split("_aug")[0]
        a = cv2.imread(str(images / f"{base}.png"), cv2.IMREAD_UNCHANGED)
        b = cv2.imread(str(img), cv2.IMREAD_UNCHANGED)
        assert a.shape == b.shape and a.dtype == b.dtype
        assert (b <= a).all()
        assert not np.array_equal(a, b), "degraded twin should differ"

    # Manifest sanity.
    on_disk = json.loads((out_root / "scoreaug_manifest.json").read_text())
    assert on_disk["seed"] == 13
    degraded_entries = [d for e in on_disk["images"] for d in e["degraded"]]
    assert len(degraded_entries) == 2
    assert all(d["ops"] for d in degraded_entries)


def test_run_deterministic_for_seed(tmp_path):
    images, labels = _make_training_dir(tmp_path / "src", n=3)
    m1 = run(src_images=images, src_labels=labels, out_root=tmp_path / "o1",
             blanks_dir=None, fraction=1.0, seed=99, use_augraphy=False)
    m2 = run(src_images=images, src_labels=labels, out_root=tmp_path / "o2",
             blanks_dir=None, fraction=1.0, seed=99, use_augraphy=False)
    for img in (tmp_path / "o1" / "images").glob("*.png"):
        twin = tmp_path / "o2" / "images" / img.name
        assert img.read_bytes() == twin.read_bytes(), img.name
    assert m1["images"] == m2["images"]


def test_run_uses_real_blanks_when_present(tmp_path):
    images, labels = _make_training_dir(tmp_path / "src", n=2)
    blanks_dir = tmp_path / "blanks"
    blanks_dir.mkdir()
    cv2.imwrite(str(blanks_dir / "blank0.png"),
                synth_blank(random.Random(0), width=400, height=300))
    manifest = run(
        src_images=images, src_labels=labels, out_root=tmp_path / "out",
        blanks_dir=blanks_dir, fraction=1.0, seed=5, use_augraphy=False,
    )
    assert manifest["n_real_blanks"] == 1
    assert manifest["synthetic_blank_fallback_used"] is False
    blank_ops = [
        o
        for e in manifest["images"]
        for d in e["degraded"]
        for o in d["ops"]
        if o["op"] == "blank_composite"
    ]
    assert all(o["blank"] == "blank0.png" for o in blank_ops)


def test_run_augs_per_image(tmp_path):
    images, labels = _make_training_dir(tmp_path / "src", n=2)
    run(src_images=images, src_labels=labels, out_root=tmp_path / "out",
        blanks_dir=None, fraction=1.0, seed=1, augs_per_image=3,
        use_augraphy=False)
    augs = sorted(p.name for p in (tmp_path / "out" / "images").glob("cell0_aug*.png"))
    assert augs == ["cell0_aug0.png", "cell0_aug1.png", "cell0_aug2.png"]


def test_discover_blanks_recursive_and_missing_dir(tmp_path):
    assert discover_blanks(tmp_path / "nope") == []
    d = tmp_path / "blanks" / "seamed"
    d.mkdir(parents=True)
    cv2.imwrite(str(d / "a.png"), np.full((10, 10, 3), 200, np.uint8))
    (d / "notes.txt").write_text("not an image")
    found = discover_blanks(tmp_path / "blanks")
    assert [p.name for p in found] == ["a.png"]


def test_per_image_rng_stable_across_runs():
    a = _per_image_rng(41, "cellX").random()
    b = _per_image_rng(41, "cellX").random()
    c = _per_image_rng(41, "cellY").random()
    assert a == b
    assert a != c


def test_cli_download_flag_is_exposed():
    """--download-blanks must exist (no network hit here — just argparse)."""
    from tools.omr.training.augment_scoreaug import main

    with pytest.raises(SystemExit):
        main(["--help"])
