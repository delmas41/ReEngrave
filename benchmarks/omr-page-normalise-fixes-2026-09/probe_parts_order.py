"""⚠️ Does `parts[0]` carry meaning? Priced on Sean's OWN confirmed maps.

The merge refused three finished rows because their entry 0 is not
sorted-unique, and the proposed repair was to SORT on write. That is only safe
if the order is meaningless — so this asks the consumer instead of assuming.

`page_normalise.normalise` does:

    keep   = parts[idx[0]]          # <- the FIRST index
    others = [parts[i] for i in idx[1:]]

so the first index decides which part's bar SURVIVES a `silent_all` measure,
i.e. whose RESTS the derived truth carries. `candidate_maps.flat` already
documents the convention ("printed part first, tacet folds after") and the
completion benchmark priced it at +8 edits over its candidate maps. This
re-prices it over the maps a human actually confirmed.

    python3 benchmarks/omr-page-normalise-fixes-2026-09/probe_parts_order.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-scan-e2e-2026-09"))

import page_normalise                              # noqa: E402
from tools.omr import omr_ned as omr_ned_mod       # noqa: E402

REC = (MAIN / ".claude/worktrees/reconciliation/benchmarks"
       "/omr-scan-e2e-2026-09/fixtures")
ADDITIONS = (MAIN / "benchmarks/omr-scan-e2e-2026-09"
             / "works.staves-additions-completion.json")
OUT = HERE / "parts-order.json"


def main() -> int:
    add = json.loads(ADDITIONS.read_text())
    tmp = Path(tempfile.mkdtemp(prefix="parts-order-"))
    pairs, rows = [], []
    for rid, r in add["rows"].items():
        if r.get("status") != "done":
            continue
        smap = r.get("staves_for_works_json") or []
        arms = {
            "as_confirmed": [{"name": s["name"], "parts": list(s["parts"])}
                             for s in smap],
            "sorted": [{"name": s["name"], "parts": sorted(set(s["parts"]))}
                       for s in smap],
        }
        truth = REC / f"{rid}.truth.musicxml"
        pred = REC / f"{rid}.reconciliation.omr.musicxml"
        if not truth.is_file() or not pred.is_file():
            print(f"SKIP {rid}: no fixture", file=sys.stderr)
            continue
        unsorted_entries = [k for k, s in enumerate(smap)
                            if list(s["parts"]) != sorted(set(s["parts"]))]
        for tag, m in arms.items():
            page_normalise.write(truth, m, tmp / f"{rid}.{tag}.musicxml")
            pairs.append((f"{rid}|{tag}", pred, tmp / f"{rid}.{tag}.musicxml"))
        rows.append({"row_id": rid, "n_entries": len(smap),
                     "unsorted_entries": unsorted_entries})

    by = {}
    for i in range(0, len(pairs), 4):
        s = omr_ned_mod.score_batch(pairs[i:i + 4], detail="AllObjects",
                                    timeout_s=3600.0)
        by.update({p["name"]: p for p in s.get("pairs", [])})

    print(f"{'row':34s} {'as confirmed':>13s} {'sorted':>9s} {'delta':>7s}  "
          f"unsorted entries")
    ta = ts = 0
    for r in rows:
        a = by[f"{r['row_id']}|as_confirmed"]["omr_ed"]
        b = by[f"{r['row_id']}|sorted"]["omr_ed"]
        r["as_confirmed_edits"], r["sorted_edits"] = a, b
        r["delta"] = b - a
        ta += a
        ts += b
        print(f"{r['row_id']:34s} {a:>13d} {b:>9d} {b - a:>+7d}  "
              f"{r['unsorted_entries']}")
    print(f"{'TOTAL':34s} {ta:>13d} {ts:>9d} {ts - ta:>+7d}")

    doc = {
        "generated_by": "benchmarks/omr-page-normalise-fixes-2026-09/"
                        "probe_parts_order.py",
        "question": "is `parts` a SET, or does parts[0] carry meaning?",
        "answer": ("parts[0] IS load-bearing: page_normalise keeps "
                   "parts[idx[0]] and merges the rest into it, so the first "
                   "index decides whose bar survives a silent_all measure"),
        "total_as_confirmed": ta, "total_sorted": ts, "delta": ts - ta,
        "rows": rows,
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
