"""2.248 r4: 12 blind tiles drawn from the WRITTEN file only (the ON arm's exported hosts), never from a record row: r3's tool drew
record pitch verdicts and 6 of its 12 tiles were boxes nothing was written for. Each tile: one staff's far note, a thin orange box sized
to the mark at its own place, cropped tall enough to show the whole staff it is counted from (so the ledger lines can be counted).
Key outside the tiles folder.  usage: make_tiles.py LANE_OUT_DIR"""
import collections
import json
import pathlib
import random
import sys

from PIL import Image, ImageDraw

from tools.omr.staged import lane_report as LR
from tools.omr.preprocessing import render_page

W = pathlib.Path(sys.argv[1]) / "work"
OUT = pathlib.Path("out/print/2.248-r4-tiles")
rng = random.Random(2484)


def load(p):
    r = json.load(open(p))
    return r.get("record", r)


items = []
for plate in ("litolff", "brahms"):
    on = json.load(open(W / ("%s.on.symbols.json" % plate)))["hosts"]
    off = {h["rg"]: h for h in json.load(open(W / ("%s.off.symbols.json" % plate)))["hosts"] if h.get("rg")}
    # the replay keeps no full record: the head's geometry position (box centre vs its CUT staff) comes from the replayed night slice
    pos_of = {}
    for line in open("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night/%s/observations.jsonl" % plate):
        if '"notehead_staff_position"' in line:
            o = json.loads(line)
            pos_of[o["subject"]] = o["value"]
    for h in on:
        if h.get("kind") != "note" or not h.get("rg") or h["rg"] not in off:
            continue
        o = off[h["rg"]]
        if o.get("pitch") != h.get("pitch"):
            group = "pitch_changed"
        elif h.get("blue") and not o.get("blue"):
            group = "far_unread_blue" if (pos_of.get(h["rg"]) is None or round(pos_of[h["rg"]]) < -1 or round(pos_of[h["rg"]]) > 9) else "blue_in_staff_bar_changed"
        else:
            continue
        pos = pos_of.get(h["rg"])
        if pos is None:
            continue
        items.append(dict(plate=plate, page=h["page"], box=h["box"], rg=h["rg"], part=h["part"], measure=h["measure"], group=group,
                          written_on=h["pitch"], written_off=o.get("pitch"), position=round(pos, 2)))
print(collections.Counter((i["plate"], i["group"]) for i in items))
rng.shuffle(items)
pick = [i for i in items if i["group"] == "pitch_changed"][:6]
rest = [i for i in items if i["group"] == "far_unread_blue"]
byp = collections.defaultdict(list)
for i in rest:
    byp[i["plate"]].append(i)
while len(pick) < 12 and any(byp.values()):
    for p in ("litolff", "brahms"):
        if byp[p] and len(pick) < 12:
            pick.append(byp[p].pop())
rng.shuffle(pick)

tdir = OUT / "tiles"
tdir.mkdir(parents=True, exist_ok=True)
for f in tdir.glob("*"):
    f.unlink()
cache = {}
key = []
for n, it in enumerate(pick, 1):
    plate, pg = it["plate"], it["page"]
    if (plate, pg) not in cache:
        cache.clear()
        cache[(plate, pg)] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
    im = cache[(plate, pg)]
    u = LR.PLATES[plate]["unit"]
    x0, y0, x1, y1 = it["box"]
    cy = (y0 + y1) / 2
    top = cy - it["position"] * u / 2.0          # the counted staff's top line, roughly (only to size the crop, never to read)
    bot = top + 4 * u
    Y0, Y1 = int(min(y0, top) - 2 * u), int(max(y1, bot) + 2 * u)
    cx = (x0 + x1) / 2
    X0, X1 = int(cx - 5 * u), int(cx + 5 * u)
    crop = im.crop((X0, Y0, X1, Y1)).copy()
    ImageDraw.Draw(crop).rectangle([x0 - 2 - X0, y0 - 2 - Y0, x1 + 2 - X0, y1 + 2 - Y0], outline=(255, 120, 0), width=2)
    scale = 520.0 / crop.width
    crop = crop.resize((520, int(crop.height * scale)))
    crop.save(tdir / ("tile_%02d.png" % n))
    key.append(dict(it, tile=n, crop_origin=[X0, Y0], staff_side="below the note" if it["position"] < 0 else "above the note"))
(tdir / "README.md").write_text(
    "# 2.248 round 4 -- 12 tiles\n\nEach picture is a piece of a scanned score page with ONE thin orange box around one note and nothing "
    "else drawn. The box only says where to look. Each picture shows the whole staff the note belongs to.\n\n"
    "**One question, for every tile:** which line or space is the note in the box on, counted from its own staff -- e.g. "
    "'second ledger line above', 'third space below' (or 'not a note', or 'belongs to the other staff').\n\nAnswer by tile number.\n")
(OUT / "key.json").write_text(json.dumps(key, indent=1, default=str))
print("tiles", len(key), collections.Counter(k["group"] for k in key))
