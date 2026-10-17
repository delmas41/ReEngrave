"""ROADMAP 2.159 -- Sean's hand-truth page (Brahms 317803 pdf 0; data/hand-truth/pages/imslp317803/0.json): every
BLACK-classed notehead box of the 20261016-night record on that page, joined to his box by overlap; how well each stored
head measure separates his black from his half heads (best single cut, errors), and the located-box slit reading.
usage: truth_p0_2_159.py SLICEDIR OUTDIR"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from separate_2_159 import measures, best_cut, HIGHER_IS_HOLLOW  # noqa: E402

SD, OUT = sys.argv[1:3]
HT = json.load(open("data/hand-truth/pages/imslp317803/0.json"))
assert HT.get("dpi") in (None, 600), HT.get("dpi")
th = []
for b in HT["boxes"]:
    if b["cls"].startswith("notehead"):
        x0, y0, x1, y1 = b["rect"]
        th.append(("black" if "Black" in b["cls"] else "hollow", (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))))
heads = {}
for line in open(os.path.join(SD, "brahms", "p00.observations.jsonl")):
    if not any(q in line for q in ('"glyph_box"', '"notehead_ink"', '"cell_staff_space"')):
        continue
    o = json.loads(line)
    heads.setdefault(o["subject"], {})[o["quantity"]] = o
space = {s: h["cell_staff_space"]["value"] for s, h in heads.items() if "cell_staff_space" in h}
L = json.load(open(os.path.join(OUT, "located_brahms.json")))
rows = []
for s, h in heads.items():
    b = h.get("glyph_box")
    if not b or not str(b["value"][0]).startswith("noteheadBlack") or "notehead_ink" not in h:
        continue
    bb = b["detail"].get("bbox_page_px")
    best = None
    for t, r in th:
        ix = min(r[2], bb[2]) - max(r[0], bb[0])
        iy = min(r[3], bb[3]) - max(r[1], bb[1])
        if ix > 0 and iy > 0 and (best is None or ix * iy > best[0]):
            best = (ix * iy, t)
    if best is None:
        continue
    sp = space.get(s.replace("glyph/", "cell/").rsplit("/", 1)[0])
    w, hh = b["value"][3] / sp, b["value"][4] / sp
    sized = 0.9 <= hh <= 1.8 and 1.1 <= w <= 1.9
    m = measures({"notehead_ink": h["notehead_ink"]})
    if s in L:
        m["located-box rows_share"] = L[s]["iw"]["rows_share"]
    rows.append(dict(subject=s, truth=best[1], sized=sized, m=m))
print("hand-truth p0 BLACK-classed boxes joined: %d (%d hollow), head-sized %d" % (
    len(rows), sum(r["truth"] == "hollow" for r in rows), sum(r["sized"] for r in rows)))
res = {}
for n in sorted({k for r in rows for k in r["m"]}):
    for gated in (False, True):
        pairs = [(r["m"][n], r["truth"] == "hollow") for r in rows if n in r["m"] and (not gated or r["sized"])]
        if not pairs or all(y for _, y in pairs) or not any(y for _, y in pairs):
            print("%-34s %-10s n=%d (hollow %d): one class only" % (n, gated, len(pairs), sum(y for _, y in pairs)))
            continue
        c = best_cut(pairs, n in HIGHER_IS_HOLLOW or n.startswith("located"))
        res["%s|%s" % (n, gated)] = c
        hv = sorted(x for x, y in pairs if y)
        bv = sorted(x for x, y in pairs if not y)
        print("%-34s %-10s n=%3d (hollow %2d) best cut %s errors %d (hollow missed %d, black called hollow %d)"
              "  hollow %.3f..%.3f black %.3f..%.3f" % (n, "head-sized" if gated else "all boxes", len(pairs),
                                                       len(hv), c[0], c[1], c[2], c[3], hv[0], hv[-1], bv[0], bv[-1]))
# the located reading where the detector box is NOT head-sized (the 2.159 population)
ns = [r for r in rows if not r["sized"] and "located-box rows_share" in r["m"]]
for t in ("black", "hollow"):
    v = [r["m"]["located-box rows_share"] for r in ns if r["truth"] == t]
    print("not-head-sized, located box, Sean says %s: n=%d, >=0.18: %d, <=0.06: %d" % (
        t, len(v), sum(x >= 0.18 for x in v), sum(x <= 0.06 for x in v)))
json.dump({"rows": rows, "cuts": res}, open(os.path.join(OUT, "truth_p0.json"), "w"), indent=0)
