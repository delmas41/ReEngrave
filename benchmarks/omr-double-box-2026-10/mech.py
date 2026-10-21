"""2.185: assign each T>=THRESH cluster ONE cause by rule, from extract + pairs. usage: mech.py EXTRACT.json PAIRS.json THRESH OUT.json
Cause ladder (first that holds):
  production boxes only (reader `detector`), two or more on one ink (connected under IoU>=THRESH among production boxes alone):
     cross_staff_crop_overlap   the production boxes sit in cells of different staves (two cell crops overlap, each runs the detector)
     same_cell_samec_iou_ge_07  same cell, same class, IoU>=0.7: class-wise NMS at 0.7 should have suppressed it  (ANOMALY)
     same_cell_samec_lt_07      same cell, same class, 0.3..0.7 (below the NMS cut)
     same_cell_diff_class       same cell, different classes (class-wise NMS never compares classes)
  otherwise the ink holds <=1 production box and a later pass added boxes:
     view_small_over_prod / stem_end_head_over_prod / lowconf_over_prod / letter_look_over_prod   (one production box + pass box(es))
     pass_only                  no production box at all (pass boxes among themselves)"""
import json, sys, collections
ex, pr, T, out = sys.argv[1:5]; T = float(T)
d = json.load(open(ex)); P = json.load(open(pr))["pairs"]
bx = [b for b in d["boxes"] if b["bbox"] and b["cls"] not in ("staff", "brace")]
parent = list(range(len(bx)))
def find(x):
    while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
    return x
E = [p for p in P if p["iou"] >= T]
for p in E: parent[find(p["a"])] = find(p["b"])
iou = {}
for p in E: iou[(p["a"], p["b"])] = p["iou"]
cl = collections.defaultdict(list)
for i in range(len(bx)): cl[find(i)].append(i)
cl = [v for v in cl.values() if len(v) > 1]
def staff(i): return "/".join(bx[i]["subject"].split("/")[:4])
def cell(i): return "/".join(bx[i]["subject"].split("/")[:5])
res = {}
for c in cl:
    prod = [i for i in c if bx[i]["reader"] == "detector"]
    other = [i for i in c if bx[i]["reader"] != "detector"]
    # production-only components
    pp = {}
    for i in prod: pp[i] = i
    def f2(x):
        while pp[x] != x: pp[x] = pp[pp[x]]; x = pp[x]
        return x
    pe = [(a, b) for (a, b) in iou if a in pp and b in pp]
    for a, b in pe: pp[f2(a)] = f2(b)
    comps = collections.defaultdict(list)
    for i in prod: comps[f2(i)].append(i)
    dbl = [v for v in comps.values() if len(v) > 1]
    if dbl:
        mem = max(dbl, key=len)
        if len({staff(i) for i in mem}) > 1: cause = "cross_staff_crop_overlap"
        else:
            cls = {bx[i]["cls"] for i in mem}
            if len(cls) > 1: cause = "same_cell_diff_class"
            else:
                m = max((iou.get((min(a, b), max(a, b)), 0) for a in mem for b in mem if a != b), default=0)
                cause = "same_cell_samec_iou_ge_07" if m >= 0.7 else "same_cell_samec_lt_07"
        if other: cause += "+pass"
    else:
        kinds = {bx[i]["reader"] for i in other}
        names = {"yolo_detector_view": "view_small", "yolo_rescue_stem_head": "stem_end_head", "yolo_rescue_lowconf": "lowconf", "yolo_letter_look": "letter_look"}
        tag = "+".join(sorted(names.get(k, k) for k in kinds))
        cause = (tag + "_over_prod") if prod else "pass_only:" + tag
    res[tuple(sorted(c))] = cause
cnt = collections.Counter(res.values())
json.dump({",".join(map(str, k)): v for k, v in res.items()}, open(out, "w"))
for k, v in cnt.most_common(): print("%6d  %s" % (v, k))
