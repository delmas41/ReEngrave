"""2.299: the 12 blind staff-start tiles for Sean.
    PYTHONPATH=. python3 tiles299.py SELECT  CENSUS.json OFF_L.json ON_L.json OFF_B.json ON_B.json OUT_DIR
    PYTHONPATH=. python3 tiles299.py RENDER  SEL.json OUT_DIR

THE RULE (stated, seeded, `random.Random(2299)`):
  0. a staff start Sean already read in the 2.292 tiles is not asked again (it is reported as an agreement instead);
  1. every staff-system whose KEY changed OFF -> ON to a value other than the INFER fill (new key != old fill): all of them;
  2. then every staff newly READ by the new reader (key standing filled/abstained OFF -> read ON), the crushed (K1) and mis-classed (K3/K4) buckets
     and the rest, up to 8 in all, drawn at random when more;
  3. then 2 Brahms controls: staves whose three-flat key the EXISTING path reads on Brahms p0 / p4 (unchanged, seeded draw);
  4. the remainder (to 12) NEAR-MISS refusals: Litolff staves with a key object whose reading the new reader REFUSED although the print is probably
     a key (their notes are blue for the key) -- seeded draw, one per refusal reason first. They say whether the refusal was right or the cut was.
Each tile is the START of ONE staff: the clef, the WHOLE key signature, the meter if printed, up to the first note (the crop never ends inside the
signature: it reaches at least 4 staff spaces past the key's last slot); nothing of ours is drawn but one thin blue box around the key signature
(clef excluded). Numbers only on the sheet; the key (plate, staff, rule, OFF/ON verdict) is written one level above the tiles.
"""
import json
import os
import random
import sys

import fitz
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDFS = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
BLUE = (31, 111, 235)


def load(p):
    return json.load(open(p))


def key_of(d, staff):
    return d["staffs"][staff]["key"][0]


def select(census_p, off_l, on_l, off_b, on_b, out_dir):
    cen = load(census_p)
    runs = {("litolff", "off"): load(off_l), ("litolff", "on"): load(on_l), ("brahms", "off"): load(off_b), ("brahms", "on"): load(on_b)}
    rng = random.Random(2299)
    ans = load(os.path.join(HERE, "..", "why-key-clef-inferred-2026-11", "answers", "answers-2.292-r1.json"))["answers"]
    answered = {(a["plate"], a["staff"]) for a in ans.values()}          # Sean already read these staff starts (2.292): not asked twice
    rows = []
    for r in cen:
        plate, st = r["plate"], r["staff"]
        a, b = key_of(runs[(plate, "off")], st), key_of(runs[(plate, "on")], st)
        r["off"] = [a["decider"], a["outcome"], a["value"]]
        r["on"] = [b["decider"], b["outcome"], b["value"]]
        r["changed"] = r["off"] != r["on"]
        r["new_ne_fill"] = r["changed"] and a["decider"].startswith("infer") and b["outcome"] == "decided" and b["value"] != a["value"]
        rows.append(r)
    sel = []

    def add(r, why):
        if (r["plate"], r["staff"]) in answered:
            return
        if all((s["plate"], s["staff"]) != (r["plate"], r["staff"]) for s in sel):
            sel.append(dict(plate=r["plate"], staff=r["staff"], rule=why, bucket=r["bucket"], off=r["off"], on=r["on"], why=r["slots"].get("why"),
                            json=(on_l if r["plate"] == "litolff" else on_b)))

    for r in rows:
        if r["new_ne_fill"]:
            add(r, "1 key changed (new != old fill)")
    new_read = [r for r in rows if r["changed"] and r["plate"] == "litolff" and not r["new_ne_fill"]]
    rng.shuffle(new_read)
    for r in new_read[:max(0, 8 - len(sel))]:
        add(r, "2 newly READ")
    ctrl = [r for r in rows if r["plate"] == "brahms" and r["off"][1] == "decided" and not r["off"][0].startswith("infer") and r["off"][2] == -3]
    rng.shuffle(ctrl)
    for r in ctrl[:2]:
        add(r, "3 Brahms control (existing read, unchanged)")
    near = [r for r in rows if r["plate"] == "litolff" and r["standing"] == "filled" and r["blue_key"] > 0 and r["has_ko"]
            and r["slots"]["why"] not in ("no_slots", "no_clef") and not r["changed"]]
    rng.shuffle(near)
    byw = {}
    for r in near:
        byw.setdefault(r["slots"]["why"], []).append(r)
    order = []
    while any(byw.values()) and len(order) < 40:
        for w in sorted(byw):
            if byw[w]:
                order.append(byw[w].pop(0))
    for r in order:
        if len(sel) >= 12:
            break
        add(r, "4 near-miss refusal (%s)" % r["slots"]["why"])
    rng.shuffle(sel)
    return sel


def geometry(d, staff):
    ev = d["staffs"][staff]["evidence"]
    lines = ev["staff_lines"][0]["value"]
    SP = float(ev["staff_spacing"][0]["value"])
    x0, x1 = ev["staff_extent"][0]["value"]
    keyx = None
    for r in ev.get("claimed_area", []):
        dt = r.get("detail")
        if isinstance(dt, dict) and dt.get("source") == "system_key_object":
            v = r["value"]
            if isinstance(v, list) and len(v) == 4:
                keyx = (v[0], v[2]) if keyx is None else (min(keyx[0], v[0]), max(keyx[1], v[2]))
    p = staff.split("/")
    syms = [s["page_box"] for s in d["symbols"] if s["sub"].split("/")[1:4] == p[1:4] and s.get("page_box")]
    return int(p[1]), lines, SP, x0, keyx, syms


def render(sel, out_dir):
    tiles = os.path.join(out_dir, "tiles")
    os.makedirs(tiles, exist_ok=True)
    docs = {}
    key = {}
    cache = {}
    for n, s in enumerate(sel, 1):
        d = cache.setdefault(s["json"], load(s["json"]))
        doc = docs.setdefault(s["plate"], fitz.open(PDFS[s["plate"]]))
        pg, lines, SP, x0, keyx, syms = geometry(d, s["staff"])
        top, bot = lines[0], lines[-1]
        kx0 = keyx[0] if keyx else x0 + 3 * SP
        # the key's right edge: the area's, but never short of the 3 slots a flat run can hold past the clef edge (a crushed run reaches ~1.3 SP a slot)
        kx1 = max(keyx[1] if keyx else kx0, kx0 + 4.4 * SP)
        first_after = min([b[0] for b in syms if b[0] > kx1 + 0.5 * SP], default=None)
        right = kx1 + 4.0 * SP
        if first_after is not None:
            right = max(right, min(first_after - 0.4 * SP, x0 + 26 * SP))
        right = min(right, x0 + 26 * SP)
        left = x0 - 0.7 * SP
        clip = (left, top - 3.0 * SP, right, bot + 3.0 * SP)
        Z = 1000.0 / (clip[2] - clip[0])
        pix = doc[pg].get_pixmap(matrix=fitz.Matrix(600 / 72 * Z, 600 / 72 * Z), clip=fitz.Rect(*[v * 72 / 600 for v in clip]))
        im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
        sx, sy = im.width / (clip[2] - clip[0]), im.height / (clip[3] - clip[1])
        box = [(kx0 - 0.15 * SP - clip[0]) * sx, (top - 1.5 * SP - clip[1]) * sy, (kx1 + 0.35 * SP - clip[0]) * sx, (bot + 1.5 * SP - clip[1]) * sy]
        ImageDraw.Draw(im).rectangle(box, outline=BLUE, width=2)
        fn = "tile_%02d.png" % n
        im.save(os.path.join(tiles, fn))
        key[str(n)] = {k: v for k, v in s.items() if k != "json"}
        key[str(n)]["file"] = fn
    json.dump(key, open(os.path.join(out_dir, "key.json"), "w"), indent=1)
    sheet(tiles, len(sel))
    print("tiles", len(sel), "->", tiles)


def sheet(tiles, n):
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 64)
    except Exception:
        font = ImageFont.load_default()
    ims = []
    for i in range(1, n + 1):
        im = Image.open(os.path.join(tiles, "tile_%02d.png" % i)).convert("RGB")
        W = 700
        im = im.resize((W, int(im.height * W / im.width)))
        strip = Image.new("RGB", (W, 84), (255, 255, 255))
        ImageDraw.Draw(strip).text((10, 8), str(i), fill=(0, 0, 0), font=font)
        both = Image.new("RGB", (W, strip.height + im.height), (255, 255, 255))
        both.paste(strip, (0, 0))
        both.paste(im, (0, strip.height))
        ims.append(both)
    cols = 3
    w, h = max(i.width for i in ims), max(i.height for i in ims)
    rows = (len(ims) + cols - 1) // cols
    sh = Image.new("RGB", (cols * (w + 16), rows * (h + 16)), (255, 255, 255))
    for i, im in enumerate(ims):
        sh.paste(im, ((i % cols) * (w + 16), (i // cols) * (h + 16)))
    sh.save(os.path.join(tiles, "sheet.png"))


if __name__ == "__main__":
    if sys.argv[1] == "SELECT":
        out_dir = sys.argv[7]
        sel = select(*sys.argv[2:7], out_dir)
        for s in sel:
            print(s["plate"], s["staff"], s["rule"], s["bucket"], s["off"], "->", s["on"])
        json.dump(sel, open(os.path.join(out_dir, "sel.json"), "w"), indent=1)
    else:
        render(load(sys.argv[2]), sys.argv[3])
