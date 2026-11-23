"""2306 r10: for the HOLLOW heads among r10_near's reproduced no_stroke heads: in the stem column the old join names (its side of the head box, the
box edge +-0.5 sp), from the head's centre out 3.5 sp in the stem direction: is the column inked on the raster (share of rows), and which page-map
strokes cover it -- their kind, length, whether a vertical piece is there but shorter than the reader's reach. Usage (cwd = tree): r10_hollow.py DUMP REC PDF"""
import sys, os, json, collections
sys.path.insert(0, os.getcwd())
from tools.omr.preprocessing import render_page
dump, rec_p, pdf = sys.argv[1:4]
rows = [r for r in json.load(open(dump)) if r.get("offline") == "no_stroke" and r.get("hollow") and r.get("old_dir") in ("up", "down")]
pages = {int(r["g"].split("/")[1]) for r in rows}
R = json.load(open(rec_p))["record"]
strokes = collections.defaultdict(list)
for o in R["observations"]:
    if o["quantity"] == "page_stroke" and int(o["subject"].split("/")[1]) in pages:
        d = o["detail"]
        strokes[int(o["subject"].split("/")[1])].append((o["value"], [float(v) for v in d["bbox_page_px"]], d.get("length_spaces"), d.get("ordinal")))
del R
ras = {}
c = collections.Counter()
for r in rows:
    p = int(r["g"].split("/")[1])
    if p not in ras:
        ras[p] = render_page(pdf, p, dpi=600).rgb.mean(axis=2) < 128
    ink = ras[p]
    x0, y0, x1, y1 = r["head_box"]
    sp = (r.get("nearest") or {}).get("sp") or 16.0
    cy = (y0 + y1) / 2.0
    xe = x1 if r["old_dir"] == "up" else x0
    ya, yb = (cy - 3.5 * sp, y0) if r["old_dir"] == "up" else (y1, cy + 3.5 * sp)
    # the stem column: the best-inked 3-px column within +-0.5 sp of the edge, outside the head box rows
    best = 0.0
    for x in range(int(xe - 0.5 * sp), int(xe + 0.5 * sp) + 1):
        col = ink[int(ya):int(yb), x - 1:x + 2].any(axis=1)
        best = max(best, float(col.mean()) if col.size else 0.0)
    cover = [(k, round(L or 0, 2), o) for k, b, L, o in strokes[p] if b[0] <= xe + 0.5 * sp and b[2] >= xe - 0.5 * sp and b[3] >= ya and b[1] <= yb]
    kinds = sorted({k for k, L, o in cover})
    present = "column inked" if best >= 0.8 else ("column partly inked" if best >= 0.4 else "column empty")
    vert = [L for k, L, o in cover if k == "vertical"]
    if not cover:
        how = "no page stroke there"
    elif vert and max(vert) >= 1.5:
        how = "a vertical >= 1.5 sp there (refused by position)"
    elif vert:
        how = "only short vertical pieces (max %.1f sp)" % max(vert)
    else:
        how = "no vertical; stroke kinds there: " + ",".join(kinds)
    c[(present, how)] += 1
    print(r["g"], r["ledger"] and "ledger" or "staff", r["old_dir"], present, round(best, 2), how, cover[:4])
print()
for k, n in c.most_common():
    print("%3d  %s | %s" % (n, k[0], k[1]))
