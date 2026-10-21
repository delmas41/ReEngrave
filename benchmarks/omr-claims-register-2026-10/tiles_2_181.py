"""2.181 blind tiles: at most 12 under out/print/2.181-review/ (ONE blue box each, nothing else of ours, plus a README); the KEY goes to
out/print/2.181-key.json (outside the tiles folder). Tiles and key come from this one run and are checked equal.

Question for Sean (README): is the thing in the blue box a note, or what is it?
usage: tiles_2_181.py OUTROOT RUNDIR SLICEDIR   (reads RUNDIR/{litolff,brahms}.diff.json + .on.json from compare/replay_2_181)
Pool: boxes the register CHANGED -- newly refused heads/rests, newly narrowed (written blue) heads/rests, old refusals now only
narrowed -- mostly, plus 3 controls (real heads standing just right of a claimed clef in a system's first bar, kept in both arms)."""
import json
import os
import random
import sys

sys.path.insert(0, ".")
from PIL import Image, ImageDraw  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

OUTROOT, RUN, SD = sys.argv[1:4]
TILES = os.path.join(OUTROOT, "2.181-review")
KEY = os.path.join(OUTROOT, "2.181-key.json")
PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
rnd = random.Random(2181)
_boxes = {}


def box_of(doc, g):
    pg = int(g.split("/")[1])
    if (doc, pg) not in _boxes:
        m = {}
        for line in open("%s/%s/p%02d.observations.jsonl" % (SD, doc, pg)):
            if '"glyph_box"' in line:
                o = json.loads(line)
                if o["quantity"] == "glyph_box":
                    m[o["subject"]] = (o["value"][0], o["detail"]["bbox_page_px"])
        _boxes[(doc, pg)] = m
    return _boxes[(doc, pg)].get(g, (None, None))


changed, controls = [], []
for doc in ("litolff", "brahms"):
    try:
        d = json.load(open("%s/%s.diff.json" % (RUN, doc)))
        on = json.load(open("%s/%s.on.json" % (RUN, doc)))
        off = json.load(open("%s/%s.off.json" % (RUN, doc)))
    except OSError:
        continue
    for g, v in d["new_refused"].items():
        changed.append((doc, g, "refused_head:" + str(v[1])))
    for g, v in d["rests_new"].items():
        changed.append((doc, g, "refused_rest:" + str(v[1])))
    for g, v in d["newly_narrowed"].items():
        changed.append((doc, g, "narrowed_head:" + str(v[0])))
    for g, v in d["rest_narrowed"].items():
        if g not in off["rest_refusals"]:
            changed.append((doc, g, "narrowed_rest:" + str(v[0])))
    for g, _o, how, v in d["parity_diffs"]:
        changed.append((doc, g, "old_refusal_now_" + how))
    for c in on["claims"]:
        if c["owner"] != "clef" or c["cell"] != 0 or c["standing"] != "READ":
            continue
        s = c["subject"].split("/")
        a = c["value"]
        sp = (a[3] - a[1]) / 3.0
        pre = "glyph/%s/%s/%s/0/" % (s[1], s[2], s[3])
        for g, v in on["glyphs"].items():
            if (g.startswith(pre) and v["outcome"] == "decided" and not v["rest"] and g not in on["refusals"]
                    and g not in on["narrowed"] and g not in off["refusals"]):
                cls, b = box_of(doc, g)
                if b and str(cls).startswith("notehead") and 0 <= b[0] - a[2] <= 3 * sp and b[3] > a[1] and b[1] < a[3]:
                    controls.append((doc, g, "control_note_after_clef"))
seen = set()
changed = [c for c in changed if not (c[:2] in seen or seen.add(c[:2]))]
rnd.shuffle(changed)
rnd.shuffle(controls)
by_kind = {}
for it in changed:
    by_kind.setdefault(it[2].split(":")[0], []).append(it)
pick = []
while len(pick) < 9 and any(by_kind.values()):
    for k in sorted(by_kind):
        if by_kind[k] and len(pick) < 9:
            pick.append(by_kind[k].pop())
items = pick[:9] + controls[:3]
rnd.shuffle(items)
os.makedirs(TILES, exist_ok=True)
for f in os.listdir(TILES):
    if f.startswith("tile_"):
        os.remove(os.path.join(TILES, f))
rasters = {}
key = []
for n, (doc, g, kind) in enumerate(items, 1):
    cls, b = box_of(doc, g)
    pg = int(g.split("/")[1])
    if (doc, pg) not in rasters:
        rasters.clear()
        rasters[(doc, pg)] = Image.fromarray(render_page(PDFS[doc], pg, dpi=600).rgb).convert("RGB")
    im = rasters[(doc, pg)]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    unit = 32.0 if doc == "brahms" else 15.75
    x0, y0, x1, y1 = int(cx - 6 * unit), int(cy - 5 * unit), int(cx + 6 * unit), int(cy + 5 * unit)
    crop = im.crop((x0, y0, x1, y1)).copy()
    rect = [round(b[0] - x0), round(b[1] - y0), round(b[2] - x0), round(b[3] - y0)]
    ImageDraw.Draw(crop).rectangle(rect, outline=(31, 111, 235), width=2)
    crop.save(os.path.join(TILES, "tile_%02d.png" % n))
    key.append(dict(tile=n, doc=doc, glyph=g, cls=cls, kind=kind, page=pg, box_page_px=b, crop_origin=[x0, y0], rect_in_tile=rect))
open(os.path.join(TILES, "README.md"), "w").write(
    "# 2.181 review\n\nEach picture is a piece of a scanned score page with ONE blue box on it and nothing else drawn.\n\n"
    "**Question, for every tile:** is the thing in the blue box a note, or what is it? (a note -- say its value if you can --, a rest, "
    "a clef or part of one, a bracket, a barline, a meter number, ...)\n\nAnswer by tile number, for example `1 8th note, 2 clef, 3 bracket`.\n")
json.dump(key, open(KEY, "w"), indent=1)
tiles = sorted(f for f in os.listdir(TILES) if f.startswith("tile_"))
assert len(tiles) == len(key) == len(items) <= 12, (len(tiles), len(key))
assert [int(t[5:7]) for t in tiles] == [k["tile"] for k in key]
for k in key:            # the blue box in each tile IS the key row's box (re-derived from the crop origin)
    bx = k["box_page_px"]
    assert k["rect_in_tile"] == [round(bx[0] - k["crop_origin"][0]), round(bx[1] - k["crop_origin"][1]),
                                 round(bx[2] - k["crop_origin"][0]), round(bx[3] - k["crop_origin"][1])]
print("tiles", len(tiles), "kinds", {k: sum(1 for i in key if i["kind"] == k) for k in sorted({i["kind"] for i in key})},
      "pool", len(changed), "controls", len(controls))
