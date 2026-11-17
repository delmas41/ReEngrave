"""2.305 r9 -- 12 blind tiles for Sean from what the lane CHANGED (changes.py), 6 per plate, drawn at random (seed) -- or, with --places KEY.json, the
SAME places as an earlier key (the remake). Each tile: ONE staff (the staff of the arc's first note, plus only as much above / below as the arc's ink and
its two notes need), both ends of the arc and both ticked notes whole; a thin orange box on each piece of ink the reader held as this arc (a cap and a
cup an old pairing held are two boxes); a small tick under each of the two notes the file joined (or joined before, for a removed arc); nothing else.
Every tile 1250 px wide (small crops enlarged), at least 450 px tall. sheet.png two per row; the key goes OUTSIDE the tile folder and says, per tile,
what the file wrote before and writes now.

    python3 tiles.py OUTDIR KEY.json SEED chg-brahms.json chg-litolff.json [--places OLDKEY.json]
"""
import json
import os
import random
import sys

sys.path.insert(0, os.getcwd())
from PIL import Image, ImageDraw  # noqa: E402

from tools.omr.preprocessing import render_page  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDF = {"brahms": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
       "litolff": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"}
ORANGE = (255, 120, 0)
W, MIN_H = 1250, 450
WORDS = {1: "one", 2: "two", 3: "three"}


def said(kinds):
    if not kinds:
        return "nothing"
    if len(set(kinds)) == 1:
        k = kinds[0]
        return ("a %s" % k) if len(kinds) == 1 else "%s %ss" % (WORDS.get(len(kinds), len(kinds)), k)
    return " and ".join("a %s" % k for k in kinds)


def line_of(r):
    return "before: %s between the ticked notes; now: %s" % (said(r["before"]), said(r["after"]))


def main():
    out, key_path, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    args = [a for a in sys.argv[4:] if not a.startswith("--")]
    places = None
    if "--places" in sys.argv:
        places = json.load(open(sys.argv[sys.argv.index("--places") + 1]))["tiles"]
        args = [a for a in args if a != sys.argv[sys.argv.index("--places") + 1]]
    pools = [json.load(open(p)) for p in args]
    if places is not None:
        by = {(r["plate"], r["a"], r["b"]): r for pool in pools for r in pool}
        drawn = [by[(t["plate"], t["a"], t["b"])] for t in places]
    else:
        rng = random.Random(seed)
        drawn = []
        for pool in pools:
            ok = [r for r in pool if r.get("ink")]
            drawn += rng.sample(ok, min(6, len(ok)))
        rng.shuffle(drawn)
    os.makedirs(out, exist_ok=True)
    pages, tiles, key = {}, [], []
    for i, r in enumerate(drawn, 1):
        pk = (r["plate"], r["page"])
        if pk not in pages:
            pages[pk] = Image.fromarray(render_page(PDF[r["plate"]], r["page"], dpi=600).rgb).convert("RGB")
        im = pages[pk].copy()
        dr = ImageDraw.Draw(im)
        boxes = []
        for bx in (r.get("ink_boxes") or [r["ink"]]):
            if bx not in boxes:
                boxes.append(bx)
        if r.get("src") in ("old_box",):
            # the old box path's boxes are found by place (changes.py); a box lying wholly under another box's width but clear of it in height is a
            # different, smaller arc there (Brahms p0 12/0: a short slur under the long one), not this arc's ink
            boxes = [bx for bx in boxes if not any(o is not bx and o[0] <= bx[0] and bx[2] <= o[2] and (bx[1] > o[3] or bx[3] < o[1])
                                                   for o in boxes)]
        def _iou(p, q):
            ix = max(0.0, min(p[2], q[2]) - max(p[0], q[0]))
            iy = max(0.0, min(p[3], q[3]) - max(p[1], q[1]))
            u = (p[2] - p[0]) * (p[3] - p[1]) + (q[2] - q[0]) * (q[3] - q[1]) - ix * iy
            return ix * iy / u if u > 0 else 0.0
        merged = []          # the same ink boxed again from a neighbouring cell is ONE box on the tile
        for bx in boxes:
            for m in merged:
                if _iou(m, bx) > 0.6:
                    m[:] = [min(m[0], bx[0]), min(m[1], bx[1]), max(m[2], bx[2]), max(m[3], bx[3])]
                    break
            else:
                merged.append(list(bx))
        boxes = merged
        for bx in boxes:
            dr.rectangle([bx[0] - 3, bx[1] - 3, bx[2] + 3, bx[3] + 3], outline=ORANGE, width=2)
        ticks = []
        for nb in (r["a_box"], r["b_box"]):
            cx = (nb[0] + nb[2]) / 2.0
            ticks.append((cx, nb[3] + 12, nb[3] + 32))
            dr.line([(cx, nb[3] + 12), (cx, nb[3] + 32)], fill=ORANGE, width=3)
        lines = r.get("staff_lines") or []
        sp = (lines[-1] - lines[0]) / 4.0 if len(lines) == 5 else 30.0
        xs = [v for bx in boxes for v in (bx[0], bx[2])] + [r["a_box"][0], r["a_box"][2], r["b_box"][0], r["b_box"][2]]
        ys = [v for bx in boxes for v in (bx[1], bx[3])] + [r["a_box"][1], r["b_box"][1]] + [t[2] for t in ticks] + list(lines[:1]) + list(lines[-1:])
        x0, x1 = min(xs) - 2 * sp, max(xs) + 2 * sp
        y0, y1 = min(ys) - 0.75 * sp, max(ys) + 0.75 * sp
        if x1 - x0 < 0.64 * W:          # enlarge at most ~1.6x: a small crop takes more of its own staff left and right instead of blurring
            c = (x0 + x1) / 2.0
            x0, x1 = c - 0.32 * W, c + 0.32 * W
        if y0 < 0:
            y0 = 0
        if y1 > im.height:
            y1 = im.height
        x0, x1 = max(0, x0), min(im.width, x1)
        crop = im.crop((int(x0), int(y0), int(x1), int(y1)))
        band = crop.resize((W, int(round(crop.height * W / crop.width))), Image.LANCZOS)
        # ONE staff: the band holds only the staff, the arc's ink and its two notes; a band shorter than MIN_H is set on plain paper, never widened
        # onto the neighbouring staves
        tile = Image.new("RGB", (W, max(MIN_H, band.height)), "white")
        tile.paste(band, (0, (tile.height - band.height) // 2))
        tile.save(os.path.join(out, "tile_%02d.png" % i))
        tiles.append(tile)
        key.append(dict(tile=i, file_said=line_of(r),
                        **{k: r[k] for k in ("plate", "page", "change", "a", "b", "before", "after", "src", "ink_from")}, ink_boxes=boxes))
    rows = [tiles[j:j + 2] for j in range(0, len(tiles), 2)]
    gap, lab = 30, 34
    H = sum(max(t.height for t in row) + lab for row in rows)
    sheet = Image.new("RGB", (2 * W + gap, H), "white")
    dr = ImageDraw.Draw(sheet)
    y = 0
    for j, row in enumerate(rows):
        for k, t in enumerate(row):
            dr.text((k * (W + gap) + 6, y + 8), "Tile %d" % (2 * j + k + 1), fill=(0, 0, 0))
            sheet.paste(t, (k * (W + gap), y + lab))
        y += max(t.height for t in row) + lab
    sheet.save(os.path.join(out, "sheet.png"))
    with open(os.path.join(out, "README.txt"), "w") as fh:
        fh.write("2.305 r9 arc tiles (seed %d). Each orange box is ink the reader read as this ONE arc (two boxes: it held two pieces of ink as "
                 "one arc); the two orange ticks are under the two notes the file joins with it (or joined before this change).\nQuestion per "
                 "tile: is there one arc from the first ticked note to the second? If yes, a tie or a slur? If not, what is the boxed ink?\n" % seed)
    json.dump(dict(seed=seed, tiles=key), open(key_path, "w"), indent=1)
    print("tiles", [(k["tile"], k["plate"], tiles[k["tile"] - 1].size, k["file_said"]) for k in key])


if __name__ == "__main__":
    main()
