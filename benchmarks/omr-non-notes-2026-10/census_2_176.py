"""2.176 step 1b: for every UNREFUSED decided head (notehead_is_not_a_notehead decided False; duration decided), how much of its box lies on a
box of ANOTHER detector class on the same page (rest, accidental, dynamic, clef, time_sig, articulation, ornament, flag, stem, barline...)?
Output: scratch/census176_DOC.json rows {subject, held, cls, w, h (spaces), best:[class, head_cover, other_cover, other_conf]...}.
usage: census_2_176.py DOC OFFJSON REFUSEDJSON OUT"""
import collections
import glob
import json
import os
import sys

DOC, OFF, REF, OUT = sys.argv[1:5]
off = json.load(open(OFF))
held = {tuple(h) for h in off["held_bars"]}
refused = json.load(open(REF))
glyphs = off["glyphs"]
rows = []
for p in sorted(glob.glob("scratch/slices/%s/p*.observations.jsonl" % DOC)):
    pg = int(os.path.basename(p)[1:3])
    boxes = []   # (subject, class, category, x0,y0,x1,y1, conf)
    conf = {}
    cellspace = {}
    for line in open(p):
        o = json.loads(line)
        q = o["quantity"]
        if q == "glyph_box":
            bb = (o.get("detail") or {}).get("bbox_page_px")
            if bb:
                boxes.append([o["subject"], o["value"][0], (o.get("detail") or {}).get("category"), bb[0], bb[1], bb[2], bb[3], o["value"]])
        elif q == "glyph_conf":
            conf[o["subject"]] = o["value"]
        elif q == "cell_staff_space":
            cellspace[o["subject"]] = o["value"]
    for b in boxes:
        s = b[0]
        if b[2] != "notehead" or glyphs.get(s) is None:
            continue
        v = glyphs[s]
        if v["rest"] or v["measure_rest"] or v["outcome"] != "decided":
            continue
        r = refused.get(s)
        if r is None or r[1] is True:
            continue
        parts = s.split("/")
        bar = (int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
        ax0, ay0, ax1, ay1 = b[3:7]
        aa = max(ax1 - ax0, 1e-9) * max(ay1 - ay0, 1e-9)
        k = (ax1 - ax0) / float(b[7][3])          # page px per canonical px
        sp = 100.0 * k
        hits = []
        for o in boxes:
            if o[0] == s or o[2] == "notehead" or o[2] == "staff":
                continue
            bx0, by0, bx1, by1 = o[3:7]
            iw = min(ax1, bx1) - max(ax0, bx0)
            ih = min(ay1, by1) - max(ay0, by0)
            if iw <= 0 or ih <= 0:
                continue
            inter = iw * ih
            ba = max(bx1 - bx0, 1e-9) * max(by1 - by0, 1e-9)
            hits.append([o[1], o[2], round(inter / aa, 3), round(inter / ba, 3), round(conf.get(o[0], -1), 3), round(conf.get(s, -1), 3), o[0]])
        hits.sort(key=lambda h: -h[2])
        rows.append(dict(subject=s, held=bar in held, cls=b[1], w=round((ax1 - ax0) / sp, 3), h=round((ay1 - ay0) / sp, 3), conf=round(conf.get(s, -1), 3), hits=hits[:4]))
json.dump(rows, open(OUT, "w"))
c = collections.Counter()
for r in rows:
    for h in r["hits"][:1]:
        if h[2] >= 0.5:
            c[(h[1], h[0], r["held"])] += 1
print(DOC, "unrefused decided heads", len(rows), "held", sum(r["held"] for r in rows))
for k, n in sorted(c.items(), key=lambda kv: -kv[1])[:60]:
    print(n, k)
