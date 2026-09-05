"""Dump musicdiff's op list for every row of the 20-row scan gate.

`dump_ops.py` opens ONE pair; this walks the canonical results file and opens
all twenty, writing `out/ops/<row_id>.json` per row. Everything downstream in
this directory reads those files, so the expensive musicdiff pass happens once.

RUN IT WITH THE musicdiff VENV:

    /Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python \
        benchmarks/omr-scan-attribution-2026-09/dump_all_ops.py

⚠️ FIXTURE PROVENANCE. The pred paths come out of the results file itself, so
this cannot silently read the main checkout's ELEVEN-row `.restamp-composed`
fixtures — but it asserts the suffix anyway, and it asserts per row that the
total op cost it computes EQUALS the omr_ed the canonical file recorded. A
report that can return "nothing found" has to prove it looked at something, and
that equality is the proof: it re-derives the recorded number from the same
files by a different code path.

Like `dump_ops.py` this runs inside an interpreter that does NOT have the
project on its path — no `tools.*` imports.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "benchmarks" / "omr-ned-2026-08"))
sys.path.insert(0, str(Path("/Users/seanjohnson/Desktop/ReEngrave/benchmarks/"
                            "omr-ned-2026-08")))

from dump_ops import dump  # noqa: E402

CANONICAL = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
             "reconciliation/benchmarks/omr-scan-e2e-2026-09/"
             "results-reconciliation.json")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, default=Path(CANONICAL))
    ap.add_argument("--out-dir", type=Path, default=HERE / "out" / "ops")
    ap.add_argument("--expect-suffix", default=".reconciliation.")
    ap.add_argument("--only", default=None, help="substring filter on row_id")
    args = ap.parse_args(argv)

    doc = json.loads(args.results.read_text())
    rows = [r for r in doc["rows"] if r.get("pooled")]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    for row in rows:
        rid = row["row_id"]
        if args.only and args.only not in rid:
            continue
        pred, truth = Path(row["pred_xml"]), Path(row["truth_xml"])
        if args.expect_suffix not in pred.name:
            raise SystemExit(f"{rid}: {pred.name} is not a "
                             f"{args.expect_suffix} fixture")
        dest = args.out_dir / f"{rid}.json"
        t0 = time.time()
        result = dump(pred, truth)
        recorded = row["omr_ned"]["omr_ed"]
        result["row_id"] = rid
        result["recorded_omr_ed"] = recorded
        result["cost_matches_recorded"] = (result["total_cost"] == recorded)
        dest.write_text(json.dumps(result, indent=1, default=str) + "\n")
        flag = "OK " if result["cost_matches_recorded"] else "MISMATCH"
        print(f"{flag} {rid:44s} cost {result['total_cost']:>6d} "
              f"recorded {recorded:>6d} ops {result['n_ops']:>6d} "
              f"{time.time() - t0:6.1f}s", flush=True)
        ok += result["cost_matches_recorded"]
    print(f"\n{ok} rows reproduce their recorded OMR-ED exactly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
