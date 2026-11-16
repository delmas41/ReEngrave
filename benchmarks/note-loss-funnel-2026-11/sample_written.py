"""ROADMAP 2.311 -- 12 WRITTEN NOTES AT RANDOM (6 per plate), as blind tiles for Sean.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/sample_written.py \
        --lit LIT.facts.json --bra BRA.facts.json --out out/print/2.311-written --key out/print/2.311-written-key.json

Population: every <note> (not rest) the exported file holds on the frozen sample's count pages (benchmarks/lane-report/
sample.json; Litolff's context page 1 is not counted), that has a place on the page (its glyph key). Nothing filtered.
Drawn with random.Random(2311) from the list sorted by glyph key. Each tile: the print as rendered for the record (600 dpi),
12 x 10 staff spaces around the mark, ONE thin orange box = the glyph box the note was written from, nothing else; at
least 450 px tall; one sheet.png in two columns, numbered. The key (what we wrote) is written OUTSIDE the tile folder.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

from tools.omr.preprocessing import render_page
from tools.omr.staged.lane_report import LIB, PLATES

ORANGE = (255, 140, 0)
SAMPLE = json.load(open("benchmarks/lane-report/sample.json"))


def population(f: dict, plate: str) -> list:
    pages = set(SAMPLE["plates"][plate]["pages"])
    return sorted((h for h in f["written"] if h["kind"] == "note" and h["page"] in pages and h.get("rg")), key=lambda h: h["rg"])


def cut(items: list, out: Path, key_path: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    W = 600
    tiles, key, cache = [], [], {}
    for n, it in enumerate(items, 1):
        plate, pg = it["plate"], it["page"]
        if (plate, pg) not in cache:
            cache.clear()
            cache[(plate, pg)] = Image.fromarray(render_page(str(LIB / PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
        im = cache[(plate, pg)]
        u = PLATES[plate]["unit"]
        b = it["box"]
        bb = [b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2]
        cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        x0, y0 = max(0, int(cx - 6 * u)), max(0, int(cy - 5 * u))
        x1, y1 = x0 + int(12 * u), y0 + int(10 * u)
        crop = im.crop((x0, y0, x1, y1)).copy()
        s = W / crop.width
        crop = crop.resize((W, int(crop.height * s)), Image.LANCZOS)
        ImageDraw.Draw(crop).rectangle([round((bb[0] - x0) * s), round((bb[1] - y0) * s), round((bb[2] - x0) * s),
                                        round((bb[3] - y0) * s)], outline=ORANGE, width=2)
        crop.save(out / ("tile_%02d.png" % n))
        tiles.append(crop)
        key.append(dict(tile=n, plate=plate, page=pg, rg=it["rg"], box=b, written_type=it["type"],
                        written_dots=len((it.get("sub") or {}).get("dot") or []), pitch=it["pitch"], blue=it["blue"],
                        part=it["part"], measure=it["measure"], crop_origin=[x0, y0], scale=s))
    h = max(t.height for t in tiles)
    cols = 2
    rows = (len(tiles) + 1) // cols
    sheet = Image.new("RGB", (cols * (W + 12) + 12, rows * (h + 34) + 12), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for n, t in enumerate(tiles):
        x, y = 12 + (n % cols) * (W + 12), 12 + (n // cols) * (h + 34)
        d.text((x, y + 4), "%d" % (n + 1), fill=(0, 0, 0))
        sheet.paste(t, (x, y + 22))
    sheet.save(out / "sheet.png")
    (out / "README.md").write_text(
        "# 2.311 written notes, drawn at random\n\nTwelve pieces of the printed page. Each has ONE thin orange box and "
        "nothing else drawn; the box is the mark one written note was made from.\n\n**Question, for every tile:** Is the "
        "boxed mark a note? If yes, what value (and dotted)?\n\nAnswer by tile number.\n")
    key_path.write_text(json.dumps(key, indent=1, default=str))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lit", required=True)
    ap.add_argument("--bra", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--seed", type=int, default=2311)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    items = []
    for plate, path in (("litolff", a.lit), ("brahms", a.bra)):
        pop = population(json.load(open(path)), plate)
        print(plate, "population", len(pop))
        items += [dict(h, plate=plate) for h in rng.sample(pop, 6)]
    cut(items, Path(a.out), Path(a.key))
    print("tiles", len(items))


if __name__ == "__main__":
    main()
