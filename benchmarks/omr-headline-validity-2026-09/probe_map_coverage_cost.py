"""What it would COST to normalise the rest of the scan gate.

The hand-read `staves[i].parts` maps are the bottleneck on page-normalisation:
a row without one is not normalised, is not guessed at, and its structural
share is unmeasured. This turns "we can only normalise half the pool" into a
number Sean can decide on — which pages, how many staves, and how many pooled
`entire staff` edits are currently unattributable because of it.

The per-row `entire staff insert/delete` counts come from the CANONICAL 20-row
baseline (`results-reconciliation.json`, pooled 0.8444), so the attribution is
against the figure that is actually quoted.

    python3 benchmarks/omr-headline-validity-2026-09/probe_map_coverage_cost.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"
BASELINE = SCAN / "results-reconciliation.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(BENCH / "map-coverage-cost.json"))
    args = ap.parse_args(argv)

    doc = json.loads((SCAN / "works.json").read_text())
    rows = doc["rows"]
    by_id = {r["row_id"]: r for r in rows}
    for row in rows:
        v = row.get("staves")
        if isinstance(v, str) and v.startswith("same-as:"):
            row["staves"] = by_id[v.split(":", 1)[1]]["staves"]

    base = json.loads(BASELINE.read_text())
    es = {}
    for r in base["rows"]:
        rid = r["row_id"].replace(".reconciliation", "")
        cats = (r.get("omr_ned") or {}).get("categories") or {}
        es[rid] = {"entire_staff": cats.get("entire staff insert/delete", 0),
                   "entire_measure": cats.get("entire measure insert/delete", 0),
                   "omr_ed": (r.get("omr_ned") or {}).get("omr_ed", 0)}

    out = []
    for row in rows:
        rid = row["row_id"]
        has = isinstance(row.get("staves"), list)
        page = row["page"]
        out.append({
            "row_id": rid,
            "has_hand_map": has,
            "n_systems": page.get("n_systems"),
            "staves_on_page": page.get("n_staves"),
            # what a human would have to read to build the missing map: the
            # LINEUP of each system on the page, i.e. every printed staff, and
            # for each the reference part(s) it carries.
            "staves_a_human_would_read": 0 if has else (page.get("n_staves") or 0),
            **es.get(rid, {}),
        })

    mapped = [r for r in out if r["has_hand_map"]]
    unmapped = [r for r in out if not r["has_hand_map"]]
    doc_out = {
        "generated_by": "benchmarks/omr-headline-validity-2026-09/"
                        "probe_map_coverage_cost.py",
        "baseline": {"file": str(BASELINE),
                     "pooled_omr_ned": base["pooled"]["omr_ned"],
                     "pooled_omr_ed": base["pooled"]["omr_ed"],
                     "pooled_entire_staff":
                         base["pooled"]["categories"]
                         ["entire staff insert/delete"]},
        "coverage": {
            "n_rows": len(out),
            "n_mapped": len(mapped),
            "n_unmapped": len(unmapped),
            "entire_staff_on_mapped_rows": sum(r.get("entire_staff", 0)
                                               for r in mapped),
            "entire_staff_on_unmapped_rows": sum(r.get("entire_staff", 0)
                                                 for r in unmapped),
            "staves_a_human_would_read_to_close_the_gap":
                sum(r["staves_a_human_would_read"] for r in unmapped),
        },
        "rows": out,
    }
    Path(args.out).write_text(json.dumps(doc_out, indent=1) + "\n")

    print(f"{'row':40s} {'map':>4s} {'sys':>4s} {'staves':>7s} "
          f"{'ent.staff':>10s} {'to read':>8s}")
    for r in out:
        print(f"{r['row_id']:40s} {'yes' if r['has_hand_map'] else 'NO':>4s} "
              f"{r['n_systems'] or 0:>4d} {r['staves_on_page'] or 0:>7d} "
              f"{r.get('entire_staff', 0):>10d} "
              f"{r['staves_a_human_would_read']:>8d}")
    c = doc_out["coverage"]
    print()
    print(f"mapped {c['n_mapped']} / unmapped {c['n_unmapped']} of "
          f"{c['n_rows']} rows")
    print(f"`entire staff` edits on MAPPED rows (attributable today): "
          f"{c['entire_staff_on_mapped_rows']}")
    print(f"`entire staff` edits on UNMAPPED rows (cause UNKNOWN today): "
          f"{c['entire_staff_on_unmapped_rows']}")
    print(f"printed staves a human would have to read to close the gap: "
          f"{c['staves_a_human_would_read_to_close_the_gap']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
