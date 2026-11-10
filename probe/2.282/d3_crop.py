"""2.282: crops of the arm disagreements (my own look, rule 7). Orange = the stroke (or the head box), blue = accidental boxes, green = head boxes, red = rests, grey = others
that overlap it. usage: d3_crop.py PLATE BASE_DIR D1.json OUT.png [N] [KIND]"""
import json
import subprocess
import sys

plate, base, d1, out = sys.argv[1:5]
n = int(sys.argv[5]) if len(sys.argv) > 5 else 12
kinds = sys.argv[6].split(",") if len(sys.argv) > 6 else ["stroke", "head"]
rows = [r for r in json.load(open(d1)) if r["kind"] in kinds][:n]
need_cells = {r["cell"] if r["kind"] == "stroke" else "cell/" + r["sub"][6:].rsplit("/", 1)[0] for r in rows}
need_s = {(r["cell"], r["ordinal"]) for r in rows if r["kind"] == "stroke"}
sbox, gbox = {}, {}
for line in open(base + "/observations.jsonl"):
    if '"stroke"' in line or '"glyph_box"' in line:
        o = json.loads(line)
        q, sub = o["quantity"], o["subject"]
        if not sub.startswith("glyph/"):
            continue
        cell = "cell/" + sub[6:].rsplit("/", 1)[0]
        if cell not in need_cells:
            continue
        if q == "stroke":
            k = (cell, int(sub.rsplit("/", 1)[1]) - 375000)
            if k in need_s:
                sbox[k] = o["detail"].get("bbox_page_px")
        elif q == "glyph_box":
            gbox.setdefault(cell, {})[sub] = (o["value"][0], (o["detail"] or {}).get("bbox_page_px"))
items = []
spp = {"litolff": 15.75, "brahms": 27.2}[plate]


def ov(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / max(1.0, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))


for r in rows:
    if r["kind"] == "stroke":
        cell = r["cell"]
        box = sbox.get((cell, r["ordinal"]))
        lab = "%s %s %s->%s" % (plate[0].upper(), cell[5:], (r["base"] or [None, None])[:2], (r["arm"] or [None, None])[:2])
    else:
        cell = "cell/" + r["sub"][6:].rsplit("/", 1)[0]
        box = r["box"]
        lab = "%s %s %s->%s" % (plate[0].upper(), r["sub"][6:], r["base"][1], r["arm"][1])
    if not box:
        continue
    bx = []
    for k, (cls, b) in gbox.get(cell, {}).items():
        if not b or ov(box, b) < 0.2 or b == box:
            continue
        lc = cls.lower()
        col = (0, 90, 255) if lc.startswith("accidental") else (0, 170, 60) if lc.startswith("notehead") else (220, 0, 0) if lc.startswith("rest") else (150, 150, 150)
        if lc in ("staff",):
            continue
        bx.append((b, list(col)))
    items.append(dict(plate=plate, page=r["page"], box=box, sp=spp, boxes=[[b, c] for b, c in bx], label=lab))
json.dump(items, open(out + ".json", "w"))
subprocess.run([sys.executable, "probe/2.282/crop.py", out, out + ".json"], check=True)
