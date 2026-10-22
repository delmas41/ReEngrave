"""Which staves' own margin label disagrees with the name they are exported as.

Free evidence — no truth file, no adjudication — and the veto-pricing session
named it as reported-not-built. Used here as the COST column the `impossible`
count cannot serve as: `impossible` can only fall, so a fix that trades a
categorically-wrong name for an ordinarily-wrong one looks free to it.

Usage: diff_contradictions.py A.json B.json
"""
from __future__ import annotations

import collections
import json
import sys


def contradictions(path):
    b = json.load(open(path))["contextual"]["absent_instrument_veto"]
    slot = {(s["page_index"], s["system_index"], s["staff_index"]): s["slot"]
            for s in b["staff_slots"]}
    name = {s["slot"]: s["instrument"] for s in b["slot_instruments"]}
    ev = collections.defaultdict(dict)
    for e in b["label_evidence"]:
        ev[e["page_index"]][e["staff_index"]] = e["instrument"]
    out = {}
    for k, s in slot.items():
        nm = name.get(s) if s >= 0 else None
        own = ev.get(k[0], {}).get(k[2])
        if own and nm and own != nm:
            out[k] = (own, nm)
    return out


def main():
    a, b = sys.argv[1], sys.argv[2]
    A, B = contradictions(a), contradictions(b)
    for tag, m in ((a, A), (b, B)):
        print(f"{tag}: {len(m)} contradictions "
              f"{collections.Counter(f'{x}->{y}' for x, y in m.values()).most_common()}")
    print(f"\nonly in B ({b}):")
    for k in sorted(set(B) - set(A)):
        print(f"   p{k[0]} sy{k[1]} st{k[2]}  {B[k][0]} -> {B[k][1]}")
    print(f"only in A ({a}):")
    for k in sorted(set(A) - set(B)):
        print(f"   p{k[0]} sy{k[1]} st{k[2]}  {A[k][0]} -> {A[k][1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
