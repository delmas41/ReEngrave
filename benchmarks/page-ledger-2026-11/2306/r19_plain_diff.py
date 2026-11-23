"""2.306 r19: bars where the ON file is PLAIN (no red, no blue in the bar) and DIFFERENT from the OFF file, from a lane_report work dir.
Usage: r19_plain_diff.py WORK PLATE NPY_DIR OUT_PREFIX [--n 12] [--skip place,place]
Writes OUT_PREFIX.txt (every bar: place, part, measure, OFF and ON as written) and OUT_PREFIX.png (up to N, seeded order: one staff crop of
the printed page, a thin box around the bar's written marks; no reading of ours drawn)."""
import json
import os
import random
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw

work, plate, npy_dir, out = sys.argv[1:5]
N = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 12
skip = set(sys.argv[sys.argv.index("--skip") + 1].split(",")) if "--skip" in sys.argv else set()


def bars(path):
    root = ET.parse(path).getroot()
    out = {}
    for part in root.iter("part"):
        pid = part.get("id")
        for m in part.iter("measure"):
            xml = ET.tostring(m, encoding="unicode")
            notes = []
            for n in m.iter("note"):
                p = n.find("pitch")
                pitch = (p.findtext("step") + (p.findtext("alter") or "") + p.findtext("octave")) if p is not None else "rest"
                notes.append("%s%s %s%s v%s%s" % ("+" if n.find("chord") is not None else "", pitch, n.findtext("type") or "?",
                                                   "." * len(n.findall("dot")), n.findtext("voice"), " tie" if n.find("tie") is not None else ""))
            rgs = [n.get("rg") for n in m.iter("note") if n.get("rg")]
            # keyed by the bar's own place on the page (page/system/staff/cell of its marks), never by part id or bar number: two files that
            # load different pages number their parts and bars differently (compare like with like, by place)
            cells = sorted({"/".join(r.split("/")[1:5]) for r in rgs})
            key = cells[0] if len(cells) == 1 else (pid, m.get("number"))
            out[key] = dict(notes=notes, red="#D00000" in xml, blue="#1F6FEB" in xml, rgs=rgs, part=pid, number=m.get("number"))
    return out


syms = {a: json.load(open(os.path.join(work, "%s.%s.symbols.json" % (plate, a)))) for a in ("off", "on")}
pages = set(json.load(open(os.environ["LANE_REPORT_SAMPLE"]))["plates"][plate]["pages"]) if os.environ.get("LANE_REPORT_SAMPLE") else None
box_of = {}
for a in ("off", "on"):
    for h in syms[a]["hosts"]:
        if h.get("rg") and h.get("box"):
            box_of[h["rg"]] = (h["page"], h["box"])
off, on = bars(os.path.join(work, plate + ".off.musicxml")), bars(os.path.join(work, plate + ".on.musicxml"))
rows = []
for k, b in on.items():
    a = off.get(k)
    if a is None or b["red"] or b["blue"] or a["notes"] == b["notes"]:
        continue
    rg = [r for r in b["rgs"] + a["rgs"] if r in box_of]
    if not rg:
        continue
    page = box_of[rg[0]][0]
    if pages is not None and page not in pages:
        continue
    cell = "/".join(rg[0].split("/")[1:5])
    if cell in skip:
        continue
    bx = [box_of[r][1] for r in rg if box_of[r][0] == page]
    rows.append(dict(cell=cell, part=b["part"], measure=b["number"], page=page, off=a["notes"], on=b["notes"], off_red=a["red"], off_blue=a["blue"],
                     box=[min(v[0] for v in bx), min(v[1] for v in bx), max(v[2] for v in bx), max(v[3] for v in bx)]))
with open(out + ".txt", "w") as f:
    for r in rows:
        f.write("%s %s m%s  OFF%s: %s\n            ON: %s\n" % (r["cell"], r["part"], r["measure"], " (red)" if r["off_red"] else " (blue)" if r["off_blue"] else "",
                                                          "; ".join(r["off"]), "; ".join(r["on"])))
print(plate, "plain-and-different bars:", len(rows))
pick = sorted(rows, key=lambda r: r["cell"])
random.Random(2188).shuffle(pick)
pick = pick[:N]
tiles = []
for i, r in enumerate(pick):
    img = np.load(os.path.join(npy_dir, "%s_p%d.npy" % (plate, r["page"])))
    x0, y0, x1, y1 = r["box"]
    X0, Y0 = max(0, int(x0) - 120), max(0, int(y0) - 160)
    X1, Y1 = min(img.shape[1], int(x1) + 120), min(img.shape[0], int(y1) + 160)
    c = Image.fromarray(img[Y0:Y1, X0:X1]).convert("RGB")
    d = ImageDraw.Draw(c)
    d.rectangle([x0 - X0 - 6, y0 - Y0 - 6, x1 - X0 + 6, y1 - Y0 + 6], outline=(255, 140, 0), width=2)
    d.text((4, 4), "%d" % (i + 1), fill=(255, 0, 0))
    c.thumbnail((520, 520))
    tiles.append(c)
    r["tile"] = i + 1
if tiles:
    W = 4
    sheet = Image.new("RGB", (520 * W, 520 * ((len(tiles) + W - 1) // W)), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % W) * 520, (i // W) * 520))
    sheet.save(out + ".png")
json.dump(pick, open(out + ".key.json", "w"), indent=1)
