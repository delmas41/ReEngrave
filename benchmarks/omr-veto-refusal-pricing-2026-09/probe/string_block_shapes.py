"""Which string slots does the alignment use, system by system?

Four of the eighteen refusals removed a WRONG name, and all four come from ONE
shape: a bottom block of four staves aligned onto slots 13-16 instead of
12,13,14,16 — the DP deleted the Violin I slot where the page had condensed
Violoncello and Basso onto one staff (or the detector missed the Cello staff).
This counts how often each shape occurs, so the shape can be read as systematic
or as a pair of accidents.

Reference slots 12-16 are Violin, Violin, Viola, Cello, Contrabass.
Arithmetic on the composition harness's spans-on report blob; no run.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOB = (ROOT.parent / "omr-spans-veto-composition-2026-09" / "out" /
        "whole-spans-on.json")
STRING_SLOTS = {12, 13, 14, 15, 16}
NAME = {12: "Vn", 13: "Vn", 14: "Va", 15: "Vc", 16: "Cb"}


def main() -> None:
    blob = json.loads(BLOB.read_text())["contextual"]["absent_instrument_veto"]
    by_system = collections.defaultdict(list)
    for s in blob["staff_slots"]:
        by_system[(s["page_index"], s["system_index"])].append(s)
    vetoed = {(v["page_index"], v["system_index"], v["staff_index"])
              for v in blob["vetoes"]}

    shapes = collections.Counter()
    shapes_with_veto = collections.Counter()
    for (page, sysi), staves in sorted(by_system.items()):
        if page < 44:
            continue                      # the finale's 17-slot reference only
        used = tuple(sorted(s["slot"] for s in staves
                            if s["slot"] in STRING_SLOTS))
        if not used:
            continue
        shapes[used] += 1
        if any((page, sysi, s["staff_index"]) in vetoed for s in staves):
            shapes_with_veto[used] += 1

    print("finale systems by the string slots their bottom block took")
    print(f"{'slots':<24} {'systems':>7} {'with a refusal':>15}")
    for used, n in sorted(shapes.items(), key=lambda kv: -kv[1]):
        pretty = ",".join(f"{s}{NAME[s]}" for s in used)
        print(f"{pretty:<24} {n:>7} {shapes_with_veto[used]:>15}")
    four = {u: n for u, n in shapes.items() if len(u) == 4}
    print()
    print("blocks of exactly FOUR string staves — which slot was deleted:")
    for used, n in sorted(four.items(), key=lambda kv: -kv[1]):
        missing = sorted(STRING_SLOTS - set(used))
        print(f"  deleted slot {missing[0]} ({NAME[missing[0]]}): {n} systems"
              f"   [{','.join(str(s) for s in used)}]")


if __name__ == "__main__":
    main()
