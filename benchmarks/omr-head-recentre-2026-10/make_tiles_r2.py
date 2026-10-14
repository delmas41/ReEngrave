"""ROADMAP 2.115 ROUND 2 blind tiles -> out/print/2.115-round2/, cut from the REAL gather A/B (not the page-frame measurement).
Items: every head whose `notehead_ink` reading CLASS (hollow <= 0.75 / between / black >= 0.85, min of ink_raw and ink_off_line centre) changed OFF -> ON in
the two A/B records, capped at 15 (those that changed, then 2 controls = moved heads that stayed black). Nothing of ours drawn but a small red corner bracket on the
standard head box at the re-centred position; question 'hollow or black? (or: not a note)'; hidden manifest. 32 px per staff space.
usage: make_tiles_r2.py OUTDIR off_lit on_lit off_bra on_bra"""
import json, random, sys
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "benchmarks/omr-head-recentre-2026-10")
import explore as X
from tools.omr.staged import readout as RO, gather as G
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
def cls(d):
    v = [d[k]["windows"]["center"] for k in ("ink_raw", "ink_off_line") if d.get(k) and d[k]["windows"]["center"] is not None]
    if not v: return "unread"
    return "hollow" if min(v) <= 0.75 else ("black" if min(v) >= 0.85 else "between")
def reads(r):
    return {o["subject"]: o for o in r.observations if o["quantity"] == "notehead_ink"}
items = []
for doc, (po, pn) in (("litolff", sys.argv[2:4]), ("brahms", sys.argv[4:6])):
    a, b = RO.load_run(po), RO.load_run(pn); ra, rb = reads(a), reads(b)
    sp = X.sp_of(a)
    for k, o in rb.items():
        d = o.get("detail") or {}; pb = d.get("part_boxed") or {}
        if not pb.get("accepted") or k not in ra: continue
        ca, cb = cls(ra[k].get("detail") or {}), cls(d)
        g = b.glyphs[k]
        items.append(dict(doc=doc, key=k, cls=g.cls, box=list(g.box_page), dy=pb["dy_sp"], sp=sp, before=ca, after=cb,
                          raw_off=[(ra[k]["detail"].get(q) or {}).get("windows", {}).get("center") for q in ("ink_raw", "ink_off_line")],
                          raw_on=[(d.get(q) or {}).get("windows", {}).get("center") for q in ("ink_raw", "ink_off_line")]))
chg = [i for i in items if i["before"] != i["after"]]; ctl = [i for i in items if i["before"] == i["after"] == "black"]
random.Random(20261014).shuffle(chg); random.Random(7).shuffle(ctl)
chg = chg[:15]; sel = [dict(i, group="CHANGED") for i in chg] + [dict(i, group="CONTROL black (moved, stayed black)") for i in ctl[:2]]
random.Random(20261015).shuffle(sel)
imgs = {"litolff": X.render_page(Path(X.LIT), 1, dpi=600).rgb, "brahms": X.render_page(Path(X.BRA), 0, dpi=600).rgb}
man = []; tmpl = {}
for n, it in enumerate(sel, 1):
    img = imgs[it["doc"]]; sp = it["sp"]
    x0, y0, x1, y1 = it["box"]; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + it["dy"] * sp
    bx0, bx1, by0, by1 = G._standard_head_box(cx, cy, sp)
    ax0, ay0 = int(max(0, cx - 6 * sp)), int(max(0, cy - 6.5 * sp)); ax1, ay1 = int(min(img.shape[1], cx + 6 * sp)), int(min(img.shape[0], cy + 6.5 * sp))
    crop = img[ay0:ay1, ax0:ax1].copy(); sc = 32.0 / sp
    crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    if crop.ndim == 2: crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    rx0, ry0, rx1, ry1 = [int(round(v * sc)) for v in (bx0 - ax0, by0 - ay0, bx1 - ax0, by1 - ay0)]
    for (px, py, dx, dy) in ((rx0, ry0, 1, 1), (rx1, ry0, -1, 1), (rx0, ry1, 1, -1), (rx1, ry1, -1, -1)):
        cv2.line(crop, (px, py), (px + dx * 10, py), (30, 30, 220), 2); cv2.line(crop, (px, py), (px, py + dy * 10), (30, 30, 220), 2)
    hdr = np.full((56, crop.shape[1], 3), 255, np.uint8)
    cv2.putText(hdr, f"Tile {n}: hollow or black? (or: not a note)", (6, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.imwrite(str(out / f"tile_{n:02d}.png"), np.vstack([hdr, crop]))
    man.append(dict(n=n, hidden={k: it[k] for k in ("doc", "key", "group", "cls", "dy", "before", "after", "raw_off", "raw_on")}))
    tmpl[f"tile_{n:02d}"] = {"answer": ""}
(out / "manifest.json").write_text(json.dumps({"tiles": man, "n_changed_total": len(chg) if len(chg) < 15 else sum(i["before"] != i["after"] for i in items), "n_moved_total": len(items)}, indent=1))
(out / "answers.template.json").write_text(json.dumps(tmpl, indent=1))
(out / "LEGEND.md").write_text(f"""# 2.115 round 2: blind tiles ({len(sel)})

One question on every tile: **is the note inside the red bracket hollow (white inside), black, or not a note at all?**
The red corner bracket only says which mark; nothing of ours is drawn. 32 px per staff space; random order; two are controls of known answer (black heads the
rule moved and that stayed black). Copy `answers.template.json` to `answers.json` and fill in "hollow", "black" or "not a note".
`manifest.json` (what the rule did to each) is read only after the answers. These replace round 1's page-frame tiles (`out/print/2.115-recentre/`).
""")
print(len(sel), "tiles;", len(items), "moved;", sum(i["before"] != i["after"] for i in items), "class changed")
