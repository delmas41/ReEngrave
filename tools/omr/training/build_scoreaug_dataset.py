"""Wire ScoreAug/Augraphy domain augmentation into a trainable YOLO dataset.

`augment_scoreaug.py` degrades a flat images/+labels/ dir but emits no
`data.yaml`, so its output isn't directly trainable. This script is the glue:
it takes a prepared YOLO dataset (as produced by `prepare_yolo_data.py`) and
produces a drop-in augmented dataset whose **train** split is domain-degraded
(clean originals kept + degraded twins, labels byte-identical) while the
**val** split stays **clean** — so val measures generalization and the WTC /
orchestral evals stay honest.

Input (from prepare_yolo_data.py):
    <prepared>/
        images/train  images/val
        labels/train  labels/val
        data.yaml         (path, train, val, nc, names)

Output:
    <out>/
        train/images  train/labels  train/scoreaug_manifest.json
        data.yaml         (train -> train/images, val -> the ORIGINAL clean
                           val, same nc + names)

Only the train split is touched; nc/names are copied verbatim (keep nc=208 —
this does NOT add classes). Because augment_scoreaug's degradations are
photometric-only, every label file is byte-identical to its source.

Usage (on the GPU box, right after prepare_yolo_data.py):
    python3 -m tools.omr.training.build_scoreaug_dataset \
        --prepared data/deepscoresv2-yolo \
        --out      data/deepscoresv2-yolo-scoreaug \
        --blanks-dir tools/omr/training/data/blanks \
        --fraction 0.5 --augs-per-image 1 --seed 41 --require-augraphy

Then train on <out>/data.yaml.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from tools.omr.training import augment_scoreaug as A


def _resolve(base: Path, rel: str) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else (base / p)


def build(
    *,
    prepared: Path,
    out: Path,
    blanks_dir: Path,
    fraction: float,
    augs_per_image: int,
    seed: int,
    require_augraphy: bool,
) -> Path:
    prepared = prepared.resolve()
    cfg_path = prepared / "data.yaml"
    if not cfg_path.exists():
        raise SystemExit(f"no data.yaml in --prepared: {cfg_path}")
    cfg = yaml.safe_load(cfg_path.read_text())
    for key in ("train", "val", "nc", "names"):
        if key not in cfg:
            raise SystemExit(f"{cfg_path} missing '{key}'")

    base = Path(cfg["path"]).resolve() if cfg.get("path") else prepared
    train_images = _resolve(base, cfg["train"])
    val_images = _resolve(base, cfg["val"])
    if not train_images.is_dir():
        raise SystemExit(
            f"train images dir not found: {train_images} "
            "(expected the dir form 'images/train', not a list file)"
        )
    # ultralytics convention: labels mirror images with /images/ -> /labels/.
    train_labels = train_images.parent.parent / "labels" / train_images.name
    if not train_labels.is_dir():
        raise SystemExit(f"train labels dir not found: {train_labels}")
    if not val_images.is_dir():
        raise SystemExit(f"val images dir not found: {val_images}")

    have_augraphy = A._get_augraphy() is not None
    if require_augraphy and not have_augraphy:
        raise SystemExit(
            "augraphy not importable but --require-augraphy was set. "
            "Install it (pip install augraphy) or drop the flag to run "
            "blank-composite + show-through only."
        )
    if not have_augraphy:
        print("WARNING: augraphy not importable — degrading with blank "
              "composite + show-through only (no photocopier/bleed effects).")

    n_train_src = len([p for p in train_images.iterdir()
                       if p.suffix.lower() in A.IMAGE_EXTS])
    print(f"prepared dataset : {prepared}")
    print(f"  train images   : {train_images}  ({n_train_src} imgs)")
    print(f"  train labels   : {train_labels}")
    print(f"  val (kept clean): {val_images}")
    print(f"  nc / names      : {cfg['nc']} / {len(cfg['names'])} names")
    print(f"augraphy         : {'ON (' + A._get_augraphy().__version__ + ')' if have_augraphy else 'OFF'}")
    print(f"effects          : {list(A.AUGRAPHY_SAFE_EFFECTS)}")
    print()

    out = out.resolve()
    train_out = out / "train"
    manifest = A.run(
        src_images=train_images,
        src_labels=train_labels,
        out_root=train_out,
        blanks_dir=blanks_dir,
        fraction=fraction,
        seed=seed,
        augs_per_image=augs_per_image,
        use_augraphy=True if (require_augraphy and have_augraphy) else None,
    )

    new_cfg = {
        "path": str(out),
        "train": "train/images",
        "val": str(val_images),   # absolute -> clean val, untouched
        "nc": cfg["nc"],
        "names": cfg["names"],
    }
    out_yaml = out / "data.yaml"
    out_yaml.write_text(yaml.safe_dump(new_cfg, sort_keys=False, allow_unicode=True))

    n_written = manifest["n_degraded_written"]
    print(f"\nwrote {out_yaml}")
    print(f"  train: {n_train_src} originals + {n_written} degraded twins "
          f"= {n_train_src + n_written} images")
    print(f"  val:   clean (unchanged) -> {val_images}")
    print(f"  synthetic-blank fallback used: {manifest['synthetic_blank_fallback_used']}")
    print(f"\nTrain with:\n  --data {out_yaml}")
    return out_yaml


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--prepared", type=Path, required=True,
                    help="Prepared YOLO dataset dir (has images/train, "
                         "labels/train, data.yaml).")
    ap.add_argument("--out", type=Path, required=True,
                    help="Output dir for the augmented dataset + data.yaml.")
    ap.add_argument("--blanks-dir", type=Path, default=A.DEFAULT_BLANKS_DIR,
                    help=f"TISMIR blank pages dir. Default: {A.DEFAULT_BLANKS_DIR}")
    ap.add_argument("--fraction", type=float, default=0.5,
                    help="Fraction of train images that get a degraded twin. "
                         "Default 0.5")
    ap.add_argument("--augs-per-image", type=int, default=1,
                    help="Degraded variants per selected train image. Default 1")
    ap.add_argument("--seed", type=int, default=41, help="RNG seed. Default 41")
    ap.add_argument("--require-augraphy", action="store_true",
                    help="Hard-fail if augraphy isn't importable (so a real "
                         "run never silently ships without the photometric "
                         "effects).")
    args = ap.parse_args(argv)
    if not 0.0 <= args.fraction <= 1.0:
        ap.error("--fraction must be in [0, 1]")
    if args.augs_per_image < 1:
        ap.error("--augs-per-image must be >= 1")
    build(
        prepared=args.prepared,
        out=args.out,
        blanks_dir=args.blanks_dir,
        fraction=args.fraction,
        augs_per_image=args.augs_per_image,
        seed=args.seed,
        require_augraphy=args.require_augraphy,
    )


if __name__ == "__main__":
    main()
