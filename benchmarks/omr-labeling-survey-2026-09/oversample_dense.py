"""Oversample the DENSE base cells in a built catalog's TRAIN split.

The hollow (scan) cells are inherently low-density; left un-oversampled they
become a majority of the training cells and narrow the density prior (the
mechanism behind the clef fine-tune's 2506->114 dense-notehead collapse). This
duplicates the dense base (v1-v4) train lines FACTOR times so hollow stays a
clear minority, exactly as the 2026-09-03 ship run did (there at 2x; the cloud
imgsz-2048 run uses a higher ratio per next-steps-omr-2026-09-03).

ultralytics keeps duplicate lines in a train list (get_img_files sorts, no
set()), so a 3x line is seen 3x per epoch. The VAL split is left untouched — a
clean, non-oversampled monitor.

Usage (on the training box, AFTER build_catalog_yaml):
    python3 oversample_dense.py --catalog <root>/catalog.yaml --factor 3
Writes <root>/catalog-<factor>xdense.yaml + <root>/_catalog_train_<factor>xdense.txt.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import yaml

# The dense base = the four engraved orchestral versions. Everything else
# (v5/v6 clef — not in these mixes — and v7+ hollow) is NOT oversampled.
DENSE_PREFIXES = ("/v1-", "/v2-", "/v3-", "/v4-")


def is_dense(line: str) -> bool:
    return any(p in line for p in DENSE_PREFIXES)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True, type=Path)
    ap.add_argument("--factor", type=int, default=3)
    args = ap.parse_args()

    cat = yaml.safe_load(args.catalog.read_text())
    train_txt = Path(cat["train"])
    lines = [ln for ln in train_txt.read_text().splitlines() if ln.strip()]

    dense = [ln for ln in lines if is_dense(ln)]
    hollow = [ln for ln in lines if not is_dense(ln)]
    out_lines = dense * args.factor + hollow  # order does not matter; ultralytics shuffles

    root = args.catalog.parent
    new_train = (root / f"_catalog_train_{args.factor}xdense.txt").resolve()
    new_train.write_text("\n".join(out_lines) + "\n")

    new_cat = dict(cat)
    # ABSOLUTE train path: ultralytics joins a relative train with the yaml's
    # `path:` key (which build_catalog_yaml sets absolute), doubling it. An
    # absolute train path is used as-is. `val` is already absolute from build.
    new_cat["train"] = str(new_train)
    new_yaml = root / f"catalog-{args.factor}xdense.yaml"
    new_yaml.write_text(yaml.safe_dump(new_cat, sort_keys=False))

    print(f"dense base:  {len(dense):4d} cells x{args.factor} = {len(dense)*args.factor}")
    print(f"hollow:      {len(hollow):4d} cells x1")
    print(f"train total: {len(out_lines):4d} images/epoch "
          f"(dense {len(dense)*args.factor/max(1,len(out_lines))*100:.0f}% / "
          f"hollow {len(hollow)/max(1,len(out_lines))*100:.0f}%)")
    print(f"wrote {new_yaml}")
    print(f"      {new_train}")


if __name__ == "__main__":
    main()
