"""ROADMAP 2.245 -- 12 blind tiles for Sean: "what is the ink in each box, and is it one mark?"

One staff per tile (the staff nearest the box, +-2 spaces, widened only to hold the box), a thin orange box at the detector box's own
page extent, nothing else drawn. key.json is written OUTSIDE the tile folder. Picks (seed 2245, from the 20261029-night slices of the
frozen sample, `look.py`'s reading of the record):
  * the four places of the lane (Sean's earlier tiles: 2.240-s2 tiles 2, 9, 12; 2.242 tile 1);
  * 4 more head-class boxes 3+ spaces wide that ADJUDICATE keeps as heads today (what `OMR_BOX_KIND_SIZE` refuses);
  * 2 more `tie` boxes whose system-arc trace does not bow (bow < 0.15 sp over 3+ sp: the hairpin-as-arc count);
  * 2 controls the rule leaves alone: a head box 2.5-3.0 spaces wide, and a head box of ordinary size.
Usage: python3 benchmarks/wrong-kind-boxes-2026-10/tiles.py BOXES.json STRAIGHT.json
  (BOXES.json / STRAIGHT.json: the lane's measurement dumps, every detector box of the sample with its size in spaces and verdicts; the
  straight system arcs -- see FINDINGS "how often".)
"""
from __future__ import annotations

import json
import pathlib
import random
import sys

from PIL import Image, ImageDraw

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import look  # noqa: E402

ROOT = HERE.parents[1]
OUT = ROOT / "out/print/2.245-tiles"
FOUR = [("litolff", "glyph/10/1/9/7/12", "2.240-s2 tile 2"), ("brahms", "glyph/19/0/9/1/17", "2.240-s2 tile 9"),
        ("brahms", "glyph/5/0/4/4/15", "2.240-s2 tile 12"), ("litolff", "glyph/4/0/8/5/8", "2.242 tile 1")]


def tile(plate, page, box, path):
    pws, img, sp = look.page(plate, page)
    x0, y0, x1, y1 = box
    st = look.nearest_staff(pws, (y0 + y1) / 2)
    cx = (x0 + x1) / 2
    ta = int(min(st.top_y - 2 * sp, y0 - 0.5 * sp))
    tb = int(max(st.bottom_y + 2 * sp, y1 + 0.5 * sp))
    tl = int(min(cx - 6 * sp, x0 - sp))
    tr = int(max(cx + 6 * sp, x1 + sp))
    t = img.crop((tl, ta, tr, tb)).copy()
    ImageDraw.Draw(t).rectangle([x0 - tl - 2, y0 - ta - 2, x1 - tl + 2, y1 - ta + 2], outline=(255, 120, 0), width=2)
    t.save(path)
    return int(st.staff_index), [tl, ta]


def main(boxes_path, straight_path):
    boxes = json.loads(pathlib.Path(boxes_path).read_text())
    straight = json.loads(pathlib.Path(straight_path).read_text())
    rng = random.Random(2245)
    by = {(pl, r["g"]): r for pl, rows in boxes.items() for r in rows}
    picks = []
    for pl, g, src in FOUR:
        r = by[(pl, g)]
        picks.append(dict(plate=pl, g=g, pb=r["pb"], cls=r["cls"], w_sp=r["w"], h_sp=r["h"], conf=r["conf"], why="lane case (" + src + ")"))
    four = {g for _pl, g, _s in FOUR}

    def kept(r):
        return r["nh"] and r["nh"][0] == "decided" and r["nh"][1] is False

    wide = [(pl, r) for pl, rows in sorted(boxes.items()) for r in rows
            if r["cls"].lower().startswith("notehead") and r["w"] >= 3.0 and kept(r) and r["g"] not in four]
    for pl, r in rng.sample(wide, 4):
        picks.append(dict(plate=pl, g=r["g"], pb=r["pb"], cls=r["cls"], w_sp=r["w"], h_sp=r["h"], conf=r["conf"],
                          why="head box >= 3.0 sp kept as a head (OMR_BOX_KIND_SIZE refuses)"))
    st = [s for s in straight if s["g"] not in four]
    for s in rng.sample(st, 2):
        picks.append(dict(plate=s["plate"], g=s["g"], pb=s["pb"], cls="tie", why="tie box whose system-arc trace does not bow"))
    mid = [(pl, r) for pl, rows in sorted(boxes.items()) for r in rows
           if r["cls"].lower().startswith("notehead") and 2.5 <= r["w"] < 3.0 and kept(r)]
    norm = [(pl, r) for pl, rows in sorted(boxes.items()) for r in rows
            if r["cls"].lower().startswith("notehead") and 1.2 <= r["w"] <= 1.6 and 1.0 <= r["h"] <= 1.4 and kept(r)]
    for (pl, r), why in ((rng.choice(mid), "CONTROL: head box 2.5-3.0 sp, left alone"), (rng.choice(norm), "CONTROL: ordinary head box")):
        picks.append(dict(plate=pl, g=r["g"], pb=r["pb"], cls=r["cls"], w_sp=r["w"], h_sp=r["h"], conf=r["conf"], why=why))
    rng.shuffle(picks)
    (OUT / "tiles").mkdir(parents=True, exist_ok=True)
    key = []
    for i, pk in enumerate(picks, 1):
        page = int(pk["g"].split("/")[1])
        name = "tile_%02d.png" % i
        staff, origin = tile(pk["plate"], page, pk["pb"], OUT / "tiles" / name)
        key.append({"tile": i, "page": page, "staff_index_on_page": staff, "crop_origin": origin, **pk})
    (OUT / "key.json").write_text(json.dumps(key, indent=1))
    # sheet
    ims = [Image.open(OUT / "tiles" / ("tile_%02d.png" % i)) for i in range(1, len(picks) + 1)]
    cw, ch, cols = 420, 300, 4
    S = Image.new("RGB", (cols * cw, 3 * (ch + 20)), "white")
    d = ImageDraw.Draw(S)
    for i, im in enumerate(ims):
        im = im.convert("RGB")
        im.thumbnail((cw - 8, ch - 8))
        x, y = (i % cols) * cw, (i // cols) * (ch + 20)
        S.paste(im, (x + 4, y + 18))
        d.text((x + 4, y + 2), str(i + 1), fill=(0, 0, 0))
    S.save(OUT / "tiles" / "sheet.png")
    (OUT / "tiles" / "README.md").write_text(
        "# 2.245 tiles -- what is the ink in each box?\n\n"
        "Twelve tiles, one staff each, from the Litolff Beethoven 5 and the Breitkopf Brahms 1 scans. Each has ONE thin orange box; "
        "the orange only shows where to look, it is not a reading.\n\n"
        "**For each tile: what is the ink in the box, and is it one mark?** (for example: a note, two notes, part of a slur, part of "
        "a hairpin, a ledger line, a rest, a beam.)\n\n"
        "The answers go in `../answers.json`.\n")
    print("wrote", len(key), "tiles to", OUT)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
