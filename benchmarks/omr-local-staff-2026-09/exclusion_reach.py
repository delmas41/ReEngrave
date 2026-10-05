#!/usr/bin/env python3
"""lane-ledger-exclusion: REACH before accuracy.  For each rule, on how many of
the 55 heads does it fire at all (a box dropped / a row kept / blanking
prevented), and where.  A rule that fires on none is DEAD, not clean.

    python3 exclusion_reach.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import edge_census as ec  # noqa: E402
import score_exclusion as se  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

KEPT = []          # (row abs y, box) every time the one-sided test says "ledger"
_orig = lg._thin_flat_one_sided_jut


def _spy(ink, x0, yy0, img_gray, thr, abs_y, tx0, tx1, spacing):
    r = _orig(ink, x0, yy0, img_gray, thr, abs_y, tx0, tx1, spacing)
    if r:
        KEPT.append((abs_y, tx0, tx1))
    return r


def main():
    lg._thin_flat_one_sided_jut = _spy
    heads = {d: ec.load_heads(d) for d in ts.DOCS}
    n_drop = n_keep = 0
    for d, hs in heads.items():
        for h in hs:
            base = lg.exclusion_boxes_for(h["subject"], h["box"], h["boxes"], h["acc"])
            dropped = lg.exclusion_boxes_for(h["subject"], h["box"], h["boxes"], h["acc"],
                                             drop_same_ink_other_staff=True)
            if len(base) != len(dropped):
                n_drop += 1
                gone = [b for b in base if b not in dropped]
                print(f"same: {d[:8]} {h['subject']:18} drops {len(base) - len(dropped)} box(es) {[[round(v) for v in b] for b in gone]}")
            KEPT.clear()
            se.read(h, **se.RULES["one"])
            rows = sorted({(k[0], k[1], k[2]) for k in KEPT})
            if rows:
                n_keep += 1
                ys = sorted({r[0] for r in rows})
                print(f"one:  {d[:8]} {h['subject']:18} keeps rows {ys[0]}..{ys[-1]} ({len(ys)} rows) of box x {sorted({(r[1], r[2]) for r in rows})}")
    print(f"\nREACH  same: {n_drop} of 55 heads;  one: {n_keep} of 55 heads")


if __name__ == "__main__":
    main()
