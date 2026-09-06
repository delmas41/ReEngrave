"""How big is the population BOTH the veto and the whole-work scorer act on blind?

`score_2x2.judgeable` scores a staff only on a system whose size equals its
region's printed lineup, because on a reduced system which parts were dropped is
a fact about the page. The 18 refusals all sit outside that population — but so
does everything else that happens there, including names that are wrong. This
counts the population and breaks the names down, so the 18 can be read against
the size of what is unscored rather than against the 807 that are.

Pure arithmetic on the composition harness's spans-on report blob.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOB = (ROOT.parent / "omr-spans-veto-composition-2026-09" / "out" /
        "whole-spans-on.json")
# score_2x2.LINEUPS, copied so this cannot drift from it silently.
REGIONS = [(0, 43, 12), (44, 200, 17)]


def lineup_size(page: int) -> int | None:
    for lo, hi, n in REGIONS:
        if lo <= page <= hi:
            return n
    return None


def main() -> None:
    blob = json.loads(BLOB.read_text())["contextual"]["absent_instrument_veto"]
    name_by_slot = {s["slot"]: s["instrument"] for s in blob["slot_instruments"]}
    src_by_slot = {s["slot"]: s["source"] for s in blob["slot_instruments"]}
    ev = collections.defaultdict(dict)
    for e in blob["label_evidence"]:
        ev[e["page_index"]][e["staff_index"]] = e["instrument"]
    vetoed = {(v["page_index"], v["system_index"], v["staff_index"])
              for v in blob["vetoes"]}
    by_system = collections.defaultdict(list)
    for s in blob["staff_slots"]:
        by_system[(s["page_index"], s["system_index"])].append(s)

    total = judgeable = 0
    unjudgeable_unlabelled = 0
    names = collections.Counter()
    vet_in = collections.Counter()
    for (page, _sys), staves in by_system.items():
        n = lineup_size(page)
        full = (n is not None and len(staves) == n)
        for s in staves:
            total += 1
            key = (s["page_index"], s["system_index"], s["staff_index"])
            if full:
                judgeable += 1
                vet_in["judgeable"] += key in vetoed
                continue
            vet_in["reduced"] += key in vetoed
            if ev[page].get(s["staff_index"]) is not None:
                continue
            unjudgeable_unlabelled += 1
            slot = s["slot"]
            if slot is not None and slot >= 0:
                names[(name_by_slot.get(slot, "?"),
                       src_by_slot.get(slot, "?"))] += 1
            else:
                names[("<no slot>", "-")] += 1

    print(f"staff records                              : {total}")
    print(f"  on FULL systems (judgeable by the scorer): {judgeable}")
    print(f"  on REDUCED systems                       : {total - judgeable}")
    print(f"    of those, carrying NO label of their own: "
          f"{unjudgeable_unlabelled}")
    print()
    print(f"refusals landing on a judgeable staff      : {vet_in['judgeable']}")
    print(f"refusals landing on a reduced system       : {vet_in['reduced']}")
    print()
    print("names given to an unlabelled staff on a reduced system:")
    for (name, src), c in names.most_common():
        print(f"  {c:5d}  {name:<14} (slot source: {src})")


if __name__ == "__main__":
    main()
