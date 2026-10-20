"""2.177 blind tiles: at most 12 under out/print/2.177-review/ (ONE blue box each, nothing else of ours, plus a README); the KEY goes to
out/print/2.177-key.json (outside the tiles folder). Tiles and key come from this one run and are checked equal.

Question for Sean (README): is the thing in the blue box part of the meter, or something else (what)?
usage: tiles_2_177.py OUTROOT   (reads scratch/out177/{litolff,brahms}.{off,on}.json + scratch/slices/*)
Pool: boxes the meter object CHANGED (newly refused heads / rests, and rests the claim now keeps) + 3 controls (real notes standing right
after a claimed meter: decided in both arms, not refused)."""
import json
import os
import random
import sys

sys.path.insert(0, ".")
from PIL import Image, ImageDraw  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

OUTROOT = sys.argv[1]
TILES = os.path.join(OUTROOT, "2.177-review")
KEY = os.path.join(OUTROOT, "2.177-key.json")
PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
rnd = random.Random(2177)


def box_of(doc, g):
    pg = int(g.split("/")[1])
    for l in open("scratch/slices/%s/p%02d.observations.jsonl" % (doc, pg)):
        if g in l and '"glyph_box"' in l:
            o = json.loads(l)
            if o["subject"] == g and o["quantity"] == "glyph_box":
                return o["value"][0], o["detail"]["bbox_page_px"]
    return None, None


changed, controls = [], []
for doc in ("litolff", "brahms"):
    try:
        off = json.load(open("scratch/out177/%s.off.json" % doc))
        on = json.load(open("scratch/out177/%s.on.json" % doc))
    except OSError:
        continue
    for g, v in on["refusals"].items():
        if v[1] == "inside_the_meter" and g not in off["refusals"]:
            changed.append((doc, g, "refused_head"))
    for g, v in on["rest_refusals"].items():
        if v[1] == "inside_the_meter" and g not in off["rest_refusals"]:
            changed.append((doc, g, "refused_rest"))
    for g in off["rest_refusals"]:
        if g not in on["rest_refusals"]:
            changed.append((doc, g, "rest_kept_now"))
    # controls: a decided, non-rest head in the SAME cell as a claim, whose box starts to the right of the claimed area (within 4 spaces)
    for c in on["claims"]:
        s = c["subject"].split("/")
        area = c["value"]
        cell = c["cell"]
        sp = (area[3] - area[1]) / 4.0
        pre = "glyph/%s/%s/%s/%s/" % (s[1], s[2], s[3], cell)
        for g, v in on["glyphs"].items():
            if g.startswith(pre) and v["outcome"] == "decided" and not v["rest"] and not v["measure_rest"] and g not in on["refusals"]:
                cls, b = box_of(doc, g)
                if b and 0 <= (b[0] - area[2]) <= 4 * sp and b[3] > area[1] and b[1] < area[3]:
                    controls.append((doc, g, "control_note_after_meter"))
rnd.shuffle(changed)
rnd.shuffle(controls)
by_kind = {}
for it in changed:
    by_kind.setdefault(it[2], []).append(it)
pick = []
while len(pick) < 9 and any(by_kind.values()):
    for k in list(by_kind):
        if by_kind[k] and len(pick) < 9:
            pick.append(by_kind[k].pop())
ctl = controls[:3]
items = pick + ctl
rnd.shuffle(items)
os.makedirs(TILES, exist_ok=True)
rasters = {}
key = []
for n, (doc, g, kind) in enumerate(items, 1):
    cls, b = box_of(doc, g)
    pg = int(g.split("/")[1])
    if (doc, pg) not in rasters:
        rasters.clear()
        rasters[(doc, pg)] = Image.fromarray(render_page(PDFS[doc], pg, dpi=600).rgb).convert("RGB")
    im = rasters[(doc, pg)]
    sp = (b[3] - b[1]) / 1.0
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    unit = 32.0 if doc == "brahms" else 15.75
    x0, y0, x1, y1 = int(cx - 5 * unit), int(cy - 4 * unit), int(cx + 5 * unit), int(cy + 4 * unit)
    crop = im.crop((x0, y0, x1, y1)).copy()
    d = ImageDraw.Draw(crop)
    d.rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(31, 111, 235), width=2)
    crop.save(os.path.join(TILES, "tile_%02d.png" % n))
    key.append(dict(tile=n, doc=doc, glyph=g, cls=cls, kind=kind, page=pg))
open(os.path.join(TILES, "README.md"), "w").write(
    "# 2.177 review\n\nEach picture is a piece of a scanned score page with ONE blue box on it and nothing else drawn.\n\n"
    "**Question, for every tile:** is the thing in the blue box part of the meter (the two numbers of a time signature), or something "
    "else? If something else, what is it (note, rest, flat, clef, ...)?\n\nAnswer by tile number, for example `1 meter, 2 rest, 3 8th note`.\n")
json.dump(key, open(KEY, "w"), indent=1)
tiles = sorted(f for f in os.listdir(TILES) if f.startswith("tile_"))
assert len(tiles) == len(key) == len(items) <= 12, (len(tiles), len(key))
assert [int(t[5:7]) for t in tiles] == [k["tile"] for k in key]
print("tiles", len(tiles), "kinds", {k: sum(1 for i in key if i["kind"] == k) for k in {i["kind"] for i in key}})
