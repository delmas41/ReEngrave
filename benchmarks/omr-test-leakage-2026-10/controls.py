"""Near-duplicate controls for leakage_guard.near_score (TS1 images are read from the 2.110 worktree, read-only).
positive = the 9 key-matched v13/TEST pairs; negative A = same page, different cell; negative B = other page/other edition."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent)); import leakage_guard as g
HERE = Path(__file__).parent; REPO = g.REPO
T = Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.110/benchmarks/omr-labeling-hollow4-test-litolff-p1-2026-10/cells")
rows = json.load(open(REPO / "benchmarks/omr-labeling-hollow4-test-litolff-p1-2026-10/cells.json"))
test = [g.Cell(r["cell_id"], T / f"{r['cell_id']}.png", (g.edition_key(r["pdf"]), r["page"], r["system_index"], r["staff_index"], r["measure_index"]), "t", r["staff_line_ys_canonical"]) for r in rows]
ul = g.MAIN / "data" / "user-labeled"
v13 = g.load_version(ul, "v13-2026-09-03-complete-v7-beet5-bolero")
v18 = g.load_version(ul, "v18-2026-09-03-complete-breitkopf")[:9]
v1 = g.load_version(ul, "v1-2026-05-18-orchestral")[:9]
pos, negA, negB = [], [], []
tk = {c.key: c for c in test}
def sc(t, c): return g.near_score(t.image(), c.image(), g.staff_space(t.image(), t.lines), g.staff_space(c.image(), c.lines))
for t in v13:
    for c in test:
        s = sc(t, c)
        if s is None: continue
        (pos if c.key == t.key else negA).append(round(s, 3))
for t in v18 + v1:
    for c in test:
        s = sc(t, c)
        if s is not None: negB.append(round(s, 3))
def summ(a): a = np.array(a); return {"n": len(a), "min": float(a.min()), "median": float(np.median(a)), "p99": float(np.percentile(a, 99)), "max": float(a.max())}
out = {"positive_same_key_pairs": summ(pos), "positive_sorted": sorted(pos), "negative_A_same_page_other_cell": summ(negA),
       "negative_A_top5": sorted(negA)[-5:], "negative_B_other_page_edition": summ(negB), "negative_B_top5": sorted(negB)[-5:]}
(HERE / "controls.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
