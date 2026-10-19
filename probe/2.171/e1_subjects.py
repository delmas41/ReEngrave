"""2.171 probe 1 (no detector, no records written): build the SUBJECT list for the crop-mechanism experiments from the 2.167d data files.
Subjects per plate:
  lost   the 2.167d lost real symbols (A never boxed, B under the 0.25 floor, C wrong class, D boxed then dropped by a gate) that can be
         located: B/C/D by (class, conf) match to the 0.05-floor base re-run boxes of the bar; A by the item's x position (a region).
  kept   symbols the record kept at >= 0.25 in the same 45 bars in the classes the lost ones come from (dot, flag, rest, black head),
         written (exporter fate 'written'). 'Read correctly' is OUR record's say-so, not truth (CLAUDE.md rule 7).
  judged Sean's judged tiles whose subject glyph is in one of these bars (benchmarks/acceptance/judged-tiles.json).
usage: e1_subjects.py  -> probe/2.171/data/subjects.json and a printed census"""
import collections
import json
import os
import random

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = ROOT + "/probe/2.167d/data/"
OUT = ROOT + "/probe/2.171/data/"
os.makedirs(OUT, exist_ok=True)


def fam(cls):
    if cls is None:
        return None
    if cls == "augmentationDot":
        return "dot"
    if cls.startswith("flag"):
        return "flag"
    if cls.startswith("rest"):
        return "rest"
    if cls in ("noteheadBlackOnLine", "noteheadBlackInSpace"):
        return "blackhead"
    if cls.startswith("notehead"):
        return "otherhead"
    return "other"


def want(it):
    w = it["want_family"]
    return {"notehead": "blackhead", "rest": "rest", "flag": "flag", "augmentationDot": "dot"}.get(w)


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


judged = json.load(open(ROOT + "/benchmarks/acceptance/judged-tiles.json"))["tiles"]
out = {}
random.seed(2171)
for plate in ("lit", "bra"):
    rr = json.load(open(D + "%s_rerun.json" % plate))
    rec = json.load(open(D + "%s_rec.json" % plate))
    bf = json.load(open(D + "%s_boxfates.json" % plate))
    an = json.load(open(D + "%s_items_analysed.json" % plate))["items"]
    items_raw = json.load(open(ROOT + "/probe/2.167d/items_%s.json" % plate))["bars"]
    subs = []
    # ---- lost
    for it in an:
        if it["kind"] == "extra" or it["want_family"] is None:
            continue
        key = it["key"]
        R = rr[key]
        sp = R["spacing"]
        x0, y0, x1, y1 = R["cell"]
        top, bot = R["lines"][0], R["lines"][4]
        st = it["stage"]
        if st.startswith("never boxed"):
            raw = items_raw[str(it["bar"])]["items"][it["item"]]
            # the item's index in the raw list equals `item`
            x = x0 + raw["x_sp"] * sp
            bb = [x - 0.6 * sp, top - 0.5 * sp, x + 0.6 * sp, bot + 0.5 * sp]
            cause = "A"
            region = True
        else:
            if "[in neighbour cell]" in st:
                continue
            cands = [b for b in R["variants"]["base"]["boxes"] if b[0] == it["cls"] and abs(b[1] - it["conf"]) < 0.002]
            if len(cands) != 1:
                continue
            bb = cands[0][2:6]
            region = False
            if st.startswith("boxed under"):
                cause = "C" if "wrong class" in st else "B"
            elif st.startswith("boxed >=0.25"):
                cause = "C" if (fam(it["cls"]) != want(it)) else "D"
            else:
                continue
        subs.append(dict(plate=plate, key=key, role="lost", cause=cause, bbox=[round(v, 1) for v in bb], region=region,
                         cls=it["cls"], rec_conf=it["conf"], want=want(it), what=it["what"], sure=it["sure"], kind=it["kind"]))
    nlost = len(subs)
    # ---- kept
    pool = collections.defaultdict(list)
    for key, c in rec["cells"].items():
        if key not in rr:
            continue
        fates = {r["sub"]: r["fate"] for r in bf.get(key, [])}
        for g in c["glyphs"]:
            f = fam(g["cls"])
            if f in ("dot", "flag", "rest", "blackhead") and g["conf"] >= 0.25 and (f in ("dot", "flag") or fates.get(g["sub"]) == "written"):
                pool[f].append(dict(plate=plate, key=key, role="kept", cause="", bbox=[round(v, 1) for v in g["bbox"]], region=False,
                                    cls=g["cls"], rec_conf=round(g["conf"], 3), want=f, what="kept+written in the record", sure=None, kind=""))
    print(plate, "kept pool", {k: len(v) for k, v in pool.items()})
    # balanced: up to 18 per family, preferring a spread of confidences
    for f, lst in pool.items():
        lst.sort(key=lambda s: s["rec_conf"])
        n = 26 if plate == "lit" else 20
        if len(lst) > n:
            idx = sorted(set(int(round(i * (len(lst) - 1) / (n - 1))) for i in range(n)))
            lst = [lst[i] for i in idx]
        subs.extend(lst)
    # ---- judged tiles whose glyph is in one of these bars
    bars = set(rr)
    j = []
    for t in judged:
        s = t.get("subject")
        if t.get("subject_kind") == "glyph" and s and s.startswith("glyph/"):
            k = "/".join(s.split("/")[1:5])
            if k in bars:
                j.append(dict(key=k, subject=s, answer=t["answer"], answer_kind=t["answer_kind"], item=t["item"], date=t["date"], doc=t["doc"]))
    for t in j:
        g = [g for g in rec["cells"][t["key"]]["glyphs"] if g["sub"] == t["subject"]]
        if g and fam(g[0]["cls"]) in ("dot", "flag", "rest", "blackhead", "otherhead"):
            subs.append(dict(plate=plate, key=t["key"], role="judged", cause="", bbox=[round(v, 1) for v in g[0]["bbox"]], region=False,
                             cls=g[0]["cls"], rec_conf=round(g[0]["conf"], 3), want=fam(g[0]["cls"]), what="Sean judged: %s (%s, %s)" % (t["answer"], t["item"], t["date"]), sure=None, kind=""))
    print(plate, "lost located", nlost, "of", sum(1 for it in an if it["kind"] != "extra" and it["want_family"]), "subjects", len(subs), "judged tiles in these bars", len(j))
    out[plate] = dict(subjects=subs, judged=j)
    c = collections.Counter((s["role"], s["cause"], s["want"]) for s in subs)
    for k, v in sorted(c.items()):
        print("  ", k, v)
json.dump(out, open(OUT + "subjects.json", "w"), indent=1)
