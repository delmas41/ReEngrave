"""Merge a subset of DeepScoresV2 ds2_complete shards into a single
train.json / test.json pair that prepare_yolo_data.py can consume.

DeepScoresV2's ds2_complete tarball ships annotations split across
~103 train shards + ~26 test shards (`deepscores-complete-N_train.json`,
`deepscores-complete-N_test.json`), each ~230 MB and ~2,000 images. The
existing prepare_yolo_data.py expects a single
deepscores_train.json / deepscores_test.json pair (the layout used by
the smaller ds2_dense tarball).

This script reads selected shards, remaps `image_id` and annotation key
ids so they don't collide across shards, and writes the merged pair
into the same directory. After running, prepare_yolo_data.py can be
pointed at `data/deepscoresv2/ds2_complete` exactly as if it were a
single-file dataset.

CLI:
    python3 -m tools.omr.training.merge_shards \
        --src data/deepscoresv2/ds2_complete \
        --train-shards 0 1 2 3 \
        --test-shards 0

The merged output (~1 GB for 4 train + 1 test shard) is written to:
    data/deepscoresv2/ds2_complete/deepscores_train.json
    data/deepscoresv2/ds2_complete/deepscores_test.json

Memory: each shard is loaded fully into RAM (json.load). For 8+ train
shards on a 16 GB machine, you may need to write a streaming merger.
On the Vast.ai 256 GB RAM A100 instances this completes in ~2 min.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


def merge_shards(
    src: Path,
    shard_ids: Iterable[int],
    suffix: str,
    out_path: Path,
) -> None:
    """Merge `deepscores-complete-{N}_{suffix}.json` for each N in `shard_ids`
    into a single COCO-like JSON written to `out_path`. Image and
    annotation ids are remapped to a globally unique sequence.
    """
    print(f"\n=== Merging {len(list(shard_ids))} {suffix} shard(s) into {out_path.name} ===")
    shard_ids = list(shard_ids)

    out: dict | None = None
    img_id_offset = 0
    ann_id_offset = 0
    n_images = 0
    n_annotations = 0

    for sid in shard_ids:
        p = src / f"deepscores-complete-{sid}_{suffix}.json"
        if not p.exists():
            print(f"  WARN: {p.name} missing, skipping")
            continue
        print(f"  loading {p.name} ({p.stat().st_size/1e6:.0f} MB)…")
        with open(p) as f:
            d = json.load(f)

        if out is None:
            out = {
                "info": d["info"],
                "annotation_sets": d["annotation_sets"],
                "categories": d["categories"],
                "images": [],
                "annotations": {},
            }

        old_to_new_img: dict[str, int] = {}
        for img in d["images"]:
            new_id = int(img["id"]) + img_id_offset
            old_to_new_img[str(img["id"])] = new_id
            new_img = dict(img, id=new_id)
            if "ann_ids" in new_img:
                new_img["ann_ids"] = [
                    str(int(a) + ann_id_offset) for a in new_img["ann_ids"]
                ]
            out["images"].append(new_img)
            n_images += 1

        for old_aid, ann in d["annotations"].items():
            new_aid = int(old_aid) + ann_id_offset
            new_ann = dict(ann)
            new_ann["img_id"] = str(old_to_new_img[str(ann["img_id"])])
            out["annotations"][str(new_aid)] = new_ann
            n_annotations += 1

        max_img_id = max(int(img["id"]) for img in d["images"])
        max_ann_id = max(int(k) for k in d["annotations"].keys())
        img_id_offset += max_img_id + 1
        ann_id_offset += max_ann_id + 1

    if out is None:
        raise RuntimeError(f"no shards loaded for suffix={suffix}")

    print(f"  total: {n_images} images, {n_annotations} annotations")
    print(f"  writing {out_path}")
    with open(out_path, "w") as f:
        json.dump(out, f)
    print(f"  wrote {out_path.stat().st_size/1e6:.0f} MB")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--src", required=True, type=Path,
                    help="Path to data/deepscoresv2/ds2_complete (directory with the shard JSONs)")
    ap.add_argument("--train-shards", nargs="+", type=int, default=[0, 1, 2, 3],
                    help="Which train shard ids to merge")
    ap.add_argument("--test-shards", nargs="+", type=int, default=[0],
                    help="Which test shard ids to merge")
    args = ap.parse_args()

    src = args.src.resolve()
    if not src.exists():
        print(f"ERROR: --src does not exist: {src}")
        return 2

    merge_shards(src, args.train_shards, "train", src / "deepscores_train.json")
    merge_shards(src, args.test_shards, "test", src / "deepscores_test.json")
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
