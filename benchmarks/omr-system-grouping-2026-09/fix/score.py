"""End-to-end Phase-1 scorer for the system-START detector.

Semantics match the Phase-2 integration: the detector is CONSTRUCTIVE — it can
only ADD a break at a detected system start, never merge. So the final grouping
is `existing_rule_breaks | detector_breaks`, and a page is CORRECT iff that
union equals the ground-truth break set.

  - FAILURE page fixed  = union == GT   (was wrong before)
  - CONTROL page kept   = union == GT   (still right; any detector break outside
                          GT is a REGRESSION)

Detector under test: cue A (systemic / leftmost-barline continuity), gated.
  cueA[i] = # crossing columns in [x_start-Lsp, x_start+Rsp] over gap i.
  A gap is "barline-crossed" if cueA[i] >= MIN_CROSS.
  Page GATE: trust the cue only if the fraction of barline-crossed gaps
             (among gaps the existing rule did NOT already break) >= GATE_FRAC.
  If gated ON: predict a break at every gap with cueA[i] < MIN_CROSS.
  If gated OFF: predict nothing (abstain) — the page has no continuous left
             barline to reason about (Mahler-style family-broken barlines).

Usage:
  python3 score.py [--sweep] [--L 2.0 --R 4.5 --min-cross 1 --gate 0.7]
  python3 score.py --grid           # sweep band/gate params, report best
"""
from __future__ import annotations

import argparse
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import _harness as H


# ── cue A measurement ─────────────────────────────────────────────────────────
def cueA_counts(L, L_sp, R_sp, ink=0.8, gap_tol=0.6):
    staves = L.staves
    if len(staves) < 2:
        return []
    sp = statistics.median([s.line_spacing_px for s in staves]) or 1.0
    xstart = int(statistics.median([s.x_start for s in staves]))
    x0 = max(0, int(xstart - L_sp * sp))
    x1 = min(L.binary.shape[1], int(xstart + R_sp * sp))
    out = []
    for up, lo in zip(staves, staves[1:]):
        top = up.bottom_y + 2
        bot = lo.top_y - 2
        spacing = max(up.line_spacing_px, lo.line_spacing_px)
        top = max(0, top); bot = min(L.binary.shape[0], bot)
        if bot <= top or x1 <= x0:
            out.append(-1); continue
        band = (L.binary[top:bot, x0:x1] < 128).astype(np.uint8)
        k = max(3, int(round(spacing * gap_tol)) * 2 + 1)
        closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k, 1), np.uint8))
        out.append(int((closed.mean(axis=0) > ink).sum()))
    return out


@dataclass
class Params:
    L_sp: float = 2.0
    R_sp: float = 4.5
    min_cross: int = 1
    gate_frac: float = 0.7
    # relative mode (optional): break where cueA << page-typical
    relative: bool = False
    rel_frac: float = 0.4       # break if cueA[i] <= rel_frac * page_hi
    rel_gate_abs: int = 6       # trust the cue only if page_hi >= this


def _page_hi(ca, cand):
    import numpy as np
    vals = [ca[i] for i in cand]
    return float(np.percentile(vals, 75)) if vals else 0.0


def detect_breaks(L, p: Params):
    """Return (detector_break_set, gated_on, cueA_list)."""
    ca = cueA_counts(L, p.L_sp, p.R_sp)
    if not ca:
        return set(), False, ca
    existing = L.existing_breaks
    # Gate on the gaps the existing rule did NOT already break (interior candidates).
    cand = [i for i in range(len(ca)) if i not in existing and ca[i] >= 0]
    if not cand:
        return set(), False, ca
    if p.relative:
        hi = _page_hi(ca, cand)
        if hi < p.rel_gate_abs:
            return set(), False, ca
        thr = p.rel_frac * hi
        det = {i for i in cand if ca[i] <= thr}
        return det, True, ca
    crossed = sum(1 for i in cand if ca[i] >= p.min_cross)
    frac = crossed / len(cand)
    gated_on = frac >= p.gate_frac
    if not gated_on:
        return set(), False, ca
    det = {i for i in cand if 0 <= ca[i] < p.min_cross}
    return det, True, ca


OVERMERGE_KINDS = ("failure", "discovered_overmerge")


def score(cases, p: Params, verbose=True):
    rows = []
    # tallies
    fixed = still = 0                      # original 3 failures
    disc_fixed = disc_miss = 0             # discovered instrumental over-merges
    vocal_fixed = vocal_miss = 0           # discovered vocal over-merges (Phase 3)
    kept = regressed = 0                   # genuine controls
    n_controls = sum(1 for c in cases if c.kind == "control")
    for case in cases:
        L = H.load(case)
        det, gated, ca = detect_breaks(L, p)
        final = set(L.existing_breaks) | det
        gt = set(L.gt_breaks)
        correct = final == gt
        fp = det - gt                      # detector breaks outside GT (regression source)
        if case.kind == "failure":
            if correct:
                fixed += 1; status = "FIXED"
            else:
                still += 1; status = "FIXED-BUT-FP" if fp else "still-broken"
        elif case.kind == "discovered_overmerge":
            if correct:
                disc_fixed += 1; status = "FIXED(disc)"
            else:
                disc_miss += 1; status = "missed(disc)" if not fp else "disc-FP"
        elif case.kind == "discovered_overmerge_vocal":
            if correct:
                vocal_fixed += 1; status = "FIXED(vocal)"
            else:
                vocal_miss += 1; status = "missed(vocal)" if not fp else "vocal-FP"
        else:  # control
            if correct and not fp:
                kept += 1; status = "kept"
            else:
                regressed += 1; status = "REGRESSED"
        rows.append((case, status, sorted(final), sorted(gt), sorted(det),
                     sorted(fp), gated))
    if verbose:
        print(f"params L={p.L_sp} R={p.R_sp} min_cross={p.min_cross} gate={p.gate_frac}")
        print(f"{'case':22s} {'kind':26s} {'status':13s} {'final':>14s} {'gt':>12s} "
              f"{'detector':>12s} {'FP':>6s} gate")
        for case, status, final, gt, det, fp, gated in rows:
            mark = "" if status.startswith(("FIXED", "kept")) else "  <=="
            print(f"{case.cid:22s} {case.kind:26s} {status:13s} {str(final):>14s} "
                  f"{str(gt):>12s} {str(det):>12s} {str(fp):>6s} {'ON ' if gated else 'off'}{mark}")
        print(f"\noriginal FAILURES fixed {fixed}/3 (still-broken {still})")
        print(f"discovered instrumental over-merges fixed {disc_fixed} (missed {disc_miss})")
        print(f"discovered VOCAL over-merges (Phase-3) fixed {vocal_fixed} (missed {vocal_miss})")
        print(f"genuine CONTROLS kept {kept}/{n_controls}   REGRESSIONS {regressed}")
    # For grid: return (original_fixed, controls_kept, regressions)
    return fixed, kept, regressed, n_controls


def grid(cases):
    best = None
    print(f"{'L':>4} {'R':>5} {'minx':>4} {'gate':>5} | {'fixed':>5} {'kept':>5} {'reg':>4}")
    for L_sp in (1.0, 1.5, 2.0, 2.5, 3.0):
        for R_sp in (2.0, 3.0, 4.0, 4.5, 5.0, 6.0):
            for min_cross in (1, 2, 3):
                for gate in (0.6, 0.7, 0.8):
                    p = Params(L_sp, R_sp, min_cross, gate)
                    f, k, r, nc = score(cases, p, verbose=False)
                    key = (f, k, -r)
                    flag = ""
                    if f >= 2 and r == 0:
                        flag = "  <-- clears bar"
                    if best is None or key > best[0]:
                        best = (key, p)
                    if (f >= 2 and r == 0) or (r == 0 and f >= 1):
                        print(f"{L_sp:>4} {R_sp:>5} {min_cross:>4} {gate:>5} | "
                              f"{f:>5} {k:>5} {r:>4}{flag}")
    print(f"\nBEST: {best[1]}  -> fixed/kept/reg = {best[0][0]},{best[0][1]},{-best[0][2]}")
    return best[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--L", type=float, default=2.0)
    ap.add_argument("--R", type=float, default=4.5)
    ap.add_argument("--min-cross", type=int, default=1)
    ap.add_argument("--gate", type=float, default=0.7)
    ap.add_argument("--grid", action="store_true")
    args = ap.parse_args()
    cases = H.all_cases(include_sweep=args.sweep)
    if args.grid:
        grid(cases)
    else:
        score(cases, Params(args.L, args.R, args.min_cross, args.gate))


if __name__ == "__main__":
    main()
