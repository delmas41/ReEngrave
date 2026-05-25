"""Per-class imgsz prescription + ensemble merge.

The Phase 3.3 model was trained at imgsz=2048, but production inference runs
at imgsz=1280 for speed (3x faster, similar wall-time on CPU). A controlled
sweep on Beethoven 5 + Ravel Bolero (see benchmarks/omr-conditional-upscale/)
showed that ~half the SMuFL classes peak at imgsz=2048 and ~half at imgsz=1280.
Running both passes and selecting per-class delivers the recall of the high-
resolution pass without losing the i1280 classes.

The prescription dict below was derived empirically — only classes with
≥3 detections and a clear count or confidence preference are listed; everything
else falls back to the default imgsz (the first one passed). When a class is
contradictory across pages (e.g. ledgerLine: Beethoven prefers 2048, Ravel
prefers 1280) we omit it from the prescription so the default wins.

Usage:
    passes = {
        1280: detector.detect(cell, imgsz=1280, ...),
        2048: detector.detect(cell, imgsz=2048, ...),
    }
    merged = merge_per_class(passes, default_imgsz=1280)
"""

from __future__ import annotations

from typing import TypeVar


# ─── Per-class imgsz prescription ───────────────────────────────────────────
#
# Format: class_name -> preferred imgsz value.
# Only classes that consistently benefit from a non-default imgsz are listed.
# Source: benchmarks/omr-conditional-upscale/RETROSPECTIVE.md (Step 2).
#
# When you add a new class, prefer i2048 only when:
#   - count at i2048 is >= 1.2x count at i1280 on multiple pages, AND
#   - mean confidence at i2048 is within 20% of i1280's.
# Otherwise the new false positives outweigh the recall gain.

IMGSZ_PRESCRIPTION: dict[str, int] = {
    # ── Small structural symbols: model needs high-resolution detail ────────
    "augmentationDot": 2048,        # Ravel +286% at i2048
    "tie": 2048,                    # Ravel +28%, Beethoven mild
    # ── Small rests (visually compact) ──────────────────────────────────────
    "rest16th": 2048,               # Ravel: 1 -> 32 at i2048 (catastrophic miss at i1280)
    "rest32nd": 2048,
    "restHBar": 2048,               # Beethoven +185%, Ravel +277%
    "restHalf": 2048,               # Beethoven +108%
    # ── Noteheads in dense chord stacks (Ravel +75-85%) ─────────────────────
    "noteheadBlackInSpace": 2048,
    "noteheadBlackOnLine": 2048,
    # ── Articulations -- mean conf rises at i2048 even when count is flat ──
    "articStaccatoAbove": 2048,
    "articStaccatoBelow": 2048,
    "articTenutoAbove": 2048,
    "articTenutoBelow": 2048,

    # ── Things that get WORSE at higher resolution -- keep at production res
    #    These have lift >=20% at i1280, indicating the model's i1280 anchors
    #    are tuned for these classes.
    "accidentalFlat": 1280,         # Ravel 13 -> 0 at i2048 (lost entirely!)
    "accidentalNatural": 1280,      # Ravel -25%, mean conf drops by 0.5
    "clefG": 1280,                  # Ravel -67% count at i2048
    "clefF": 1280,
    "clefCAlto": 1280,
    "clefCTenor": 1280,
    "timeSigCommon": 1280,          # Ravel -68% at i2048
    "timeSig0": 1280, "timeSig1": 1280, "timeSig2": 1280, "timeSig3": 1280,
    "timeSig4": 1280, "timeSig5": 1280, "timeSig6": 1280, "timeSig7": 1280,
    "timeSig8": 1280, "timeSig9": 1280,
    "flag8thUp": 1280,              # Ravel -83% at i2048
    "flag8thDown": 1280,            # Beethoven -64%
    "flag16thUp": 1280,
    "flag16thDown": 1280,
    "flag64thDown": 1280,
    "noteheadHalfOnLine": 1280,     # both pages prefer i1280
}


T = TypeVar("T")


def _class_name(det: T) -> str:
    """Pull the SMuFL class label off a SymbolDetection-shaped object."""
    return getattr(det, "smufl_name", "") or ""


def merge_per_class(passes: dict[int, list[T]], default_imgsz: int) -> list[T]:
    """Combine detection lists from multiple imgsz passes using IMGSZ_PRESCRIPTION.

    For each class:
      - if listed in the prescription, take only detections from the prescribed pass
      - otherwise take detections from the default pass

    Detections from non-default passes for unprescribed classes are dropped.

    Args:
        passes: imgsz -> list of detections from that pass.
        default_imgsz: which pass is the fallback. Must be a key in `passes`.

    Returns:
        Flat list of detections suitable for downstream processing.
    """
    if default_imgsz not in passes:
        raise ValueError(f"default_imgsz={default_imgsz} not in passes: {list(passes.keys())}")
    out: list[T] = []
    # 1) Default pass: keep classes that are either unprescribed or prescribed to default
    for det in passes[default_imgsz]:
        cls = _class_name(det)
        if IMGSZ_PRESCRIPTION.get(cls, default_imgsz) == default_imgsz:
            out.append(det)
    # 2) Non-default passes: only contribute their prescribed classes
    for imgsz, dets in passes.items():
        if imgsz == default_imgsz:
            continue
        for det in dets:
            cls = _class_name(det)
            if IMGSZ_PRESCRIPTION.get(cls) == imgsz:
                out.append(det)
    return out


def prescription_summary() -> dict[str, list[str]]:
    """Group classes by preferred imgsz -- useful for logging."""
    by_imgsz: dict[int, list[str]] = {}
    for cls, sz in IMGSZ_PRESCRIPTION.items():
        by_imgsz.setdefault(sz, []).append(cls)
    return {f"i{sz}": sorted(classes) for sz, classes in by_imgsz.items()}
