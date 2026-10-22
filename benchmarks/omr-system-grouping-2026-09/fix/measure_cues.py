"""Decisive separation measurement for cue A (systemic-barline column).

For every gap on every page, print cue-A (left_barline) split into TRUE-BREAK
vs INTERIOR. If any interior gap on a control dips into the true-break range,
the cue is dead — exactly how attempts 1-5 died (they separated on Beethoven and
collapsed on Mahler/La Mer/Boléro, whose barlines break between families).

Usage:
  python3 measure_cues.py [--sweep] [--left LEFT_SP] [--right RIGHT_SP]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _harness as H
import system_start_detector as D


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--left", type=float, default=1.5)
    ap.add_argument("--right", type=float, default=1.5)
    args = ap.parse_args()

    cases = H.all_cases(include_sweep=args.sweep)
    brk_vals, int_vals = [], []
    brk_rows, int_rows = [], []
    per_page = []
    for case in cases:
        L = H.load(case)
        gm = D.measure_page(L, left_sp=args.left, right_sp=args.right)
        page_brk = []
        page_int = []
        for m in gm:
            row = (case.cid, m.i, m.left_barline, m.wide_bridging, m.gap_px)
            if m.is_gt_break:
                brk_vals.append(m.left_barline); brk_rows.append(row); page_brk.append(m.left_barline)
            else:
                int_vals.append(m.left_barline); int_rows.append(row); page_int.append(m.left_barline)
        per_page.append((case, page_brk, page_int))

    def stats(v):
        v = sorted(v)
        n = len(v)
        if not n:
            return "n=0"
        return (f"n={n:3d} min={v[0]:4d} p05={v[max(0,n//20)]:4d} "
                f"med={v[n//2]:4d} p95={v[min(n-1,19*n//20)]:4d} max={v[-1]:4d}")

    print(f"cue A = left_barline crossing, band [x_start-{args.left}sp, x_start+{args.right}sp]")
    print(f"TRUE BREAKS   {stats(brk_vals)}")
    print(f"INTERIOR      {stats(int_vals)}")
    print()

    # The separation question: is there a threshold T such that
    #   break  <= T  and  interior > T   for EVERY gap?
    if brk_vals and int_vals:
        max_break = max(brk_vals)
        min_interior = min(int_vals)
        print(f"max(true-break) = {max_break}    min(interior) = {min_interior}")
        if max_break < min_interior:
            print(f"  SEPARABLE: any threshold in [{max_break}, {min_interior}) works "
                  f"(e.g. break if left_barline <= {max_break}).")
        else:
            print(f"  NOT SEPARABLE by a global threshold — overlap region "
                  f"[{min_interior}, {max_break}].")
        print()

    # Show the worst offenders: interior gaps with the LOWEST cue-A (closest to
    # looking like a break) and true breaks with the HIGHEST (closest to looking
    # interior).
    print("interior gaps with LOWEST left_barline (false-positive risk):")
    for cid, i, lb, wb, gp in sorted(int_rows, key=lambda r: r[2])[:15]:
        print(f"   {cid:14s} gap {i:2d}  left_barline={lb:4d}  wide={wb:4d}  gap_px={gp}")
    print("\ntrue breaks with HIGHEST left_barline (false-negative risk):")
    for cid, i, lb, wb, gp in sorted(brk_rows, key=lambda r: -r[2])[:10]:
        print(f"   {cid:14s} gap {i:2d}  left_barline={lb:4d}  wide={wb:4d}  gap_px={gp}")

    # Per-page min-interior vs max-break margin (the page-local separation).
    print("\nper-page separation (max true-break cueA  <  min interior cueA ?):")
    worst = []
    for case, pb, pi in per_page:
        mb = max(pb) if pb else None
        mi = min(pi) if pi else None
        ok = (mb is None) or (mi is None) or (mb < mi)
        worst.append((case.cid, mb, mi, ok))
    for cid, mb, mi, ok in worst:
        flag = "" if ok else "  <-- OVERLAP"
        print(f"   {cid:14s} max_break={str(mb):>4}  min_interior={str(mi):>4}  {'ok' if ok else 'BAD'}{flag}")


if __name__ == "__main__":
    main()
