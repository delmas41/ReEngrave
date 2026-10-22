"""2.167d probe 5: join my item list (items_*.json) to the record boxes, the 0.05-floor re-run and the re-cut variants.
For each item: (1) boxed? class/conf, (2) dropped where (exporter fate / floor), (4) distance to the bar crop edge, (5) found in a re-cut variant?
Also counts the NEW notehead/rest/flag/dot boxes >= 0.25 each variant adds on the same 45 bars (candidate false boxes).
usage: d5_analyse.py lit|bra  -> data/<plate>_items_analysed.json and a printed summary"""
import collections
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = ROOT + "/probe/2.167d/"
plate = sys.argv[1]
sample = json.load(open(D + "data/%s_sample.json" % plate))
rr = json.load(open(D + "data/%s_rerun.json" % plate))
rec = json.load(open(D + "data/%s_rec.json" % plate))
bf = json.load(open(D + "data/%s_boxfates.json" % plate))
items = json.load(open(D + "items_%s.json" % plate))["bars"]
VAR = ["shiftR", "shiftL", "wide", "system"]
FAM = ("notehead", "rest", "flag", "augmentationDot")


def fam(cls):
    for f in FAM:
        if cls.startswith(f) or (f == "flag" and cls.startswith("flag")):
            return f
    if cls.startswith("F8th") or cls.startswith("F16th") or cls.startswith("F32"):
        return "flag"
    if cls == "dot":
        return "augmentationDot"
    return "other"


def want_family(it):
    w = it["what"].lower()
    if "flag" in w:
        return "flag"
    if "dot" in w and it["kind"] == "wrong_value":
        return "augmentationDot"
    if it["kind"] == "missing_rest":
        return "rest"
    if it["kind"] == "missing_head":
        return "notehead"
    return None


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


out = []
newbox = collections.defaultdict(lambda: collections.Counter())
for idx, (p, s, st, c) in enumerate(sample):
    key = "%d/%d/%d/%d" % (p, s, st, c)
    R = rr[key]
    sp = R["spacing"]
    x0, y0, x1, y1 = R["cell"]
    top, bot = R["lines"][0], R["lines"][4]
    nmap = json.load(open(D + "sheets/%s_%02d.json" % (plate, idx)))
    bar = items.get(str(idx), {})
    # new boxes per variant (whole-bar census)
    base = [b for b in R["variants"]["base"]["boxes"] if b[1] >= 0.25]
    for v in VAR:
        V = R["variants"][v]
        if "boxes" not in V:
            continue
        for b in V["boxes"]:
            if b[1] < 0.25 or fam(b[0]) == "other":
                continue
            cx = (b[2] + b[4]) / 2
            cy = (b[3] + b[5]) / 2
            if not (x0 <= cx <= x1 and top - 3 * sp <= cy <= bot + 3 * sp):
                continue
            if any(fam(a[0]) == fam(b[0]) and iou(a[2:6], b[2:6]) > 0.4 for a in base):
                newbox[v]["same_as_base"] += 1
            else:
                newbox[v]["new_" + fam(b[0])] += 1
                newbox[v]["new_total"] += 1
        # base boxes the variant loses
        for a in base:
            if fam(a[0]) == "other":
                continue
            cx = (a[2] + a[4]) / 2
            if not (x0 <= cx <= x1):
                continue
            if not any(fam(a[0]) == fam(b[0]) and iou(a[2:6], b[2:6]) > 0.4 for b in V["boxes"] if b[1] >= 0.25):
                newbox[v]["lost_from_base"] += 1
    for ii, it in enumerate(bar.get("items", [])):
        locs = []   # list of dicts: bbox, cls, conf, low, dc, sub
        if "fates" in it:
            for r in bf[key]:
                if r["fate"] != "written" and any(r["fate"].startswith(f) for f in it["fates"]):
                    g = [g for g in rec["cells"][key]["glyphs"] if g["sub"] == r["sub"]][0]
                    locs.append(dict(bbox=g["bbox"], cls=g["cls"], conf=g["conf"], low=False, dc=0, sub=r["sub"], fate=r["fate"]))
        elif it.get("refs"):
            for n in it["refs"][:1] if it["kind"] != "extra" else it["refs"]:
                m = nmap[str(n)]
                f = None
                if m["sub"]:
                    kk = "/".join(m["sub"].split("/")[1:5])
                    f = [r["fate"] for r in bf.get(kk, []) if r["sub"] == m["sub"]]
                locs.append(dict(bbox=m["bbox"], cls=m["cls"], conf=m["conf"], low=m["low"], dc=m["dc"], sub=m["sub"], fate=(f[0] if f else None)))
        else:
            x = x0 + it.get("x_sp", (x1 - x0) / sp / 2) * sp
            locs.append(dict(bbox=[x - 0.6 * sp, top - 0.5 * sp, x + 0.6 * sp, bot + 0.5 * sp], cls=None, conf=None, low=False, dc=0, sub=None, fate=None, never=True))
        wf = want_family(it)
        for lc in locs:
            b = lc["bbox"]
            cx = (b[0] + b[2]) / 2
            edge = min(cx - x0, x1 - cx) / sp
            crosses = b[0] < x0 or b[2] > x1
            if lc.get("never"):
                stage = "never boxed (no box >=0.05)"
            elif lc["conf"] is not None and lc["conf"] < 0.25:
                stage = "boxed under the 0.25 floor" + ("" if (wf is None or fam(lc["cls"]) == wf) else " (wrong class)")
            elif it["kind"] == "extra":
                stage = "boxed >=0.25, not a symbol of this bar, written (%s)" % fam(lc["cls"])
            elif it["kind"] == "wrong_value":
                stage = "boxed >=0.25 (%s), value not applied" % fam(lc["cls"])
            elif lc.get("fate") and lc["fate"] != "written":
                stage = "boxed >=0.25, dropped by gate: %s" % lc["fate"].split(" dur")[0][:40]
            else:
                stage = "boxed >=0.25 (%s), other" % fam(lc["cls"] or "x")
            if lc.get("dc"):
                stage += " [in neighbour cell]"
            # variant recovery for items that can be re-found
            found = {}
            if it["kind"] != "extra" and wf:
                for v in VAR:
                    V = R["variants"][v]
                    hit = None
                    if "boxes" in V:
                        for vb in V["boxes"]:
                            if vb[1] < 0.25 or fam(vb[0]) != wf:
                                continue
                            if lc.get("never"):
                                vx = (vb[2] + vb[4]) / 2
                                vy = (vb[3] + vb[5]) / 2
                                ok = abs(vx - (b[0] + b[2]) / 2) < 0.9 * sp and top - 1.5 * sp <= vy <= bot + 1.5 * sp
                            else:
                                ok = iou(vb[2:6], b) > 0.3 or (abs((vb[2] + vb[4]) / 2 - cx) < 0.5 * sp and abs((vb[3] + vb[5]) / 2 - (b[1] + b[3]) / 2) < 0.5 * sp)
                            if ok:
                                hit = [vb[0], vb[1]]
                                break
                    found[v] = hit
                # also: base itself at >=0.25 with right family (control: should be none for lost items)
            out.append(dict(plate=plate, bar=idx, key=key, item=ii, kind=it["kind"], sure=it["sure"], what=it["what"], cls=lc["cls"], conf=lc["conf"],
                            stage=stage, edge_sp=round(edge, 2), crosses_edge=crosses, found=found, want_family=wf, bar_fam=bar.get("fam")))
json.dump(dict(items=out, newbox={k: dict(v) for k, v in newbox.items()}), open(D + "data/%s_items_analysed.json" % plate, "w"), indent=1)
print(plate, "items", len(out))
C = collections.Counter((o["kind"], o["stage"]) for o in out)
for k, v in sorted(C.items(), key=lambda kv: -kv[1]):
    print(v, k)
print("new boxes per variant (45 bars):", {k: dict(v) for k, v in newbox.items()})
