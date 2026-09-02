"""Validate `hollow_score` against the FIRST round's hand labels.

The first round (`benchmarks/omr-labeling-hollow-2026-08`) is the only place in
the repo where a human has said, cell by cell, whether a hollow notehead is
present: 25 of its 48 cells carry a verdict file with drawn boxes and 23 were
inspected and left empty. That makes it a ready-made test set for any rule that
claims to find cells worth labelling.

    python3 benchmarks/omr-labeling-hollow2-2026-09/validate_hollow_score.py

⚠️ The cell PNGs are gitignored, so this only runs on a machine that still has
`benchmarks/omr-labeling-hollow-2026-08/cells/` — which lives in the MAIN
checkout, not in a worktree. Pass --cells-root to point at it.
"""
from __future__ import annotations

import argparse
import glob
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hollow_score import score_cell  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=Path,
                    default=Path("benchmarks/omr-labeling-hollow-2026-08"))
    ap.add_argument("--cells-root", type=Path,
                    default=Path("/Users/seanjohnson/Desktop/ReEngrave"),
                    help="checkout that still holds the gitignored cells/ PNGs")
    args = ap.parse_args()

    cells = json.loads((args.batch / "cells.json").read_text())
    truth = {}
    for f in glob.glob(str(args.batch / "verdicts/*.json")):
        v = json.loads(Path(f).read_text())
        truth[v["cell_id"]] = len(v.get("added_detections") or [])

    rows = [(c["cell_id"], score_cell(c, args.cells_root)[0],
             truth.get(c["cell_id"], 0)) for c in cells]
    pos = [r for r in rows if r[2] > 0]
    neg = [r for r in rows if r[2] == 0]
    print(f"cells WITH a hollow head: {len(pos)}   WITHOUT: {len(neg)}")
    print(f"  score on positives: mean {st.mean(r[1] for r in pos):.2f}")
    print(f"  score on negatives: mean {st.mean(r[1] for r in neg):.2f}")
    for thr in (1, 2, 3):
        tp = sum(1 for r in pos if r[1] >= thr)
        fp = sum(1 for r in neg if r[1] >= thr)
        if tp + fp:
            print(f"  score >= {thr}: selects {tp+fp:2d}, {tp:2d} correct "
                  f"-> precision {tp/(tp+fp):.0%}  (uniform {len(pos)/len(rows):.0%})")
    rows.sort(key=lambda r: -r[1])
    for K in (12, 20, 25):
        tp = sum(1 for r in rows[:K] if r[2] > 0)
        print(f"  top-{K}: {tp} positives -> {tp/K:.0%}")


if __name__ == "__main__":
    main()
