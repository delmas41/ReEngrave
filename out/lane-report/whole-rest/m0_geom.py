"""whole-rest m0: line-local geometry of restWhole boxes, refused vs accepted.
usage: m0_geom.py PKL"""
import json, pickle, sys, collections, statistics as S
d = pickle.load(open(sys.argv[1], "rb"))
obs = d["observations"]; ver = d["verdicts"]
byq = collections.defaultdict(dict)
for o in obs:
    byq[o["quantity"]].setdefault(o["subject"], []).append(o)
print({q: len(v) for q, v in byq.items() if q in ("staff_lines", "staff_spacing", "glyph_box")})
ex = next(iter(byq["staff_lines"].items())); print(ex[0], json.dumps(ex[1][-1])[:300])
gb = next(iter(byq["glyph_box"].items())); print(gb[0], json.dumps(gb[1][-1])[:400])
refus = {}
for v in ver:
    if v["quantity"] == "rest_is_not_a_rest":
        refus[v["subject"]] = v["reason"] if v["value"] else "KEPT"
rows = []
for sub, os_ in byq["glyph_box"].items():
    o = os_[-1]
    if o["value"][0] != "restWhole":
        continue
    bb = (o.get("detail") or {}).get("bbox_page_px")
    if not bb:
        continue
    p = sub.split("/")          # glyph/page/system/staff/cell/idx
    staff = "/".join(["staff"] + p[1:4])
    sl = byq["staff_lines"].get(staff); sp = byq["staff_spacing"].get(staff)
    if not sl or not sp:
        continue
    lines = [float(x) for x in sl[-1]["value"]]; space = float(sp[-1]["value"])
    y0, y1 = float(bb[1]), float(bb[3])
    rows.append(dict(sub=sub, reason=refus.get(sub, "NO_VERDICT"), h=(y1 - y0) / space, w=(bb[2] - bb[0]) / space,
                     top=[(y0 - l) / space for l in lines], bot=[(y1 - l) / space for l in lines], lines=lines, space=space))
by = collections.defaultdict(list)
for r in rows:
    by[r["reason"]].append(r)
for k, v in by.items():
    hs = [r["h"] for r in v]; ws = [r["w"] for r in v]
    # which line index the TOP edge is nearest to, and its signed offset (spaces); and gap from bottom to the next line below
    tn = []; gap = []
    for r in v:
        i = min(range(len(r["top"])), key=lambda j: abs(r["top"][j]))
        tn.append((i, round(r["top"][i], 2)))
        below = [b for b in r["bot"] if b < 0]
        gap.append(round(-max(below), 2) if below else None)
    print(k, len(v), "h med %.2f [%.2f..%.2f]" % (S.median(hs), min(hs), max(hs)), "w med %.2f" % S.median(ws))
    print("   top-edge nearest line idx", collections.Counter(i for i, _ in tn).most_common())
    print("   top-edge offset sp med %.2f" % S.median(o for _, o in tn))
    g = [x for x in gap if x is not None]
    print("   bottom edge to nearest line BELOW it: med %.2f min %.2f" % (S.median(g), min(g)) if g else "")
json.dump(rows, open(sys.argv[1] + ".geom.json", "w"))
