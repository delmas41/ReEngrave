#!/usr/bin/env python3
"""Phase G — batch run the label generator across all catalog-ready
editions × all movements.

Skips combinations that are known to be lossy:
  * Beethoven 4 imslp-411721 mvt 3 — boundary unverified (movements.yaml
    has verified=false on this edition)
  * Beethoven 6 imslp-57857 mvt 3 and mvt 4 — mid-page transition at p66
    means cells on that page can't be cleanly assigned to a single mvt.
    Generate labels for mvt 1, 2, 5 only.

Output:
  phase-e-labels/{work}-{edition}-mvt{N}/  ← labels + overlays per run
  phase-g-output/batch_summary.json        ← aggregate stats

Usage:
  python3 benchmarks/omr-imslp-pipeline/phase_g_batch_emit.py
  python3 ... --skip-overlays   (faster, no debug PNGs)
  python3 ... --dry-run          (just print what would run)
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
EMIT_SCRIPT = WORKTREE / "benchmarks/omr-imslp-pipeline/phase_e_emit_labels.py"
OUT_BASE = WORKTREE / "benchmarks/omr-imslp-pipeline/phase-e-labels"
SUMMARY_DIR = WORKTREE / "benchmarks/omr-imslp-pipeline/phase-g-output"
SUMMARY_DIR.mkdir(parents=True, exist_ok=True)


# (work, edition, [list of movements to run])
RUNS: list[tuple[str, str, list[int]]] = [
    ("beethoven-symphony-1", "imslp-52848",  [1, 2, 3, 4]),
    ("beethoven-symphony-2", "imslp-503997", [1, 2, 3, 4]),
    ("beethoven-symphony-2", "imslp-977672", [1, 2, 3, 4]),
    ("beethoven-symphony-4", "imslp-411721", [1, 2, 4]),     # skip mvt 3 (unverified)
    ("beethoven-symphony-6", "imslp-57857",  [1, 2, 5]),     # skip mvt 3+4 (mid-page transition at p66)
    ("beethoven-symphony-8", "imslp-06303",  [1, 2, 3, 4]),
    ("beethoven-symphony-8", "imslp-875077", [1, 2, 3, 4]),
]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-overlays", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv[1:])

    print(f"Planned runs:")
    for work, edition, mvts in RUNS:
        print(f"  {work} / {edition} / mvts {mvts}")
    total_runs = sum(len(mvts) for _, _, mvts in RUNS)
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
            "labels_total": 0,
            "homography_failures": 0,
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
                print(f"  ! TIMEOUT after 1 hour")
                aggregate["totals"]["runs_failed"] += 1
                aggregate["runs"].append({
                    "work": work, "edition": edition, "mvt": mvt,
                    "status": "timeout",
                })
                continue

            elapsed = time.time() - t0
            # Read the run's summary.json if it exists
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
                    "status": "failed",
                    "exit_code": result.returncode,
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
                      "cells_with_xml_match", "labels_total",
                      "homography_failures"):
                aggregate["totals"][k] += run_summary.get(k, 0)
            match_rate = (run_summary["cells_with_xml_match"]
                          / max(1, run_summary["cells_total"]))
            print(f"  OK in {elapsed:.1f}s: "
                  f"{run_summary['pages_processed']} pages, "
                  f"{run_summary['cells_total']} cells, "
                  f"{run_summary['labels_total']} labels, "
                  f"{match_rate * 100:.1f}% XML match")

    aggregate["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    out_path = SUMMARY_DIR / "batch_summary.json"
    out_path.write_text(json.dumps(aggregate, indent=2))
    print(f"\n{'═' * 70}")
    print(f"Wrote {out_path}")
    print(f"Totals: {aggregate['totals']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
