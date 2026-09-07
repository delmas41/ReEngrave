"""correct / wrong / unnamed per arm, per REGION, against a hand-read lineup.

`score_full_systems.py` grades exactly two arms and pools the regions; a swap
lives inside one region and is invisible in a pooled total, so this grades any
number of arms and prints the per-region split beside the total.

The judgeability rule is unchanged and is `score_full_systems.py`'s: only FULL
systems (staff count == the region's own lineup size), because a system
carrying every staff its region has IS that lineup, in printed order.

    score_arms.py --lineups L.json TAG=ARM.json [TAG=ARM.json ...]
"""
from __future__ import annotations

import argparse
import collections
import json


def load(path):
    b = json.load(open(path))["contextual"]["absent_instrument_veto"]
    slots = {(s["page_index"], s["system_index"], s["staff_index"]): s["slot"]
             for s in b["staff_slots"]}
    by_slot = {s["slot"]: s["instrument"] for s in b["slot_instruments"]}
    return {k: (by_slot.get(v) if v >= 0 else None) for k, v in slots.items()}


def truth(keys, lineups):
    by_system: dict[tuple[int, int], list[int]] = {}
    for p, sy, st in keys:
        by_system.setdefault((p, sy), []).append(st)
    out, region = {}, {}
    for (p, sy), staves in by_system.items():
        for i, row in enumerate(lineups):
            if row["first"] <= p <= row["last"] and len(staves) == row["size"]:
                for pos, st in enumerate(sorted(staves)):
                    out[(p, sy, st)] = row["lineup"][pos]
                    region[(p, sy, st)] = i
                break
    return out, region


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lineups", required=True)
    ap.add_argument("arms", nargs="+", help="TAG=PATH")
    args = ap.parse_args()

    lineups = json.load(open(args.lineups))
    arms = {}
    for spec in args.arms:
        tag, path = spec.split("=", 1)
        arms[tag] = load(path)
    keysets = {frozenset(v) for v in arms.values()}
    if len(keysets) != 1:
        raise SystemExit("REFUSING: arms saw different staff records")

    t, region = truth(list(next(iter(arms.values()))), lineups)
    print(f"judgeable staves on full systems: {len(t)}\n")

    hdr = f"{'arm':26s}" + "".join(
        f"{'r' + str(i) + ' c/w/u':>16s}" for i in range(len(lineups)))
    print(hdr + f"{'TOTAL c/w/u':>18s}")
    detail = {}
    for tag, em in arms.items():
        per = collections.defaultdict(lambda: [0, 0, 0])
        wrongs = collections.Counter()
        for k, want in t.items():
            got = em.get(k)
            i = 2 if got is None else (0 if got == want else 1)
            per[region[k]][i] += 1
            per["all"][i] += 1
            if i == 1:
                wrongs[(region[k], want, got)] += 1
        row = f"{tag:26s}"
        for i in range(len(lineups)):
            c, w, u = per[i]
            row += f"{c:5d}/{w:4d}/{u:4d}"
        c, w, u = per["all"]
        print(row + f"  {c:5d}/{w:4d}/{u:4d}")
        detail[tag] = wrongs

    for tag, wrongs in detail.items():
        print(f"\n{tag} — wrong (region: printed -> emitted):")
        for (i, want, got), n in wrongs.most_common(10):
            print(f"   r{i}  {n:4d}  {want:14s} -> {got}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
