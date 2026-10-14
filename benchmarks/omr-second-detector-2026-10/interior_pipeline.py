"""The 2.88 centre ink AS THE PIPELINE FILED IT (`Q.NOTEHEAD_INK` raw / off-line centre, on the detector box, canonical frame, OFF record) for the
production BLACK-class boxes of the 95 clean Litolff cells, split by Sean's hand truth: a truth hollow head under a black box (the real
disagreement population) vs a black box no truth hollow matches. usage: interior_pipeline.py"""
import collections, json, sys, statistics
from pathlib import Path
import numpy as np
sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-second-detector-2026-10")
import importlib.util
sp_ = importlib.util.spec_from_file_location("score_ab", "benchmarks/omr-labeling-hollow4-2026-10/score_ab.py"); S = importlib.util.module_from_spec(sp_); sp_.loader.exec_module(S)
import score_second as SS
from tools.omr.staged import readout as RO
run = RO.load_run("runs/2.114/ab/rec-lit-off.json")
truth, n, cellset = S.litolff_truth(); leak = SS.leaked_cells(); clean = {k for k in cellset if k not in leak}
ink = {o["subject"]: o for o in run.observations if o["quantity"] == "notehead_ink"}
rows = collections.defaultdict(list)
for g in run.glyphs.values():
    k = (g.system, g.staff, g.cell)
    if g.page != 1 or k not in clean or not (g.cls or "").startswith("noteheadBlack") or g.box_canon is None: continue
    o = ink.get(g.key)
    if not o: continue
    d = o["detail"]; w = lambda r: ((d.get(r) or {}).get("windows") or {}).get("center")
    lab = "hollow under black box" if any(S.same(t, g.box_canon) for t in truth.get(k, [])) else "black, no truth hollow"
    rows[lab].append((w("ink_raw"), w("ink_off_line"), g.key))
for lab, v in rows.items():
    for j, name in ((0, "raw centre"), (1, "off-line centre")):
        x = np.array([r[j] for r in v if r[j] is not None], float)
        print(f"{lab:24s} {name:16s} n={len(x):3d} min {x.min():.2f} p5 {np.percentile(x,5):.2f} med {np.median(x):.2f} p95 {np.percentile(x,95):.2f} max {x.max():.2f}  <0.90: {int((x<0.9).sum())}")
