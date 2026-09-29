"""Arm E's only difference from arm B: duplicate every TRAIN-split cell that
holds >=1 label line, so the minority class is oversampled the same way
oversample_dense.py already oversamples the dense base for the main ship
recipe (round 6's own file, same mechanism, generalized from "is this a v1-v4
dense-base line" to "does this cell's label file have any rows").

The rehearsal FINDINGS.md's own words motivate this arm: "the model deletes
classes it is being trained on" -- optimization dynamics, not corpus silence.
A class-balanced/oversampled minority is the standard mitigation for exactly
that failure mode, and rest_experiment_lib's corpus B already guarantees
every cell's rests are genuinely labeled (arm E must NOT run on arm A/C,
whose positive cells are the same ones but incompletely labeled -- that would
oversample the very unlabeled-positive problem this experiment is about).

    python3 .../oversample_positive_cells.py --catalog cat-B-completed/catalog.yaml --factor 4
Writes <root>/catalog-<factor>xpos.yaml + <root>/_catalog_train_<factor>xpos.txt.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import yaml


def _label_path(image_line: str) -> Path:
    # ultralytics' own convention: .../images/<name>.png -> .../labels/<name>.txt
    p = Path(image_line.strip())
    parts = list(p.parts)
    try:
        i = parts.index("images")
        parts[i] = "labels"
    except ValueError:
        return p.with_suffix(".txt")
    return Path(*parts).with_suffix(".txt")


def is_positive(image_line: str) -> bool:
    lp = _label_path(image_line)
    if not lp.exists():
        return False
    return any(ln.strip() for ln in lp.read_text().splitlines())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True, type=Path)
    ap.add_argument("--factor", type=int, default=4)
    args = ap.parse_args()

    cat = yaml.safe_load(args.catalog.read_text())
    train_txt = Path(cat["train"])
    lines = [ln for ln in train_txt.read_text().splitlines() if ln.strip()]

    pos = [ln for ln in lines if is_positive(ln)]
    neg = [ln for ln in lines if not is_positive(ln)]
    out_lines = pos * args.factor + neg

    root = args.catalog.parent
    new_train = (root / f"_catalog_train_{args.factor}xpos.txt").resolve()
    new_train.write_text("\n".join(out_lines) + "\n")

    new_cat = dict(cat)
    new_cat["train"] = str(new_train)
    new_yaml = root / f"catalog-{args.factor}xpos.yaml"
    new_yaml.write_text(yaml.safe_dump(new_cat, sort_keys=False))

    print(f"positive cells: {len(pos):4d} x{args.factor} = {len(pos)*args.factor}")
    print(f"negative cells: {len(neg):4d} x1")
    print(f"train total: {len(out_lines):4d} images/epoch "
          f"(positive {len(pos)*args.factor/max(1,len(out_lines))*100:.0f}%)")
    print(f"wrote {new_yaml}")
    print(f"      {new_train}")


if __name__ == "__main__":
    main()
