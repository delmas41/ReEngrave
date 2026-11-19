"""2.322 measure 3, hand-labelled page: Brahms p0 (data/hand-truth, Sean's labels). A head box is a REAL head when a labelled notehead (any notehead class) overlaps it
(IoU >= 0.3), NOT a head otherwise. Cross with the box's claimant share and written flag.    python3 truth_p0.py DATADIR"""
import collections
import json
import pathlib
import sys

from tools.omr.staged import claim_readout as CR

data = pathlib.Path(sys.argv[1])
pg = 0
page = json.load(open("data/hand-truth/pages/imslp317803/0.json"))
truth = [b for b in page["boxes"] if str(b["cls"]).lower().startswith("notehead")]
print("labelled noteheads on Brahms p0:", len(truth), "of", len(page["boxes"]), "boxes")
LATER = {"accidental", "arc", "hairpin", "dynamic", "mark", "dot", "rest"}
heads = [h for h in json.load(open(data / "brahms_heads2.json")) if h["page"] == pg]


def iou(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x1 - x0) * max(0, y1 - y0)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


rows = []
for h in heads:
    best = max((iou(h["box"], t["rect"]) for t in truth), default=0.0)
    sh = h["share"]
    k = max(sh, key=lambda x: sh[x]) if sh else None
    rows.append({"subject": h["subject"], "real": best >= 0.3, "iou": round(best, 2), "written": h["written"], "claimant": k, "share": sh.get(k, 0.0) if k else 0.0,
                 "head_only_px": h["head_only_px"], "none_share": h["none_share"], "beam_role_share": h.get("beam_role_share")})
tab = collections.Counter()
for r in rows:
    band = "none" if r["share"] == 0 else ("<.10" if r["share"] < 0.1 else (".10-.50" if r["share"] < 0.5 else ">=.50"))
    tier = "-" if not r["claimant"] else ("later" if r["claimant"] in LATER else "earlier")
    tab[(band, tier, "real" if r["real"] else "NOT a head", "written" if r["written"] else "unwritten")] += 1
print("head boxes on p0:", len(rows))
for k in sorted(tab):
    print("  ", k, tab[k])
print("written, NOT a labelled head:", sum(1 for r in rows if r["written"] and not r["real"]), "| written and real:", sum(1 for r in rows if r["written"] and r["real"]))
for X in (0.1, 0.25, 0.5):
    sel = [r for r in rows if r["claimant"] and r["share"] >= X and r["written"]]
    print("written boxes with a claimant share >= %.2f: %d, real %d, not a head %d" % (X, len(sel), sum(r["real"] for r in sel), sum(not r["real"] for r in sel)))
    for r in sel:
        if not r["real"]:
            print("      not a head:", r["subject"], r["claimant"], r["share"], "head-only px", r["head_only_px"])
nb = [r for r in rows if r["written"] and (r["beam_role_share"] or 0) >= 0.5]
print("written with beam-role stroke ink >= .5 of box: %d, real %d" % (len(nb), sum(r["real"] for r in nb)))
nn = [r for r in rows if r["written"] and r["none_share"] >= 0.5]
print("written with no-owner ink >= .5 of box: %d, real %d" % (len(nn), sum(r["real"] for r in nn)))
json.dump(rows, open(data / "brahms_p0_truth_cross.json", "w"), indent=1)
