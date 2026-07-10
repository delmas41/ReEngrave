"""ScoreAug-style scan-degradation augmentation for YOLO training data.

Implements the data-degradation recipe from the TISMIR paper "Real World
Music Object Recognition" (Tuggener et al., 10.5334/tismir.157): composite
real *blank* scanned IMSLP pages onto clean training images with a
per-pixel darker-min merge, so the paper texture / stains / vignette of a
real scan land on the image while every ink pixel survives. Because the
merge only changes pixel values (never geometry), the YOLO label files
are copied VERBATIM — labels stay byte-identical to the source labels.

Three degradation families, randomly chosen/combined per selected image:

  (a) ScoreAug blank compositing — pick a random blank page, randomly
      augment it (small rotation, blur, additive noise,
      brightness/contrast jitter), scale-and-crop it to the target image
      size, then merge via ``np.minimum`` (darker pixel wins).
  (b) Mirrored show-through — composite a horizontally flipped copy of
      ANOTHER source image at low opacity (5–15%) to simulate ink
      bleed-through from the reverse side of the page.
  (c) Augraphy photometric effects — if the ``augraphy`` package is
      importable: InkBleed, BleedThrough, LowInkPeriodicLines,
      LowInkRandomLines, InkMottling, NoiseTexturize, and a tame
      BadPhotoCopy. Augraphy's spatial / warping augmentations are
      NEVER used (they would move pixels out from under the bboxes).
      Without augraphy installed the script still works with (a)+(b).

Output layout (a complete drop-in training dir):

  <out-root>/
    images/<stem>.png            ← untouched original (always copied)
    images/<stem>_aug0.png       ← degraded variant(s)
    labels/<stem>.txt            ← copied verbatim
    labels/<stem>_aug0.txt       ← byte-identical copy of <stem>.txt
    scoreaug_manifest.json       ← per-image record of what was applied

Blank pages
-----------

The paper's blank scans are released as ``blanks.tar`` on the
``TISMIR_publication`` branch of https://github.com/raember/s2anet. The
file is git-LFS-tracked, so raw.githubusercontent serves only the LFS
pointer; the actual bytes (~186 MB, 51 PNGs of scanned blank IMSLP pages)
come from the LFS media endpoint. Either run::

    python3 -m tools.omr.training.augment_scoreaug --download-blanks \
        --blanks-dir tools/omr/training/data/blanks

or fetch by hand::

    curl -L -o blanks.tar \
      "https://media.githubusercontent.com/media/raember/s2anet/TISMIR_publication/blanks.tar"
    tar xf blanks.tar   # → blanks/seamed/*.png + blanks/seamless/*.png

If no real blanks are available at augmentation time the script falls
back to synthetic paper-texture blanks (off-white base + multi-octave
noise + random stains + vignette) and clearly reports the fallback —
but the real scans are strictly better; download them when you can.

CLI:
    # one-time blank download
    python3 -m tools.omr.training.augment_scoreaug --download-blanks

    # degrade a training dir (originals kept, 50% get a degraded twin)
    python3 -m tools.omr.training.augment_scoreaug \
        --src-images data/user-labeled/v1-2026-05-18-orchestral/images \
        --src-labels data/user-labeled/v1-2026-05-18-orchestral/labels \
        --out-root   tools/omr/training/data/scoreaug/v1-scoreaug \
        --blanks-dir tools/omr/training/data/blanks \
        --fraction 0.5 --seed 41
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import sys
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# git-LFS media endpoint for the TISMIR blanks archive (raw.githubusercontent
# serves only the 134-byte LFS pointer for this path).
BLANKS_TAR_URL = (
    "https://media.githubusercontent.com/media/"
    "raember/s2anet/TISMIR_publication/blanks.tar"
)
BLANKS_TAR_SHA256 = (
    "4225b5c75ed30c735e264e6ea8c238d52ceb3ef7d36aa34a0eafe2dac2fce92f"
)
BLANKS_TAR_SIZE = 195_164_160  # bytes, per the LFS pointer

DEFAULT_BLANKS_DIR = Path("tools/omr/training/data/blanks")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

# Probability that each degradation family is applied to a selected image.
# If the dice give an empty set, blank compositing is forced so every
# "degraded" output really is degraded.
P_BLANK_COMPOSITE = 0.85
P_SHOW_THROUGH = 0.5
P_AUGRAPHY = 0.5

# Names of the Augraphy effects we consider photometric-safe. Anything
# not in this list — especially geometric/warping augs like BookBinding,
# Folding, Geometric, PageBorder — must never be added: they move pixels
# and would silently invalidate the (copied-verbatim) YOLO labels.
AUGRAPHY_SAFE_EFFECTS = (
    "InkBleed",
    "BleedThrough",
    "LowInkPeriodicLines",
    "LowInkRandomLines",
    "InkMottling",
    "NoiseTexturize",
    "BadPhotoCopy",
)

AUGRAPHY_INSTALL_HINT = (
    "augraphy not importable — Augraphy effects disabled (ScoreAug blank "
    "compositing + show-through still run). To enable: "
    "pip install augraphy   (https://github.com/sparkfish/augraphy)"
)


# ---------------------------------------------------------------------------
# Lazy augraphy import
# ---------------------------------------------------------------------------


_AUGRAPHY_MODULE = None
_AUGRAPHY_CHECKED = False


def _get_augraphy():
    """Import augraphy lazily; return the module or None."""
    global _AUGRAPHY_MODULE, _AUGRAPHY_CHECKED
    if not _AUGRAPHY_CHECKED:
        _AUGRAPHY_CHECKED = True
        try:
            import augraphy  # heavy: pulls numba, sklearn, skimage

            _AUGRAPHY_MODULE = augraphy
        except ImportError:
            _AUGRAPHY_MODULE = None
    return _AUGRAPHY_MODULE


# ---------------------------------------------------------------------------
# Blank handling
# ---------------------------------------------------------------------------


def download_blanks(blanks_dir: Path, *, url: str = BLANKS_TAR_URL) -> Path:
    """Download blanks.tar from the s2anet TISMIR_publication branch and
    extract it under `blanks_dir`. Returns the extraction root.

    The tar contains blanks/seamed/*.png and blanks/seamless/*.png.
    """
    blanks_dir.mkdir(parents=True, exist_ok=True)
    tar_path = blanks_dir / "blanks.tar"
    if not tar_path.exists() or tar_path.stat().st_size != BLANKS_TAR_SIZE:
        print(f"downloading {url}\n  → {tar_path} (~186 MB)")
        tmp = tar_path.with_suffix(".tar.part")
        with urllib.request.urlopen(url, timeout=120) as resp, tmp.open("wb") as f:
            shutil.copyfileobj(resp, f, length=1 << 20)
        tmp.rename(tar_path)
    else:
        print(f"blanks.tar already present: {tar_path}")

    digest = hashlib.sha256()
    with tar_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    if digest.hexdigest() != BLANKS_TAR_SHA256:
        raise SystemExit(
            f"blanks.tar sha256 mismatch: got {digest.hexdigest()}, "
            f"expected {BLANKS_TAR_SHA256} — delete {tar_path} and retry"
        )

    print("extracting …")
    with tarfile.open(tar_path) as tf:
        # Python ≥3.12 has the safe "data" filter; older versions get a
        # manual path check.
        if hasattr(tarfile, "data_filter"):
            tf.extractall(blanks_dir, filter="data")
        else:
            for m in tf.getmembers():
                p = (blanks_dir / m.name).resolve()
                if not str(p).startswith(str(blanks_dir.resolve())):
                    raise SystemExit(f"unsafe tar member: {m.name}")
            tf.extractall(blanks_dir)
    n = len(discover_blanks(blanks_dir))
    print(f"extracted — {n} blank page PNGs under {blanks_dir}")
    return blanks_dir


def discover_blanks(blanks_dir: Path) -> "list[Path]":
    """All blank-page PNGs under `blanks_dir` (recursive), sorted."""
    if not blanks_dir.is_dir():
        return []
    return sorted(
        p
        for p in blanks_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )


def synth_blank(
    rng: "random.Random",
    width: int = 1960,
    height: int = 2772,
) -> np.ndarray:
    """Generate a synthetic paper-texture blank (BGR uint8).

    Fallback for when the real TISMIR blanks aren't on disk: off-white /
    tan base + multi-octave value noise + random blurred stains + vignette
    + optional binding shadow along one vertical edge.
    """
    nprng = np.random.default_rng(rng.getrandbits(32))

    # Aged-paper base tone (BGR). Blue channel lowest → warm tan.
    base_b = rng.uniform(170, 205)
    base_g = rng.uniform(195, 225)
    base_r = rng.uniform(210, 240)
    img = np.empty((height, width, 3), dtype=np.float32)
    img[..., 0] = base_b
    img[..., 1] = base_g
    img[..., 2] = base_r

    # Multi-octave value noise ("Perlin-ish"): low-res gaussian fields
    # upscaled with cubic interpolation, halving amplitude per octave.
    texture = np.zeros((height, width), dtype=np.float32)
    amp = rng.uniform(6.0, 14.0)
    cells = 8
    for _ in range(4):
        low = nprng.normal(0.0, 1.0, size=(cells, max(1, cells * width // height)))
        texture += amp * cv2.resize(
            low.astype(np.float32), (width, height), interpolation=cv2.INTER_CUBIC
        )
        amp *= 0.5
        cells *= 2
    img += texture[..., None]

    # Random stains: dark translucent ellipses, heavily blurred.
    stain = np.zeros((height, width), dtype=np.float32)
    for _ in range(rng.randint(1, 5)):
        cx = rng.randint(0, width - 1)
        cy = rng.randint(0, height - 1)
        ax = rng.randint(width // 20, width // 4)
        ay = rng.randint(height // 20, height // 4)
        angle = rng.uniform(0, 180)
        depth = rng.uniform(8, 30)
        cv2.ellipse(stain, (cx, cy), (ax, ay), angle, 0, 360, float(depth), -1)
    k = max(3, (min(width, height) // 8) | 1)
    stain = cv2.GaussianBlur(stain, (k, k), 0)
    img -= stain[..., None]

    # Vignette: darken toward the page edges.
    yy = np.linspace(-1.0, 1.0, height, dtype=np.float32)[:, None]
    xx = np.linspace(-1.0, 1.0, width, dtype=np.float32)[None, :]
    r = np.sqrt(xx * xx + yy * yy)
    vignette = np.clip(r - rng.uniform(0.6, 0.9), 0.0, None) * rng.uniform(20, 60)
    img -= vignette[..., None]

    # Optional binding shadow along the left or right edge.
    if rng.random() < 0.6:
        shadow_w = rng.randint(width // 30, width // 10)
        ramp = np.linspace(rng.uniform(30, 70), 0.0, shadow_w, dtype=np.float32)
        if rng.random() < 0.5:
            img[:, :shadow_w] -= ramp[None, :, None]
        else:
            img[:, width - shadow_w :] -= ramp[::-1][None, :, None]

    return np.clip(img, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Degradation ops (all photometric — geometry of the SOURCE image is
# never touched, so labels stay valid)
# ---------------------------------------------------------------------------


def _augment_blank(blank: np.ndarray, rng: "random.Random") -> "tuple[np.ndarray, dict]":
    """Randomly augment a blank page: small rotation, blur, noise,
    brightness/contrast jitter. Rotation uses BORDER_REPLICATE so no
    black corners appear (which the darker-min merge would keep)."""
    params: dict = {}
    out = blank

    rot = rng.uniform(-3.0, 3.0)
    params["rotation_deg"] = round(rot, 3)
    h, w = out.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), rot, 1.0)
    out = cv2.warpAffine(
        out, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
    )

    blur_k = rng.choice([0, 0, 3, 5])
    params["blur_kernel"] = blur_k
    if blur_k:
        out = cv2.GaussianBlur(out, (blur_k, blur_k), 0)

    noise_sigma = rng.uniform(0.0, 8.0)
    params["noise_sigma"] = round(noise_sigma, 3)
    if noise_sigma > 0.5:
        nprng = np.random.default_rng(rng.getrandbits(32))
        noise = nprng.normal(0.0, noise_sigma, size=out.shape).astype(np.float32)
        out = np.clip(out.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    contrast = rng.uniform(0.85, 1.15)
    brightness = rng.uniform(-20.0, 20.0)
    params["contrast"] = round(contrast, 3)
    params["brightness"] = round(brightness, 3)
    out = np.clip(out.astype(np.float32) * contrast + brightness, 0, 255).astype(
        np.uint8
    )
    return out, params


def _fit_to_target(src: np.ndarray, tw: int, th: int, rng: "random.Random") -> np.ndarray:
    """Scale `src` so it covers (tw, th), then random-crop the target size.

    Cover-and-crop preserves the paper texture's spatial scale much
    better than a naive stretch (our cells can be 2048×146 strips).
    """
    h, w = src.shape[:2]
    scale = max(tw / w, th / h)
    if scale != 1.0:
        src = cv2.resize(
            src,
            (max(tw, int(round(w * scale))), max(th, int(round(h * scale)))),
            interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR,
        )
    h, w = src.shape[:2]
    x0 = rng.randint(0, w - tw) if w > tw else 0
    y0 = rng.randint(0, h - th) if h > th else 0
    return src[y0 : y0 + th, x0 : x0 + tw]


def apply_blank_composite(
    img: np.ndarray,
    blank: np.ndarray,
    rng: "random.Random",
) -> "tuple[np.ndarray, dict]":
    """ScoreAug: darker-min merge of an augmented blank onto the image.

    Per-pixel ``np.minimum`` keeps the darker of (image, blank) — ink
    always survives, paper texture wins over white background.
    """
    th, tw = img.shape[:2]
    blank_aug, params = _augment_blank(blank, rng)
    blank_fit = _fit_to_target(blank_aug, tw, th, rng)
    if img.ndim == 2:
        blank_fit = cv2.cvtColor(blank_fit, cv2.COLOR_BGR2GRAY)
    out = np.minimum(img, blank_fit)
    return out, params


def apply_show_through(
    img: np.ndarray,
    partner: np.ndarray,
    rng: "random.Random",
) -> "tuple[np.ndarray, dict]":
    """Mirrored show-through: darken with a horizontally flipped copy of
    ANOTHER page at low opacity, simulating reverse-side ink bleed.

    The ghost is rendered as ``255 - alpha * (255 - flipped)`` — i.e. the
    flipped page faded onto white — then merged with darker-min, so the
    op strictly darkens (never lightens real ink).
    """
    alpha = rng.uniform(0.05, 0.15)
    th, tw = img.shape[:2]
    flipped = cv2.flip(partner, 1)
    if flipped.ndim != img.ndim:
        if img.ndim == 2:
            flipped = cv2.cvtColor(flipped, cv2.COLOR_BGR2GRAY)
        else:
            flipped = cv2.cvtColor(flipped, cv2.COLOR_GRAY2BGR)
    flipped = cv2.resize(flipped, (tw, th), interpolation=cv2.INTER_AREA)
    # Show-through ink is diffuse — blur the ghost a touch.
    flipped = cv2.GaussianBlur(flipped, (5, 5), 0)
    ghost = 255.0 - alpha * (255.0 - flipped.astype(np.float32))
    out = np.minimum(img, np.clip(ghost, 0, 255).astype(np.uint8))
    return out, {"alpha": round(alpha, 4)}


def _build_augraphy_effect(name: str, rng: "random.Random"):
    """Instantiate one photometric-safe Augraphy effect with tame params.

    Verified against augraphy 8.2.x signatures. BadPhotoCopy explicitly
    disables blur_noise / wave_pattern / edge_effect to stay strictly
    photometric and keep runtime sane.
    """
    aug = _get_augraphy()
    assert aug is not None
    if name == "InkBleed":
        return aug.InkBleed(
            intensity_range=(0.3, 0.6), kernel_size=(5, 5), severity=(0.2, 0.4), p=1
        )
    if name == "BleedThrough":
        return aug.BleedThrough(
            intensity_range=(0.05, 0.2),
            alpha=rng.uniform(0.1, 0.25),
            offsets=(10, 10),
            p=1,
        )
    if name == "LowInkPeriodicLines":
        return aug.LowInkPeriodicLines(count_range=(1, 3), period_range=(12, 32), p=1)
    if name == "LowInkRandomLines":
        return aug.LowInkRandomLines(count_range=(3, 8), p=1)
    if name == "InkMottling":
        return aug.InkMottling(ink_mottling_alpha_range=(0.15, 0.3), p=1)
    if name == "NoiseTexturize":
        return aug.NoiseTexturize(sigma_range=(2, 6), turbulence_range=(2, 4), p=1)
    if name == "BadPhotoCopy":
        return aug.BadPhotoCopy(
            noise_value=(180, 255),
            noise_sparsity=(0.4, 0.9),
            noise_concentration=(0.05, 0.2),
            noise_iteration=(1, 1),
            noise_size=(1, 2),
            blur_noise=0,
            wave_pattern=0,
            edge_effect=0,
            p=1,
        )
    raise ValueError(f"unknown augraphy effect: {name}")


def apply_augraphy(
    img: np.ndarray,
    rng: "random.Random",
    n_effects: "Optional[int]" = None,
) -> "tuple[np.ndarray, dict]":
    """Apply 1–2 randomly chosen photometric-safe Augraphy effects.

    Requires augraphy to be importable (caller checks). Any effect whose
    output shape/dtype differs from the input is discarded — belt and
    braces against a version drifting into spatial behavior.
    """
    was_gray = img.ndim == 2
    work = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if was_gray else img.copy()

    if n_effects is None:
        n_effects = rng.randint(1, 2)
    chosen = rng.sample(list(AUGRAPHY_SAFE_EFFECTS), k=n_effects)
    applied = []
    for name in chosen:
        effect = _build_augraphy_effect(name, rng)
        # Augraphy consumes BOTH numpy's and python's global RNG state —
        # seed them per-effect so runs are reproducible for a given --seed.
        np.random.seed(rng.getrandbits(32))
        random.seed(rng.getrandbits(64))
        out = effect(work.copy())
        if isinstance(out, tuple):
            out = out[0]
        if (
            not isinstance(out, np.ndarray)
            or out.shape != work.shape
            or out.dtype != work.dtype
        ):
            print(f"    WARN: augraphy {name} changed shape/dtype — skipped")
            continue
        work = out
        applied.append(name)

    if was_gray:
        work = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    return work, {"effects": applied}


# ---------------------------------------------------------------------------
# Per-image pipeline
# ---------------------------------------------------------------------------


def degrade_image(
    img: np.ndarray,
    *,
    rng: "random.Random",
    blanks: "list[Path]",
    partner: "Optional[np.ndarray]",
    use_augraphy: bool,
    synth_fallback_used: "list[bool]",
) -> "tuple[np.ndarray, list[dict]]":
    """Apply a random combination of the degradation families to `img`.

    At least one family is always applied (blank compositing is the
    forced default). Returns (degraded_image, ops_record).
    """
    ops: "list[dict]" = []
    do_blank = rng.random() < P_BLANK_COMPOSITE
    do_show = partner is not None and rng.random() < P_SHOW_THROUGH
    do_augraphy = use_augraphy and rng.random() < P_AUGRAPHY
    if not (do_blank or do_show or do_augraphy):
        do_blank = True

    out = img

    # Show-through goes first: real bleed-through sits UNDER the paper
    # grime that the blank composite adds.
    if do_show:
        out, params = apply_show_through(out, partner, rng)
        ops.append({"op": "show_through", **params})

    if do_blank:
        if blanks:
            blank_path = rng.choice(blanks)
            blank = cv2.imread(str(blank_path), cv2.IMREAD_COLOR)
            if blank is None:
                blank = synth_blank(rng)
                blank_name = "<synthetic:unreadable-blank>"
                synth_fallback_used[0] = True
            else:
                blank_name = blank_path.name
        else:
            blank = synth_blank(rng)
            blank_name = "<synthetic:no-blanks-dir>"
            synth_fallback_used[0] = True
        out, params = apply_blank_composite(out, blank, rng)
        ops.append({"op": "blank_composite", "blank": blank_name, **params})

    if do_augraphy:
        out, params = apply_augraphy(out, rng)
        if params["effects"]:
            ops.append({"op": "augraphy", **params})

    return out, ops


def _per_image_rng(seed: int, stem: str) -> "random.Random":
    """Deterministic RNG per (seed, image) — stable regardless of how many
    images are in the run or their order."""
    digest = hashlib.sha256(f"{seed}:{stem}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _load_image(path: Path) -> "Optional[np.ndarray]":
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    if img.ndim == 3 and img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


# ---------------------------------------------------------------------------
# Top-level run
# ---------------------------------------------------------------------------


def run(
    *,
    src_images: Path,
    src_labels: Path,
    out_root: Path,
    blanks_dir: "Optional[Path]",
    fraction: float,
    seed: int,
    augs_per_image: int = 1,
    use_augraphy: "Optional[bool]" = None,
) -> dict:
    """Build the degraded training dir. Returns the manifest dict."""
    if not src_images.is_dir():
        raise SystemExit(f"src images dir not found: {src_images}")
    if not src_labels.is_dir():
        raise SystemExit(f"src labels dir not found: {src_labels}")

    image_paths = sorted(
        p for p in src_images.iterdir() if p.suffix.lower() in IMAGE_EXTS
    )
    if not image_paths:
        raise SystemExit(f"no images found in {src_images}")

    if use_augraphy is None:
        use_augraphy = _get_augraphy() is not None
    if use_augraphy and _get_augraphy() is None:
        use_augraphy = False
    if not use_augraphy:
        print(AUGRAPHY_INSTALL_HINT)

    blanks = discover_blanks(blanks_dir) if blanks_dir else []
    if blanks:
        print(f"{len(blanks)} blank pages from {blanks_dir}")
    else:
        print(
            "WARNING: no blank pages found — falling back to SYNTHETIC "
            "paper-texture blanks. For the real TISMIR blanks run:\n"
            "  python3 -m tools.omr.training.augment_scoreaug --download-blanks"
        )

    out_images = out_root / "images"
    out_labels = out_root / "labels"
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    selector = random.Random(seed)
    n_select = int(round(fraction * len(image_paths)))
    selected = set(selector.sample(range(len(image_paths)), k=n_select))

    entries: "list[dict]" = []
    synth_fallback_used = [not blanks]
    n_degraded = 0
    n_skipped = 0

    for idx, img_path in enumerate(image_paths):
        stem = img_path.stem
        label_path = src_labels / f"{stem}.txt"
        if not label_path.exists():
            print(f"  SKIP {stem}: no label file")
            n_skipped += 1
            continue

        # Always ship the untouched original.
        shutil.copyfile(img_path, out_images / img_path.name)
        shutil.copyfile(label_path, out_labels / label_path.name)
        entry = {"src": img_path.name, "degraded": []}

        if idx in selected:
            img = _load_image(img_path)
            if img is None:
                print(f"  WARN {stem}: unreadable image — original kept, not degraded")
                entries.append(entry)
                continue
            rng = _per_image_rng(seed, stem)

            # Show-through partner: a different source image (if any).
            partner = None
            if len(image_paths) > 1:
                others = [p for p in image_paths if p != img_path]
                partner = _load_image(rng.choice(others))

            for k in range(augs_per_image):
                degraded, ops = degrade_image(
                    img,
                    rng=rng,
                    blanks=blanks,
                    partner=partner,
                    use_augraphy=use_augraphy,
                    synth_fallback_used=synth_fallback_used,
                )
                aug_name = f"{stem}_aug{k}{img_path.suffix}"
                cv2.imwrite(str(out_images / aug_name), degraded)
                shutil.copyfile(label_path, out_labels / f"{stem}_aug{k}.txt")
                entry["degraded"].append({"out": aug_name, "ops": ops})
                n_degraded += 1

        entries.append(entry)

    manifest = {
        "tool": "tools.omr.training.augment_scoreaug",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "src_images": str(src_images),
        "src_labels": str(src_labels),
        "blanks_dir": str(blanks_dir) if blanks_dir else None,
        "n_real_blanks": len(blanks),
        "synthetic_blank_fallback_used": synth_fallback_used[0],
        "fraction": fraction,
        "seed": seed,
        "augs_per_image": augs_per_image,
        "augraphy_available": use_augraphy,
        "n_source_images": len(image_paths),
        "n_selected": len(selected),
        "n_degraded_written": n_degraded,
        "n_skipped_no_label": n_skipped,
        "images": entries,
    }
    (out_root / "scoreaug_manifest.json").write_text(json.dumps(manifest, indent=2))

    print(
        f"\nwrote {out_root}/ — {len(image_paths) - n_skipped} originals + "
        f"{n_degraded} degraded (labels copied verbatim)"
    )
    if synth_fallback_used[0]:
        print(
            "NOTE: synthetic blanks were used for at least one image — "
            "download the real TISMIR blanks for best results."
        )
    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: "Optional[list[str]]" = None) -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--src-images", type=Path,
                    help="Directory of source training images.")
    ap.add_argument("--src-labels", type=Path,
                    help="Directory of YOLO .txt labels (matched by stem).")
    ap.add_argument("--out-root", type=Path,
                    help="Output dir; gets images/ + labels/ + manifest.")
    ap.add_argument("--blanks-dir", type=Path, default=DEFAULT_BLANKS_DIR,
                    help="Directory of blank scanned pages (searched "
                         f"recursively). Default: {DEFAULT_BLANKS_DIR}")
    ap.add_argument("--fraction", type=float, default=0.5,
                    help="Fraction of images that get a degraded twin "
                         "(originals are always kept). Default: 0.5")
    ap.add_argument("--seed", type=int, default=41,
                    help="RNG seed — same seed → identical output. Default: 41")
    ap.add_argument("--augs-per-image", type=int, default=1,
                    help="Degraded variants per selected image (suffixes "
                         "_aug0, _aug1, …). Default: 1")
    ap.add_argument("--no-augraphy", action="store_true",
                    help="Skip Augraphy effects even if the package is installed.")
    ap.add_argument("--download-blanks", action="store_true",
                    help="Download + extract the TISMIR blanks.tar into "
                         "--blanks-dir, then exit.")
    args = ap.parse_args(argv)

    if args.download_blanks:
        download_blanks(args.blanks_dir)
        return

    missing = [
        n for n in ("src_images", "src_labels", "out_root")
        if getattr(args, n) is None
    ]
    if missing:
        ap.error(
            "the following arguments are required: "
            + ", ".join("--" + n.replace("_", "-") for n in missing)
        )
    if not 0.0 <= args.fraction <= 1.0:
        ap.error("--fraction must be in [0, 1]")
    if args.augs_per_image < 1:
        ap.error("--augs-per-image must be >= 1")

    run(
        src_images=args.src_images,
        src_labels=args.src_labels,
        out_root=args.out_root,
        blanks_dir=args.blanks_dir,
        fraction=args.fraction,
        seed=args.seed,
        augs_per_image=args.augs_per_image,
        use_augraphy=False if args.no_augraphy else None,
    )


if __name__ == "__main__":
    main()
