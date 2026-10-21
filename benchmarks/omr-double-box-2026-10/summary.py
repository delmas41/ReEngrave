"""2.185: the headline tables, both plates, both runs, from tables.py --rows output. usage: summary.py lit18 lit20 bra18 bra20 (rows files in DIR)"""
import json, sys, collections
D = sys.argv[1]
names = sys.argv[2:]
def load(n): return json.load(open("%s/%s.rows.json" % (D, n)))
def meta(n): return json.load(open("%s/%s.T0.5.json" % (D, n)))
CAUSE = {"cross_staff_crop_overlap": "cross-staff crop overlap", "same_cell_samec_lt_07": "same cell, same class, IoU .5-.7 (below NMS cut)",
         "same_cell_diff_class": "same cell, different class (class-wise NMS)", "same_cell_samec_iou_ge_07": "same cell, same class, IoU>=.7 (should not survive NMS)",
         "view_small_over_prod": "2.172 small view over a production box", "stem_end_head_over_prod": "2.179 stem-end head over a production box"}
def cg(c):
    b = c.split("+")[0]
    if b in CAUSE: return CAUSE[b]
    if b.startswith("pass_only") or b.endswith("_over_prod") or b.startswith("yolo_rescue"): return "other pass (" + b.replace("_over_prod", "") + ")"
    return b
for n in names:
    rows = load(n); m = meta(n)
    nb = sum(x["n"] for x in rows)
    print("\n==== %s: %d boxes (%d scorable); %d double-box inks (IoU>=0.5), %d boxes in them = %.1f%% of all boxes" % (n, m["nbox_all"], m["nbox_scorable"], len(rows), nb, 100 * nb / m["nbox_all"]))
    c = collections.Counter(); b = collections.Counter(); o = collections.defaultdict(collections.Counter)
    for x in rows:
        k = cg(x["cause"]); c[k] += 1; b[k] += x["n"]; o[k][x["out"]] += 1
    for k, v in c.most_common(): print("  %5d inks %6d boxes  %-58s %s" % (v, b[k], k, dict(o[k])))
    print("  -- by family (reading-relevant: >=1 judged member), outcome counts")
    f = collections.defaultdict(collections.Counter)
    for x in rows:
        if x["judged"] == 0: continue
        fam = x["fam"] if not x["fam"].startswith("X:") else "cross-family"
        f[fam][x["out"]] += 1
    for k in sorted(f, key=lambda k: -sum(f[k].values())): print("  %-14s %5d  %s" % (k, sum(f[k].values()), dict(f[k])))
