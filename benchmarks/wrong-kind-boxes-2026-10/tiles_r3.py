"""ROADMAP 2.245 round 3 -- 12 blind tiles for Sean: "what is the ink in each box, and is it one mark?"

Read off the ON arm's GATHERED records of the round-2 lane report (`out/lane-report/2.245-r3/work/{plate}.on.gathered.record.json`), by
text (the records are 1-3 GB): the head boxes GATHER split off a wide head box (incl. the places of round-1 tiles 4 and 10), wide boxes
left as the refused remainder and one left unread, system-arc traces refused because they do not bow, CV hairpins refused as narrower
than a hairpin, and round-1 tile 9's place (a head box on a C clef). One staff per tile, one thin orange box, nothing else; key.json
OUTSIDE the tile folder. Seed 2245. Usage: python3 benchmarks/wrong-kind-boxes-2026-10/tiles_r2.py
"""
from __future__ import annotations

import json
import pathlib
import random
import re
import sys

from PIL import Image, ImageDraw

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import look  # noqa: E402
import tiles as T1  # noqa: E402

ROOT = HERE.parents[1]
WORK = ROOT / "out/lane-report/2.245-r3/work"
OUT = ROOT / "out/print/2.245-r3-tiles"

BOX = re.compile(r'"subject":"(glyph/[0-9/]+)","quantity":"glyph_box","value":\["([A-Za-z0-9]+)",[^\]]*\][^{}]*"detail":\{[^{}]*?'
                 r'"box_kind":\{([^{}]*)\}[^{}]*?"bbox_page_px":\[([^\]]*)\]')
ANYBOX = re.compile(r'"subject":"(glyph/[0-9/]+)","quantity":"glyph_box","value":\["([A-Za-z0-9]+)",[^\]]*\][^{}]*"detail":\{[^{}]*?'
                    r'"bbox_page_px":\[([^\]]*)\]')
WHY = re.compile(r'"subject":"([a-z]+/[0-9/]+)","quantity":"(system_arc|wedge_box)"[^{}]*"reason":"below_threshold","detail":\{([^{}]*)\}')


def scan(plate):
    text = (WORK / ("%s.on.gathered.record.json" % plate)).read_text()
    split, boxes, why = [], {}, []
    for m in BOX.finditer(text):
        split.append((m.group(1), m.group(2), json.loads("{" + m.group(3) + "}"), [float(v) for v in m.group(4).split(",")]))
    for m in ANYBOX.finditer(text):
        boxes[m.group(1)] = [float(v) for v in m.group(3).split(",")]
    for m in WHY.finditer(text):
        d = json.loads("{" + m.group(3) + "}")
        if d.get("why") in ("trace_does_not_bow", "narrower_than_a_hairpin"):
            why.append((m.group(1), m.group(2), d))
    return split, boxes, why


def main():
    rng = random.Random(2245)
    picks = []
    data = {pl: scan(pl) for pl in ("litolff", "brahms")}
    # round-2 tiles 2, 3, 6, 10: the wide boxes there (what round 3 does with them: split, covered + refused, or unread)
    places = {"litolff": ["glyph/6/0/3/8/14", "glyph/4/0/5/13/5", "glyph/2/0/7/10/3", "glyph/4/1/3/3/8"]}
    for pl, gs in places.items():
        for g, _c, k, b in data[pl][0]:
            if g in gs:
                why = ("wide head box, inside unread (abstains)" if k.get("unread") else "wide head box, refused remainder")
                picks.append(dict(plate=pl, g=g, pb=b, why=why + " -- round-2 tile place"))
    added = [(pl, g, b, k) for pl, (sp, _bx, _w) in data.items() for g, _c, k, b in sp if "split_from" in k]
    hollow = [a for a in added if a[3].get("hollow")]
    filled = [a for a in added if not a[3].get("hollow")]
    for pl, g, b, k in rng.sample(hollow, min(2, len(hollow))) + rng.sample(filled, min(6 - min(2, len(hollow)), len(filled))):
        picks.append(dict(plate=pl, g=g, pb=b, why="head GATHER split off a wide head box (%s)" % ("hollow" if k.get("hollow") else "filled")))
    rem = [(pl, g, b) for pl, (sp, _bx, _w) in data.items() for g, _c, k, b in sp
           if k.get("unread") is False and "split_from" not in k and g not in places.get(pl, [])]
    for pl, g, b in rng.sample(rem, min(12 - len(picks), len(rem))):
        picks.append(dict(plate=pl, g=g, pb=b, why="wide head box, refused remainder"))
    picks = picks[:12]
    rng.shuffle(picks)
    (OUT / "tiles").mkdir(parents=True, exist_ok=True)
    key = []
    for i, pk in enumerate(picks, 1):
        page = int(pk["g"].split("/")[1])
        staff, origin = T1.tile(pk["plate"], page, pk["pb"], OUT / "tiles" / ("tile_%02d.png" % i))
        key.append({"tile": i, "page": page, "staff_index_on_page": staff, "crop_origin": origin, **pk})
    (OUT / "key.json").write_text(json.dumps(key, indent=1))
    ims = [Image.open(OUT / "tiles" / ("tile_%02d.png" % i)).convert("RGB") for i in range(1, len(picks) + 1)]
    cw, ch, cols = 420, 300, 4
    S = Image.new("RGB", (cols * cw, ((len(ims) + cols - 1) // cols) * (ch + 20)), "white")
    d = ImageDraw.Draw(S)
    for i, im in enumerate(ims):
        im.thumbnail((cw - 8, ch - 8))
        x, y = (i % cols) * cw, (i // cols) * (ch + 20)
        S.paste(im, (x + 4, y + 18))
        d.text((x + 4, y + 2), str(i + 1), fill=(0, 0, 0))
    S.save(OUT / "tiles" / "sheet.png")
    (OUT / "tiles" / "README.md").write_text(
        "# 2.245 round 3 tiles -- what is the ink in each box?\n\n"
        "Twelve tiles, one staff each, from the Litolff Beethoven 5 and the Breitkopf Brahms 1 scans. Each has ONE thin orange box; "
        "the orange only shows where to look, it is not a reading.\n\n"
        "**For each tile: what is the ink in the box, and is it one mark?** (for example: a note, two notes, part of a slur, part of "
        "a hairpin, a letter, a beam, part of a clef.)\n\nThe answers go in `../answers.json`.\n")
    print("wrote", len(key), "tiles to", OUT)


if __name__ == "__main__":
    main()
