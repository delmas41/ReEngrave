#!/usr/bin/env python3
"""How much of the captured IMSLP instrumentation actually parses.

The parse RATE is the deliverable of this workstream, not the code, so it is
computed from the committed catalog rather than quoted from a session — re-run
it and the numbers regenerate.

    python3 benchmarks/omr-instrumentation-capture-2026-09/measure_parse_rate.py
    python3 .../measure_parse_rate.py --json out.json

Three different denominators, reported apart because they answer different
questions:

  coverage    works whose page states a roster at all
  fragment    of the comma-separated fragments in those rosters, how many
              resolved to an instrument or a section (the abstention rate is
              1 - this)
  work        works whose roster parsed COMPLETELY — the number that matters
              for a staff-identity join, since a roster missing a part joins
              wrong rather than not at all
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.library.score_library import load_catalog  # noqa: E402


def measure(catalog: dict) -> dict:
    works = catalog.get("works", {})
    facts = {w: e["instrumentation"] for w, e in works.items()
             if e.get("instrumentation")}

    with_roster = {w: f for w, f in facts.items() if f.get("dialect") != "empty"}
    parsed = unparsed = 0
    complete = partial = none_at_all = 0
    dialects: collections.Counter = collections.Counter()
    fields: collections.Counter = collections.Counter()
    instruments: collections.Counter = collections.Counter()
    sections: collections.Counter = collections.Counter()
    misses: collections.Counter = collections.Counter()
    depluralized = 0
    per_work = []

    for work_id, fact in sorted(with_roster.items()):
        n_ok, n_bad = len(fact["roster"]), len(fact["unparsed"])
        parsed += n_ok
        unparsed += n_bad
        dialects[fact["dialect"]] += 1
        fields[fact.get("roster_field") or "(none)"] += 1
        if n_ok and not n_bad:
            complete += 1
        elif n_ok:
            partial += 1
        else:
            none_at_all += 1
        for item in fact["roster"]:
            if item["kind"] == "instrument":
                instruments[item["instrument"]] += 1
                depluralized += bool(item.get("lexicon_depluralized"))
            else:
                sections[item["section"]] += 1
        for text in fact["unparsed"]:
            misses[text.strip().lower()[:60]] += 1
        per_work.append({
            "work_id": work_id,
            "dialect": fact["dialect"],
            "parse_rate": fact["parse_rate"],
            "parsed": n_ok,
            "unparsed": fact["unparsed"],
        })

    total = parsed + unparsed
    conflicts = [w for w, e in works.items() if e.get("instrumentation_conflict")]
    return {
        "works_recorded": len(facts),
        "works_with_a_roster": len(with_roster),
        "works_with_no_roster_stated": len(facts) - len(with_roster),
        "conflicted_work_ids": sorted(conflicts),
        "fragments_total": total,
        "fragments_parsed": parsed,
        "fragments_unparsed": unparsed,
        "fragment_parse_rate": round(parsed / total, 4) if total else None,
        "works_parsed_completely": complete,
        "works_parsed_partially": partial,
        "works_parsed_not_at_all": none_at_all,
        "work_complete_rate": round(complete / len(with_roster), 4) if with_roster else None,
        "dialects": dict(dialects),
        "roster_field": dict(fields),
        "instrument_items": sum(instruments.values()),
        "section_items": sum(sections.values()),
        "depluralized_items": depluralized,
        "distinct_instruments": len(instruments),
        "top_instruments": instruments.most_common(20),
        "sections": dict(sections),
        "top_unparsed": misses.most_common(30),
        "per_work": per_work,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    ap.add_argument("--catalog", type=Path)
    args = ap.parse_args()
    report = measure(load_catalog(args.catalog))

    print(f"works recorded            {report['works_recorded']}")
    print(f"  with a roster stated    {report['works_with_a_roster']}")
    print(f"  page states none        {report['works_with_no_roster_stated']}")
    print(f"dialects                  {report['dialects']}")
    print(f"roster field              {report['roster_field']}")
    print(f"\nfragments                 {report['fragments_total']}")
    print(f"  parsed                  {report['fragments_parsed']}  "
          f"({report['fragment_parse_rate']})")
    print(f"  abstained               {report['fragments_unparsed']}")
    print(f"  of parsed: instruments  {report['instrument_items']}  "
          f"sections {report['section_items']}  "
          f"(depluralized {report['depluralized_items']})")
    print(f"\nworks parsed completely   {report['works_parsed_completely']}  "
          f"({report['work_complete_rate']})")
    print(f"  partially               {report['works_parsed_partially']}")
    print(f"  not at all              {report['works_parsed_not_at_all']}")
    if report["conflicted_work_ids"]:
        print(f"\nwork_id collisions        {report['conflicted_work_ids']}")
    print("\ntop unparsed fragments")
    for text, n in report["top_unparsed"]:
        print(f"  {n:3d}  {text}")
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
