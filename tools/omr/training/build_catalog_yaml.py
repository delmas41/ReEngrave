"""Build the unified `data/user-labeled/catalog.yaml` from all versioned
labeling sessions.

The catalog is a single ultralytics-compatible YOLO data config that
unions all `vN-DATE-NAME/` subdirectories. Each version contributes its
own train/val split (held out *within* that version) so that retraining
sees a stable val set per version while still benefiting from new data.

Why per-version val splits, not a global one?
  - Holding out a chunk of every session means the val set keeps growing
    in lockstep with train. A global random split would have to re-shuffle
    on every rebuild, which makes run-to-run val numbers non-comparable.
  - Per-version split is also deterministic: same `--val-fraction` and
    same `--seed` → identical split, every time.

Output:
  data/user-labeled/catalog.yaml      ← consumed by `train_yolo.py --data`
  data/user-labeled/_catalog_train.txt ← list of train image paths
  data/user-labeled/_catalog_val.txt   ← list of val image paths

The `.txt` files are ultralytics' "list-of-paths" input format, which we
use because (a) we don't want to copy/move images across the train/val
boundary, and (b) the version directories are immutable.

CLI:
    python3 -m tools.omr.training.build_catalog_yaml \\
        --root data/user-labeled/ \\
        --val-fraction 0.15
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .deepscores_classes import DEEPSCORES_V2_CLASSES


# ---------------------------------------------------------------------------
# Catalog scanning
# ---------------------------------------------------------------------------


@dataclass
class VersionSlice:
    name: str                       # e.g. "v1-2026-05-17-orchestral"
    dir: Path                       # absolute path
    train_images: list[Path] = field(default_factory=list)
    val_images: list[Path] = field(default_factory=list)
    metadata: dict | None = None


def _stable_hash_fraction(key: str) -> float:
    """Map a string deterministically to [0..1)."""
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    # Take 8 bytes → uint64 → /2^64
    return int.from_bytes(digest[:8], "big") / 2 ** 64


def _scan_version_dir(d: Path, val_fraction: float, seed: str) -> VersionSlice:
    images_dir = d / "images"
    labels_dir = d / "labels"
    if not images_dir.is_dir() or not labels_dir.is_dir():
        return VersionSlice(name=d.name, dir=d.resolve())
    slice_ = VersionSlice(name=d.name, dir=d.resolve())
    meta_p = d / "metadata.json"
    if meta_p.exists():
        try:
            slice_.metadata = json.loads(meta_p.read_text())
        except json.JSONDecodeError:
            slice_.metadata = None

    paired: list[Path] = []
    for img in sorted(images_dir.iterdir()):
        if img.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            continue
        lbl = labels_dir / f"{img.stem}.txt"
        if not lbl.exists():
            continue  # skip images with no label file
        paired.append(img.resolve())

    for img in paired:
        # Deterministic per-image split: hash of "<version>:<stem>" with
        # the seed mixed in. Same val_fraction + same seed → same split.
        h = _stable_hash_fraction(f"{seed}:{d.name}:{img.stem}")
        if h < val_fraction:
            slice_.val_images.append(img)
        else:
            slice_.train_images.append(img)
    return slice_


def discover_versions(root: Path) -> list[Path]:
    """Find all `vN-*/` subdirectories at the top level of `root`."""
    if not root.exists():
        return []
    out: list[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        # Allow lowercase or uppercase v, digits, then a dash, then anything
        if not name.lower().startswith("v"):
            continue
        # Must look like "vN-..." — i.e. a digit right after "v"
        if len(name) < 2 or not name[1].isdigit():
            continue
        out.append(child)
    return out


# ---------------------------------------------------------------------------
# Class names resolution
# ---------------------------------------------------------------------------


def load_class_names(
    weights_path: Path | None,
    fallback_json: Path | None,
) -> list[str]:
    """See verdicts_to_yolo_labels.load_class_names — same contract."""
    if weights_path is not None and weights_path.exists():
        try:
            import torch
        except ImportError:
            torch = None
        if torch is not None:
            ckpt = torch.load(str(weights_path), map_location="cpu",
                              weights_only=False)
            model = ckpt.get("model") if isinstance(ckpt, dict) else ckpt
            names = getattr(model, "names", None)
            if isinstance(names, dict):
                return [names[i] for i in sorted(int(k) for k in names.keys())]
            if isinstance(names, list):
                return list(names)
    if fallback_json is not None and fallback_json.exists():
        return json.loads(fallback_json.read_text())
    return list(DEEPSCORES_V2_CLASSES)


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=Path("data/user-labeled"), type=Path,
                    help="Catalog root containing vN-*/ version dirs.")
    ap.add_argument("--val-fraction", type=float, default=0.15,
                    help="Per-version fraction held out for val "
                         "(default 0.15).")
    ap.add_argument("--seed", default="reengrave",
                    help="Seed string mixed into the val-split hash. "
                         "Change to reshuffle.")
    ap.add_argument("--weights", type=Path,
                    default=Path("tools/omr/training/data/weights/"
                                 "deepscoresv2-yolov8l-8shards-100ep.pt"),
                    help="Trained .pt file to read class names from.")
    ap.add_argument("--fallback-class-names",
                    default=Path("tools/omr/training/data/"
                                 "deepscoresv2_208_classes.json"),
                    type=Path)
    ap.add_argument("--output-yaml", default=None, type=Path,
                    help="Override output path. Defaults to "
                         "<root>/catalog.yaml.")
    args = ap.parse_args()

    root: Path = args.root.resolve()
    val_fraction = float(args.val_fraction)
    if not (0.0 <= val_fraction <= 0.5):
        raise SystemExit(
            "val-fraction must be in [0.0, 0.5]; "
            f"got {val_fraction!r}"
        )

    version_dirs = discover_versions(root)
    if not version_dirs:
        print(f"no version directories under {root} — "
              f"nothing to catalog yet.")
        # Still emit a catalog stub so the path exists. Downstream training
        # will fail-fast with an empty list.
        print("(writing empty catalog stub anyway)")

    slices = [
        _scan_version_dir(d, val_fraction, args.seed)
        for d in version_dirs
    ]

    train_paths: list[Path] = []
    val_paths: list[Path] = []
    for s in slices:
        train_paths.extend(s.train_images)
        val_paths.extend(s.val_images)

    class_names = load_class_names(args.weights, args.fallback_class_names)

    # Write list-of-paths files
    train_txt = root / "_catalog_train.txt"
    val_txt = root / "_catalog_val.txt"
    root.mkdir(parents=True, exist_ok=True)
    train_txt.write_text("\n".join(str(p) for p in train_paths) +
                         ("\n" if train_paths else ""))
    val_txt.write_text("\n".join(str(p) for p in val_paths) +
                       ("\n" if val_paths else ""))

    # Write data.yaml
    output_yaml = args.output_yaml or (root / "catalog.yaml")
    payload = {
        "path": str(root),
        "train": str(train_txt),
        "val": str(val_txt),
        "nc": len(class_names),
        "names": class_names,
    }
    output_yaml.parent.mkdir(parents=True, exist_ok=True)
    output_yaml.write_text(yaml.safe_dump(payload, sort_keys=False))

    # Write a sidecar summary for humans
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "root": str(root),
        "val_fraction": val_fraction,
        "seed": args.seed,
        "n_versions": len(slices),
        "n_train_images": len(train_paths),
        "n_val_images": len(val_paths),
        "n_classes": len(class_names),
        "weights_source": str(args.weights),
        "versions": [
            {
                "name": s.name,
                "dir": str(s.dir),
                "n_train_images": len(s.train_images),
                "n_val_images": len(s.val_images),
                "metadata_present": s.metadata is not None,
                "labeler": (s.metadata or {}).get("labeler"),
                "description": (s.metadata or {}).get("description"),
                "created_utc": (s.metadata or {}).get("created_utc"),
            }
            for s in slices
        ],
    }
    (root / "_catalog_summary.json").write_text(json.dumps(summary, indent=2))

    # Pretty stdout
    print(f"catalog root:    {root}")
    print(f"versions found:  {len(slices)}")
    for s in slices:
        labeler = (s.metadata or {}).get("labeler") or "?"
        print(f"  {s.name}  train={len(s.train_images):>4}  "
              f"val={len(s.val_images):>3}  labeler={labeler}")
    print(f"\ntotals:")
    print(f"  train images: {len(train_paths)}")
    print(f"  val images:   {len(val_paths)}")
    print(f"  classes:      {len(class_names)}")
    print(f"\nwrote:")
    print(f"  {output_yaml}")
    print(f"  {train_txt}")
    print(f"  {val_txt}")
    print(f"  {root / '_catalog_summary.json'}")
    print(f"\nPoint training at: --data {output_yaml}")


if __name__ == "__main__":
    main()
