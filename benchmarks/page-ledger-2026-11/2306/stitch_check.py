"""2306 r6: every page stem the r4 run-stitching built out of 2+ vertical pieces: for each gap between consecutive pieces, how much of the gap is
inked IN THE STEM'S OWN COLUMN on the page raster (the stem's own ink, or a mark lying across it). A gap whose column is mostly empty paper was bridged
over paper (the r4 rule says never). Then, for the target glyphs (written OFF and lost ON / eighth -> quarter), whether their page stem is such a run.
Usage (cwd = tree): stitch_check.py REC.json PDF WHY.txt [--dump OUT.json]"""
import sys, os, json, re, collections
sys.path.insert(0, os.getcwd())
import numpy as np
from tools.omr.preprocessing import render_page
rec_p, pdf, why = sys.argv[1], sys.argv[2], sys.argv[3]
targets = {}
for line in open(why):
    m = re.match(r"(LOST|EIGHTH->QUARTER) (glyph/\S+) ", line)
    if m:
        targets[m.group(2)] = m.group(1)
R = json.load(open(rec_p))["record"]
obs = R["observations"]
strokes = {}
claims = {}
pstem = {}
for o in obs:
    q = o["quantity"]
    if q == "page_stroke":
        d = o["detail"]
        strokes[(int(o["subject"].split("/")[1]), int(d["ordinal"]))] = (d["bbox_page_px"], float(d.get("staff_space_local_px") or 0) or None)
    elif q == "claimed_area" and o["reader"] == "cv_page_stems" and isinstance(o["value"], int):
        claims[(int(o["subject"].split("/")[1]), int(o["value"]))] = o["detail"]
    elif q == "page_stem" and o["subject"] in targets:
        pstem[o["subject"]] = o
del R, obs
pages = sorted({p for p, _ in claims})
gapinfo = {}
cnt = collections.Counter()
for p in pages:
    a = render_page(pdf, p, dpi=600).rgb
    ink = a.mean(axis=2) < 128
    H, W = ink.shape
    for (pp, o), d in claims.items():
        if pp != p:
            continue
        mem = [strokes.get((p, m)) for m in d["page_strokes"]]
        if len(mem) < 2 or any(x is None for x in mem):
            cnt["single" if len(mem) < 2 else "no_stroke_row"] += 1
            continue
        boxes = sorted([m[0] for m in mem], key=lambda b: b[1])
        sp = next((m[1] for m in mem if m[1]), 16.0)
        x0, x1 = int(round(min(b[0] for b in boxes))), int(round(max(b[2] for b in boxes)))
        worst = 0.0
        gaps = []
        for b0, b1 in zip(boxes, boxes[1:]):
            y0, y1 = int(round(b0[3])), int(round(b1[1]))
            if y1 - y0 <= 0.3 * sp:
                continue
            # a row of the gap is "inked" when at least half the stem column's width carries ink there
            rows = ink[max(0, y0):min(H, y1), max(0, x0):min(W, x1 + 1)]
            if rows.size == 0:
                continue
            filled = (rows.mean(axis=1) >= 0.5)
            # the longest run of EMPTY rows in the gap, in staff spaces
            run = best = 0
            for f in filled:
                run = 0 if f else run + 1
                best = max(best, run)
            gaps.append(round(best / sp, 2))
            worst = max(worst, best / sp)
        gapinfo[(p, o)] = (gaps, worst, d.get("heads"), d.get("stem_box"))
        cnt["stitched"] += 1
        if worst > 0.3:
            cnt["stitched, empty paper > 0.3 sp in a gap"] += 1
        if worst > 1.0:
            cnt["stitched, empty paper > 1 sp in a gap"] += 1
print("stems on the pages:", dict(cnt))
tc = collections.Counter()
for g, kind in sorted(targets.items()):
    o = pstem.get(g)
    if o is None:
        tc[(kind, "no page stem reading (abstained)")] += 1
        print(kind, g, "page abstained")
        continue
    p = int(g.split("/")[1])
    gi = gapinfo.get((p, int(o["detail"]["page_stroke"])))
    if gi is None:
        tc[(kind, "single-piece stem")] += 1
        print(kind, g, "single piece", o["detail"].get("stem_box"), o["detail"].get("direction"))
        continue
    lab = "stitched, empty paper %s" % ("> 0.3 sp" if gi[1] > 0.3 else "<= 0.3 sp")
    tc[(kind, lab)] += 1
    print(kind, g, lab, "gaps (longest empty run, sp)", gi[0], "heads on run", gi[2], "box", gi[3], o["detail"].get("direction"))
print()
for k, n in sorted(tc.items()):
    print(n, k)
if "--dump" in sys.argv:
    json.dump({"%d/%d" % k: v for k, v in gapinfo.items()}, open(sys.argv[sys.argv.index("--dump") + 1], "w"))
