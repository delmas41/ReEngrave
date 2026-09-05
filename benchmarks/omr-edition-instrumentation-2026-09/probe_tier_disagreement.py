#!/usr/bin/env python3
"""How often do the two instrumentation tiers disagree, and about WHAT?

Offline and recomputable — it reads the committed catalog and nothing else, so
it can be re-run after the parser or the comparison rule changes without
touching IMSLP or a single PDF.

    python3 benchmarks/omr-edition-instrumentation-2026-09/probe_tier_disagreement.py
    python3 ... --verdict edition_missing --limit 40     # the rows, for a human

⚠️ **THE HEADLINE IS THE MIX, NOT THE RATE.**  "Work says 12, edition reads 8"
is three findings wearing one shape — a genuine editorial variant, a
condensation, or a failed read — and a single disagreement percentage says which
of them nothing at all.  The report therefore splits every disagreement by the
read's own yield and by the edition's ``score_type``, and prints the rows so
they can be adjudicated by hand.  The hand adjudication is in FINDINGS.md; this
script produces its input, never its conclusion.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from tools.library import edition_instrumentation as ed  # noqa: E402
from tools.library.score_library import CATALOG_PATH, load_catalog  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    ap.add_argument("--verdict", help="print the rows with this verdict")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", type=Path, default=HERE / "tier-disagreement.json")
    args = ap.parse_args()

    catalog = load_catalog(args.catalog)
    editions = catalog.get("editions", {})
    rows = ed.compare_catalog(catalog)
    n = len(rows)
    if not n:
        print("no edition facts in the catalog — run "
              "`python3 -m tools.library.edition_instrumentation --acquire` first")
        return 2

    print(f"{'='*74}\nWORK TIER vs EDITION TIER — {n} held editions\n{'='*74}")

    verdicts = Counter(r["verdict"] for r in rows)
    for verdict, count in verdicts.most_common():
        print(f"  {verdict:22s} {count:4d}  {count/n:6.3f}  {'#'*int(46*count/n)}")

    comparable = [r for r in rows
                  if r["verdict"] not in ("no_work_roster", "no_edition_roster")]
    print(f"\n  comparable (both tiers present)   {len(comparable):4d}"
          f"  ({len(comparable)/n:.3f})")
    if comparable:
        agree = sum(1 for r in comparable if r["verdict"] == "agrees")
        print(f"  of those, AGREE                   {agree:4d}"
              f"  ({agree/len(comparable):.3f})")

    print("\n  ⚠️ SHORTFALLS SPLIT BY THE READ'S OWN YIELD — this is the split "
          "that\n     separates 'our reader missed it' from 'this printing may "
          "not have it':")
    split = Counter(r.get("missing_explained_by") for r in comparable
                    if r.get("missing_explained_by"))
    for key, count in split.most_common():
        print(f"    {key:20s} {count:4d}")

    print("\n  BY SCORE TYPE (an arrangement is a KIND of edition, not an error):")
    by_type = defaultdict(Counter)
    for row in rows:
        by_type[editions[row["path"]]["instrumentation"]["score_type"]][
            row["verdict"]] += 1
    for score_type, counter in sorted(by_type.items(),
                                      key=lambda kv: -sum(kv[1].values())):
        total = sum(counter.values())
        print(f"    {score_type:12s} {total:4d}   " +
              "  ".join(f"{v}={c}" for v, c in counter.most_common()))

    print("\n  WHAT THE EDITION NAMES AND THE WORK DOES NOT (top 15) — as much a\n"
          "  work-tier LEXICON GAP as an editorial variant:")
    extra = Counter(name for r in comparable for name in r["edition_extra"])
    for name, count in extra.most_common(15):
        print(f"    {name:22s} {count:4d}")

    print("\n  WHAT THE WORK NAMES AND THE PAGE DOES NOT (top 15):")
    missing = Counter(name for r in comparable for name in r["edition_missing"])
    for name, count in missing.most_common(15):
        print(f"    {name:22s} {count:4d}")

    print("\n  EDITION-QUALITY INDEX (nothing else in the project holds one):")
    q = [editions[r["path"]]["instrumentation"]["quality"] for r in rows]
    got = [x for x in q if x["acquired"]]
    print(f"    labels its staves                 {len(got):4d}/{n}"
          f"  ({len(got)/n:.3f})")
    if got:
        buckets = Counter()
        for x in got:
            y = x["yield"] or 0.0
            buckets["1.00" if y >= 0.999 else "0.75-0.99" if y >= .75
                    else "0.50-0.74"] += 1
        for b in ("1.00", "0.75-0.99", "0.50-0.74"):
            print(f"      yield {b:10s}              {buckets.get(b,0):4d}")
        late = sum(1 for x in got if x["roster_page"] not in (0, 1, 2))
        print(f"    roster only past page 2           {late:4d}"
              f"  — 'page 1' is the wrong unit")

    if args.verdict:
        print(f"\n{'='*74}\nROWS: {args.verdict}\n{'='*74}")
        picked = [r for r in rows if r["verdict"] == args.verdict]
        for row in picked[: args.limit or len(picked)]:
            print(f"\n  {row['work_id']}  ({row['path'].split('/')[-1][:70]})")
            print(f"    jaccard {row.get('jaccard')}  yield "
                  f"{row.get('edition_yield')}  {row.get('score_type')}"
                  f"  {row.get('missing_explained_by','')}")
            if row.get("edition_extra"):
                print(f"    page only: {', '.join(row['edition_extra'])}")
            if row.get("edition_missing"):
                print(f"    work only: {', '.join(row['edition_missing'])}")

    args.out.write_text(json.dumps({"n": n, "verdicts": dict(verdicts),
                                    "rows": rows}, indent=1) + "\n")
    print(f"\n  wrote {args.out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
