"""Pre-register the random cell sample that decides the pre-fill's fate.

The 0.84 / 0.88 / 0.96 figures all come from SIX cells chosen because the
pre-fill decided the most in them — the densest bars, where alignment slips
most. That sample cannot answer "can pre-filled boxes be admitted as
labels", however it comes out, and every writeup here says so.

This picks the replacement sample the honest way and, crucially, BEFORE any
of it is labeled:

- **seeded** (`--seed`, default 20260903) so the draw is reproducible and
  cannot be re-rolled until it flatters something;
- **excludes the six** already-completed cells, whose labels exist;
- **shuffled**, and the output is an ORDERED list — label it in order and
  stopping at any point still leaves a valid random sample, because the
  prefix of a shuffle is itself a uniform sample. That is what makes a
  15-cell registration safe to ask for when 12 may be all there is time
  for;
- **records each cell's pre-fill status and box count AT REGISTRATION**, so
  the analysis population is fixed in advance and nobody can later pick the
  subset that scores best.

The status is read from a transcription the caller names, because the
pre-fill's output depends on the weights that produced it (see FINDINGS.md
"Phase B"): register against the same reading the labels will be scored
against.

    python3 benchmarks/omr-prefill-admission-2026-09/select_phase_c_cells.py \
        --transcription <reading>.json --out PHASE_C_CELLS.json

Writes nothing into the batch.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.training import mxl_verdicts as mv  # noqa: E402

DEFAULT_BENCH = REPO / "benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1"
# Labeled completely by hand on 2026-09-03; their labels exist, so they can
# never be part of an out-of-sample draw.
ALREADY_COMPLETED = [
    "brahms1-p2-sys0-s3-m4", "brahms1-p2-sys0-s9-m0", "brahms1-p3-sys0-s5-m5",
    "brahms1-p3-sys0-s9-m1", "brahms1-p4-sys0-s0-m3", "brahms1-p4-sys0-s10-m5",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bench-dir", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--transcription", type=Path, default=None,
                    help="the reading to register against (default: the batch's own)")
    ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--seed", type=int, default=20260903)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    bench = args.bench_dir

    tpath = args.transcription or (bench / "transcription.json")
    transcription = json.loads(tpath.read_text())
    truth = mv.load_truth(bench / "reference.mxl")
    windows = mv.load_windows(bench / "windows.json")
    manifest = json.loads((bench / "cells.json").read_text())
    ctx_by_key = mv.index_transcription(transcription)

    pool = [e["cell_id"] for e in manifest if e["cell_id"] not in set(ALREADY_COMPLETED)]
    rng = random.Random(args.seed)
    order = list(pool)
    rng.shuffle(order)
    chosen = order[: args.n]

    by_id = {e["cell_id"]: e for e in manifest}
    rows = []
    for rank, cid in enumerate(chosen, 1):
        entry = by_id[cid]
        key = (entry.get("page"), entry.get("system_index"),
               entry.get("staff_index"), entry.get("measure_index"))
        dp = bench / "detections" / f"{cid}.json"
        dets = json.loads(dp.read_text()).get("detections", []) if dp.exists() else []
        cp = mv.prefill_cell(entry, ctx_by_key.get(key),
                             windows.get(int(entry.get("page", -1))), truth, dets)
        n_head = sum(1 for d in cp.decisions if d.get("category") == "notehead")
        rows.append({
            "rank": rank, "cell_id": cid,
            "page": entry.get("page"), "staff_index": entry.get("staff_index"),
            "measure_index": entry.get("measure_index"),
            "prefill_status": cp.status,
            "prefill_reason": cp.reason,
            "n_prefill_boxes": len(cp.decisions),
            "n_prefill_noteheads": n_head,
            "n_admit_labels": sum(1 for d in cp.decisions if d.get("admission") == "labels"),
            "n_admit_queue": sum(1 for d in cp.decisions if d.get("admission") == "queue"),
        })

    doc = {
        "registered_for": "Phase C — the out-of-sample admission measurement",
        "bench": str(bench.name),
        "transcription": str(tpath),
        "transcription_weights": transcription.get("weights"),
        "seed": args.seed,
        "n_requested": args.n,
        "pool_size": len(pool),
        "excluded_already_completed": ALREADY_COMPLETED,
        "protocol": (
            "Label these cells COMPLETELY (every symbol, not one pass's) in "
            "rank order, with the server started --blind so the pre-fill's "
            "hints and queue order are withheld. Stopping early is fine: the "
            "prefix of a shuffle is still a uniform sample. Score with "
            "mxl_verdicts --score --score-classes all restricted to the "
            "cells actually completed."
        ),
        "cells": rows,
    }
    total = sum(r["n_prefill_boxes"] for r in rows)
    labels = sum(r["n_admit_labels"] for r in rows)
    prefilled = sum(1 for r in rows if r["prefill_status"] == "prefilled")
    print(f"seed {args.seed}: {len(rows)} of {len(pool)} eligible cells")
    print(f"  {prefilled} prefilled, {len(rows) - prefilled} abstained")
    print(f"  {total} pre-filled boxes registered ({labels} in the labels tier)")
    print(f"{'rank':>4}  {'cell':32} {'status':10} {'boxes':>5} {'labels':>6}")
    for r in rows:
        print(f"{r['rank']:>4}  {r['cell_id']:32} {r['prefill_status']:10} "
              f"{r['n_prefill_boxes']:>5} {r['n_admit_labels']:>6}")
    if args.out:
        args.out.write_text(json.dumps(doc, indent=2) + "\n")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
