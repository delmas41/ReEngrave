"""ROADMAP 2.311 small test -- crops of the refused notes (our look) and 12 blind tiles for Sean, both drawn from the page image.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/beam_crops.py \
        --lit-notes L.beamnotes.json --lit-extra L.extra.json --bra-notes B.beamnotes.json --bra-extra B.extra.json \
        --look-dir LOOKDIR --tiles out/print/2.311-beams --key out/print/2.311-beams-key.json

LOOK: 18 notes per plate drawn with random.Random(2311101) from the refused-note list sorted by key (not by outcome), sheets of 6, the same drawing as the tile
but with the key number under it (our own look, rule 7).
TILES: 6 per plate, random.Random(2311102) from the same sorted list, none of them in the look sample. One staff per tile (the vertical window runs to the
midpoint to the staves above and below, further only where this note's stem or ledger stack needs it), 22 staff spaces wide, whole stem and the beams around it
inside the window, ONE thin orange box from the head to the stem tip (where the record has no stem, the box runs 3.5 staff spaces from the head the way the
head's place on the staff says a stem goes; the key says so). Nothing else drawn, no numbers on the tile.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

from checksheet import page_image

ORANGE = (255, 140, 0)
W_OUT = 1250


def note_box(it: dict, sp: float, lines: list) -> tuple:
    hb = it["head_box"]
    sb = it.get("stem_box")
    if sb:
        return [min(hb[0], sb[0]), min(hb[1], sb[1]), max(hb[2], sb[2]), max(hb[3], sb[3])], "stem_read"
    d = (it.get("stem_dir") or [None, None])[1]
    cy = (hb[1] + hb[3]) / 2
    if d not in ("up", "down"):
        d = "up" if cy > (lines[0] + lines[4]) / 2 else "down"
        how = "stem_direction_from_head_place"
    else:
        how = "stem_not_read_direction_from_record"
    b = list(hb)
    if d == "up":
        b[1] -= 3.5 * sp
    else:
        b[3] += 3.5 * sp
    return b, how


def render(it: dict, extra: dict, W: int = W_OUT) -> tuple:
    page, system, staff = it["page"], it["system"], it["staff"]
    lines = extra["staff_lines"]["%d/%d/%d" % (page, system, staff)]
    sp = (lines[4] - lines[0]) / 4.0
    im = page_image(it["plate"], page)
    box, how = note_box(it, sp, lines)
    allst = [v for k, v in extra["staff_lines"].items() if k.split("/")[0] == str(page) and v != lines]
    above = [v[4] for v in allst if v[4] < lines[0]]
    below = [v[0] for v in allst if v[0] > lines[4]]
    up_nb, dn_nb = (max(above) if above else None), (min(below) if below else None)
    top = (lines[0] + up_nb) / 2 if up_nb is not None else lines[0] - 8 * sp
    bot = (lines[4] + dn_nb) / 2 if dn_nb is not None else lines[4] + 8 * sp
    need_top = min(box[1], lines[0]) - 2.2 * sp
    need_bot = max(box[3], lines[4]) + 2.2 * sp
    # window = what this staff and this note need (staff +-2.5 sp, the box +-2.2 sp), never past the midpoint to the neighbouring staff
    mid_top, mid_bot = top, bot
    top = max(mid_top, min(need_top, lines[0] - 2.5 * sp))
    bot = min(mid_bot, max(need_bot, lines[4] + 2.5 * sp))
    top, bot = min(top, box[1] - 1.0 * sp), max(bot, box[3] + 1.0 * sp)       # the whole stem, even past the midpoint
    cx = (box[0] + box[2]) / 2
    cw = 22 * sp
    X0, X1, Y0, Y1 = int(cx - cw / 2), int(cx + cw / 2), int(top), int(bot)
    canvas = Image.new("RGB", (X1 - X0, Y1 - Y0), (255, 255, 255))
    sx0, sy0, sx1, sy1 = max(0, X0), max(0, Y0), min(im.width, X1), min(im.height, Y1)
    canvas.paste(im.crop((sx0, sy0, sx1, sy1)), (sx0 - X0, sy0 - Y0))
    s = W / canvas.width
    crop = canvas.resize((W, int(round(canvas.height * s))), Image.LANCZOS)
    pad = 0.15 * sp
    ImageDraw.Draw(crop).rectangle([round((box[0] - pad - X0) * s), round((box[1] - pad - Y0) * s), round((box[2] + pad - X0) * s), round((box[3] + pad - Y0) * s)],
                                   outline=ORANGE, width=2)
    return crop, dict(box_page_px=[round(x, 1) for x in box], box_how=how, crop_origin=[X0, Y0], scale=round(s, 4), staff_lines=lines, staff_space=round(sp, 2),
                      crop_h_staff_spaces=round((bot - top) / sp, 1))


def sheet(tiles: list, out: Path, cols: int = 2, labels: list | None = None) -> None:
    W = max(t.width for t in tiles)
    rows = (len(tiles) + cols - 1) // cols
    rh = [max(t.height for t in tiles[r * cols:(r + 1) * cols]) for r in range(rows)]
    sh = Image.new("RGB", (cols * (W + 12) + 12, sum(h + 30 for h in rh) + 12), (255, 255, 255))
    d = ImageDraw.Draw(sh)
    y = 12
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c
            if i >= len(tiles):
                continue
            x = 12 + c * (W + 12)
            d.text((x, y + 4), (labels[i] if labels else "%d" % (i + 1)), fill=(0, 0, 0))
            sh.paste(tiles[i], (x, y + 22))
        y += rh[r] + 30
    sh.save(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    for n in ("lit-notes", "lit-extra", "bra-notes", "bra-extra", "look-dir", "tiles", "key", "look-key"):
        ap.add_argument("--" + n, required=True)
    a = ap.parse_args()
    pops = {}
    for plate, nf, ef in (("litolff", a.lit_notes, a.lit_extra), ("brahms", a.bra_notes, a.bra_extra)):
        notes = sorted(json.load(open(nf)), key=lambda i: i["key"])
        pops[plate] = (notes, json.load(open(ef)))
    look, tile = [], []
    for plate in ("litolff", "brahms"):
        notes, _ = pops[plate]
        rng = random.Random(2311101)
        lk = rng.sample(notes, 18)
        look += lk
        rng2 = random.Random(2311102)
        rest = [n for n in notes if n not in lk]
        tile += rng2.sample(rest, 6)
    Path(a.look_dir).mkdir(parents=True, exist_ok=True)
    lkey = []
    for s in range(0, len(look), 6):
        imgs, labs = [], []
        for n, it in enumerate(look[s:s + 6], s + 1):
            crop, geo = render(it, pops[it["plate"]][1], 760)
            imgs.append(crop)
            labs.append("%d %s p%d %s | %s | %s" % (n, it["plate"], it["page"], it["key"], it["reason"], it["mechanism"]))
            lkey.append(dict(look=n, **it, **geo))
        sheet(imgs, Path(a.look_dir) / ("look_%d.png" % (s // 6 + 1)), 2, labs)
    Path(a.look_key).write_text(json.dumps(lkey, indent=1, default=str))
    out = Path(a.tiles)
    out.mkdir(parents=True, exist_ok=True)
    imgs, key = [], []
    for n, it in enumerate(tile, 1):
        crop, geo = render(it, pops[it["plate"]][1])
        crop.save(out / ("tile_%02d.png" % n))
        imgs.append(crop)
        key.append(dict(tile=n, **{k: it[k] for k in ("plate", "page", "system", "staff", "cell", "key", "fate", "reason", "mechanism", "candidates", "levels", "head_class", "bar_kind")}, **geo))
    sheet(imgs, out / "sheet.png", 2)
    (out / "README.md").write_text("# 2.311 beams: 12 refused notes drawn at random\n\nTwelve pieces of the printed page, one staff each. ONE thin orange box = one note, "
                                   "from its head to the tip of its stem. Nothing else is drawn.\n\n**Question, for every tile:** what is the boxed note's value "
                                   "(whole, half, quarter, eighth, sixteenth, ...; dotted or not)? Say \"cannot tell\" if you cannot.\n\nAnswer by tile number.\n")
    Path(a.key).write_text(json.dumps(key, indent=1, default=str))
    print("look", len(look), "tiles", len(tile), [(t["plate"], t["page"]) for t in tile])


if __name__ == "__main__":
    main()
