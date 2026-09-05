"""Build the DSv2-rehearsal mixed dataset. Runs ON THE RENTED BOX.

Round 5 established that fine-tuning on the ~750-cell scan-label corpus
deletes whole classes (tie/slur/beam/augmentationDot/accidentalFlat/restWhole/
ledgerLine -> exactly 0) regardless of training method, and named DSv2
rehearsal as the one untried training-side fix (ROUND5_METHOD_2026-09-04.md
section 4). This builds the mix that prices it:

  1. Build the scan-label catalog (the 14 admitted versions, nc=208 capped)
     via the repo's own build_catalog_yaml — the round-5 mix, ~5211 boxes.
  2. Verify the prepared DSv2 data.yaml `names` equals
     deepscoresv2_208_classes.json AT EVERY INDEX. That JSON was verified on
     the Mac to equal both donor checkpoints' own model.names index-by-index,
     so this check chains the DSv2 labels to the model's real class space.
     ABORT on any mismatch — the 208 space has 40 DUPLICATED NAMES
     (augmentationDot at 40+159, clefG at 5+141, slur twice), so a by-NAME
     remap is exactly the recorded build_rehearsal_versions.py defect and is
     never attempted here.
  3. Sample DSv2 train pages: target = RATIO x scan-train image count.
     Coverage-first: walk classes rarest-first and keep >= MIN_COVER images
     containing each class (all of them when fewer exist), then fill the
     remaining budget uniformly. Deterministic (seed 20260904).
  4. mix/mix_train.txt = scan train lines + DSv2 sample. ⚠️ The DSv2 lines
     must stay UNRESOLVED symlink paths (str(p), never p.resolve()): the
     images under deepscoresv2-yolo/images/ are symlinks into
     ds2_dense/images/, and a resolved line makes ultralytics derive the
     label path under ds2_dense/labels/ — which does not exist — so every
     DSv2 page silently trains as BACKGROUND. Cost this session one wasted
     training pass; the val cache read (found 96, missing 150).
     mix/mix_val.txt   = scan val lines + VAL_DSV2 DSv2 val pages (monitor
     only — checkpoint choice happens on the Mac gate, not on val fitness).
  5. mix/data.yaml with nc=208 and the verified names.
  6. mix/mix_report.json — actual counts, the true ratio, per-class instance
     counts of the DSv2 sample (for FINDINGS.md).
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CLASSES_JSON = ROOT / "tools/omr/training/deepscoresv2_208_classes.json"
SCAN_ROOT = ROOT / "data/user-labeled"
DSV2_YOLO = ROOT / "data/deepscoresv2-yolo"
MIX = ROOT / "mix"

SEED = 20260904
MIN_COVER = 10       # min images kept per DSv2 class (when that many exist)
VAL_DSV2 = 150       # DSv2 val pages added to the val monitor


def build_scan_catalog() -> tuple[list[str], list[str]]:
    """Run the repo's catalog builder over the admitted membership."""
    cmd = [sys.executable, "-m", "tools.omr.training.build_catalog_yaml",
           "--root", str(SCAN_ROOT),
           "--fallback-class-names", str(CLASSES_JSON)]
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)
    cat = yaml.safe_load((SCAN_ROOT / "catalog.yaml").read_text())
    if int(cat["nc"]) != 208:
        sys.exit(f"ABORT: scan catalog nc={cat['nc']}, expected 208")
    train = [ln for ln in Path(cat["train"]).read_text().splitlines() if ln.strip()]
    val = [ln for ln in Path(cat["val"]).read_text().splitlines() if ln.strip()]
    print(f"scan catalog: {len(train)} train / {len(val)} val cells")
    return train, val


def verify_dsv2_names() -> list[str]:
    names_208 = json.loads(CLASSES_JSON.read_text())
    data = yaml.safe_load((DSV2_YOLO / "data.yaml").read_text())
    ds_names = data["names"]
    if isinstance(ds_names, dict):
        ds_names = [ds_names[i] for i in range(len(ds_names))]
    if len(ds_names) != len(names_208):
        sys.exit(f"ABORT: DSv2 data.yaml has nc={len(ds_names)}, the checkpoints "
                 f"have nc={len(names_208)}. Do NOT remap by name (40 duplicate "
                 "names); this needs a human decision.")
    bad = [i for i, (a, b) in enumerate(zip(ds_names, names_208)) if a != b]
    if bad:
        sys.exit(f"ABORT: DSv2 class list differs from the checkpoints' at "
                 f"indices {bad[:10]}{'...' if len(bad) > 10 else ''} "
                 f"(e.g. {bad[0]}: {ds_names[bad[0]]!r} vs {names_208[bad[0]]!r}). "
                 "Do NOT remap by name.")
    print(f"DSv2 class space verified: {len(ds_names)} names, every index matches "
          "the checkpoints' own model.names")
    return names_208


def dsv2_split(split: str) -> tuple[list[Path], dict[Path, collections.Counter]]:
    imgs_dir = DSV2_YOLO / "images" / split
    labels_dir = DSV2_YOLO / "labels" / split
    images, by_img = [], {}
    for img in sorted(imgs_dir.iterdir()):
        if img.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            continue
        lbl = labels_dir / f"{img.stem}.txt"
        if not lbl.exists():
            continue
        counts = collections.Counter()
        for ln in lbl.read_text().splitlines():
            tok = ln.split()
            if tok:
                counts[int(tok[0])] += 1
        images.append(img)
        by_img[img] = counts
    return images, by_img


def sample_coverage_first(
    images: list[Path], by_img: dict[Path, collections.Counter],
    target: int, rng: random.Random,
) -> list[Path]:
    if len(images) <= target:
        print(f"DSv2 train has only {len(images)} pages <= target {target}: taking ALL")
        return list(images)
    class_to_imgs: dict[int, list[Path]] = collections.defaultdict(list)
    for img in images:
        for c in by_img[img]:
            class_to_imgs[c].append(img)
    chosen: set[Path] = set()
    # rarest classes first so coverage picks double-count as little as possible
    for c in sorted(class_to_imgs, key=lambda c: len(class_to_imgs[c])):
        have = sum(1 for i in class_to_imgs[c] if i in chosen)
        need = min(MIN_COVER, len(class_to_imgs[c])) - have
        if need <= 0:
            continue
        pool = [i for i in class_to_imgs[c] if i not in chosen]
        rng.shuffle(pool)
        chosen.update(pool[:need])
    rest = [i for i in images if i not in chosen]
    rng.shuffle(rest)
    fill = max(0, target - len(chosen))
    chosen.update(rest[:fill])
    return sorted(chosen)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ratio", type=float, default=3.0,
                    help="DSv2:scan image-count ratio (default 3)")
    args = ap.parse_args()

    scan_train, scan_val = build_scan_catalog()
    names = verify_dsv2_names()

    rng = random.Random(SEED)
    tr_imgs, tr_by_img = dsv2_split("train")
    va_imgs, _ = dsv2_split("val")
    print(f"DSv2 prepared: {len(tr_imgs)} train / {len(va_imgs)} val pages")

    target = int(round(args.ratio * len(scan_train)))
    ds_sample = sample_coverage_first(tr_imgs, tr_by_img, target, rng)

    va_pool = list(va_imgs)
    rng.shuffle(va_pool)
    ds_val = sorted(va_pool[:VAL_DSV2])

    MIX.mkdir(exist_ok=True)
    train_lines = scan_train + [str(p) for p in ds_sample]
    val_lines = scan_val + [str(p) for p in ds_val]
    (MIX / "mix_train.txt").write_text("\n".join(train_lines) + "\n")
    (MIX / "mix_val.txt").write_text("\n".join(val_lines) + "\n")
    (MIX / "data.yaml").write_text(yaml.safe_dump({
        "path": str(MIX.resolve()),
        "train": str((MIX / "mix_train.txt").resolve()),
        "val": str((MIX / "mix_val.txt").resolve()),
        "nc": len(names),
        "names": names,
    }, sort_keys=False))

    # ---- report ----
    inst = collections.Counter()
    for img in ds_sample:
        inst.update(tr_by_img[img])
    classes_present = sorted(inst)
    all_classes_in_dsv2 = set()
    for c in tr_by_img.values():
        all_classes_in_dsv2.update(c)
    report = {
        "seed": SEED,
        "requested_ratio": args.ratio,
        "scan_train": len(scan_train), "scan_val": len(scan_val),
        "dsv2_train_total": len(tr_imgs), "dsv2_val_total": len(va_imgs),
        "dsv2_sampled": len(ds_sample), "dsv2_val_sampled": len(ds_val),
        "actual_ratio": round(len(ds_sample) / max(1, len(scan_train)), 3),
        "mix_train_images": len(train_lines), "mix_val_images": len(val_lines),
        "min_cover": MIN_COVER,
        "dsv2_classes_with_instances": len(all_classes_in_dsv2),
        "sample_classes_with_instances": len(classes_present),
        "sample_instances_by_class": {
            names[c]: inst[c] for c in classes_present},
        "sample_class_ids": classes_present,
    }
    (MIX / "mix_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items()
                      if k != "sample_instances_by_class"}, indent=1))
    missing = sorted(all_classes_in_dsv2 - set(classes_present))
    if missing:
        print(f"WARNING: {len(missing)} DSv2 classes lost by sampling: "
              f"{[names[c] for c in missing][:12]}")
    else:
        print("coverage: every DSv2 class with instances survives the sample")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
