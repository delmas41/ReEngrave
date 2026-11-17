"""2.306 r14: 12 blind tiles for Sean, drawn at random (seed 2306014, 6 per plate) from what the lane CHANGED between the base arm and the r14 arm
(each a re-adjudicated record of its own tree's gather, flag ON): (a) a written note whose flag / beam changed, (b) a head the page stem reader
reads now and refused before. Each tile: one staff around the note, the STEM'S INK as the reader holds it boxed orange (`Q.PAGE_STEM` stem_box),
a small orange tick under the head it was joined to, nothing else; >= 450 px tall. `sheet.png` two per row; key OUTSIDE the tile folder.

    PYTHONPATH=. python3 benchmarks/page-ledger-2026-11/2306/r14_tiles.py OUTDIR KEY.json \
        brahms PAGE.png BASE.facts BASE.record R14.facts R14.record  litolff PAGE.png BASE.facts BASE.record R14.facts R14.record
"""
import json
import os
import random
import sys

from PIL import Image, ImageDraw

from tools.omr.staged.judged import boxes_overlap
from tools.omr.staged.record_io import load_record

SP = {"brahms": 32.0, "litolff": None}
outdir, keyp = sys.argv[1], sys.argv[2]
args = sys.argv[3:]
plates = [args[i:i + 6] for i in range(0, len(args), 6)]
os.makedirs(os.path.join(outdir, "tiles"), exist_ok=True)


def stems_of(rec_p):
    rec = load_record(rec_p)["record"]
    read, refused = {}, {}
    for o in rec["observations"]:
        if o["quantity"] == "page_stem":
            d = o.get("detail") or {}
            read[o["subject"]] = dict(stem_box=d.get("stem_box"), how=d.get("how"), direction=d.get("direction"))
    for a in rec.get("abstentions") or ():
        if a.get("quantity") == "page_stem":
            refused[a["subject"]] = (a.get("detail") or {}).get("how")
    return read, refused


def bf(h):
    s = h.get("sub") or {}
    return ("beam" if s.get("beam") else ("flag" if s.get("flag") else "none"))


key = []
tiles = []
rng = random.Random(2306014)
for plate, png, bfacts, brec, rfacts, rrec in plates:
    B, R = json.load(open(bfacts)), json.load(open(rfacts))
    bread, brefused = stems_of(brec)
    rread, _ = stems_of(rrec)
    bw = [h for h in B["written"] if h["kind"] == "note"]
    rw = [h for h in R["written"] if h["kind"] == "note"]
    pool = []
    # (a) the written note's flag/beam changed (matched by place)
    for h in rw:
        m = [b for b in bw if b["rg"] == h["rg"]] or sorted(
            [b for b in bw if b["page"] == h["page"] and boxes_overlap(b["box"], h["box"])[0]],
            key=lambda b: -boxes_overlap(b["box"], h["box"])[1])
        if m and bf(m[0]) != bf(h) and h["rg"] in rread:
            pool.append(dict(kind="flag_or_beam", rg=h["rg"], box=h["box"], page=h["page"], before=bf(m[0]), after=bf(h), type=h["type"]))
    # (b) a head the page reads now and refused before (matched by place through the glyph boxes)
    bglyph = B["glyphs"]
    for rg, st in rread.items():
        g = R["glyphs"].get(rg)
        if not g:
            continue
        same = [k for k, bg in bglyph.items() if bg["page"] == g["page"] and boxes_overlap(bg["box"], g["box"])[0]]
        if same and all(k not in bread for k in same) and any(k in brefused for k in same):
            pool.append(dict(kind="stem_now_read", rg=rg, box=g["box"], page=g["page"], before=brefused.get(same[0]), after=st["how"]))
    seen, uniq = set(), []
    for p in pool:
        if p["rg"] not in seen:
            seen.add(p["rg"])
            uniq.append(p)
    pick = rng.sample(uniq, min(6, len(uniq)))
    print(plate, "changed places", len(uniq), {k: sum(1 for p in uniq if p["kind"] == k) for k in ("flag_or_beam", "stem_now_read")})
    img = Image.open(png).convert("RGB")
    for p in pick:
        st = rread[p["rg"]]
        hb = p["box"]
        sp = SP[plate] or (hb[3] - hb[1]) / 1.05
        im = img.copy()
        d = ImageDraw.Draw(im)
        sb = st["stem_box"]
        if sb:
            d.rectangle([sb[0] - 5, sb[1] - 3, sb[2] + 5, sb[3] + 3], outline=(255, 120, 0), width=3)
        cx = (hb[0] + hb[2]) / 2
        # the tick stands under the head, on the side away from the stem, so it never sits inside the stem's box
        ty = hb[3] + 0.6 * sp
        tx0, tx1 = (cx, hb[2] + 0.5 * sp) if st["direction"] == "down" else (hb[0] - 0.5 * sp, cx)
        d.line([tx0, ty, tx1, ty], fill=(255, 120, 0), width=4)
        y0 = min(hb[1], sb[1] if sb else hb[1]) - 1.5 * sp
        y1 = max(hb[3], sb[3] if sb else hb[3]) + 1.5 * sp
        cy = (y0 + y1) / 2
        half = max((y1 - y0) / 2, 5.5 * sp)
        c = im.crop((int(cx - 9 * sp), int(cy - half), int(cx + 9 * sp), int(cy + half)))
        if c.height < 460:
            c = c.resize((int(c.width * 460 / c.height), 460))
        tiles.append(c)
        key.append(dict(tile=len(tiles), plate=plate, **{k: v for k, v in p.items()}, stem_how=st["how"], stem_direction=st["direction"]))
        c.save(os.path.join(outdir, "tiles", "tile%02d.png" % len(tiles)))
W = max(t.width for t in tiles)
H = max(t.height for t in tiles)
sheet = Image.new("RGB", (2 * W + 30, ((len(tiles) + 1) // 2) * (H + 40)), "white")
dr = ImageDraw.Draw(sheet)
for i, t in enumerate(tiles):
    x, y = (i % 2) * (W + 30), (i // 2) * (H + 40)
    dr.text((x + 4, y + 4), "Tile %d" % (i + 1), fill=(0, 0, 0))
    sheet.paste(t, (x, y + 30))
sheet.save(os.path.join(outdir, "sheet.png"))
json.dump(dict(seed=2306014, question="The orange tick marks a note. Is the orange box all of that note's stem (yes / only part / not its stem)? "
               "And does the note carry a flag or a beam, or neither?", tiles=key), open(keyp, "w"), indent=1, default=str)
print(len(tiles), "tiles")
