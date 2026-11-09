"""2.280 r2: for each of the old micro's false-stem heads, what ELSE has a box on that ink in the re-adjudicated record (flag ON), and what did every
verdict say about the head box (notehead / accidental precision, accidental_owner, stroke owner).  usage: q3_five.py REC_ROOT PLATE"""
import collections
import json
import sys

root, plate = sys.argv[1:3]
res = json.load(open("out/2.280-micro/proto_%s.json" % plate))["results"]
subs = [s for s, r in res.items() if "notnote30" in r["groups"] and r["B"]["status"] == "filed"]
if len(sys.argv) > 3:
    subs = [s for s, r in res.items() if "notnote30" in r["groups"]]
glyph, cellof = {}, collections.defaultdict(list)
cls_names = {}
for line in open(root + "/" + plate + "/observations.jsonl"):
    if '"glyph_box"' in line:
        o = json.loads(line)
        if o["quantity"] == "glyph_box" and o["detail"].get("bbox_page_px"):
            cell = "cell/" + o["subject"][6:].rsplit("/", 1)[0]
            glyph[o["subject"]] = dict(cls=o["value"][0], name=o["detail"].get("name") or o["detail"].get("category"), box=o["detail"]["bbox_page_px"],
                                       score=o.get("score"), cell=cell, reader=o.get("reader"))
            cellof[cell].append(o["subject"])
want = {s for s in subs}
cells = {glyph[s]["cell"] for s in want if s in glyph}
verd = collections.defaultdict(list)
owner = {}
for line in open(root + "/" + plate + "/verdicts.jsonl"):
    if not any(("/%s" % c[5:]) in line or c in line for c in cells):
        continue
    v = json.loads(line)
    if v["subject"].startswith("glyph/") and v["subject"] in cellof.get(("cell/" + v["subject"][6:].rsplit("/", 1)[0]), []) and \
            ("cell/" + v["subject"][6:].rsplit("/", 1)[0]) in cells:
        verd[v["subject"]].append((v["quantity"], v["outcome"], v.get("reason"), v["value"] if not isinstance(v["value"], (dict, list)) else "..."))
    elif v["subject"] in cells and v["quantity"] == "stroke_owner":
        owner[v["subject"]] = v


def ov(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    ia = ix * iy
    return ia / max(1.0, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))


for s in subs:
    g = glyph.get(s)
    print("\n==", s, "label", res[s]["label"], "box", [round(x) for x in g["box"]], "cls", g["cls"], g["name"])
    for t in cellof[g["cell"]]:
        h = glyph[t]
        o = ov(g["box"], h["box"])
        if o >= 0.3:
            print("   box", t.split("/")[-1], "cls", h["cls"], h["name"], "score %.2f" % (h["score"] or 0), "overlap %.2f" % o, "reader", h["reader"])
            for q in verd.get(t, []):
                if q[0] in ("notehead_is_not_a_notehead", "accidental_is_not_an_accidental", "accidental_owner", "page_mark", "ledger_is_not_a_ledger") or "claim" in str(q[2]):
                    print("        ", q)
    ov_ = owner.get(g["cell"])
    if ov_:
        d = ov_.get("detail") or {}
        cf = d.get("claim_final") or {}
        print("   claim_final held:", {k: v for k, v in (cf.get("held") or {}).items() if k.startswith(s.rsplit("/", 1)[0])}, "marks:", {k: v for k, v in (cf.get("marks") or {}).items() if k.startswith(s.rsplit("/", 1)[0])})
