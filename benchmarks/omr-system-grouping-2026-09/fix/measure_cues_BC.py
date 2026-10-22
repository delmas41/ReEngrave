"""Measure the two NAMED cues from the task spec, honestly, and test whether
either recovers the one failure cue A misses (B9-p25).

Cue C (bracket restart): bracket ink crossing a gap LEFT of x_start. Prediction
from attempt-4 + publisher-conventions: brackets are per-FAMILY, so they do NOT
cross either a family boundary OR a system boundary -> 0 at both -> no precision.

Cue B (clef-header column): per-staff clef-sized cluster just right of x_start.
Prediction: EVERY staff carries a clef at the system's left edge (all staves of
both stacked systems share the same header x), so presence is uniform and cannot
locate a stacked-system break.
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _harness as H
import system_start_detector as D


def cueC_separation():
    print("=" * 70)
    print("CUE C — bracket-column crossing (left of x_start), per gap")
    brk, inter = [], []
    for case in H.all_cases(include_sweep=True):
        if case.kind == "control" or case.kind in ("failure", "discovered_overmerge"):
            L = H.load(case)
            for i in range(len(L.staves) - 1):
                v = D.bracket_column_present(L.binary, L.staves, i)
                (brk if i in L.gt_breaks else inter).append(v)
    def st(v):
        v = sorted(x for x in v if x >= 0); n = len(v)
        return f"n={n:3d} min={v[0]} p50={v[n//2]} p95={v[min(n-1,19*n//20)]} max={v[-1]}" if n else "n=0"
    print(f"  TRUE BREAKS  {st(brk)}")
    print(f"  INTERIOR     {st(inter)}")
    print("  -> if both minima are 0 and ranges overlap, cue C cannot separate "
          "(confirms attempt-4: perfect recall, no precision).")


def cueB_separation():
    print("=" * 70)
    print("CUE B — clef-header cluster presence per staff, and at gap boundaries")
    # Per staff: does it carry a header cluster? Fraction of staves with one.
    have = 0; total = 0
    # At each gap: do BOTH staves carry a cluster? (a stacked-system break has
    # clusters on both sides, same as an interior gap -> uniform)
    brk_both, int_both = [], []
    for case in H.all_cases(include_sweep=True):
        L = H.load(case)
        flags = [D.header_cluster_x(L.binary, L.staves, s)[0] for s in L.staves]
        have += sum(flags); total += len(flags)
        for i in range(len(L.staves) - 1):
            both = flags[i] and flags[i + 1]
            (brk_both if i in L.gt_breaks else int_both).append(both)
    print(f"  staves carrying a header cluster: {have}/{total} ({have/total:.0%})")
    print(f"  TRUE-BREAK gaps with clusters on BOTH sides: "
          f"{sum(brk_both)}/{len(brk_both)}")
    print(f"  INTERIOR   gaps with clusters on BOTH sides: "
          f"{sum(int_both)}/{len(int_both)}")
    print("  -> if both are ~100%, per-staff clef presence is uniform and cannot "
          "locate a stacked-system break.")


def analyze_b9p25():
    print("=" * 70)
    print("B9-p25 — why cue A misses it, and whether any cue recovers it")
    case = next(c for c in H.FAILURES if c.cid == "B9-p25")
    L = H.load(case)
    i = 11  # the true break
    staves = L.staves
    sp = statistics.median([s.line_spacing_px for s in staves])
    xstart = int(statistics.median([s.x_start for s in staves]))
    print(f"  median spacing {sp:.1f}px  median x_start {xstart}")
    # cue A at several bands
    for L_sp, R_sp in [(1.5, 1.5), (2.0, 3.0), (2.0, 4.5), (0.5, 0.5), (1.0, 0.0)]:
        import score as S
        ca = S.cueA_counts(L, L_sp, R_sp)
        print(f"  cueA band[-{L_sp},+{R_sp}]: gap11={ca[11]}  "
              f"(neighbours 9,10,12,13 = {ca[9]},{ca[10]},{ca[12]},{ca[13]})")
    print(f"  cue C bracket-cross gap11 = {D.bracket_column_present(L.binary, staves, 11)}")
    # where is the left ink at gap 11? bucket columns by rel-x
    import cv2, numpy as np
    up, lo = staves[11], staves[12]
    x0 = xstart - int(3 * sp); x1 = xstart + int(6 * sp)
    band = (L.binary[up.bottom_y + 2:lo.top_y - 2, x0:x1] < 128).astype(np.uint8)
    k = max(3, int(round(sp * 0.6)) * 2 + 1)
    closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k, 1), np.uint8))
    hot = [round((c + x0 - xstart) / sp, 1) for c in np.flatnonzero(closed.mean(0) > 0.8)]
    print(f"  gap11 crossing cols (sp from x_start): {hot}")
    print("  (these are the brace curve at the left of system-2's first staves;")
    print("   they clear min_cross so gap11 is judged 'barline-crossed' -> not a break.)")


if __name__ == "__main__":
    cueC_separation()
    cueB_separation()
    analyze_b9p25()
