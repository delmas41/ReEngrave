"""ROADMAP 2.311 small test -- ONE TILE SET FOR SEAN: "what note is in the box?" (12 far heads, seed 2311312, 8 Litolff + 4 Brahms).

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/ledger_tiles.py INK.json OUTDIR KEY.json

Heads: the record places them 2+ ledger lines out (FINAL position, as in ledger_heights.py), the staff is the head's own (not moved to
another staff), the staff's printed clef was read as a plain G or F clef, and no other staff's lines fall inside the crop.
Tile: one staff from the page image, the WHOLE staff and every ledger line between it and the head, one thin orange box sized to the
head, nothing else drawn; same scale for both plates (45 px per staff space), same width 540, same height 640 (white below the crop).
A caption band under the page crop names the staff's clef (a fact read from the record's clef_glyph, not the pitch).
The key (outside the folder) holds the pitch we read and the clef.
"""
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from checksheet import page_image
from ledger_heights import load, owed
from tools.omr.pitch_resolver import _pitch_from_position
from tools.omr.staged.lane_report import RECORDS

SLICE = {"litolff": "claim-readout-slices-2306-smp4-lit", "brahms": "claim-readout-slices-2306-smp4-bra"}
import numpy as np

_G = {}
PX_PER_SP, W, H = 45.0, 540, 640
CLEF = {"clefG": "treble", "clefF": "bass"}


def clefs(plate):
    out = {}
    for line in open(RECORDS / SLICE[plate] / "observations.jsonl"):
        if '"quantity": "clef_glyph"' in line[:300]:
            o = json.loads(line)
            out.setdefault(o["subject"], o["value"])
    return out


def main(ink, outdir, keyfile):
    o = json.load(open(ink))
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    chosen = []
    for plate, n in (("litolff", 8), ("brahms", 4)):
        cl = clefs(plate)
        rows, _ = load(plate)
        staves = {}
        for sub, r in rows["staff_lines"].items():
            _, p, s, st = sub.split("/")
            staves.setdefault(int(p), []).append(r["value"])
        cand = []
        for h in o[plate]:
            if owed(h["final"]) < 2:
                continue
            kind = CLEF.get(cl.get("staff/%d/%d/%d" % (h["page"], h["system"], h["staff"])))
            if kind is None:
                continue
            sp = (h["lines"][4] - h["lines"][0]) / 4.0
            b = h["box"]
            cy = (b[1] + b[3]) / 2
            top, bot = min(h["lines"][0], cy) - 2.2 * sp, max(h["lines"][4], cy) + 2.2 * sp
            clash = any(l[0] != h["lines"][0] and any(top <= y <= bot for y in l) for l in staves[h["page"]])
            if clash:
                continue
            # a head-shaped box over real ink (our look at the first sheet found a word and a brace boxed): 0.8-2.2 sp wide,
            # 0.6-1.5 sp tall, at least half dark, and at least one ledger stroke counted by us
            bw, bh = (b[2] - b[0]) / sp, (b[3] - b[1]) / sp
            if not (0.8 <= bw <= 2.2 and 0.6 <= bh <= 1.5) or h["ink_count"] < 1:
                continue
            g = (np.array(page_image(plate, h["page"]).convert("L")) if _G.get("k") != (plate, h["page"]) else _G["g"])
            _G.update(k=(plate, h["page"]), g=g)
            if (g[int(b[1]):int(b[3]), int(b[0]):int(b[2])] < 128).mean() < 0.5:
                continue
            cand.append(dict(h, plate=plate, kind=kind))
        cand.sort(key=lambda h: h["key"])
        chosen += random.Random(2311312).sample(cand, n)
        print(plate, "candidates", len(cand))
    random.Random(2311312).shuffle(chosen)
    key = []
    tiles = []
    for i, h in enumerate(chosen, 1):
        sp = (h["lines"][4] - h["lines"][0]) / 4.0
        b = h["box"]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        k = PX_PER_SP / sp
        half_w = (W / k) / 2
        top = min(h["lines"][0], cy) - 2.0 * sp
        bot = max(h["lines"][4], cy) + 2.0 * sp
        im = page_image(h["plate"], h["page"]).crop((int(cx - half_w), int(top), int(cx + half_w), int(bot))).convert("RGB")
        d = ImageDraw.Draw(im)
        d.rectangle([b[0] - int(cx - half_w), b[1] - int(top), b[2] - int(cx - half_w), b[3] - int(top)], outline=(255, 140, 0), width=2)
        im = im.resize((W, int(im.height * k)))
        t = Image.new("RGB", (W, H), "white")
        t.paste(im, (0, 0))
        ImageDraw.Draw(t).text((8, im.height + 8), "%s clef" % h["kind"], fill=(0, 0, 0))
        assert im.height + 24 <= H and im.height >= 450 - 24, (i, im.height)
        t.save(outdir / ("tile_%02d.png" % i))
        tiles.append(t)
        pitch = _pitch_from_position(h["final"], h["kind"])
        key.append(dict(tile=i, plate=h["plate"], glyph=h["key"], page=h["page"], box=[round(v, 1) for v in b], clef=h["kind"],
                        position_read=h["final"], pitch_read=pitch, ledger_lines_owed=owed(h["final"]),
                        decided_by="ledger count" if h["ledger"] is not None else "geometry extrapolation (ledger read refused)",
                        geometry_position=h["geom_round"], geometry_pitch=_pitch_from_position(h["geom_round"], h["kind"]),
                        our_stroke_count=h["ink_count"]))
    rows = (len(tiles) + 1) // 2
    sheet = Image.new("RGB", (2 * (W + 12) + 12, rows * (H + 12) + 12), (200, 200, 200))
    for i, t in enumerate(tiles):
        sheet.paste(t, (12 + (i % 2) * (W + 12), 12 + (i // 2) * (H + 12)))
    sheet.save(outdir / "sheet.png")
    json.dump(key, open(keyfile, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:4])
