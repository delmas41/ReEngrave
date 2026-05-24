#!/usr/bin/env python3
"""Phase D — aggregate per-PDF alignment results into a catalog summary.

Reads every phase-d-output/{work}__{edition}.json and produces a markdown
table for PHASE_D_CATALOG_SUMMARY.md. Run this after phase_d_run_alignment.py
completes (or to refresh the summary while the runner is still in progress).

Output: prints the markdown to stdout; copy/paste into the summary doc.
"""

from __future__ import annotations

import json
import sys
import statistics
from pathlib import Path

OUT_DIR = Path(__file__).parent / "phase-d-output"


def load_results() -> list[dict]:
    results = []
    for f in sorted(OUT_DIR.glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            results.append(json.loads(f.read_text()))
        except Exception:
            continue
    return results


def main() -> int:
    results = load_results()
    if not results:
        print("No results yet.")
        return 1

    # Group by work
    by_work: dict[str, list[dict]] = {}
    for r in results:
        by_work.setdefault(r["work"], []).append(r)

    print(f"## Aggregate ({len(results)} editions processed)\n")

    # Failure: PDF detected 0 measures (likely scan or detection issue)
    failures = [r for r in results if r["pdf_detected_measures"] == 0]
    succeeded = [r for r in results if r["pdf_detected_measures"] > 0]
    print(f"- Succeeded: {len(succeeded)} editions")
    print(f"- Detected 0 measures: {len(failures)} editions")
    if succeeded:
        deltas = [r["delta_pct"] for r in succeeded]
        within_5 = sum(1 for d in deltas if abs(d) <= 5)
        within_10 = sum(1 for d in deltas if abs(d) <= 10)
        within_20 = sum(1 for d in deltas if abs(d) <= 20)
        print(f"- Within  ±5%: {within_5}/{len(succeeded)} editions  ← catalog-ready")
        print(f"- Within ±10%: {within_10}/{len(succeeded)}")
        print(f"- Within ±20%: {within_20}/{len(succeeded)}")
        print()
        print(f"- Mean delta:   {statistics.mean(deltas):+.1f}%")
        print(f"- Median delta: {statistics.median(deltas):+.1f}%")
        print(f"- Std dev:      {statistics.stdev(deltas):.1f}%" if len(deltas) > 1 else "")
        print(f"- Min delta:    {min(deltas):+.1f}%  ({min(succeeded, key=lambda r: r['delta_pct'])['edition']})")
        print(f"- Max delta:    {max(deltas):+.1f}%  ({max(succeeded, key=lambda r: r['delta_pct'])['edition']})")

    print()
    print("## Per-work breakdown\n")
    for work in sorted(by_work):
        editions = by_work[work]
        print(f"### {work}\n")
        xml_total = editions[0]["xml_total_measures"]
        print(f"XML total measures: {xml_total}\n")
        print(f"| Edition | PDF pages | PDF measures | Δ | Δ % | Status |")
        print(f"|---|---:|---:|---:|---:|:---:|")
        for r in sorted(editions, key=lambda r: r["edition"]):
            pdf_m = r["pdf_detected_measures"]
            delta = r["delta"]
            pct = r["delta_pct"]
            if pdf_m == 0:
                status = "FAIL"
            elif abs(pct) <= 5:
                status = "OK"
            elif abs(pct) <= 20:
                status = "review"
            else:
                status = "high-delta"
            print(f"| {r['edition']} | {r['total_pages']} | {pdf_m} | {delta:+d} | {pct:+.1f}% | {status} |")
        print()

    print()
    print("## Catalog-ready editions (Δ within ±5%, ranked by accuracy)\n")
    print(f"| Work | Edition | PDF measures | XML | Δ % |")
    print(f"|---|---|---:|---:|---:|")
    ready = sorted([r for r in succeeded if abs(r["delta_pct"]) <= 5],
                   key=lambda r: abs(r["delta_pct"]))
    for r in ready:
        print(f"| {r['work']} | {r['edition']} | {r['pdf_detected_measures']} | "
              f"{r['xml_total_measures']} | {r['delta_pct']:+.1f}% |")
    print(f"\nTotal: {len(ready)} editions")

    if failures:
        print()
        print("## Failures (PDF detected 0 measures — likely scan or pipeline issue)\n")
        for r in failures:
            print(f"- {r['work']} / {r['edition']}: {r['total_pages']} pages, ran in {r['elapsed_seconds']:.0f}s")

    return 0


if __name__ == "__main__":
    sys.exit(main())
