#!/usr/bin/env python3
"""REACH FIRST — how many staves can each consumer of a roster even act on?

MEASUREMENT ONLY, and free: it reads the 20-row gate's STORED transcriptions and
never runs a detector. It answers, per row and pooled, the question
`probe_fill_reach.py` established has to come before any pricing:

    for each consumer, what is the population it can act on AT ALL,
    independently of how good the identity supplying it is?

Four consumers are in scope:

    IDENTITY      staves with no `instrument` today, or one the score-order
                  prior deduced rather than read. A roster can newly name these.
    PART NAMING   staves whose exported part name is a coordinate stub
                  (`Staff p1-s0-3`) rather than an instrument.
    CLEF FILL     staves with NO clef read (`clef_correction`'s FILL path is
                  `apply and not detected`).
    STITCH        rows where `_stitch_slots` REFUSES — several systems that do
                  not agree on staff count, so the exporter falls back to
                  per-system fragment parts.

    python3 benchmarks/omr-roster-wiring-2026-09/probe_consumer_reach.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

FIXTURES = Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
                "reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures")
TAG = "reconciliation"

# Clef sources that count as a clef actually READ off the page. The rest are
# join-derived and are exactly what the FILL path writes.
RAW_CLEF_SOURCES = {"detector", "detector_header", "specialist", "cv_locator"}


def rows():
    works = json.loads((REPO / "benchmarks/omr-scan-e2e-2026-09/works.json")
                       .read_text())
    return works["rows"]


def systems_of(doc):
    return [s for p in doc.get("pages", []) for s in p.get("systems", [])
            if s.get("staves")]


def main():
    from tools.omr.export import _stitch_slots, _stitch_slots_by_slot

    tot = Counter()
    per_row = []
    for row in rows():
        rid = row["row_id"]
        f = FIXTURES / f"{rid}.{TAG}.omr.json"
        if not f.exists():
            print(f"  MISSING {f}")
            continue
        doc = json.loads(f.read_text())
        systems = systems_of(doc)
        staves = [st for s in systems for st in s["staves"]]
        n = len(staves)

        named = sum(1 for st in staves if st.get("instrument"))
        by_src = Counter(st.get("instrument_source") for st in staves
                         if st.get("instrument"))
        unnamed = n - named
        derived = by_src.get("score_order", 0) + by_src.get(
            "score_order_ambiguity", 0)

        noclef = 0
        for st in staves:
            src = st.get("clef_source")
            if src not in RAW_CLEF_SOURCES:
                noclef += 1

        stitch = _stitch_slots(doc)
        by_slot = _stitch_slots_by_slot(doc)
        sizes = sorted({len(s["staves"]) for s in systems})

        slotted = sum(1 for st in staves if (st.get("slot_index") or -1) >= 0)

        per_row.append(dict(
            row_id=rid, n=n, n_systems=len(systems), sizes=sizes,
            named=named, unnamed=unnamed, derived=derived,
            noclef=noclef, slotted=slotted,
            stitch=("joined" if stitch is not None else "REFUSED"),
            by_slot=("available" if by_slot is not None else "-"),
            ctx=(doc.get("contextual") or {}).get("available"),
            ctx_reason=(doc.get("contextual") or {}).get("reason"),
        ))
        tot["n"] += n
        tot["named"] += named
        tot["unnamed"] += unnamed
        tot["derived"] += derived
        tot["noclef"] += noclef
        tot["slotted"] += slotted
        tot["rows"] += 1
        if stitch is None:
            tot["stitch_refused_rows"] += 1
            tot["stitch_refused_staves"] += n
        if stitch is None and by_slot is not None:
            tot["by_slot_rows"] += 1

    print(f"\n{'='*104}\nCONSUMER REACH — 20-row scan gate, stored `{TAG}` "
          f"transcriptions, no detector run\n{'='*104}")
    print(f"{'row':38s} {'stav':>4s} {'sys':>3s} {'sizes':>10s} {'named':>5s} "
          f"{'UNnam':>5s} {'deriv':>5s} {'NOCLEF':>6s} {'slot':>4s} "
          f"{'stitch':>8s} {'byslot':>9s}")
    for r in per_row:
        print(f"{r['row_id']:38s} {r['n']:4d} {r['n_systems']:3d} "
              f"{str(r['sizes']):>10s} {r['named']:5d} {r['unnamed']:5d} "
              f"{r['derived']:5d} {r['noclef']:6d} {r['slotted']:4d} "
              f"{r['stitch']:>8s} {r['by_slot']:>9s}")

    n = tot["n"]
    print(f"\n{'-'*104}")
    print(f"  POOLED over {tot['rows']} rows, {n} staves")
    print(f"    identity: named today {tot['named']:4d} ({tot['named']/n:.3f})"
          f"   UNNAMED {tot['unnamed']:4d} ({tot['unnamed']/n:.3f})"
          f"   of the named, DERIVED {tot['derived']:4d}")
    print(f"    → IDENTITY consumer reach (unnamed + derived) = "
          f"{tot['unnamed'] + tot['derived']:4d} "
          f"({(tot['unnamed'] + tot['derived'])/n:.3f})")
    print(f"    → PART-NAMING reach (staves exporting a coordinate stub) = "
          f"{tot['unnamed']:4d} ({tot['unnamed']/n:.3f})")
    print(f"    → CLEF-FILL reach (no clef read)            = "
          f"{tot['noclef']:4d} ({tot['noclef']/n:.3f})")
    print(f"    → STITCH reach: {tot['stitch_refused_rows']} of {tot['rows']} "
          f"rows refuse the ordinal join, "
          f"{tot['stitch_refused_staves']} staves; "
          f"{tot.get('by_slot_rows', 0)} of those have a complete slot join "
          f"available today")
    print(f"    staves carrying a slot_index: {tot['slotted']}/{n} "
          f"({tot['slotted']/n:.3f})")

    (HERE / "consumer-reach.json").write_text(
        json.dumps({"meta": {"tag": TAG, "fixtures": str(FIXTURES)},
                    "rows": per_row, "pooled": dict(tot)}, indent=1))
    print(f"\n  wrote {HERE/'consumer-reach.json'}")


if __name__ == "__main__":
    main()
