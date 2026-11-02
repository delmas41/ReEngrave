"""2.255 blind tiles, cut ONLY from the exported ON file's hosts (out/2.255/cross/*.on.symbols.json): every far note whose
written mark changed (OFF vs ON), then controls (far notes written plain in both arms, drawn at random, seed 2255) to 12.
One staff each (the head's own staff, whole, plus the head and 1.5 sp around), a thin box sized to the head, nothing else
drawn.  tiles/ holds only NN.png; the key is written beside it (key.json), never inside.
usage: make_tiles.py CROSS_DIR OUT_DIR"""
import json
import os
import random
import sys

from PIL import Image, ImageDraw

from tools.omr.preprocessing import render_page
from tools.omr.staged import lane_report as LR

W, out = sys.argv[1], sys.argv[2]
os.makedirs(os.path.join(out, "tiles"), exist_ok=True)
items = []
for plate in ("litolff", "brahms"):
    base = LR.slice_dir(plate, "20261029-night")
    lines = {}
    for l in open(base / "observations.jsonl"):
        if '"staff_lines"' in l:
            o = json.loads(l)
            lines[o["subject"]] = [float(v) for v in o["value"]]
    off = {h["rg"]: h for h in json.load(open("%s/%s.off.symbols.json" % (W, plate)))["hosts"] if h.get("rg")}
    on = [h for h in json.load(open("%s/%s.on.symbols.json" % (W, plate)))["hosts"] if h.get("rg") and h.get("kind") == "note"]
    for h in on:
        p = h["rg"].split("/")
        key = "staff/%s/%s/%s" % (p[1], p[2], p[3])
        ln = lines.get(key)
        if not ln:
            continue
        sp = (ln[-1] - ln[0]) / 4.0
        cy = (h["box"][1] + h["box"][3]) / 2.0
        pos = (cy - ln[0]) / (sp / 2.0)
        if -1.5 <= pos <= 9.5:
            continue
        o = off.get(h["rg"])
        changed = o is None or o.get("pitch") != h.get("pitch") or o.get("blue") != h.get("blue")
        items.append(dict(plate=plate, rg=h["rg"], page=h["page"], box=h["box"], staff=key, lines=ln, sp=sp,
                          part=h.get("part"), measure=h.get("measure"), written=h.get("pitch"), blue=bool(h.get("blue")),
                          off_written=o and o.get("pitch"), off_blue=o and bool(o.get("blue")), changed=changed))
ch = [i for i in items if i["changed"]]
ctl = [i for i in items if not i["changed"] and not i["blue"]]
random.Random(2255).shuffle(ctl)
pick = ch + ctl[:12 - len(ch)]
random.Random(7).shuffle(pick)
key, cache = [], {}
for n, it in enumerate(pick, 1):
    pdf = str(LR.LIB / LR.PLATES[it["plate"]]["pdf"])
    k = (it["plate"], it["page"])
    if k not in cache:
        cache.clear()
        cache[k] = Image.fromarray(render_page(pdf, it["page"], dpi=600).rgb).convert("RGB")
    b, ln, sp = it["box"], it["lines"], it["sp"]
    cx = (b[0] + b[2]) / 2.0
    y0 = int(min(ln[0], b[1]) - 1.5 * sp)
    y1 = int(max(ln[-1], b[3]) + 1.5 * sp)
    x0, x1 = int(cx - 5 * sp), int(cx + 5 * sp)
    c = cache[k].crop((x0, y0, x1, y1)).copy()
    ImageDraw.Draw(c).rectangle([b[0] - x0 - 1, b[1] - y0 - 1, b[2] - x0 + 1, b[3] - y0 + 1], outline=(255, 140, 0), width=2)
    scale = max(1, int(round(700 / c.height))) if c.height < 700 else 1
    c = c.resize((c.width * scale, c.height * scale), Image.LANCZOS)
    c.save(os.path.join(out, "tiles", "%02d.png" % n))
    key.append(dict(tile=n, **{kk: it[kk] for kk in ("plate", "rg", "page", "part", "measure", "staff", "written", "blue",
                                                     "off_written", "off_blue", "changed")},
                    box=[round(v, 1) for v in b]))
    print(n, it["plate"], it["rg"], it["written"], "blue" if it["blue"] else "plain", "changed" if it["changed"] else "control")
json.dump(dict(question="Which line or space is the boxed note on, counted from its own staff (the staff drawn whole)?",
               what_the_colour_means="the orange box is the note asked about; nothing else is drawn",
               source="cut from the exported ON file only (out/2.255/cross/*.on.symbols.json), lane-2.255-ledger-read",
               tiles=key), open(os.path.join(out, "key.json"), "w"), indent=1)
