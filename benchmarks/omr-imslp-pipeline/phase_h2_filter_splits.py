#!/usr/bin/env python3
"""Phase H attempt 2 — filter the catalog splits to only movements with
high XML-match rate, so YOLO sees fully-labeled pages instead of pages
where 30-50% of cells have no labels.

Phase H attempt 1 failed because the training data included movements
where 30-50% of cells got no XML match → no labels → model learned the
"predict nothing" shortcut. This filter drops those movements from train
(but the val set stays — we already picked val movements with ≥99% match).

Reads:
  benchmarks/omr-imslp-pipeline/phase-g-output/batch_summary.json
  benchmarks/omr-imslp-pipeline/phase-h-data/{images,labels}/<key>/...

Writes (next to existing train.txt / val.txt):
  train.filtered.txt        — only high-match movements
  data-catalog-only.filtered.yaml — references train.filtered.txt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parent / "phase-h-data"
SUMMARY = Path(__file__).resolve().parent / "phase-g-output" / "batch_summary.json"


# Same val keys as the original phase_h_build_splits.py
VAL_KEYS: list[str] = [
    "beethoven-symphony-1-imslp-52848-mvt4",
    "beethoven-symphony-2-imslp-503997-mvt2",
    "beethoven-symphony-2-imslp-977672-mvt3",
    "beethoven-symphony-4-imslp-411721-mvt2",
    "beethoven-symphony-6-imslp-57857-mvt2",
    "beethoven-symphony-8-imslp-06303-mvt4",
    "beethoven-symphony-8-imslp-875077-mvt4",
]


def key_for_run(r: dict) -> str:
    return f"{r['work']}-{r['edition']}-mvt{r['mvt']}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--summary", default=str(SUMMARY))
    ap.add_argument("--threshold", type=float, default=0.95,
                    help="Keep movements with XML-match rate >= this (0-1)")
    ap.add_argument("--target-base", default="{DATA_BASE}/phase-h-data",
                    help="Remote path prefix in the emitted text files")
    args = ap.parse_args()

    out_root = Path(args.out).resolve()
    images_root = out_root / "images"
    summary = json.loads(Path(args.summary).read_text())

    # Compute match rate per movement
    rates: dict[str, float] = {}
    pages_count: dict[str, int] = {}
    for r in summary["runs"]:
        k = key_for_run(r)
        rate = r["cells_with_xml_match"] / max(1, r["cells_total"])
        rates[k] = rate
        pages_count[k] = r["pages_processed"]

    # Train candidates = all movements EXCEPT val
    train_candidates = sorted(set(rates) - set(VAL_KEYS))

    # Filter by threshold
    kept = [k for k in train_candidates if rates[k] >= args.threshold]
    dropped = [k for k in train_candidates if rates[k] < args.threshold]

    print(f"Filter threshold: ≥ {args.threshold*100:.0f}% XML match")
    print(f"\nKEPT train movements ({len(kept)}):")
    for k in kept:
        print(f"  {k:<48} match={rates[k]*100:>5.1f}%  pages={pages_count[k]:>3}")
    print(f"\nDROPPED train movements ({len(dropped)}):")
    for k in dropped:
        print(f"  {k:<48} match={rates[k]*100:>5.1f}%  pages={pages_count[k]:>3}")
    print(f"\nVAL movements (unchanged, {len(VAL_KEYS)}):")
    for k in VAL_KEYS:
        print(f"  {k:<48} match={rates[k]*100:>5.1f}%  pages={pages_count[k]:>3}")

    # Build train.filtered.txt
    def remap(p: Path) -> str:
        rel = p.relative_to(out_root)
        return f"{args.target_base}/{rel.as_posix()}"

    train_paths: list[str] = []
    for k in kept:
        kdir = images_root / k
        if not kdir.exists():
            print(f"  WARN: images dir missing for {k}, skipping")
            continue
        for png in sorted(kdir.glob("p*.png")):
            train_paths.append(remap(png))

    val_paths: list[str] = []
    for k in VAL_KEYS:
        kdir = images_root / k
        if not kdir.exists():
            continue
        for png in sorted(kdir.glob("p*.png")):
            val_paths.append(remap(png))

    print(f"\nTrain images written: {len(train_paths)}")
    print(f"Val   images written: {len(val_paths)} (unchanged)")

    (out_root / "train.filtered.txt").write_text("\n".join(train_paths) + "\n")
    (out_root / "val.txt").write_text("\n".join(val_paths) + "\n")  # rewrite for safety

    # Build the filtered yaml — reuses the prod-208 nc + names from the
    # existing data-catalog-only.yaml (just swap the train path).
    src_yaml = out_root / "data-catalog-only.yaml"
    if not src_yaml.exists():
        print(f"ERROR: source yaml missing at {src_yaml}")
        return 2
    src = src_yaml.read_text()
    out_yaml = src.replace("train: train.txt", "train: train.filtered.txt")
    (out_root / "data-catalog-only.filtered.yaml").write_text(out_yaml)
    print(f"\nWrote data-catalog-only.filtered.yaml")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
