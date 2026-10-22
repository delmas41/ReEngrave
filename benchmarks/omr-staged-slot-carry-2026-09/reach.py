#!/usr/bin/env python3
"""What would a cross-system SLOT CARRY be worth on the STAGED path?

⚠️⚠️ THE GAP, from `benchmarks/omr-roster-truncation-reprice-2026-09`: the
LEGACY path stamps one instrument name per SLOT onto every staff of that slot
on every page (`contextual.py:1527`); the STAGED path has no equivalent, because
`adjudicate_instrument` is `Kind.STAFF` reading `Q.MARGIN_LABEL` at default
`Scope.EXACT`. That is a SIXTH instance of *"shipped means the LEGACY path"*.

**REACH BEFORE ACCURACY.** This counts, from a committed record and nothing
else, how many unnamed staff-systems sit at a slot another system DOES name --
which is the most a carry could ever reach. It does NOT say a carry would be
RIGHT: two systems can print different lineups at the same ordinal, which is
exactly the graft `_slots_are_ordinals` refuses and this project has paid for.

⚠️ The funnel is reported in full, because the interesting number is where it
STOPS: a staff with no name usually has no SLOT either, and a carry keyed on a
slot nobody could assign reaches nothing.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def system_of(subject: str):
    """`staff/<page>/<system>/<staff>` -> (page, system); None otherwise."""
    p = subject.split("/")
    return (p[1], p[2]) if len(p) == 4 and p[0] == "staff" else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", required=True)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    data = json.loads(Path(args.run).read_text())
    if "record" not in data:
        raise KeyError(f"{args.run} has no 'record' key; refusing to guess.")
    rec = data["record"]

    slot, inst = {}, {}
    slot_reason, inst_reason = {}, {}
    for v in rec["verdicts"]:
        q, s = v.get("quantity"), v.get("subject", "")
        if system_of(s) is None:
            continue
        if q == "slot_index":
            slot[s] = v.get("value")
            slot_reason[s] = v.get("reason")
        elif q == "instrument":
            val = v.get("value")
            inst[s] = (val or {}).get("name") if isinstance(val, dict) else None
            inst_reason[s] = v.get("reason")

    staves = sorted(set(slot) | set(inst))
    if not staves:
        print("DEAD: no staff-scoped slot_index or instrument verdict.",
              file=sys.stderr)
        return 2

    named = {s for s in staves if inst.get(s)}
    unnamed = [s for s in staves if not inst.get(s)]

    # what each SLOT is called, from the staves that DO name one
    by_slot = collections.defaultdict(collections.Counter)
    for s in named:
        if slot.get(s) is not None:
            by_slot[slot[s]][inst[s]] += 1

    funnel = collections.Counter()
    reachable, blocked_no_slot, blocked_slot_unnamed, contested = [], [], [], []
    for s in unnamed:
        funnel["unnamed staff-systems"] += 1
        sl = slot.get(s)
        if sl is None:
            funnel["  ...and NO SLOT either -- a carry has no key"] += 1
            blocked_no_slot.append(s)
            continue
        names = by_slot.get(sl)
        if not names:
            funnel["  ...slot known, but NO system names that slot"] += 1
            blocked_slot_unnamed.append(s)
            continue
        if len(names) > 1:
            funnel["  ...slot named DIFFERENTLY by different systems"] += 1
            contested.append((s, dict(names)))
            continue
        funnel["  ...REACHABLE: one unambiguous name at that slot"] += 1
        reachable.append((s, next(iter(names))))

    print(f"record      : {args.run}")
    print(f"staff-systems with an identity verdict : {len(staves)}")
    print(f"  NAMED   : {len(named)}   "
          f"{dict(collections.Counter(inst_reason[s] for s in named))}")
    print(f"  UNNAMED : {len(unnamed)} "
          f"{dict(collections.Counter(inst_reason.get(s) for s in unnamed))}")
    print(f"  slot_index reasons on the UNNAMED: "
          f"{dict(collections.Counter(slot_reason.get(s) for s in unnamed))}\n")
    print("THE FUNNEL -- where a cross-system slot carry stops:")
    for k, n in funnel.most_common():
        print(f"   {n:4d}  {k}")

    if reachable:
        print("\n   the reachable ones, and what a carry would call them:")
        for s, name in reachable[:12]:
            print(f"      {s:18} -> {name}")
        if len(reachable) > 12:
            print(f"      ... and {len(reachable) - 12} more")
    if contested:
        print("\n   ⚠️ CONTESTED slots -- a carry here would GRAFT:")
        for s, names in contested[:8]:
            print(f"      {s:18} slot {slot[s]} is {names}")

    out = {"staves": len(staves), "named": len(named),
           "unnamed": len(unnamed), "funnel": dict(funnel),
           "reachable": [{"subject": s, "would_be_named": n}
                         for s, n in reachable],
           "contested": [{"subject": s, "names": n} for s, n in contested]}
    if args.json_out:
        args.json_out.write_text(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
