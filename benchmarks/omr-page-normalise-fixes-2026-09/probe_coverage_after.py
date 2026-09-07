"""What the map-coverage split becomes once the four Mahler rows are merged.

⚠️ THIS IS A PROJECTION, NOT A MEASUREMENT OF A MERGED FILE, and it says so in
its own output. `works.json` was NOT written: the completion additions rows are
still `status: "in_progress"`, so merging them would be recording a
confirmation nobody made — and `merge_additions` refuses to overwrite a row
that already carries a map, so a premature write would lock Sean's own reading
out of the file.

The arithmetic is `probe_map_coverage_cost.py`'s, on the same inputs (the
canonical `results-reconciliation.json`), with the four rows moved from the
unmapped column to the mapped one. Nothing is re-scored, because the split is
an ACCOUNTING of the baseline's own per-row `entire staff` counts — merging a
map does not change the pooled figure at all (0.8444 is untouched by all of
this); it changes what can be SAID about it.

    python3 benchmarks/omr-page-normalise-fixes-2026-09/probe_coverage_after.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"
BASELINE = SCAN / "results-reconciliation.json"

#: the rows this fix unblocks — every one validated by `merge_additions`.
WOULD_MERGE = ("mahler-sym5-mvt1-local-p2", "mahler-sym5-mvt1-local-p3",
               "mahler-sym5-mvt1-local-p4", "mahler-sym5-mvt1-local-p5")


def main() -> int:
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
        es[rid] = cats.get("entire staff insert/delete", 0)

    def split(mapped_ids: set[str]) -> dict:
        att = sum(v for k, v in es.items() if k in mapped_ids)
        unk = sum(v for k, v in es.items() if k not in mapped_ids)
        to_read = sum((by_id[k]["page"].get("n_staves") or 0)
                      for k in es if k not in mapped_ids)
        return {"rows_mapped": len(mapped_ids), "rows_total": len(es),
                "entire_staff_attributable": att,
                "entire_staff_cause_unknown": unk,
                "printed_staves_a_human_would_read": to_read}

    today = {r["row_id"] for r in rows if isinstance(r.get("staves"), list)}
    after = today | set(WOULD_MERGE)

    out = {
        "generated_by": "benchmarks/omr-page-normalise-fixes-2026-09/"
                        "probe_coverage_after.py",
        "wrote_works_json": False,
        "projection": True,
        "note": ("`printed_staves_a_human_would_read` counts works.json's own "
                 "`page.n_staves`, which is FIVE-LINE staves only — Mahler's "
                 "one-line percussion rules are not in it and the residual "
                 "they leave is a pipeline ceiling, not a labelling gap."),
        "would_merge": list(WOULD_MERGE),
        "today": split(today),
        "after_the_four_mahler_rows": split(after),
        "still_unattributed_after": {
            rid: es[rid] for rid in es if rid not in after},
    }
    (HERE / "coverage-after.json").write_text(json.dumps(out, indent=1) + "\n")

    for label in ("today", "after_the_four_mahler_rows"):
        d = out[label]
        print(f"{label:32s} mapped {d['rows_mapped']:>2d}/{d['rows_total']}  "
              f"attributable {d['entire_staff_attributable']:>6d}  "
              f"unknown {d['entire_staff_cause_unknown']:>5d}  "
              f"staves to read {d['printed_staves_a_human_would_read']:>3d}")
    print("\nstill unattributed after:", out["still_unattributed_after"])
    print("⚠️ PROJECTION — works.json was not written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
