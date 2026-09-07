#!/usr/bin/env python3
"""Second route to the denominator: probe staff counts vs `scan_eval`'s own.

The probe walks `pages -> systems -> staves` itself. `scan_eval` counts the same
staves independently while building its results table
(`entry["detected"]["staves"]`) and writes them to its results JSON. If the two
disagree, the probe is not looking at the staves the gate thinks it ran on, and
every per-staff figure below it is wrong by that amount.

Keyed differently on purpose: one is a fresh walk of the fixture, the other is a
number the harness computed at transcription time and stored. Every finding
corrected on this project this week was caught by two columns keyed differently
disagreeing.

Exits non-zero on a missing input, an empty join, or ANY disagreement.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: crosscheck_staff_counts.py PROBE.json SCAN_EVAL_RESULTS.json",
              file=sys.stderr)
        return 2
    probe_p, scan_p = Path(argv[1]), Path(argv[2])
    for p in (probe_p, scan_p):
        if not p.is_file():
            print(f"REFUSED: missing {p}", file=sys.stderr)
            return 2
    probe = json.loads(probe_p.read_text())
    scan = json.loads(scan_p.read_text())

    # scan_eval writes its per-row list under "rows"; older arms used
    # "results". Try both, then let the guards below refuse an empty join —
    # reading the wrong key must REFUSE, not report agreement.
    if isinstance(scan, dict):
        scan_rows = scan.get("rows") or scan.get("results")
    else:
        scan_rows = scan
    if not scan_rows:
        print("REFUSED: no rows in the scan_eval results", file=sys.stderr)
        return 2
    # scan_eval stamps the arm tag into row_id; the probe strips it.
    by_row: dict[str, int] = {}
    for r in scan_rows:
        rid = str(r.get("row_id", "")).split(".")[0]
        det = (r.get("detected") or {}).get("staves")
        if det is not None:
            by_row[rid] = det
    if not by_row:
        print("REFUSED: no detected.staves in the scan_eval results",
              file=sys.stderr)
        return 2

    bad, joined = [], 0
    for row in probe["rows"]:
        rid = row["row_id"]
        if rid not in by_row:
            bad.append((rid, row["staves"], "NOT IN scan_eval"))
            continue
        joined += 1
        if by_row[rid] != row["staves"]:
            bad.append((rid, row["staves"], by_row[rid]))
    if joined == 0:
        print("REFUSED: the two files share no row — an empty join, which is "
              "NOT agreement", file=sys.stderr)
        return 2

    print(f"joined {joined} rows")
    for rid, mine, theirs in bad:
        print(f"  DISAGREE {rid}: probe {mine}, scan_eval {theirs}")
    if bad:
        print(f"FAIL: {len(bad)} disagreement(s)", file=sys.stderr)
        return 1
    total = sum(row["staves"] for row in probe["rows"])
    print(f"OK: probe and scan_eval agree on every row; {total} staves total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
