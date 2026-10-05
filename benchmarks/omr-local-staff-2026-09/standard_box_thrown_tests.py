#!/usr/bin/env python3
"""lane-standard-head-box step 4: for the four 'thrown past the head' tiles
(`3/0/7/4/3`, `3/0/7/6/1`, `3/0/7/7/0`, `3/1/0/6/0`), which test in
`ledger_grid.py` throws the line, with its numbers -- at the detector box (S0)
and at the standard box (S1). Reads only; the two tests are re-evaluated here
number by number and each re-evaluation is asserted equal to the real function
(`_rung_row_clears_box`, `head_middle_rung_evidence`).

    python3 benchmarks/omr-local-staff-2026-09/standard_box_thrown_tests.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import numpy as np  # noqa: E402

import score_standard_box as sb  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

TILES = {"glyph/3/0/7/4/3": 1457.0, "glyph/3/0/7/6/1": 1583.5,
         "glyph/3/0/7/7/0": 1580.0, "glyph/3/1/0/6/0": 2268.5}


def runs_of(cols, bridge=0):
    runs, n, i = [], len(cols), 0
    while i < n:
        if cols[i]:
            j = i
            while j < n and cols[j]:
                j += 1
            if runs and bridge and i - runs[-1][1] <= bridge:
                runs[-1][1] = j
            else:
                runs.append([i, j])
            i = j
        else:
            i += 1
    return runs


def clears_numbers(img, y, x, bx, sp, excl):
    h, w = img.shape
    bx0, bx1 = bx
    pad = lg.RUNG_BOX_VISIBILITY_SPACES * sp
    cx0, cx1 = max(0, int(bx0 - pad)), min(w, int(bx1 + pad))
    yi = int(round(y))
    y0, y1 = max(0, yi - 1), min(h, yi + 2)
    win = img[y0:y1, cx0:cx1]
    thr = lg._otsu_threshold(win)
    ink = win <= thr
    if excl:
        ink = lg._exclude_other_heads_ink(ink, excl, cx0, y0, sp)
    runs = runs_of(ink.any(axis=0), int(round(lg.RUNG_BRIDGE_GAP_SPACES * sp)))
    pc = int(round(x)) - cx0
    cont = [r for r in runs if r[0] <= pc < r[1]]
    need = (bx1 - bx0) + 2 * lg.RUNG_BEYOND_BOX_MIN_SPACES * sp
    if not cont:
        return dict(run_px=None, need_px=round(need, 1), passed=False)
    s, e = cont[0]
    return dict(run_px=e - s, run_x=[s + cx0, e + cx0], need_px=round(need, 1), box_w_px=round(bx1 - bx0, 1),
                run_over_spacing=round((e - s) / sp, 2), need_over_spacing=round(need / sp, 2),
                passed=(e - s) >= need)


def middle_numbers(img, box, sp, excl):
    x0, y0, x1, y1 = box
    mid = (y0 + y1) / 2.0
    h, w = img.shape
    pad = lg.RUNG_BOX_VISIBILITY_SPACES * sp
    cx0, cx1 = max(0, int(x0 - pad)), min(w, int(x1 + pad))
    tol = lg.MIDDLE_ROW_TOL_SPACES * sp
    wy0, wy1 = max(0, int(round(mid - tol))), min(h, int(round(mid + tol)) + 1)
    win = img[wy0:wy1, cx0:cx1]
    thr = lg._otsu_threshold(win)
    ink = win <= thr
    if excl:
        ink = lg._exclude_other_heads_ink(ink, excl, cx0, wy0, sp, img, thr)
    runs = runs_of(ink.any(axis=0))
    pc = int(round((x0 + x1) / 2.0)) - cx0
    cont = [r for r in runs if r[0] <= pc < r[1]]
    stub = lg.THROUGH_RUNG_STUB_PROBE_SPACES * sp
    out = dict(mid_row=round(mid, 1), rows=[wy0, wy1 - 1], band_px=wy1 - wy0, stub_need_px=round(stub, 1))
    if not cont:
        out.update(run=None, passed=False)
        return out
    s, e = cont[0]
    le, re_ = x0 - cx0, x1 - cx0
    out.update(run=[s + cx0, e + cx0], box_x=[round(x0, 1), round(x1, 1)],
               left_jut_px=round(le - s, 1), right_jut_px=round(e - re_, 1),
               passed=bool((s <= le - stub) or (e >= re_ + stub)))
    return out


def main():
    lit = "beethoven5-litolff"
    D = sb.build(lit)
    far = {h["subject"]: h for h in D["far"]}
    for s, ry in TILES.items():
        h = far[s]
        sp = h["spacing"]
        st = sb.standard_for(h, D)
        others = [b for (su, b) in D["nh"].get(h["page"], []) if su != s] + [b for (_x, b) in D["acc"].get(h["page"], [])]
        print(f"\n=== {s}  sp={sp:.1f}px  thrown line y={ry}")
        ov = []
        for (su, b) in D["nh"].get(h["page"], []):
            if su == s:
                continue
            ox, oy = min(h["box"][2], b[2]) - max(h["box"][0], b[0]), min(h["box"][3], b[3]) - max(h["box"][1], b[1])
            if ox > 0 and oy > 0:
                ov.append((su, "notehead", round(ox * oy / ((h["box"][2]-h["box"][0])*(h["box"][3]-h["box"][1])), 2)))
        for (su, b) in D["acc"].get(h["page"], []):
            ox, oy = min(h["box"][2], b[2]) - max(h["box"][0], b[0]), min(h["box"][3], b[3]) - max(h["box"][1], b[1])
            if ox > 0 and oy > 0:
                ov.append((su, "accidental", round(ox * oy / ((h["box"][2]-h["box"][0])*(h["box"][3]-h["box"][1])), 2)))
        print("   other boxes overlapping the detector box (subject, kind, fraction of the box):", ov)
        for tag, box in (("S0 detector box", h["box"]), ("S1 standard box", st["box"])):
            x0, y0, x1, y1 = box
            cx = (x0 + x1) / 2.0
            real_cl = lg._rung_row_clears_box(h["gray"], ry, cx, (x0, x1), sp, others)
            c = clears_numbers(h["gray"], ry, cx, (x0, x1), sp, others)
            assert c["passed"] == real_cl, (s, tag, c, real_cl)
            real_ev = lg.head_middle_rung_evidence(h["gray"], tuple(box), sp, others, None)
            m = middle_numbers(h["gray"], tuple(box), sp, others)
            assert m["passed"] == real_ev, (s, tag, m, real_ev)
            print(f"{tag}: box x {x0:.1f}-{x1:.1f} y {y0:.1f}-{y1:.1f} (w {x1-x0:.1f} h {y1-y0:.1f} px)")
            print(f"   _rung_row_clears_box at y={ry}: {c}   [RUNG_BEYOND_BOX_MIN_SPACES={lg.RUNG_BEYOND_BOX_MIN_SPACES}]")
            print(f"   head_middle_rung_evidence: {m}   [MIDDLE_ROW_TOL_SPACES={lg.MIDDLE_ROW_TOL_SPACES}, "
                  f"THROUGH_RUNG_STUB_PROBE_SPACES={lg.THROUGH_RUNG_STUB_PROBE_SPACES}]")
            m0 = middle_numbers(h["gray"], tuple(box), sp, None)
            print(f"   DIAGNOSTIC (no other-head blanking at all): head_middle_rung_evidence {m0}")
            print(f"   line y {ry} vs box middle: {(ry - (y0 + y1) / 2.0) / sp:+.2f} sp")


if __name__ == "__main__":
    main()
