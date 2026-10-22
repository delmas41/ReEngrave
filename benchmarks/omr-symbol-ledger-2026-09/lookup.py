"""Look a symbol up by its address — *"the second quarter note of bar 3"*.

The ledger's whole point is that a symbol is a row you can find. This is the
finder. It reads `out/ledger-rows.csv` and filters on the address fields, so
any claim about a specific note can be checked against the account rather than
inferred from a bucket total.

    # everything the ledger says about bar 3 of the Violin on one page
    python3 benchmarks/omr-symbol-ledger-2026-09/lookup.py \\
        --row beethoven-sym5-mvt1-984073-p1 --part Violin --measure 3

    # the symbol at a beat, exactly
    python3 ... --row <row> --part "Violin 1" --measure 3 --beat 2

    # every note we were not able to correspond, and why
    python3 ... --outcome uncorresponded --family note --limit 20
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

BENCH = Path(__file__).resolve().parent
DEFAULT_CSV = BENCH / "out" / "ledger-rows.csv"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--row", default=None, help="scan-gate row id, substring match")
    ap.add_argument("--part", default=None, help="part name, substring match")
    ap.add_argument("--measure", type=int, default=None)
    ap.add_argument("--beat", type=float, default=None,
                    help="1-based, the way a musician counts: beat 2 is onset 1.0")
    ap.add_argument("--family", default=None)
    ap.add_argument("--outcome", default=None)
    ap.add_argument("--wrong", default=None, help="only rows whose attrs_wrong names this")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--count", action="store_true", help="tally instead of listing")
    a = ap.parse_args(argv)

    if not a.csv.is_file():
        print(f"no ledger at {a.csv} — run run_ledger.py first", file=sys.stderr)
        return 2

    hits = []
    with a.csv.open() as fh:
        for r in csv.DictReader(fh):
            if a.row and a.row not in r["row_id"]:
                continue
            if a.part and a.part.lower() not in (r["part_name"] or "").lower():
                continue
            if a.measure is not None and r["measure"] != str(a.measure):
                continue
            if a.beat is not None:
                try:
                    if abs(float(r["onset_ql"] or "nan") - (a.beat - 1.0)) > 1e-6:
                        continue
                except ValueError:
                    continue
            if a.family and r["family"] != a.family:
                continue
            if a.outcome and r["outcome"] != a.outcome:
                continue
            if a.wrong and a.wrong not in (r["attrs_wrong"] or ""):
                continue
            hits.append(r)

    if a.count:
        print(f"{len(hits)} rows")
        for key in ("outcome", "reason", "family", "attrs_wrong", "basis",
                    "basis_strength", "measure_map"):
            c = Counter(r.get(key) or "-" for r in hits)
            print(f"\n  by {key}")
            for k, v in c.most_common(12):
                print(f"    {k:<34}{v:>7}")
        return 0

    print(f"{len(hits)} rows" + (f" (showing {a.limit})" if len(hits) > a.limit else ""))
    for r in hits[:a.limit]:
        bits = [r["outcome"]]
        if r["reason"]:
            bits.append(f"({r['reason']})")
        if r["attrs_wrong"]:
            bits.append(f"wrong: {r['attrs_wrong']}")
        if r["basis"]:
            bits.append(f"basis {r['basis']}/{r['basis_strength']}")
        if r["measure_map"] != "verified":
            bits.append(f"measure-map {r['measure_map']}")
        print(f"  {r['description']:<52} {' '.join(bits)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
