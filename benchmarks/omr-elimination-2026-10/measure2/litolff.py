"""2.120 round 2 (4): Litolff 984073 idx 1 hollow4 TEST cells (Sean, 2026-10-13) through the round-2 table.
Truth = his 59 hollow heads (all half heads; classes noteheadHalfOnLine/InSpace) in the cell's CANONICAL frame; 2.112's 9 leaked cells
dropped -> 50. Canonical -> page is an exact per-cell affine map read off the record's own glyph pairs (box_canon <-> box_page; residual 1e-12),
so nothing is cut or invented. Staff lines: cells.json staff_line_ys_canonical mapped the same way; ink fill from the 600 dpi page raster.
python3 measure2/litolff.py > measure2/litolff.out   (needs measure2/litolff_p1.pkl)"""
import json, glob, sys, pickle, collections
import numpy as np
sys.path.insert(0, ".")
import table as T1, table2 as T2, descriptors as D1, descriptors2 as D
HT = "/Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-labeling-hollow4-test-litolff-p1-2026-10/"
LEAK = {"litolffp1-p2-sys0-" + k for k in "s2-m3 s3-m6 s3-m7 s3-m8 s3-m11 s3-m14 s7-m1 s8-m8 s9-m15".split()}
P = pickle.load(open("measure2/litolff_p1.pkl", "rb"))
cells = json.load(open(HT + "cells.json")); byid = {c["cell_id"]: c for c in cells}
by = collections.defaultdict(list)
for g in P["rows"]:
    if g["box_canon"] and g["box_page"]: by[(g["system"], g["staff"], g["cell"])].append(g)
last = collections.defaultdict(int)
for g in P["rows"]: last[g["system"]] = max(last[g["system"]], g["cell"])
def fit(gs):
    X = np.array([[g["box_canon"][i], 1] for g in gs for i in (0, 2)]); xp = np.array([g["box_page"][i] for g in gs for i in (0, 2)])
    Y = np.array([[g["box_canon"][i], 1] for g in gs for i in (1, 3)]); yp = np.array([g["box_page"][i] for g in gs for i in (1, 3)])
    return np.linalg.lstsq(X, xp, rcond=None)[0], np.linalg.lstsq(Y, yp, rcond=None)[0]
class M(D1.StaffModel):
    def __init__(self):
        self.cells = []; self.maps = {}
M_ = M()
for c in cells:
    k = (c["system_index"], c["staff_index"], c["measure_index"]); gs = by.get(k, [])
    if not gs: continue
    ax, ay = fit(gs); M_.maps[c["cell_id"]] = (ax, ay)
    lines = sorted(ay[0] * y + ay[1] for y in c["staff_line_ys_canonical"])
    M_.cells.append(dict(id=c["cell_id"], system=c["system_index"], staff=c["staff_index"], measure=c["measure_index"],
                         x0=ax[1], x1=ax[0] * c["cell_canonical_w"] + ax[1], lines=lines, sp=float(np.mean(np.diff(lines)))))
M_.first = {}; M_.last = dict(last); M_.sys_x0 = {}
for c in M_.cells:
    M_.first[c["system"]] = 0
    if c["measure"] == 0: M_.sys_x0[c["system"]] = min(M_.sys_x0.get(c["system"], 1e9), c["x0"])
for c in M_.cells: M_.sys_x0.setdefault(c["system"], c["x0"])
g = D1.page_gray(P["pdf"], P["page"], P["dpi"])
def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    return i / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i) if i > 0 else 0.0
heads = []
for f in sorted(glob.glob(HT + "verdicts/*.verdict.json")):
    v = json.load(open(f))
    for d in v["added_detections"]:
        if d["human_class"].startswith(("noteheadHalf", "noteheadWhole", "noteheadDoubleWhole")):
            b = d["bbox"]; heads.append(dict(cell=v["cell_id"], cls=d["human_class"], canon=(b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"])))
print("truth hollow heads:", len(heads), "| in leaked cells:", sum(h["cell"] in LEAK for h in heads), "| cells with no record glyph (cannot be mapped):", sorted({h["cell"] for h in heads if h["cell"] not in M_.maps}))
S1, S2 = T1.S, T2.SYMBOLS
SB = T2.build(litolff=False)   # R2D: everything measured on Brahms, before the Litolff fix
rows = []
for h in heads:
    if h["cell"] not in M_.maps: continue
    ax, ay = M_.maps[h["cell"]]; c = byid[h["cell"]]
    pr = (ax[0]*h["canon"][0] + ax[1], ay[0]*h["canon"][1] + ay[1], ax[0]*h["canon"][2] + ax[1], ay[0]*h["canon"][3] + ay[1])
    d = D.describe(pr, g, M_)
    k = (c["system_index"], c["staff_index"], c["measure_index"])
    near = max(((iou(h["canon"], gl["box_canon"]), gl) for gl in by.get(k, [])), key=lambda z: z[0], default=(0, None))
    sym = "head_whole" if "Whole" in h["cls"] else "head_half"
    c2, _ = T2.candidates(d); c1, _ = T1.candidates(d); cb, _ = T2.candidates(d, SB)
    rows.append(dict(cell=h["cell"], leaked=h["cell"] in LEAK, sym=sym, d=d, all2=sorted(c2["all"]), allB=sorted(cb["all"]), all1=sorted(c1["all"]), conv2=sorted(c2["conv"]),
                     det_iou=near[0], det_cls=near[1]["cls"] if near[1] else None, det_status=near[1]["status"] if near[1] else None, det_score=near[1]["score"] if near[1] else None,
                     det_page=near[1]["box_page"] if near[1] else None))
json.dump(rows, open("measure2/litolff_rows.json", "w"), default=float)
def block(title, rs):
    n = len(rs)
    print("\n== %s (n=%d) ==" % (title, n))
    if not n: return
    for key, nm in (("all1", "round-1 table"), ("allB", "R2D (Brahms-measured only)"), ("all2", "R2DL FINAL (+Litolff head_half fill)"), ("conv2", "conventions only")):
        s = sum(r["sym"] in r[key] for r in rs)
        print("  %-18s hollow head survives: %d/%d (%.1f%%) | set size median %.0f max %d" % (nm, s, n, 100 * s / n, np.median([len(r[key]) for r in rs]), max(len(r[key]) for r in rs)))
    sz = collections.Counter(tuple(r["all2"]) for r in rs).most_common(4); print("  top sets:", [("/".join(a), b) for a, b in sz])
    w = [r["d"]["w"] for r in rs]; h = [r["d"]["h"] for r in rs]; f = [r["d"]["fill"] for r in rs]; cf = [r["d"]["cfill"] for r in rs]
    print("  truth head size sp: w %.2f-%.2f (med %.2f) h %.2f-%.2f (med %.2f) | fill %.2f-%.2f | centre-40%% fill %.2f-%.2f | loc %s | zone %s" % (
        min(w), max(w), np.median(w), min(h), max(h), np.median(h), min(f), max(f), min(cf), max(cf), dict(collections.Counter(r["d"]["loc"] for r in rs)), dict(collections.Counter(r["d"]["zone"] for r in rs))))
    for r in rs:
        if r["sym"] not in r["all2"]: print("   FAIL(final)", r["cell"], "w%.2f h%.2f fill%.2f %s %s" % (r["d"]["w"], r["d"]["h"], r["d"]["fill"], r["d"]["loc"], r["d"]["zone"]), r["all2"])
clean = [r for r in rows if not r["leaked"]]
block("CLEAN hollow TEST heads, Sean's tight boxes", clean)
block("all 59 (incl. 9 leaked cells -- a table has no training, so leakage cannot inflate it; shown for completeness)", rows)
print("\n== detector side, the clean heads ==")
dd = [r for r in clean if r["det_iou"] >= 0.5]
print("heads with a detector box at IoU >= 0.5 (canonical frame): %d/%d | none: %d" % (len(dd), len(clean), len(clean) - len(dd)))
print(" detector classes on them:", collections.Counter(r["det_cls"] for r in dd), "| status", collections.Counter(r["det_status"] for r in dd))
hol = [r for r in dd if str(r["det_cls"]).startswith(("noteheadHalf", "noteheadWhole"))]
blk = [r for r in dd if str(r["det_cls"]).startswith("noteheadBlack")]
dpage = []
for r in dd:
    d = D.describe(r["det_page"], g, M_); c2, _ = T2.candidates(d); dpage.append((r, d, c2))
print(" hollow-class detector boxes: %d; their class survives the table: %d; true head symbol in set: %d" % (len(hol), sum(T1.symbol_of(r["det_cls"]) in c["all"] for r, d, c in dpage if r in hol), sum(r["sym"] in c["all"] for r, d, c in dpage if r in hol)))
print(" BLACK-class boxes on true hollow heads (hollow called black): %d; table eliminates the black class: %d (caught); true head symbol in set: %d" % (
    len(blk), sum("head_black" not in c["all"] for r, d, c in dpage if r in blk), sum(r["sym"] in c["all"] for r, d, c in dpage if r in blk)))
for r, d, c in dpage:
    if r in blk: print("   black-on-hollow", r["cell"], "box w%.2f h%.2f fill%.2f cfill%.2f" % (d["w"], d["h"], d["fill"], d["cfill"]), "set", "/".join(sorted(c["all"])))
print(" cfill (centre 40%%) truth hollow heads: %s" % sorted(round(r["d"]["cfill"], 2) for r in clean))
