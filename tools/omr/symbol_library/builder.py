"""Build the symbol library from Bravura.otf.

Rasterizes a curated set of SMuFL glyphs at 3 sizes (72, 96, 120 px),
trims whitespace, computes Hu moments, and writes a manifest + per-entry
.npy templates to tools/omr/symbol_library/data/.

Usage:
    python3 -m tools.omr.symbol_library.builder
    python3 -m tools.omr.symbol_library.builder --sizes 96
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from freetype import Face

DATA_DIR = Path(__file__).parent / "data"
TEMPLATES_DIR = DATA_DIR / "templates"
BRAVURA_PATH = DATA_DIR / "Bravura.otf"
SMUFL_MAP_PATH = DATA_DIR / "glyphnames.json"
MANIFEST_PATH = DATA_DIR / "manifest.json"

# Curated MVP set. Stems are generated procedurally (Bravura has no clean stem
# glyph; SMuFL stems are positioning marks, not standalone shapes).
SMUFL_TARGETS: list[tuple[str, str]] = [
    # Noteheads
    ("noteheadBlack", "notehead"),
    ("noteheadHalf", "notehead"),
    ("noteheadWhole", "notehead"),
    ("noteheadDoubleWhole", "notehead"),
    # Flags
    ("flag8thUp", "flag"),
    ("flag8thDown", "flag"),
    ("flag16thUp", "flag"),
    ("flag16thDown", "flag"),
    # Rests
    ("restWhole", "rest"),
    ("restHalf", "rest"),
    ("restQuarter", "rest"),
    ("rest8th", "rest"),
    ("rest16th", "rest"),
    # Accidentals
    ("accidentalSharp", "accidental"),
    ("accidentalFlat", "accidental"),
    ("accidentalNatural", "accidental"),
    ("accidentalDoubleSharp", "accidental"),
    ("accidentalDoubleFlat", "accidental"),
    # Clefs
    ("gClef", "clef"),
    ("fClef", "clef"),
    ("cClef", "clef"),
    ("cClef8vb", "clef"),
    # Time signature digits
    ("timeSig0", "time_sig_digit"),
    ("timeSig1", "time_sig_digit"),
    ("timeSig2", "time_sig_digit"),
    ("timeSig3", "time_sig_digit"),
    ("timeSig4", "time_sig_digit"),
    ("timeSig5", "time_sig_digit"),
    ("timeSig6", "time_sig_digit"),
    ("timeSig7", "time_sig_digit"),
    ("timeSig8", "time_sig_digit"),
    ("timeSig9", "time_sig_digit"),
    # Barlines (also produced by Phase 1, but kept for shape-matching parity)
    ("barlineSingle", "barline"),
    ("barlineFinal", "barline"),
    ("barlineHeavy", "barline"),
]

SIZES_PX = (72, 96, 120)


def _parse_codepoint(s: str) -> int:
    # SMuFL JSON values are like "U+E0A4"
    return int(s.replace("U+", ""), 16)


def load_smufl_map() -> dict[str, int]:
    raw = json.loads(SMUFL_MAP_PATH.read_text())
    out = {}
    for name, info in raw.items():
        cp = info.get("codepoint")
        if cp:
            out[name] = _parse_codepoint(cp)
    return out


def rasterize_glyph(face: Face, codepoint: int, size_px: int) -> np.ndarray | None:
    """Render a single glyph to a uint8 array (255=paper, 0=ink). Returns
    None if the glyph has no bitmap (empty glyph)."""
    face.set_char_size(size_px * 64)
    face.load_char(chr(codepoint))
    bm = face.glyph.bitmap
    if bm.rows == 0 or bm.width == 0:
        return None
    buf = np.array(bm.buffer, dtype=np.uint8).reshape(bm.rows, bm.width)
    # FreeType bitmap: 0 = transparent (paper), 255 = ink-opaque
    # Phase 1 convention: 255 = paper, 0 = ink. Invert.
    out = 255 - buf
    return out


def trim_whitespace(img: np.ndarray, threshold: int = 200) -> np.ndarray:
    """Crop tightly around the ink. Returns the image cropped to the
    bounding box of ink pixels (where img < threshold)."""
    ink = img < threshold
    if not ink.any():
        return img
    ys, xs = np.where(ink)
    return img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def hu_moments(img: np.ndarray) -> np.ndarray:
    """Compute the 7 Hu moment invariants on a binary version of `img`.
    Returns float64 array of length 7, log-scaled for numeric stability."""
    # Binarize (Otsu); cv2.moments wants the actual pixel values
    _, binary = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)  # ink → 255
    m = cv2.moments(binary, binaryImage=True)
    hu = cv2.HuMoments(m).flatten()  # 7 values
    # Standard log-scale transform to make magnitudes comparable
    eps = 1e-30
    hu_log = -np.sign(hu) * np.log10(np.abs(hu) + eps)
    return hu_log


def make_stem_template(size_px: int) -> np.ndarray:
    """Procedurally generate a vertical-stem template. SMuFL doesn't ship a
    standalone stem glyph (stems are drawn as lines positioned relative to
    noteheads), so we make a simple thin vertical bar sized proportionally
    to the rastering size: width ≈ size/24, height ≈ size."""
    h = int(round(size_px * 1.1))
    w = max(2, int(round(size_px / 24)))
    img = np.full((h, w), 255, dtype=np.uint8)
    img[:, :] = 0  # entirely ink
    return img


def build_library(sizes: tuple[int, ...] = SIZES_PX) -> dict:
    if not BRAVURA_PATH.exists():
        raise FileNotFoundError(f"Bravura font not found at {BRAVURA_PATH}")
    if not SMUFL_MAP_PATH.exists():
        raise FileNotFoundError(f"SMuFL glyphnames.json not found at {SMUFL_MAP_PATH}")

    smufl = load_smufl_map()
    face = Face(str(BRAVURA_PATH))

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    # Clean previous templates
    for f in TEMPLATES_DIR.glob("*.npy"):
        f.unlink()

    entries: list[dict] = []
    skipped: list[str] = []

    for smufl_name, category in SMUFL_TARGETS:
        cp = smufl.get(smufl_name)
        if cp is None:
            skipped.append(smufl_name)
            continue
        for size_px in sizes:
            raster = rasterize_glyph(face, cp, size_px)
            if raster is None:
                skipped.append(f"{smufl_name}@{size_px}")
                continue
            img = trim_whitespace(raster)
            if img.shape[0] < 3 or img.shape[1] < 3:
                skipped.append(f"{smufl_name}@{size_px} (too small)")
                continue
            hu = hu_moments(img)
            rel_path = f"templates/{smufl_name}_{size_px}.npy"
            np.save(TEMPLATES_DIR / f"{smufl_name}_{size_px}.npy", img)
            entries.append({
                "smufl_name": smufl_name,
                "category": category,
                "size_px": size_px,
                "image_path": rel_path,
                "shape": list(img.shape),  # [h, w]
                "hu_moments": hu.tolist(),
                "variant_id": None,
            })

    # Procedural stems — one per size, three "stems" (skinny / medium / wide)
    for size_px in sizes:
        img = make_stem_template(size_px)
        hu = hu_moments(img)
        rel_path = f"templates/stem_{size_px}.npy"
        np.save(TEMPLATES_DIR / f"stem_{size_px}.npy", img)
        entries.append({
            "smufl_name": "stem",
            "category": "stem",
            "size_px": size_px,
            "image_path": rel_path,
            "shape": list(img.shape),
            "hu_moments": hu.tolist(),
            "variant_id": "procedural_thin",
        })

    manifest = {
        "version": 1,
        "font": "Bravura.otf",
        "sizes_px": list(sizes),
        "n_entries": len(entries),
        "skipped": skipped,
        "entries": entries,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    return manifest


def main():
    ap = argparse.ArgumentParser(description="Build the SMuFL symbol library")
    ap.add_argument(
        "--sizes",
        default=",".join(str(s) for s in SIZES_PX),
        help="Comma-separated pixel sizes (default: 72,96,120)",
    )
    args = ap.parse_args()
    sizes = tuple(int(s.strip()) for s in args.sizes.split(",") if s.strip())
    manifest = build_library(sizes)
    print(f"built {manifest['n_entries']} entries at sizes {manifest['sizes_px']}")
    if manifest["skipped"]:
        print(f"skipped: {manifest['skipped']}")
    print(f"manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
