"""ROADMAP 2.57: the per-bar grid may not lock one line over (OMR_CELL_LINE_SEED).

Grid-only control (no detector, no gather): re-render each page, `detect_staves`,
`extract_measures` with the flag OFF and ON, and measure, per bar, how far the
bar's grid is from the printed ink. The measure is the one of
`verify_staff_line_offsets.py` (the independent Opus check): a column counts
only where the window holds EXACTLY five dark runs <= 0.4 sp thick at the
recorded spacing +-20%, so no head/stem/beam/ledger/slur is in it; line k IS run
k; the bar's offset = median over its clear columns of the mean over the five
lines of (ink row - grid row), in page px; positive = ink below the grid.

  python3 benchmarks/omr-local-staff-2026-09/per_bar_grid_one_line_off.py grid litolff 1-16
  python3 ... heads  litolff 4       (fixed recorded head boxes, old vs new grid)
  python3 ... sheet                  (out/print/per_bar_grid_one_line_off.png)
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")
DOCS = {
    "litolff": (LIB / "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", 600),
    "brahms": (LIB / "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 600),
}
FLAG = "OMR_CELL_LINE_FIND"


def parse_pages(spec):
    out = []
    for part in str(spec).split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


# ---- the measure (same definition as verify_staff_line_offsets.py) ----------

def ink_runs(binary, x, y_lo, y_hi, strip):
    h, w = binary.shape
    a, b = max(0, x - strip // 2), min(w, x - strip // 2 + strip)
    y_lo, y_hi = max(0, y_lo), min(h, y_hi)
    if b <= a or y_hi <= y_lo:
        return []
    col = (binary[y_lo:y_hi, a:b] == 0).mean(axis=1) >= 0.5
    runs, start = [], None
    for i, v in enumerate(col):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((y_lo + start, y_lo + i - 1))
            start = None
    if start is not None:
        runs.append((y_lo + start, y_lo + len(col) - 1))
    return runs


def measure_column(binary, x, lines, spacing, strip):
    lo = int(round(min(lines) - 1.5 * spacing))
    hi = int(round(max(lines) + 1.5 * spacing)) + 1
    runs = ink_runs(binary, x, lo, hi, strip)
    if len(runs) != 5:
        return None
    th = [e - s + 1 for s, e in runs]
    if max(th) > 0.4 * spacing:
        return None
    c = [(s + e) / 2.0 for s, e in runs]
    if np.any(np.abs(np.diff(c) - spacing) > 0.2 * spacing):
        return None
    return c


def bar_offset(binary, staff, x0, x1, shift):
    """(median offset px, n clear columns) of the bar's grid (line_ys + shift)."""
    sp = float(staff.line_spacing_px)
    strip = max(3, int(round(0.2 * sp)))
    step = max(2, int(round(0.5 * sp)))
    lines = [float(y) for y in staff.line_ys]
    offs = []
    for x in range(int(x0) + strip, int(x1) - strip, step):
        # clear-column test is made against the RAW lines widened by the
        # needed shift: look for five runs anywhere within +-2 sp of the raw staff
        c = None
        for dy in (0, shift):
            c = measure_column(binary, x, [y + dy for y in lines], sp, strip)
            if c is not None:
                break
        if c is None:
            continue
        offs.append(float(np.mean([c[k] - (lines[k] + shift) for k in range(5)])))
    return (float(np.median(offs)), len(offs)) if offs else (None, 0)


# ---- grid ------------------------------------------------------------------

def _cells(pi, local, me, detect_staves):
    pws = detect_staves(pi)
    cells = me.extract_measures(pws)
    return pws, cells


def grid(doc, pages_spec):
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr import measure_extractor as me
    from tools.omr.staged.gather import _system_local

    pdf, dpi = DOCS[doc]
    rows = []
    for p in parse_pages(pages_spec):
        pi = render_page(str(pdf), p, dpi=dpi)
        per = {}
        for arm in ("off", "on"):
            os.environ[FLAG] = "1" if arm == "on" else "0"
            pws = detect_staves(pi)
            local = _system_local(pws.staves)
            cells = me.extract_measures(pws)
            st_by = {s.staff_index: s for s in pws.staves}
            for c in cells:
                sy, sl = local[c.staff_index]
                key = f"cell/{p}/{sy}/{sl}/{c.measure_index}"
                prov = c.__dict__.get("line_grid_localized")
                shift = int(prov["offset_px"]) if prov else 0
                x0, y0, x1, y1 = c.bbox_page_px
                st = st_by[c.staff_index]
                off, n = bar_offset(pi.binary, st, x0, x1, shift)
                per.setdefault(key, {})[arm] = {
                    "shift": shift, "off_px": off, "n_cols": n,
                    "spacing": float(st.line_spacing_px),
                    "found": (prov or {}).get("line_grid_found"),
                    "ys": [int(y) for y in st.line_ys],
                    "box": [int(x0), int(y0), int(x1), int(y1)],
                    "canon": [int(v) for v in c.staff_line_ys_canonical],
                    "scale": float(c.upscale_factor),
                }
        for k, v in per.items():
            v["cell"] = k
            rows.append(v)
        n_chg = sum(1 for v in per.values() if v.get("off", {}).get("shift") != v.get("on", {}).get("shift"))
        print(f"{doc} p{p}: cells {len(per)} grid changed {n_chg}", flush=True)
    OUT.mkdir(exist_ok=True)
    Path(OUT / f"grid_{doc}_{pages_spec.replace(',', '_')}.json").write_text(json.dumps(rows))


def summarize(doc, pages_spec):
    rows = json.loads((OUT / f"grid_{doc}_{pages_spec.replace(',', '_')}.json").read_text())
    ge = lambda a, t: sum(1 for r in rows if r.get(a, {}).get("off_px") is not None
                          and abs(r[a]["off_px"]) >= t * r[a]["spacing"])
    n_meas = sum(1 for r in rows if r.get("off", {}).get("off_px") is not None
                 and r.get("on", {}).get("off_px") is not None)
    print(doc, pages_spec, "cells", len(rows), "measured in both arms", n_meas)
    for t in (0.25, 0.4):
        print(f"  bars >= {t} sp off: off {ge('off', t)} -> on {ge('on', t)}")
    right_to_wrong = [r["cell"] for r in rows if r.get("off", {}).get("off_px") is not None
                      and r.get("on", {}).get("off_px") is not None
                      and abs(r["off"]["off_px"]) < 0.4 * r["off"]["spacing"]
                      and abs(r["on"]["off_px"]) >= 0.4 * r["on"]["spacing"]]
    print("  bars < 0.4 sp off before and >= 0.4 sp after:", len(right_to_wrong), right_to_wrong[:20])
    worse = [(r["cell"], round(r["off"]["off_px"], 1), round(r["on"]["off_px"], 1)) for r in rows
             if r.get("off", {}).get("off_px") is not None and r.get("on", {}).get("off_px") is not None
             and abs(r["on"]["off_px"]) > abs(r["off"]["off_px"]) + 1.0]
    print("  bars more than 1 px worse:", len(worse), worse[:20])
    chg = [r for r in rows if r.get("off", {}).get("shift") != r.get("on", {}).get("shift")]
    print("  bars whose shift changed:", len(chg))
    # continuity: adjacent bars of one staff, a jump of more than 0.5 sp
    for arm in ("off", "on"):
        by = defaultdict(list)
        for r in rows:
            a = r.get(arm)
            if a is None:
                continue
            _, p, sy, sl, m = r["cell"].split("/")
            by[(p, sy, sl)].append((int(m), a["shift"], a["spacing"]))
        jumps = 0
        for v in by.values():
            v.sort()
            for (m0, s0, sp), (m1, s1, _) in zip(v, v[1:]):
                if m1 == m0 + 1 and abs(s1 - s0) > 0.5 * sp:
                    jumps += 1
        print(f"  [{arm}] adjacent-bar shift jumps > 0.5 sp:", jumps)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "grid":
        grid(sys.argv[2], sys.argv[3])
        summarize(sys.argv[2], sys.argv[3])
    elif cmd == "summary":
        summarize(sys.argv[2], sys.argv[3])
