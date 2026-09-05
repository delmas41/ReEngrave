"""Does a SUCCEEDING ordinal join put the same instrument in a slot?

`_stitch_slots` refuses when two systems disagree about how many staves they
have, because position-grafting a tacet-suppressed page would put one
instrument's music onto another. The refusal is visible and the fallback is
documented. **What is not visible is a join that succeeds and is still wrong**:
Beethoven 5 p.4 counts eleven staves in both systems and they are not the same
eleven — system 1 splits `Violoncello` from `Basso` and prints no Timpani,
system 2 prints Timpani and merges the basses, so everything from slot 6 down
is shifted by one. `works.json` says so in the row's own `_purpose` field.

This prints, per multi-system row that works.json maps PER SYSTEM, whether each
ordinal slot holds the same printed instrument in both systems — and beside it
what the pipeline's own margin-label reader called that staff, which is the
signal any label-keyed repair would have to use.

FIXTURE PROVENANCE. The 20-row transcriptions live in the worktree that
produced them (`.claude/worktrees/reconciliation/.../fixtures/`, suffix
`.reconciliation.omr.json`). The main checkout's `fixtures/` still holds the
ELEVEN-row era's `.restamp-composed` set.

    python3 benchmarks/omr-structural-parts-2026-09/probe_misjoined_slots.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.export import _stitch_slots  # noqa: E402

DEFAULT_FIXTURES = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation"
    "/benchmarks/omr-scan-e2e-2026-09/fixtures")
SUFFIX = ".reconciliation.omr.json"
WORKS = ROOT / "benchmarks/omr-scan-e2e-2026-09/works.json"


def _deref(rows: dict, row: dict, key: str):
    val = row.get(key)
    if isinstance(val, str) and val.startswith("same-as:"):
        return rows.get(val.split(":", 1)[1].strip(), {}).get(key)
    return val


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    fixtures = Path(args.fixtures)

    rows = {r["row_id"]: r for r in json.loads(WORKS.read_text())["rows"]}
    report = {}
    for rid in sorted(rows):
        src = fixtures / f"{rid}{SUFFIX}"
        if not src.exists():
            continue
        sap = _deref(rows, rows[rid], "systems_as_printed")
        if not isinstance(sap, dict):
            continue  # the row asserts ONE lineup for the page; nothing to check
        result = json.loads(src.read_text())
        systems = [s for pg in result.get("pages", [])
                   for s in pg.get("systems", []) if s.get("staves")]
        joined = _stitch_slots(result) is not None
        printed = [sap[f"system_{i+1}"] for i in range(len(systems))
                   if isinstance(sap.get(f"system_{i+1}"), list)]
        if len(printed) < 2:
            continue
        n = min(len(p) for p in printed)
        slots = []
        for k in range(n):
            names = [p[k]["name"] for p in printed]
            counts = [max(1, len(p[k].get("parts") or [1])) for p in printed]
            read = [(sy["staves"][k].get("instrument")
                     or sy["staves"][k].get("instrument_label"))
                    for sy in systems if k < len(sy["staves"])]
            slots.append({"slot": k, "printed": names, "parts": counts,
                          "pipeline_read": read,
                          "same_instrument": len(set(names)) == 1,
                          "counts_agree": len(set(counts)) == 1})
        bad = [s for s in slots if not s["same_instrument"]]
        report[rid] = {"ordinal_join_succeeds": joined,
                       "system_sizes": [len(s["staves"]) for s in systems],
                       "misjoined_slots": len(bad), "slots": slots}

        flag = "MIS-JOINED" if (joined and bad) else ("refused" if not joined
                                                      else "clean")
        print(f"\n{rid}   sizes {[len(s['staves']) for s in systems]}   "
              f"ordinal join {'SUCCEEDS' if joined else 'refuses'}   -> {flag}")
        print(f"{'slot':>4} | {'printed sys1':<28} | {'printed sys2':<30} | "
              f"{'parts':>7} | pipeline read")
        for s in slots:
            mark = " " if s["same_instrument"] else "*"
            print(f"{s['slot']:>4}{mark}| {s['printed'][0]:<28} | "
                  f"{s['printed'][1]:<30} | {str(s['parts']):>7} | "
                  f"{' / '.join(str(r) for r in s['pipeline_read'])}")

    print("\n* = the ordinal slot holds a DIFFERENT printed instrument in the "
          "two systems.\n  Where the join SUCCEEDS, that music is grafted "
          "across parts and nothing reports it.")

    if args.json:
        dest = Path(args.json)
        if not dest.is_absolute():
            dest = Path(__file__).resolve().parent / dest
        dest.write_text(json.dumps(report, indent=2) + "\n")
        print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
