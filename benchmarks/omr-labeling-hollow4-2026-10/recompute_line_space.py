"""ROADMAP 2.4b -- recompute OnLine / InSpace for every hollow-head label from the staff geometry.

DECISIONS 2026-10-13 (Sean): the labelling tool's click-to-box tag extrapolates the grid off the staff and
leans 'on line'; never train on it as is. Here the class is decided from the MEASURED staff at the head's own x
(CLAUDE.md s10 "measure against the staff locally"), not from the tool's tag and not from a staff-wide value:

  1. take the five staff-line rows the cell carries (`staff_line_ys_canonical`) as a first guess;
  2. in two column strips just LEFT and RIGHT of the head box (the head's own ink excluded), find the dark
     run nearest each guess; a straight fit through the lines found there gives the staff's local offset and
     local spacing at the head's x (>= 3 lines found, else the cell-wide values, counted);
  3. the head's centre row -> staff position t = (yc - a) / b: integer = on a line (a ledger line off the staff
     is the same grid, extended by the measured spacing), half-integer = in a space;
  4. an independent INK check: is there dark ink in the strips beside the head at the head's centre row
     (a staff line or ledger line running through it)? A disagreement is reported, never silently resolved.

Writes a report (per label: tool tag, recomputed tag, frac, ink check, agreement) and, with --out-verdicts,
a COPY of the verdict files whose `human_class` is the recomputed one. The originals are never touched.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]


def local_staff(bw, guess, x0, x1, sp):
    """Fit y = a + b*k through the staff lines found in the strips beside [x0, x1)."""
    h, w = bw.shape
    strips = []
    pad = int(0.15 * sp)
    reach = int(1.4 * sp)
    for lo, hi in ((x0 - pad - reach, x0 - pad), (x1 + pad, x1 + pad + reach)):
        lo, hi = max(0, lo), min(w, hi)
        if hi - lo >= 6:
            strips.append(bw[:, lo:hi])
    if not strips:
        return None
    prof = np.concatenate(strips, axis=1).sum(axis=1).astype(float)
    width = sum(s.shape[1] for s in strips)
    ks, ys = [], []
    for k, g in enumerate(guess):
        lo, hi = int(g - 0.25 * sp), int(g + 0.25 * sp) + 1
        lo, hi = max(0, lo), min(h, hi)
        if hi <= lo:
            continue
        seg = prof[lo:hi]
        if seg.max() < 0.6 * width:
            continue
        idx = np.where(seg >= 0.8 * seg.max())[0]
        ks.append(k)
        ys.append(lo + float(idx.mean()))
    if len(ks) < 3:
        return None
    b, a = np.polyfit(ks, ys, 1)
    return float(a), float(b), len(ks)


def row_dark(bw, yc, x0, x1, sp):
    """Darkness of the rows just beside the head: fraction of near-strip columns dark inside +-0.1sp of row yc.
    The strips run 0.1sp..0.6sp out from each side of the head box (a ledger line pokes ~0.4sp past its head)."""
    h, w = bw.shape
    best = 0.0
    for lo, hi in ((x0 - int(0.6 * sp), x0 - int(0.1 * sp)), (x1 + int(0.1 * sp), x1 + int(0.6 * sp))):
        lo, hi = max(0, lo), min(w, hi)
        r0, r1 = max(0, int(yc - 0.1 * sp)), min(h, int(yc + 0.1 * sp) + 1)
        if hi - lo >= 6 and r1 > r0:
            best = max(best, float(bw[r0:r1, lo:hi].any(axis=0).mean()))
    return best


def classify(cell, bw, bbox):
    guess = [float(v) for v in cell["staff_line_ys_canonical"]]
    sp0 = (guess[-1] - guess[0]) / 4.0
    x0, x1 = int(bbox["x"]), int(bbox["x"] + bbox["w"])
    yc = bbox["y"] + bbox["h"] / 2.0
    fit = local_staff(bw, guess, x0, x1, sp0)
    if fit is None:
        a, b, n, src = guess[0], sp0, 0, "cell-wide"
    else:
        a, b, n = fit
        src = "local"
    t = (yc - a) / b
    frac = t - round(t)
    grid_on = abs(frac) < 0.25
    # INK evidence (independent of any grid extrapolation): a line through the head's centre row, or lines half
    # a space above / below it.
    on_ev = row_dark(bw, yc, x0, x1, b)
    sp_ev = max(row_dark(bw, yc - 0.5 * b, x0, x1, b), row_dark(bw, yc + 0.5 * b, x0, x1, b))
    if on_ev >= 0.6 and sp_ev < on_ev:
        ink = "online"
    elif on_ev < 0.35 and sp_ev >= 0.6:
        ink = "inspace"
    else:
        ink = "unclear"
    own = -0.3 <= t <= 4.3          # on the staff proper (outer lines included): the five measured lines ARE the grid
    if own and ink == "unclear":
        on_line, basis = grid_on, "grid(own staff)"
    elif ink == "unclear":
        on_line, basis = grid_on, "grid(extrapolated, UNCLEAR)"
    elif own:
        # on the staff the local fit is exact; the ink check only vetoes when the two disagree strongly
        on_line, basis = grid_on, "grid(own staff)"
    else:
        # a ledger zone or a neighbour staff: the grid is EXTRAPOLATED (and across a gap that is not a whole number
        # of spaces for a neighbour staff) -- the ink decides, the grid is reported; Sean's rule: the ledger lines
        # name the head, nearness and extrapolation do not
        on_line, basis = (ink == "online"), "ink(off own staff)"
    return {"t": round(t, 3), "frac": round(frac, 3), "on_line": bool(on_line), "ink": ink,
            "on_ev": round(on_ev, 2), "sp_ev": round(sp_ev, 2), "basis": basis, "grid_on_line": bool(grid_on),
            "lines_found": n, "source": src, "local_spacing": round(b, 1), "spacing_cellwide": round(sp0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=Path, default=REPO / "benchmarks/omr-labeling-hollow4-2026-10")
    ap.add_argument("--out-verdicts", type=Path, default=None)
    ap.add_argument("--report", type=Path, default=None)
    a = ap.parse_args()
    cells = {c["cell_id"]: c for c in json.loads((a.batch / "cells.json").read_text())}
    rows = []
    if a.out_verdicts:
        a.out_verdicts.mkdir(parents=True, exist_ok=True)
    for vf in sorted((a.batch / "verdicts").glob("*.verdict.json")):
        v = json.loads(vf.read_text())
        cell = cells[v["cell_id"]]
        img = cv2.imread(str(REPO / cell["cell_png_path"]), 0)
        bw = (img < 128).astype(np.uint8)
        for d in v["added_detections"]:
            cls = d["human_class"]
            if not cls.startswith(("noteheadHalf", "noteheadWhole")):
                continue
            r = classify(cell, bw, d["bbox"])
            fam = "noteheadHalf" if cls.startswith("noteheadHalf") else "noteheadWhole"
            suffix = "Small" if cls.endswith("Small") else ""
            new = fam + ("OnLine" if r["on_line"] else "InSpace") + suffix
            r.update({"cell_id": v["cell_id"], "id": d["id"], "tool": cls, "recomputed": new,
                      "agree": new == cls,
                      "ink_agrees": r["ink"] == "unclear" or (r["ink"] == "online") == r["on_line"]})
            rows.append(r)
            d["tool_class"] = cls
            d["human_class"] = new
        if a.out_verdicts:
            (a.out_verdicts / vf.name).write_text(json.dumps(v, indent=2) + "\n")
    dis = [r for r in rows if not r["agree"]]
    off = [r for r in rows if r["t"] < -0.5 or r["t"] > 4.5]
    summ = {"labels": len(rows), "tool_vs_recomputed_disagree": len(dis),
            "disagree_off_staff": sum(1 for r in dis if r in off), "off_staff_total": len(off),
            "tool_said_online_recomputed_inspace": sum(1 for r in dis if r["tool"].endswith("OnLine")),
            "tool_said_inspace_recomputed_online": sum(1 for r in dis if r["tool"].endswith("InSpace")),
            "ambiguous_frac_0.18_0.32": sum(1 for r in rows if 0.18 <= abs(r["frac"]) <= 0.32),
            "ink_check_disagrees": sum(1 for r in rows if not r["ink_agrees"]),
            "ink_unclear": sum(1 for r in rows if r["ink"] == "unclear"),
            "off_own_staff_decided_by_ink": sum(1 for r in rows if r["basis"].startswith("ink")),
            "off_own_staff_unclear": sum(1 for r in rows if "UNCLEAR" in r["basis"]),
            "cell_wide_fallback": sum(1 for r in rows if r["source"] != "local")}
    print(json.dumps(summ, indent=1))
    if a.report:
        a.report.write_text(json.dumps({"summary": summ, "labels": rows}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
