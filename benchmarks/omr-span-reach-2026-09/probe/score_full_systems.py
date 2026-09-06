"""correct / wrong / unnamed on FULL systems, against a hand-read lineup.

The argument is `score_2x2.judgeable`'s, unchanged: a system carrying every
staff its region has needs no page-by-page reading, because nothing can be
added to a full lineup — so a system of exactly N staves inside a page range
whose lineup is N IS that lineup, in printed order.

    score_full_systems.py OFF.json ON.json --lineups LINEUPS.json

LINEUPS.json: [{"first": 0, "last": 26, "size": 10, "lineup": [...],
                "read_off": "page 20, out/crops/p020_margin.png"}]

⚠️ Only regions whose lineup was READ BY EYE belong in that file. A region
scored against an inferred lineup would be scoring the pipeline against itself.
"""
from __future__ import annotations

import argparse
import collections
import json


def load(path):
    b = json.load(open(path))["contextual"]["absent_instrument_veto"]
    return ({(s["page_index"], s["system_index"], s["staff_index"]): s["slot"]
             for s in b["staff_slots"]},
            {s["slot"]: s["instrument"] for s in b["slot_instruments"]},
            {(v["page_index"], v["system_index"], v["staff_index"])
             for v in b["vetoes"]})


def names(slots, by_slot, vetoed, veto_on):
    return {k: (None if (veto_on and k in vetoed)
                else (by_slot.get(s) if s >= 0 else None))
            for k, s in slots.items()}


def truth(keys, lineups):
    by_system: dict[tuple[int, int], list[int]] = {}
    for p, sy, st in keys:
        by_system.setdefault((p, sy), []).append(st)
    out = {}
    for (p, sy), staves in by_system.items():
        for row in lineups:
            if (row["first"] <= p <= row["last"]
                    and len(staves) == row["size"]):
                for pos, st in enumerate(sorted(staves)):
                    out[(p, sy, st)] = row["lineup"][pos]
                break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spans_off")
    ap.add_argument("spans_on")
    ap.add_argument("--lineups", required=True)
    args = ap.parse_args()

    lineups = json.load(open(args.lineups))
    so, no_, vo = load(args.spans_off)
    sn, nn, vn = load(args.spans_on)
    if set(so) != set(sn):
        raise SystemExit("REFUSING: arms saw different staff records")
    t = truth(list(so), lineups)
    print(f"judgeable staves on full systems: {len(t)} of {len(so)} "
          f"({len({(k[0], k[1]) for k in t})} systems)")
    for row in lineups:
        n = len({(k[0], k[1]) for k in t
                 if row["first"] <= k[0] <= row["last"]})
        print(f"  pages {row['first']}-{row['last']} size {row['size']}: "
              f"{n} systems  (lineup read off {row['read_off']})")

    print(f"\n{'arm':24s} {'correct':>8s} {'wrong':>7s} {'unnamed':>8s}")
    cells = {}
    for stag, (s, b, v) in (("spans-off", (so, no_, vo)),
                            ("spans-on", (sn, nn, vn))):
        for vtag, von in (("veto-off", False), ("veto-on", True)):
            em = names(s, b, v, von)
            c = w = u = 0
            wrongs = collections.Counter()
            for k, want in t.items():
                got = em.get(k)
                if got is None:
                    u += 1
                elif got == want:
                    c += 1
                else:
                    w += 1
                    wrongs[(want, got)] += 1
            cells[(stag, vtag)] = (c, w, u, wrongs)
            print(f"  {stag:10s} {vtag:9s} {c:8d} {w:7d} {u:8d}")

    for tag, (c, w, u, wrongs) in cells.items():
        if not w:
            continue
        print(f"\n  {tag[0]} / {tag[1]} — wrong, (printed -> emitted):")
        for (want, got), n in wrongs.most_common(12):
            print(f"     {n:5d}  {want:14s} -> {got}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
