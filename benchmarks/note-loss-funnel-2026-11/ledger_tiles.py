"""ROADMAP 2.311 small test -- ONE TILE SET FOR SEAN: "what note is in the box?" (12 far heads, seed 2311313: 6 Litolff fallback-decided, 4 Litolff ledger-decided where the readings differ, 2 Brahms ledger-decided).

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
# heads our own look of the first remade sheet rejected (not a head of this staff / duplicate place / box over a flat): ledger_tiles_excluded.json
EXCL = set(json.load(open(Path(__file__).with_name('ledger_tiles_excluded.json'))))
PX_PER_SP, W, H = 42.0, 880, 620
CLEF = {"clefG": "treble", "clefF": "bass"}


def clefs(plate):
    """(first clef per staff, set of staves with a clef glyph in a later cell = clef in force NOT known from the first)."""
    first, later = {}, set()
    for line in open(RECORDS / SLICE[plate] / "observations.jsonl"):
        if '"quantity": "glyph_box"' in line[:300] and '"category": "clef"' in line[:1200]:
            o = json.loads(line)
            p, s, st, c, g = o["subject"].split("/")[1:]
            if int(c) > 0:
                later.add("staff/%s/%s/%s" % (p, s, st))
        elif '"quantity": "clef_glyph"' in line[:300]:
            o = json.loads(line)
            first.setdefault(o["subject"], o["value"])
    return first, later


def main(ink, outdir, keyfile):
    o = json.load(open(ink))
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    chosen = []
    for plate, groups in (("litolff", (("fallback", 6), ("ledger_differs", 4))), ("brahms", (("ledger", 2),))):
        cl, later = clefs(plate)
        rows, _ = load(plate)
        staves = {}
        for sub, r in rows["staff_lines"].items():
            _, p, s, st = sub.split("/")
            staves.setdefault(int(p), []).append(r["value"])
        cand = {g: [] for g, _ in groups}
        for h in o[plate]:
            if owed(h["final"]) < 2:
                continue
            sk = "staff/%d/%d/%d" % (h["page"], h["system"], h["staff"])
            kind = CLEF.get(cl.get(sk))
            if kind is None or sk in later:
                continue
            sp = (h["lines"][4] - h["lines"][0]) / 4.0
            b = h["box"]
            cy = (b[1] + b[3]) / 2
            lo, hi = min(h["lines"][0], cy), max(h["lines"][4], cy)
            if (hi - lo) / sp > 10.0:
                continue
            mid = (lo + hi) / 2
            top, bot = mid - 6.4 * sp, mid + 6.4 * sp
            if any(l[0] != h["lines"][0] and any(top - 0.5 * sp <= y <= bot + 0.5 * sp for y in l) for l in staves[h["page"]]):
                continue
            bw, bh = (b[2] - b[0]) / sp, (b[3] - b[1]) / sp
            if not (0.8 <= bw <= 2.2 and 0.6 <= bh <= 1.5) or h["ink_count"] < 1:
                continue
            g = (np.array(page_image(plate, h["page"]).convert("L")) if _G.get("k") != (plate, h["page"]) else _G["g"])
            _G.update(k=(plate, h["page"]), g=g)
            if (g[int(b[1]):int(b[3]), int(b[0]):int(b[2])] < 128).mean() < 0.5:
                continue
            if h["key"] in EXCL:
                continue
            h = dict(h, plate=plate, kind=kind)
            if plate == "litolff" and h["ledger"] is None:
                cand["fallback"].append(h)
            elif plate == "litolff" and h["ledger"] != h["geom_round"]:
                cand["ledger_differs"].append(h)
            elif plate == "brahms" and h["ledger"] is not None:
                cand["ledger"].append(h)
        for g, n in groups:
            cand[g].sort(key=lambda h: h["key"])
            print(plate, g, "candidates", len(cand[g]))
            pool = random.Random(2311313).sample(cand[g], len(cand[g]))
            seen = set(c["key"].rsplit("/", 2)[0] for c in chosen)
            took = 0
            for h in pool:
                place = h["key"].rsplit("/", 2)[0]
                if place in seen or took >= n:
                    continue
                seen.add(place); took += 1
                chosen.append(dict(h, group=g))
            globals().setdefault("POOLS", {})[(plate, g)] = pool[n:]
    return chosen


def render(chosen, outdir, keyfile):
    outdir = Path(outdir)
    random.Random(2311313).shuffle(chosen)
    key, tiles = [], []
    for i, h in enumerate(chosen, 1):
        sp = (h["lines"][4] - h["lines"][0]) / 4.0
        b = h["box"]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        k = PX_PER_SP / sp
        half_w = (W / k) / 2
        mid = (min(h["lines"][0], cy) + max(h["lines"][4], cy)) / 2
        top, bot = mid - 6.4 * sp, mid + 6.4 * sp
        x0, y0 = int(cx - half_w), int(top)
        im = page_image(h["plate"], h["page"]).crop((x0, y0, int(cx + half_w), int(bot))).convert("RGB")
        d = ImageDraw.Draw(im)
        d.rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(255, 140, 0), width=2)
        im = im.resize((W, int(im.height * k)))
        t = Image.new("RGB", (W, H), "white")
        t.paste(im, (0, 0))
        ImageDraw.Draw(t).text((8, im.height + 6), "%s clef" % h["kind"], fill=(0, 0, 0))
        assert im.height >= 450 and im.height + 24 <= H, (i, im.height)
        assert im.height > 0, (i, im.height)
        t.save(outdir / ("tile_%02d.png" % i))
        tiles.append(t)
        key.append(dict(tile=i, group=h["group"], plate=h["plate"], glyph=h["key"], page=h["page"], box=[round(v, 1) for v in b], clef=h["kind"],
                        position_read=h["final"], pitch_read=_pitch_from_position(h["final"], h["kind"]),
                        decided_by="ledger count" if h["ledger"] is not None else "geometry extrapolation (ledger read refused)",
                        other_reading_position=h["geom_round"] if h["ledger"] is not None else None,
                        other_reading_pitch=_pitch_from_position(h["geom_round"], h["kind"]) if h["ledger"] is not None else "none (fallback is the only reading)",
                        ledger_lines_owed=owed(h["final"]), our_stroke_count=h["ink_count"]))
    rows = (len(tiles) + 1) // 2
    sheet = Image.new("RGB", (2 * (W + 12) + 12, rows * (H + 12) + 12), (200, 200, 200))
    for i, t in enumerate(tiles):
        sheet.paste(t, (12 + (i % 2) * (W + 12), 12 + (i // 2) * (H + 12)))
    sheet.save(outdir / "sheet.png")
    json.dump(key, open(sys.argv[3], "w"), indent=1)


if __name__ == "__main__":
    ch = main(*sys.argv[1:4])
    render(ch, sys.argv[2], sys.argv[3])
