#!/usr/bin/env python3
"""Controlled ground-truth audit of the system-grouping gap-bridging window.

Question: does `gap_bridging_counts` drop the ~2px left-edge systemic barline
(the only ink crossing an instrument-family boundary), reading 0 where a barline
physically bridges the gap?

We import tools.omr FROM THE WORKTREE (path inserted relative to __file__), build
a synthetic page whose bridged-only-by-systemic-barline gaps are known by
construction, and compare the pipeline's per-gap counts against an INDEPENDENT
full-width scan that finds every near-solid column and its x-position.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import cv2

# --- import tools.omr from the worktree (relative to this file) ---
HERE = Path(__file__).resolve()
# .../<worktree>/benchmarks/omr-system-grouping-2026-09/xstart-audit/audit.py
WORKTREE = HERE.parents[3]
sys.path.insert(0, str(WORKTREE))

from tools.omr.preprocessing import render_page               # noqa: E402
from tools.omr.staff_detector import detect_staves             # noqa: E402
from tools.omr import system_grouping as SG                    # noqa: E402


def col_coverage(binary, top, bot, x0, x1, close_k):
    """Per-column vertical ink coverage over rows [top:bot], cols [x0:x1],
    after a vertical morphological close of size close_k. Returns 1-D array over
    columns. Binary convention: <128 == ink."""
    band = (binary[top:bot, x0:x1] < 128).astype(np.uint8)
    if close_k >= 3:
        band = cv2.morphologyEx(band, cv2.MORPH_CLOSE,
                                np.ones((close_k, 1), np.uint8))
    return band.mean(axis=0)


def independent_gap_scan(binary, upper, lower, ink_fraction=0.8):
    """INDEPENDENT of the pipeline window. Scan the FULL page width across the
    physical gap between two staves; return every column (absolute x) whose
    coverage >= ink_fraction, after the same vertical close the pipeline uses.
    Also returns the raw (un-closed) coverage so we can see faint bridges."""
    h, w = binary.shape
    top = max(0, upper.bottom_y + 2)
    bot = min(h, lower.top_y - 2)
    if bot <= top:
        return None
    spacing = max(upper.line_spacing_px, lower.line_spacing_px)
    k = max(3, int(round(spacing * SG.BRIDGE_GAP_TOLERANCE_SPACINGS)) * 2 + 1)
    cov_closed = col_coverage(binary, top, bot, 0, w, k)
    cov_raw = col_coverage(binary, top, bot, 0, w, 0)
    cols = np.flatnonzero(cov_closed >= ink_fraction)
    return {
        "top": top, "bot": bot, "k": k,
        "cols": cols.tolist(),
        "cov_closed": cov_closed,
        "cov_raw": cov_raw,
    }


def analyze(pdf_path, dpi, label, crops_dir=None):
    pi = render_page(Path(pdf_path), 0, dpi=dpi)
    binary = pi.binary
    h, w = binary.shape
    pws = detect_staves(pi)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    spacing = float(np.median([s.line_spacing_px for s in staves]))

    x0w, x1w = SG._robust_x_window(staves)
    x0w_c, x1w_c = max(0, x0w), min(w, x1w)
    bridging = SG.gap_bridging_counts(binary, staves)

    med_xstart = int(np.median([s.x_start for s in staves]))
    med_xend = int(np.median([s.x_end for s in staves]))

    print("=" * 78)
    print(f"{label}   dpi={dpi}   page={w}x{h}px   staff-space~{spacing:.1f}px")
    print(f"  n_staves={len(staves)}  systems={sorted(set(s.system_index for s in staves))}"
          f"  -> {len(set(s.system_index for s in staves))} system(s)")
    print(f"  median x_start={med_xstart}  median x_end={med_xend}")
    print(f"  pipeline scan window x=[{x0w}..{x1w}] (clipped [{x0w_c}..{x1w_c}])"
          f"   margin={int(round(spacing*SG.WINDOW_MARGIN_SPACINGS))}px "
          f"({SG.WINDOW_MARGIN_SPACINGS}sp)")
    print(f"  window left edge is {med_xstart - x0w_c}px LEFT of median x_start")

    # Find the systemic barline x independently: the leftmost column that is
    # near-solid across (nearly) the WHOLE system height.
    sys_top = min(s.top_y for s in staves)
    sys_bot = max(s.bottom_y for s in staves)
    full_cov = col_coverage(binary, sys_top, sys_bot, 0, w,
                            max(3, int(round(spacing*0.6))*2+1))
    # Look only in the left region (within ~8 spaces of median x_start) for the
    # systemic bar; require coverage over most of the system height.
    left_lo = max(0, med_xstart - int(8*spacing))
    left_hi = min(w, med_xstart + int(3*spacing))
    cand = [x for x in range(left_lo, left_hi) if full_cov[x] >= 0.85]
    sysbar_x = cand[0] if cand else None
    print(f"  INDEPENDENT systemic-bar detect (full system-height >=0.85 cov, "
          f"left region): {'x=%d (%+d vs median x_start)' % (sysbar_x, sysbar_x-med_xstart) if sysbar_x is not None else 'NONE FOUND'}")
    if sysbar_x is not None:
        inside = x0w_c <= sysbar_x < x1w_c
        print(f"     systemic bar at x={sysbar_x} is {'INSIDE' if inside else 'OUTSIDE'} pipeline window [{x0w_c}..{x1w_c}]")

    print(f"\n  {'gap':>4} {'pair(y)':>16} {'pipe':>5} | independent full-width scan")
    print(f"  {'':>4} {'':>16} {'cnt':>5} | truth: #cols>=0.8 (closed)   near-x_start? cols (x-med_xstart)")
    rows = []
    for i, (u, l) in enumerate(zip(staves, staves[1:])):
        pcnt = bridging[i]
        scan = independent_gap_scan(binary, u, l)
        if scan is None:
            print(f"  {i:>4} {'degenerate':>16} {pcnt:>5} | (no gap)")
            rows.append((i, pcnt, None, None, None))
            continue
        cols = scan["cols"]
        # near systemic barline: within +-1.5 spaces of median x_start
        near = [c for c in cols if abs(c - med_xstart) <= 1.5*spacing]
        # columns inside pipeline window
        in_win = [c for c in cols if x0w_c <= c < x1w_c]
        rel = [c - med_xstart for c in cols]
        near_str = "YES" if near else "no "
        # Is there a bridging column that the pipeline MISSED (outside window)?
        missed = [c for c in cols if not (x0w_c <= c < x1w_c)]
        tag = ""
        if pcnt == 0 and near:
            tag = "  <<< PIPELINE=0 BUT BARLINE PRESENT (BUG)"
        elif near and 0 not in [pcnt]:
            tag = ""
        rel_show = ",".join(str(r) for r in rel[:12]) + (" ..." if len(rel) > 12 else "")
        print(f"  {i:>4} {u.bottom_y:>6}->{l.top_y:<7} {pcnt:>5} | "
              f"{len(cols):>3} cols   near_x_start={near_str}  in_win={len(in_win)}"
              f"  x-rel=[{rel_show}]{tag}")
        rows.append((i, pcnt, len(cols), bool(near), missed))

        # save a crop of the left edge for the two between-group gaps of interest
        if crops_dir is not None:
            cx0 = max(0, med_xstart - int(3*spacing))
            cx1 = min(w, med_xstart + int(3*spacing))
            crop = pi.binary[scan["top"]:scan["bot"], cx0:cx1]
            outp = Path(crops_dir) / f"{label}_dpi{dpi}_gap{i}_leftedge.png"
            cv2.imwrite(str(outp), crop)
    return {
        "label": label, "dpi": dpi, "spacing": spacing,
        "n_staves": len(staves),
        "n_systems": len(set(s.system_index for s in staves)),
        "systems": [s.system_index for s in staves],
        "window": (x0w_c, x1w_c), "med_xstart": med_xstart,
        "sysbar_x": sysbar_x, "bridging": bridging, "rows": rows,
    }


if __name__ == "__main__":
    import json
    d = HERE.parent
    crops = d / "crops"
    crops.mkdir(exist_ok=True)

    # --- calibrate: one render to learn staff-space(px) per dpi, then pick 3 ---
    cal = render_page(d / "one_system.pdf", 0, dpi=100)
    cal_pws = detect_staves(cal)
    ss100 = float(np.median([s.line_spacing_px for s in cal_pws.staves]))
    print(f"calibration: at dpi=100, staff-space = {ss100:.2f}px "
          f"({cal_pws and len(cal_pws.staves)} staves)")
    # staff-space scales linearly with dpi
    targets = {13.0: None, 10.0: None, 7.5: None}
    for t in list(targets):
        targets[t] = round(100.0 * t / ss100)
    print("chosen DPIs:", {f"ss~{t}": dpi for t, dpi in targets.items()})
    print()

    results = []
    for t, dpi in sorted(targets.items(), reverse=True):
        results.append(analyze(d / "one_system.pdf", dpi, "ONE_SYS", crops))
    # two-system control at the middle resolution
    mid_dpi = targets[10.0]
    results.append(analyze(d / "two_system.pdf", mid_dpi, "TWO_SYS", crops))
    for t, dpi in sorted(targets.items(), reverse=True):
        if dpi == mid_dpi:
            continue
        results.append(analyze(d / "two_system.pdf", dpi, "TWO_SYS", crops))

    (d / "audit_results.json").write_text(json.dumps(
        [{k: v for k, v in r.items() if k not in ("rows",)} for r in results],
        indent=2, default=str))
    print("\nwrote audit_results.json")
