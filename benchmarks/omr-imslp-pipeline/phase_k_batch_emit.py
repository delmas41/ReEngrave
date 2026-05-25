#!/usr/bin/env python3
"""Phase K — batch run the CV-stem/beam label generator across all 26
catalog-ready (work, edition, mvt) tuples. Same RUNS list as Phase J.

Output goes to phase-k-labels/ + phase-k-output/.

Usage:
  python3 benchmarks/omr-imslp-pipeline/phase_k_batch_emit.py
  python3 ... --skip-overlays
  python3 ... --dry-run
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave")
WORKTREE = REPO_ROOT / ".claude/worktrees/interesting-curran-3ca1b7"
EMIT_SCRIPT = WORKTREE / "benchmarks/omr-imslp-pipeline/phase_k_emit_labels.py"
OUT_BASE = WORKTREE / "benchmarks/omr-imslp-pipeline/phase-k-labels"
SUMMARY_DIR = WORKTREE / "benchmarks/omr-imslp-pipeline/phase-k-output"
SUMMARY_DIR.mkdir(parents=True, exist_ok=True)


RUNS: list[tuple[str, str, list[int]]] = [
    ("beethoven-symphony-1", "imslp-52848",  [1, 2, 3, 4]),
    ("beethoven-symphony-2", "imslp-503997", [1, 2, 3, 4]),
    ("beethoven-symphony-2", "imslp-977672", [1, 2, 3, 4]),
    ("beethoven-symphony-4", "imslp-411721", [1, 2, 4]),
    ("beethoven-symphony-6", "imslp-57857",  [1, 2, 5]),
    ("beethoven-symphony-8", "imslp-06303",  [1, 2, 3, 4]),
    ("beethoven-symphony-8", "imslp-875077", [1, 2, 3, 4]),
]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-overlays", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv[1:])

    total_runs = sum(len(mvts) for _, _, mvts in RUNS)
    print("Planned runs:")
    for work, edition, mvts in RUNS:
        print(f"  {work} / {edition} / mvts {mvts}")
    print(f"\nTotal: {total_runs} runs")
    if args.dry_run:
        return 0

    aggregate = {
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "runs": [],
        "totals": {
            "pages_processed": 0,
            "cells_total": 0,
            "cells_with_xml_match": 0,
            "cells_stems_emitted": 0,
            "cells_stems_skipped_count_mismatch": 0,
            "cells_beams_emitted": 0,
            "cells_beams_skipped_count_mismatch": 0,
            "barlines_emitted": 0,
            "stems_emitted": 0,
            "beams_emitted": 0,
            "labels_total": 0,
            "runs_succeeded": 0,
            "runs_failed": 0,
        },
    }

    for work, edition, mvts in RUNS:
        for mvt in mvts:
            run_label = f"{work}/{edition}/mvt{mvt}"
            print(f"\n{'═' * 70}\nRunning {run_label}\n{'═' * 70}")
            t0 = time.time()
            cmd = [
                sys.executable, str(EMIT_SCRIPT),
                "--work", work,
                "--edition", edition,
                "--mvt", str(mvt),
            ]
            if args.skip_overlays:
                cmd.append("--no-overlays")
            try:
                result = subprocess.run(
                    cmd, cwd=WORKTREE, check=False,
                    capture_output=True, text=True,
                    timeout=3600,
                )
            except subprocess.TimeoutExpired:
                print("  ! TIMEOUT")
                aggregate["totals"]["runs_failed"] += 1
                aggregate["runs"].append({
                    "work": work, "edition": edition, "mvt": mvt,
                    "status": "timeout",
                })
                continue

            elapsed = time.time() - t0
            summary_path = (OUT_BASE / f"{work}-{edition}-mvt{mvt}"
                            / "summary.json")
            if result.returncode != 0 or not summary_path.exists():
                print(f"  ! FAILED (exit {result.returncode})")
                stderr_tail = result.stderr.strip().splitlines()[-5:]
                for line in stderr_tail:
                    print(f"    {line}")
                aggregate["totals"]["runs_failed"] += 1
                aggregate["runs"].append({
                    "work": work, "edition": edition, "mvt": mvt,
                    "status": "failed", "exit_code": result.returncode,
                    "stderr_tail": stderr_tail,
                })
                continue

            run_summary = json.loads(summary_path.read_text())
            run_summary["elapsed_seconds"] = round(elapsed, 1)
            run_summary["work"] = work
            run_summary["edition"] = edition
            run_summary["mvt"] = mvt
            run_summary["status"] = "ok"
            aggregate["runs"].append(run_summary)
            aggregate["totals"]["runs_succeeded"] += 1
            for k in ("pages_processed", "cells_total",
                      "cells_with_xml_match",
                      "cells_stems_emitted", "cells_stems_skipped_count_mismatch",
                      "cells_beams_emitted", "cells_beams_skipped_count_mismatch",
                      "barlines_emitted", "stems_emitted", "beams_emitted",
                      "labels_total"):
                aggregate["totals"][k] += run_summary.get(k, 0)
            mr = (run_summary["cells_with_xml_match"]
                  / max(1, run_summary["cells_total"]))
            print(f"  OK in {elapsed:.1f}s: "
                  f"{run_summary['pages_processed']}p "
                  f"{run_summary['cells_total']}c "
                  f"{run_summary['barlines_emitted']}bar+"
                  f"{run_summary['stems_emitted']}stm+"
                  f"{run_summary['beams_emitted']}bm "
                  f"= {run_summary['labels_total']} labels  "
                  f"({mr*100:.1f}% match)")

    aggregate["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    out_path = SUMMARY_DIR / "batch_summary.json"
    out_path.write_text(json.dumps(aggregate, indent=2))
    print(f"\n{'═' * 70}")
    print(f"Wrote {out_path}")
    print(f"Totals: {aggregate['totals']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
