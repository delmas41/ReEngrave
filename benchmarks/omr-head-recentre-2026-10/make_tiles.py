"""ROADMAP 2.115 blind tiles -> out/print/2.115-recentre/. One question per tile, *Hollow or black? (or: not a note)*, 32 px per staff space, the print as printed, ONE red
corner bracket (on the standard head box at the re-centred position), NOTHING else of ours drawn. Items: every head on the two truth pages whose interior reading class changed
under the rule (hollow / between / black, see measure_truth.py) + 2 controls (Brahms black heads that WERE re-centred and stayed black). Hidden manifest.
usage: make_tiles.py truth_rows.json OUTDIR"""
import json, random, sys
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "benchmarks/omr-head-recentre-2026-10")
import explore as X, measure_truth as M
from tools.omr.staged import gather as G
rows = json.load(open(sys.argv[1])); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
chg = [r for r in rows if M.state(r["before"]) != M.state(r["after"])]
ctl = [r for r in rows if r["page"] == "brahms" and r["label"] == "black" and r["moved"] and M.state(r["after"]) == "black"]
ctl = [ctl[len(ctl) // 3], ctl[2 * len(ctl) // 3]]
items = [dict(r, group="CHANGED") for r in chg] + [dict(r, group="CONTROL black (moved, stayed black)") for r in ctl]
random.Random(20261014).shuffle(items)
sp_of = {"litolff": 15.75, "brahms": X.sp_of(X.RO.load_run("runs/2.114/ab/rec-bra-off.json"))}
imgs = {"litolff": X.render_page(Path(X.LIT), 1, dpi=600).rgb, "brahms": X.render_page(Path(X.BRA), 0, dpi=600).rgb}
man = []; tmpl = {}
for n, it in enumerate(items, 1):
    img = imgs[it["page"]]; sp = sp_of[it["page"]]
    x0, y0, x1, y1 = it["box"]; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + (it["dy"] or 0) * sp
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
    man.append(dict(n=n, hidden=dict(doc=it["page"], key=it["key"], group=it["group"], truth_label=it["label"], cls=it["cls"], dy_sp=it["dy"],
                                      before_centre_raw_off=it["before"], after_centre_raw_off=it["after"], rect_page=[bx0, by0, bx1, by1])))
    tmpl[f"tile_{n:02d}"] = {"answer": ""}
(out / "manifest.json").write_text(json.dumps({"tiles": man}, indent=1)); (out / "answers.template.json").write_text(json.dumps(tmpl, indent=1))
(out / "LEGEND.md").write_text(f"""# 2.115 re-centre: blind tiles ({len(items)})

One question on every tile: **is the note inside the red bracket hollow (white inside), black, or not a note at all?**
The red corner bracket only says which mark; nothing of ours (no class, no verdict, no other colour) is drawn. 32 px per staff space; tiles are in random order;
two are controls of known answer (black heads). Copy `answers.template.json` to `answers.json` and fill in "hollow", "black" or "not a note".
`manifest.json` (what the rule did to each) is read only after the answers.
""")
print(len(items), "tiles")
