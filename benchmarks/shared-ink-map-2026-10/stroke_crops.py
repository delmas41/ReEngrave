"""ROADMAP 2.195: crops of coverage misses. usage: stroke_crops.py PLATE PARITY.json KIND N SEED OUT.png
Re-cuts the cell (same code as the gather), draws every stroke box (red vertical, blue horizontal, green curve, orange blob) and the
missed row in magenta (a stem/beam box in cell px; an arc's end points; a rung window), one tile per miss."""
import json, random, sys
sys.path.insert(0, ".")
import cv2, numpy as np
from tools.omr.staged import pipeline, gather as G, stroke_map as S
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
plate, par, kind, n, seed, out = sys.argv[1:7]
misses = json.load(open(par))[kind]["misses"]
rows_by_id = {r["id"]: r for r in json.load(open(sys.argv[7]))} if len(sys.argv) > 7 else {}
random.Random(int(seed)).shuffle(misses)
col = {"vertical": (0, 0, 255), "horizontal": (255, 0, 0), "curve": (0, 160, 0), "blob": (0, 140, 255)}
tiles, cache = [], {}
for m in misses[:int(n)]:
    subj, rid = m.split("|")
    p = subj.split("/")
    page, sysi, st, cell = int(p[1]), int(p[2]), int(p[3]), int(p[4])
    if page not in cache:
        cache[page] = pipeline.prepare_pages(PDF[plate], [page], dpi=600)[0]
    pws, cells = cache[page]
    loc = G.gather_geometry(G.Log(), pws)
    c = next(c for c in cells if loc.get(c.staff_index) == (sysi, st) and c.measure_index == cell)
    g = G._cell_grid(c)
    r = S.map_strokes(c.image_no_staff, g[1] * 2, c.staff_line_ys_canonical, c.binary)
    im = cv2.cvtColor(c.image_no_staff, cv2.COLOR_GRAY2BGR)
    for s in r.strokes:
        x, y, w, h = s.box
        cv2.rectangle(im, (x, y), (x + w, y + h), col[s.kind], 2)
    if kind.startswith("beam"):
        ob = rows_by_id[rid]["value"]; cv2.rectangle(im, (ob[0], ob[1]), (ob[0] + ob[2], ob[1] + ob[3]), (255, 0, 255), 4)
    if kind.startswith("ledger"):
        w = rows_by_id[rid]["detail"]["window_page_px"]; up, cb = c.upscale_factor, c.bbox_page_px
        cv2.rectangle(im, (int((w[0] - cb[0]) * up), int((w[1] - cb[1]) * up) - 6), (int((w[2] - cb[0]) * up), int((w[3] - cb[1]) * up) + 6), (255, 0, 255), 4)
    cv2.putText(im, m.split("|")[0].replace("glyph/", "g").replace("cell/", "c") + " " + kind, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 0, 255), 3)
    tiles.append(cv2.resize(im, None, fx=0.45, fy=0.45))
    print(m)
H = max(t.shape[0] for t in tiles)
rows = [np.hstack([cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, 6, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles[i:i + 4]]) for i in range(0, len(tiles), 4)]
W = max(r.shape[1] for r in rows)
cv2.imwrite(out, np.vstack([cv2.copyMakeBorder(r, 0, 6, 0, W - r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]))
