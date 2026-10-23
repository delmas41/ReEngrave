"""2.200 N6: which no_candidate boxes are the SAME INK as an accidental box in a neighbouring cell/staff whose owner DECIDED (a duplicate, harmless).
usage: n6_twins.py RECORD.json FEATURES.json OUT.json   (page-px IoU >= 0.3 or one box inside the other >= 0.6, different cell, accidental-class, owner decided)"""
import sys, json, collections
d = json.load(open(sys.argv[1])); rec = d.get("record", d); F = json.load(open(sys.argv[2]))
chains = collections.defaultdict(list)
for v in rec["verdicts"]:
    if v["quantity"] == "accidental_owner": chains[v["subject"]].append(v)
live = {}
for k, ch in chains.items():
    sup = {x.get("supersedes") for x in ch if x.get("supersedes")}; live[k] = ([x for x in ch if x["id"] not in sup] or ch)[-1]
acc = collections.defaultdict(list)
for o in rec["observations"]:
    if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("category") == "accidental" and not o["value"][0].lower().startswith("key"):
        b = (o.get("detail") or {}).get("bbox_page_px")
        if b: acc[int(o["subject"].split("/")[1])].append((o["subject"], b, o["value"][0]))
def rel(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    aa = (a[2]-a[0])*(a[3]-a[1]); bb = (b[2]-b[0])*(b[3]-b[1])
    return i / max(1e-9, aa + bb - i), i / max(1e-9, min(aa, bb))
res = {}
for b in F["boxes"]:
    tw = []
    for k2, b2, c2 in acc[b["page"]]:
        if k2 == b["key"] or k2.split("/")[1:5] == b["key"].split("/")[1:5]: continue
        iou, cont = rel(b["pb"], b2)
        if iou >= 0.3 or cont >= 0.6:
            v = live.get(k2); tw.append(dict(key=k2, cls=c2, iou=round(iou, 2), cont=round(cont, 2), owner=(v["outcome"], v.get("reason")) if v else None))
    res[b["key"]] = tw
json.dump(res, open(sys.argv[3], "w"))
dec = sum(1 for v in res.values() if any(t["owner"] and t["owner"][0] == "decided" for t in v)); anyt = sum(1 for v in res.values() if v)
print(len(res), "boxes;", anyt, "with a twin in another cell;", dec, "with a twin whose owner DECIDED")
