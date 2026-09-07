#!/usr/bin/env python3
"""VERIFIER round 2 — recompute Agent I's §R2.2 Q3 and Q4 tables.

Those two tables carry the RETRACTION of round-1 item 5 and are NOT produced by
any committed probe (`probe_ladder_inversion.py` emits only Q1 and Q2). This
rebuilds them, calling the real `_ledger_ladder` and reusing its own constants.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), _os.pardir))
from _fixtures import fixtures, root as _fixroot, CONTESTS, SCAN, ENGRAVED  # noqa: E402
# ⚠️ verify/ was invisible to test_probe_hygiene.py, whose file sweep was
# non-recursive and never descended. All four files here carried the very defect that lint
# exists to catch. Deferring to _fixtures.py, the designated survivor.
# committed artefacts + `tools.omr` come from the tree this file lives in
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.omr.transcribe import (                                  # noqa: E402
    _ledger_ladder, _LEDGER_RUNG_EXPECTED_SLACK,
    _LEDGER_RUNG_Y_TOL_SPACES, _LEDGER_RUNG_MIN_X_OVERLAP)

FILES = {
    "beet5-p02": "benchmarks/omr-reference-selection-2026-09/out/beet5-p02-on.json",
    "brahms1":   "benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json",
}

def bands_of(page):
    out = {}
    for sy in page.get("systems", []):
        for st in sy.get("staves", []):
            g = st.get("staff_geometry") or {}
            ys = g.get("line_ys_page") or []
            sp = g.get("line_spacing_px")
            if len(ys) >= 2 and sp:
                out[st.get("staff_index")] = (min(ys), max(ys), float(sp))
    return out

def rungs_of(page, floor=None):
    """(x0, x1, yc) per ledgerLine detection, optionally confidence-floored."""
    out = []
    for sy in page.get("systems", []):
        for st in sy.get("staves", []):
            for m in st.get("measures", []):
                for d in m.get("detections", []):
                    if d.get("class") != "ledgerLine": continue
                    b = d.get("bbox_page")
                    if not b or len(b) != 4: continue
                    if floor is not None and (d.get("confidence") or 0.0) < floor:
                        continue
                    out.append((b[0], b[0] + b[2], b[1] + b[3] / 2.0))
    return out

def matched_rungs(box, band, ledgers):
    """Re-run _ledger_ladder's matching loop and RETURN the rungs it matched."""
    top, bottom, spacing = band
    x0, y0, w, h = box[0], box[1], box[2], box[3]
    yc = y0 + h / 2.0
    if yc < top: anchor, sign = top, -1.0
    elif yc > bottom: anchor, sign = bottom, 1.0
    else: return None
    n_exp = int(abs(yc - anchor) / spacing + _LEDGER_RUNG_EXPECTED_SLACK)
    if n_exp <= 0: return None
    tol = _LEDGER_RUNG_Y_TOL_SPACES * spacing
    min_ov = _LEDGER_RUNG_MIN_X_OVERLAP * max(1.0, w)
    hits = []
    for k in range(1, n_exp + 1):
        ry = anchor + sign * k * spacing
        for lx0, lx1, ly in ledgers:
            if abs(ly - ry) > tol: continue
            if min(lx1, x0 + w) - max(lx0, x0) < min_ov: continue
            hits.append((lx0, lx1, ly)); break
    return hits if len(hits) == n_exp else None

for lab, rel in FILES.items():
    doc = json.load(open(ROOT / rel))
    outside = complete = using_impossible = matched_total = 0
    surv = {}
    base_ladders = []
    for page in doc.get("pages", []):
        bands = bands_of(page)
        allb = list(bands.values())
        led_full = rungs_of(page)
        led_by_floor = {f: rungs_of(page, f) for f in (0.30, 0.40, 0.50)}
        for sy in page.get("systems", []):
            for st in sy.get("staves", []):
                own = st.get("staff_index")
                if own not in bands: continue
                band = bands[own]
                for m in st.get("measures", []):
                    for d in m.get("detections", []):
                        if d.get("category") != "notehead": continue
                        box = d.get("bbox_page")
                        if not box or len(box) != 4: continue
                        yc = box[1] + box[3] / 2.0
                        if band[0] <= yc <= band[1]: continue
                        outside += 1
                        if _ledger_ladder(box, band, led_full)[0] != 1: continue
                        complete += 1
                        base_ladders.append(1)
                        hits = matched_rungs(box, band, led_full) or []
                        matched_total += len(hits)
                        if any(any(b0 <= ly <= b1 for b0, b1, _ in allb)
                               for _, _, ly in hits):
                            using_impossible += 1
                        for f, led_f in led_by_floor.items():
                            if _ledger_ladder(box, band, led_f)[0] == 1:
                                surv[f] = surv.get(f, 0) + 1
    n_rungs = sum(len(rungs_of(p)) for p in doc.get("pages", []))
    print(f"\n=== {lab}")
    print(f"  noteheads OUTSIDE their own band            {outside}")
    print(f"  ... with a COMPLETE ladder                  {complete}")
    print(f"  ... using >=1 rung inside SOME staff's band {using_impossible}")
    print(f"  matched rungs across those ladders          {matched_total}")
    print(f"  rungs at no floor -> complete ladders       {n_rungs} -> {complete} (1.000)")
    for f in (0.30, 0.40, 0.50):
        nr = sum(len(rungs_of(p, f)) for p in doc.get("pages", []))
        s = surv.get(f, 0)
        print(f"  floor {f:.2f}: rungs {nr:5d} -> ladders {s:4d} "
              f"({s/max(complete,1):.3f})   destroyed {1 - s/max(complete,1):.3f}")
