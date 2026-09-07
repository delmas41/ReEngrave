"""How consistent is a FULL system's per-ordinal margin label, within one lineup?

The count-keyed boundary rule is silent about a swap. The candidate signal is
the printed names — but before a rule can fire on them, the NOISE has to be
measured: two full systems of the same lineup must agree, or a rule that splits
on disagreement splits everywhere.

A **full system** is one whose staff count equals the maximum system size over
the page range being considered — the same definition `score_full_systems.py`
grades on, and the same argument: a system carrying every staff the region has
IS that region's lineup, in printed order, so staff ordinal `i` names the same
instrument on every full system of one lineup.

So for each pair of full systems this reports, over the ordinals where BOTH
carry a matched label:

    agree     same canonical instrument name
    differ    different names  <- the swap signal, and the noise floor

    ordinal_agreement.py LABELS.json --lineups LINEUPS.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def full_systems(rows, first, last, size):
    """`[(page, system_index, [instrument|None per ordinal])]`.

    ⚠️ `StaffLabel.staff_index` counts across the PAGE, so the per-system
    window is `[offset, offset + size)` in staff ordinals.
    """
    out = []
    for r in rows:
        if not (first <= r["page"] <= last):
            continue
        by_staff = {l["staff_index"]: l["instrument"] for l in r["labels"]}
        offset = 0
        for si, n in enumerate(r["systems"]):
            if n == size:
                out.append((r["page"], si,
                            [by_staff.get(offset + k) for k in range(n)]))
            offset += n
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("labels")
    ap.add_argument("--lineups", required=True)
    args = ap.parse_args()

    rows = json.load(open(args.labels))
    lineups = json.load(open(args.lineups))

    systems = {}
    for row in lineups:
        systems[(row["first"], row["last"])] = full_systems(
            rows, row["first"], row["last"], row["size"])

    print("FULL SYSTEMS PER REGION")
    for row in lineups:
        k = (row["first"], row["last"])
        print(f"  pages {k[0]:3d}-{k[1]:3d} size {row['size']:2d}: "
              f"{len(systems[k]):3d} full systems")

    def compare(a, b):
        agree = differ = 0
        diffs = collections.Counter()
        for i, (x, y) in enumerate(zip(a, b)):
            if x is None or y is None:
                continue
            if x == y:
                agree += 1
            else:
                differ += 1
                diffs[(i, x, y)] += 1
        return agree, differ, diffs

    print("\nWITHIN A REGION — the noise floor")
    for row in lineups:
        k = (row["first"], row["last"])
        s = systems[k]
        agree = differ = 0
        worst = collections.Counter()
        pairs_with_diff = 0
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                a, d, dd = compare(s[i][2], s[j][2])
                agree += a
                differ += d
                worst += dd
                if d:
                    pairs_with_diff += 1
        n_pairs = len(s) * (len(s) - 1) // 2
        rate = differ / (agree + differ) if agree + differ else float("nan")
        print(f"  pages {k[0]:3d}-{k[1]:3d}: {n_pairs:4d} pairs, "
              f"{agree:5d} agree / {differ:4d} differ = {rate:.4f}; "
              f"{pairs_with_diff} pairs carry any disagreement")
        for (i, x, y), n in worst.most_common(6):
            print(f"       ordinal {i:2d}  {x} vs {y}  x{n}")

    print("\nACROSS REGIONS — the swap")
    ks = list(systems)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            a_sys, b_sys = systems[ks[i]], systems[ks[j]]
            if not a_sys or not b_sys:
                continue
            if len(a_sys[0][2]) != len(b_sys[0][2]):
                print(f"  {ks[i]} vs {ks[j]}: different sizes, "
                      "count-keyed rule already separates them")
                continue
            agree = differ = 0
            worst = collections.Counter()
            for x in a_sys:
                for y in b_sys:
                    ag, d, dd = compare(x[2], y[2])
                    agree += ag
                    differ += d
                    worst += dd
            rate = differ / (agree + differ) if agree + differ else float("nan")
            print(f"  {ks[i]} vs {ks[j]}: {agree} agree / {differ} differ "
                  f"= {rate:.4f}")
            for (o, x, y), n in worst.most_common(8):
                print(f"       ordinal {o:2d}  {x} vs {y}  x{n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
