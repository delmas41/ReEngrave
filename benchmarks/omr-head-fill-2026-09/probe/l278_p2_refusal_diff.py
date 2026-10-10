"""ROADMAP 2.78 Phase 2 -- which notehead boxes were REFUSED or KEPT differently between two records.

PATH: STAGED, GATHER + ADJUDICATE only. BASE = a Phase 1 small-re-gather record (tree f027c8e7), ARM = a fresh
small re-gather on the final tree. Boxes are matched by `readout.match_glyphs` (box overlap, never by glyph index:
the detector's order is not guaranteed). Prints every notehead box whose ADJUDICATE status moved between
kept/narrowed/abstained and refused/given_away, with Sean's verdict on it where he judged that stem.

Sean's tiles that name a box as NOT a note (answers.json + DECISIONS 2026-10-09): 2, 3, 4, 6, 8, 14.
The whole-class box of tiles 5 and 9 is a note whose VALUE was wrong, not a refusal.

    python3 benchmarks/omr-head-fill-2026-09/probe/l278_p2_refusal_diff.py BASE.json ARM.json
"""
from __future__ import annotations

import collections
import json
import os
import sys

sys.path.insert(0, os.getcwd())

KEPT = ("kept", "narrowed", "abstained")


def main(argv=None):
    from tools.omr.staged import readout
    base, arm = readout.load_run(argv[0]), readout.load_run(argv[1])
    man = json.load(open("out/print/2.78-review/manifest.json"))
    judged = {}
    for t in man["tiles"]:
        for h in t["subject"]:
            judged[h] = t["n"]
    pairs, only_a, only_b = readout.match_glyphs(base, arm)
    print(f"matched glyph pairs {len(pairs)}  only in base {len(only_a)}  only in arm {len(only_b)}")
    moved = []
    n_notes = 0
    for ka, kb, _iou, _how in pairs:
        ga, gb = base.glyphs[ka], arm.glyphs[kb]
        if gb.family != "note":
            continue
        n_notes += 1
        sa, _ = readout.adjudicate_status(base, ga)
        sb, wb = readout.adjudicate_status(arm, gb)
        if (sa in KEPT) != (sb in KEPT):
            moved.append((ka, kb, sa, sb, wb[0] if wb else ""))
    print(f"notehead boxes matched {n_notes}; status moved between kept and refused/given_away: {len(moved)}")
    for ka, kb, sa, sb, why in moved:
        t = judged.get(ka) or judged.get(kb)
        print(f"   {ka:<22} -> {kb:<22} {sa} -> {sb}   {why[:90]}   {'Sean tile ' + str(t) if t else '(not among the 14)'}")
    cnt = collections.Counter()
    for ka, kb, _iou, _how in pairs:
        ga = base.glyphs[ka]
        if ga.family != "note":
            continue
        sa, _ = readout.adjudicate_status(base, ga)
        sb, _ = readout.adjudicate_status(arm, arm.glyphs[kb])
        cnt[(sa, sb)] += 1
    print("status transitions (base -> arm):", {f"{a}->{b}": n for (a, b), n in sorted(cnt.items()) if a != b})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
