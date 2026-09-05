"""Which truth part musicdiff coupled to which predicted part, per scan row.

`dump_ops.py` locates an op by the MEASURE or NOTE it holds, and a part-level
op (`inspart` / `delpart`) holds neither — it holds an `AnnPart`. So every one
of them lands in `dump_ops`' catch-all bucket with `part_index -1`, and the
part coupling cannot be reconstructed from those files. It can be read straight
off the op, because `AnnPart` carries its own `part_idx`.

    /Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python \
        benchmarks/omr-scan-attribution-2026-09/dump_part_coupling.py

Writes `out/part_coupling.json`: per row, the truth part indices musicdiff
could not couple (`inspart`), the predicted ones it could not couple
(`delpart`), and — the reason this exists — the resulting ordered pairing.
musicdiff's part coupling is order-preserving, so dropping the uncoupled
indices from each side and zipping what remains IS the coupling; the two
survivor lists having equal length is asserted here rather than downstream.

⚠️ It also records each part's bar count AS musicdiff COUNTS IT, which is not
the number of `<measure>` elements: `AnnPart.__init__` drops any measure with
`n_of_elements == 0`. Anything that compares bar counts must use this number.

Runs inside the musicdiff venv — no `tools.*` imports.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from music21 import converter
from musicdiff import AnnScore, Comparison, DetailLevel

CANONICAL = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
             "reconciliation/benchmarks/omr-scan-e2e-2026-09/"
             "results-reconciliation.json")


def couple(pred: Path, truth: Path) -> dict:
    pred_score = converter.parse(str(pred))
    truth_score = converter.parse(str(truth))
    level = DetailLevel.AllObjects
    ann_pred = AnnScore(pred_score, level)
    ann_truth = AnnScore(truth_score, level)
    ops, cost = Comparison.annotated_scores_diff(ann_pred, ann_truth)

    ins = sorted(op[2].part_idx for op in ops if op[0] == "inspart")
    dele = sorted(op[1].part_idx for op in ops if op[0] == "delpart")
    n_truth = len(ann_truth.part_list)
    n_pred = len(ann_pred.part_list)
    truth_left = [i for i in range(n_truth) if i not in set(ins)]
    pred_left = [j for j in range(n_pred) if j not in set(dele)]
    if len(truth_left) != len(pred_left):
        raise SystemExit(f"{pred.name}: {len(truth_left)} truth vs "
                         f"{len(pred_left)} pred survivors — the coupling is "
                         "not order-preserving-with-holes as assumed")
    return {
        "cost": cost,
        "n_truth_parts": n_truth,
        "n_pred_parts": n_pred,
        "inspart_truth_idx": ins,
        "delpart_pred_idx": dele,
        "pairs": list(zip(truth_left, pred_left)),
        "truth_bars": [p.n_of_bars for p in ann_truth.part_list],
        "pred_bars": [p.n_of_bars for p in ann_pred.part_list],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, default=Path(CANONICAL))
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parent / "out"
                    / "part_coupling.json")
    args = ap.parse_args(argv)

    doc = json.loads(args.results.read_text())
    out = {}
    for row in doc["rows"]:
        if not row.get("pooled"):
            continue
        rid = row["row_id"]
        got = couple(Path(row["pred_xml"]), Path(row["truth_xml"]))
        if got["cost"] != row["omr_ned"]["omr_ed"]:
            raise SystemExit(f"{rid}: cost {got['cost']} != recorded "
                             f"{row['omr_ned']['omr_ed']}")
        out[rid] = got
        print(f"OK  {rid:44s} parts {got['n_truth_parts']:>3d}->"
              f"{got['n_pred_parts']:<3d} coupled {len(got['pairs']):>3d}",
              flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
