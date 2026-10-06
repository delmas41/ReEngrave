"""Summarise staff_lines_per_bar.py output: (a) raw vs (b) per-bar grid, per cell and per sample."""
import json, sys
import numpy as np

rows = []
for p in sys.argv[1:]:
    rows += json.load(open(p))
for doc in sorted({r["doc"] for r in rows}):
    sub = [r for r in rows if r["doc"] == doc]
    cells = [(r["sp"], c) for r in sub for c in r["cells"] if c.get("n", 0) >= 2]
    n_all = sum(len(r["cells"]) for r in sub)
    print(f"[{doc}] staves {len(sub)}  cells {n_all}  cells with >=2 clean samples {len(cells)}")
    for name, key_med, key_max in (("(a) raw staff-wide", "a_med", "a_max"), ("(b) per-bar grid", "b_med", "b_max")):
        med = np.array([abs(c[key_med]) for sp, c in cells])
        mx = np.array([c[key_max] for sp, c in cells])
        sps = np.array([sp for sp, c in cells])
        print(f"  {name}: |cell median offset| median {np.median(med):.1f}px p90 {np.percentile(med,90):.1f} max {med.max():.1f};"
              f" cell max-offset p90 {np.percentile(mx,90):.1f}px;"
              f" cells with median >= 0.25sp: {int((med/sps>=0.25).sum())}, >= 0.4sp: {int((med/sps>=0.4).sum())};"
              f" cells with ANY point >= 0.25sp: {int((mx/sps>=0.25).sum())}, >= 0.4sp: {int((mx/sps>=0.4).sum())}")
    tilt = np.array([abs(c["b_tilt_px"]) for sp, c in cells])
    sps = np.array([sp for sp, c in cells])
    print(f"  (b) tilt ACROSS one bar (linear fit x cell width): median {np.median(tilt):.1f}px p90 {np.percentile(tilt,90):.1f} max {tilt.max():.1f};"
          f" >= 0.25sp in {int((tilt/sps>=0.25).sum())} cells")
    unl = [(sp, c) for sp, c in cells if c["shift"] == 0]
    print(f"  cells not shifted (shift 0): {len(unl)}; of those, raw median >= 0.25sp: {sum(1 for sp,c in unl if abs(c['a_med'])/sp>=0.25)}")
    # staves where (a) off >= .4 sp at some cell but (b) not
    fix = bad_b = 0
    for r in sub:
        cs = [c for c in r["cells"] if c.get("n", 0) >= 2]
        if not cs:
            continue
        a = max(abs(c["a_med"]) for c in cs) / r["sp"]; b = max(abs(c["b_med"]) for c in cs) / r["sp"]
        if a >= 0.4 and b < 0.25: fix += 1
        if b >= 0.4: bad_b += 1
    print(f"  staves with a cell median >=0.4sp raw: ... made <0.25sp in every cell by the per-bar grid: {fix}; staves still >=0.4sp in some cell under (b): {bad_b}")
    worst = sorted([(abs(c["b_med"]) / r["sp"], r["staff"], c) for r in sub for c in r["cells"] if c.get("n", 0) >= 3], key=lambda t: -t[0])[:8]
    for v, s, c in worst:
        print(f"    worst (b) cell: staff {s} x {c['x0']}-{c['x1']} shift {c['shift']} b_med {c['b_med']} ({v:.2f} sp) b_max {c['b_max']} n {c['n']}")
