#!/usr/bin/env python3
"""Phase H — assemble train/val splits and write data.yaml for the
catalog-augmented YOLO fine-tune.

Inputs:
  phase-h-data/
    images/<key>/p###.png   (from phase_h_render_pages.py)
    labels/<key>/p###.txt   (from phase_h_render_pages.py)

Outputs:
  phase-h-data/
    train.txt        ← absolute image paths, catalog only (no DSv2)
    train.repeated.txt ← train.txt with each line repeated N times
                          (catalog-only fine-tune mode uses train.txt;
                           mix-with-DSv2 mode uses train.repeated.txt)
    val.txt          ← absolute image paths, holdout-per-edition
    data-catalog-only.yaml   ← fine-tune ONLY on catalog
    data-catalog-mix.yaml    ← mix with DSv2 (assumes DSv2 splits exist
                                at <DSV2_BASE>/train.txt and val.txt)
    splits.json      ← machine-readable record of the train/val pick

Holdout strategy: one movement per edition (7 movements total), biased
toward 100%-XML-match movements so val labels are clean.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

DEFAULT_OUT = Path(__file__).resolve().parent / "phase-h-data"

# One holdout movement per edition. Biased toward 100% XML-match rate
# so the val labels are clean (= mAP signal isn't dominated by missing
# labels). Chosen from benchmarks/omr-imslp-pipeline/phase-g-output/
# batch_summary.json.
#
# Picked sizes target ~15-25% val ratio — small enough to leave most data
# in train, large enough for stable mAP per class.
HOLDOUT_KEYS: list[str] = [
    "beethoven-symphony-1-imslp-52848-mvt4",   # 14p, 100% match, 7070 labels
    "beethoven-symphony-2-imslp-503997-mvt2",  # 13p, 100%, 5298
    "beethoven-symphony-2-imslp-977672-mvt3",  # 7p, 100%, 1810
    "beethoven-symphony-4-imslp-411721-mvt2",  # 12p, 100%, 3196
    "beethoven-symphony-6-imslp-57857-mvt2",   # 19p, 100%, 5791
    "beethoven-symphony-8-imslp-06303-mvt4",   # 29p, 100%, 10562
    "beethoven-symphony-8-imslp-875077-mvt4",  # 30p, 99.4%, 16587
]


def list_pages(images_root: Path) -> dict[str, list[Path]]:
    """Walk images/<key>/p###.png and return {key: [abs_image_path, ...]}."""
    out: dict[str, list[Path]] = {}
    for key_dir in sorted(images_root.iterdir()):
        if not key_dir.is_dir():
            continue
        pngs = sorted(key_dir.glob("p*.png"))
        if pngs:
            out[key_dir.name] = pngs
    return out


def write_paths(paths: list[Path], txt: Path) -> None:
    txt.write_text("\n".join(str(p) for p in paths) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help="Root of phase-h-data/ (images/, labels/ live here; "
                         "the txt/yaml files will be written here too)")
    ap.add_argument("--target-base", default="{DATA_BASE}/phase-h-data",
                    help="On the remote box, where this directory lives. "
                         "Used to rewrite absolute paths in train/val.txt "
                         "to the target location. The default keeps "
                         "{DATA_BASE} as a sed-able placeholder.")
    ap.add_argument("--repeat", type=int, default=200,
                    help="Per-line repetition factor in train.repeated.txt "
                         "(catalog upsampling for DSv2 mix). 200× × ~400 "
                         "train images = ~80k effective samples per epoch.")
    ap.add_argument("--dsv2-base", default="{DATA_BASE}/deepscoresv2-yolo",
                    help="Where the DSv2 YOLO split lives on the remote "
                         "box (its train.txt / val.txt). The catalog-mix "
                         "yaml will reference DSv2_BASE/train.txt and "
                         "val.txt.")
    args = ap.parse_args()

    out_root = Path(args.out).resolve()
    images_root = out_root / "images"
    labels_root = out_root / "labels"
    if not images_root.exists() or not labels_root.exists():
        print(f"missing {images_root} or {labels_root} — run "
              f"phase_h_render_pages.py first")
        return 2

    pages_by_key = list_pages(images_root)
    all_keys = sorted(pages_by_key.keys())
    print(f"Found {len(all_keys)} (work, edition, mvt) tuples, "
          f"{sum(len(v) for v in pages_by_key.values())} images")

    missing_holdouts = [k for k in HOLDOUT_KEYS if k not in pages_by_key]
    if missing_holdouts:
        print(f"ERROR: holdout keys not present in images/: {missing_holdouts}")
        return 2

    val_keys = sorted(HOLDOUT_KEYS)
    train_keys = sorted(set(all_keys) - set(val_keys))

    # Build absolute paths under TARGET_BASE for portability.
    def remap(p: Path) -> str:
        # Strip the local out_root prefix and prepend target_base.
        rel = p.relative_to(out_root)
        return f"{args.target_base}/{rel.as_posix()}"

    train_paths = [
        Path(remap(p))
        for k in train_keys
        for p in pages_by_key[k]
    ]
    val_paths = [
        Path(remap(p))
        for k in val_keys
        for p in pages_by_key[k]
    ]
    print(f"  train: {len(train_paths)} images across {len(train_keys)} mvts")
    print(f"  val:   {len(val_paths)} images across {len(val_keys)} mvts")

    write_paths(train_paths, out_root / "train.txt")
    write_paths(val_paths, out_root / "val.txt")

    # train.repeated.txt — replicate each train path N times so when
    # combined with DSv2's train.txt, the catalog gets enough exposure.
    rep_path = out_root / "train.repeated.txt"
    with rep_path.open("w") as f:
        for p in train_paths:
            for _ in range(args.repeat):
                f.write(f"{p}\n")
    print(f"  train.repeated.txt: {len(train_paths)} × {args.repeat} = "
          f"{len(train_paths) * args.repeat} lines")

    # Class names: prod-208 class list (read directly from the warm-start
    # weights so the yaml matches the model head exactly). The earlier
    # 146-class DSv2 list was the source of a Phase K-blocker bug:
    # catalog labels at class 207 were filtered as "out of range" during
    # val cache building, leaving the val set empty and crashing training
    # with `No valid images found in cache`. See PHASE_K_RESULTS.md.
    try:
        from ultralytics import YOLO
        weights_path = Path("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
                            "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt")
        prod_names = YOLO(str(weights_path)).names
        names_list = [prod_names[i] for i in range(len(prod_names))]
        nc = len(names_list)
    except Exception as exc:  # noqa: BLE001
        print(f"  WARN: could not read prod model names ({exc!r}); "
              f"falling back to 146-class DSv2 list")
        from tools.omr.training.deepscores_classes import DEEPSCORES_V2_CLASSES
        names_list = list(DEEPSCORES_V2_CLASSES)
        nc = len(names_list)

    # data-catalog-only.yaml — fine-tune on catalog ONLY
    # (Phase 3.4 v1b-style; smallest, fastest, preserves DSv2 by warm start)
    catalog_only = {
        "path": args.target_base,
        "train": "train.txt",
        "val": "val.txt",
        "nc": nc,
        "names": names_list,
    }

    # data-catalog-mix.yaml — DSv2 + upsampled catalog (handoff plan)
    #
    # Strategy: write a single combined train.txt at runtime by concat'ing
    # DSv2's train.txt with catalog/train.repeated.txt. Ultralytics
    # actually supports `train` as a list of paths, but mixing splits
    # cleanly is more reliable when we hand it a single combined list.
    # The mix yaml below uses `train: train.mix.txt`; the bootstrap
    # script on the remote box generates that file as:
    #   cat DSV2_BASE/train.txt PHASE_H/train.repeated.txt > train.mix.txt
    mix_yaml = {
        "path": args.target_base,
        "train": "train.mix.txt",   # built at runtime; see bootstrap
        # ultralytics 8.x val expects a single path. Use orchestral
        # holdout so per-epoch val reports orchestral mAP. Run DSv2 val
        # post-training with `model.val(data=DSv2_yaml)` for the
        # regression check.
        "val": "val.txt",
        "nc": nc,
        "names": names_list,
    }

    # Manual YAML emit (no PyYAML dependency required on the remote box's
    # bootstrap-only environment — though ultralytics ships it).
    def to_yaml(d: dict) -> str:
        lines = []
        for k, v in d.items():
            if isinstance(v, list) and k != "names":
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {item}")
            elif isinstance(v, list):
                # names = 146-class list — write inline-block
                lines.append(f"{k}:")
                for name in v:
                    lines.append(f"  - {name}")
            else:
                lines.append(f"{k}: {v}")
        return "\n".join(lines) + "\n"

    (out_root / "data-catalog-only.yaml").write_text(to_yaml(catalog_only))
    (out_root / "data-catalog-mix.yaml").write_text(to_yaml(mix_yaml))
    print(f"wrote data-catalog-only.yaml and data-catalog-mix.yaml")

    # splits.json — for the audit trail
    (out_root / "splits.json").write_text(json.dumps({
        "train_keys": train_keys,
        "val_keys": val_keys,
        "train_image_count": len(train_paths),
        "val_image_count": len(val_paths),
        "repeat_factor": args.repeat,
        "target_base": args.target_base,
        "dsv2_base": args.dsv2_base,
        "nc": nc,
    }, indent=2))
    print(f"wrote splits.json")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
