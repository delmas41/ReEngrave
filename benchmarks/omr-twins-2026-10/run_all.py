import json, sys, collections, statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import match as M, analyze as A, raster as R
from match import REPO, OUT

def load(name): return json.load(open(OUT / name))

# ============ BRAHMS ==========================================================
bd = load("brahms_p0.json"); bg = bd["glyphs"]
bt, b_unins = M.truth_notes_brahms()
M.match_brahms(bg, bt)
stems, bcells = A.brahms_stems()
gray_b = R.page_gray(bd["pdf"], 0)
agree = collections.Counter()
for t in bt:
    t["cell_rect"] = list(bcells[t["cell"]].rect)
    t["stem"] = A.stem_dir_truth(t, stems)
    t["posk"] = A.pos_kind_brahms(t, bcells)
    rs = R.stem_side(gray_b, t["rect"], t["space"])[0]
    agree[(t["stem"], rs)] += 1
print("raster stem reader vs Sean's stem boxes (Brahms):", dict(agree))
sp_b = lambda t: t["space"]
b_pairs, b_unp = A.analyze("brahms", bg, bt, sp_b)

# ============ LITOLFF =========================================================
ld = load("litolff_p1.json"); lg = ld["glyphs"]
lt, l_all, l_cells, l_leak = M.litolff_truth()
cellsj = {(int(c["system_index"]), int(c["staff_index"]), int(c["measure_index"])): c
          for c in json.loads((REPO / "benchmarks/omr-labeling-hollow4-test-litolff-p1-2026-10/cells.json").read_text())}
for t in lt:
    c = cellsj[t["cell"]]; ys = c["staff_line_ys_canonical"]
    t["space"] = sum(ys[i+1]-ys[i] for i in range(4)) / 4
    t["staff_top_c"], t["staff_bot_c"] = ys[0], ys[4]
M.match_litolff(lg, lt)
# cell canonical -> page affine from glyphs that carry both boxes
aff = {}
by = collections.defaultdict(list)
for k, g in lg.items():
    if g["box_canon"] and g["box_page"]: by[(g["system"], g["staff"], g["cell"])].append(g)
for key, gs in by.items():
    sx = statistics.median([(g["box_page"][2]-g["box_page"][0]) / (g["box_canon"][2]-g["box_canon"][0]) for g in gs if g["box_canon"][2] > g["box_canon"][0]])
    sy = statistics.median([(g["box_page"][3]-g["box_page"][1]) / (g["box_canon"][3]-g["box_canon"][1]) for g in gs if g["box_canon"][3] > g["box_canon"][1]])
    ox = statistics.median([g["box_page"][0] - g["box_canon"][0]*sx for g in gs]); oy = statistics.median([g["box_page"][1] - g["box_canon"][1]*sy for g in gs])
    aff[key] = (sx, sy, ox, oy, len(gs))
gray_l = R.page_gray(ld["pdf"], 1)
for t in lt:
    a = aff.get(t["cell"])
    if a:
        r = t["rect"]; t["rect_page"] = [r[0]*a[0]+a[2], r[1]*a[1]+a[3], r[2]*a[0]+a[2], r[3]*a[1]+a[3]]; t["scale"] = a[0]
        sp_page = t["space"]*a[1]
        st, up, dn = R.stem_side(gray_l, t["rect_page"], sp_page)
        t["stem"] = st if st in ("up", "down", "none") else "both?"
        t["stem_raster"] = [st, up, dn]
    else:
        t["rect_page"] = None; t["stem"] = "?"
    ys_top, ys_bot = t["staff_top_c"], t["staff_bot_c"]
    cy = (t["rect"][1]+t["rect"][3])/2
    t["posk"] = "ledger" if (cy < ys_top - 0.6*t["space"] or cy > ys_bot + 0.6*t["space"]) else t["pos"]
sp_l = lambda t: t["space"]
l_pairs, l_unp = A.analyze("litolff", lg, lt, sp_l)
json.dump({"brahms": {"truth": bt, "pairs": b_pairs, "unpaired": b_unp, "n_truth_in_uninspected_cells_excluded": b_unp and b_unins or b_unins},
           "litolff": {"truth": lt, "pairs": l_pairs, "unpaired": l_unp, "n_all_test_heads": l_all, "n_leaked_heads_dropped": l_all - len(lt), "cells": l_cells, "leaked_cells": l_leak}},
          open(OUT / "analysis.json", "w"), default=str)
for nm, tt, pp, uu in (("brahms", bt, b_pairs, b_unp), ("litolff", lt, l_pairs, l_unp)):
    print(nm, "truth", len(tt), "written", sum(t["stage"] == 7 for t in tt), "missed", sum(t["stage"] < 7 for t in tt), "pairs", len(pp), "unpaired", len(uu))
    print("  sig counts", collections.Counter((t["kind"], t["stem"], t["posk"]) for t in tt).most_common(20))
