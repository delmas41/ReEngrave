"""ROADMAP 2.312 r2 -- 12 blind tiles of far heads whose WRITTEN pitch changed OFF vs ON (lane_report work dir), for Sean.

    PYTHONPATH=. python3 benchmarks/ledger-count-2026-11/r2_tiles.py WORK_DIR OUT_DIR KEY.json [SEED=2312] [N=12]

Pairs each arm's written notes by glyph key (`symbols.json` hosts); a change = the same glyph written with another pitch, or written in
one arm only (a far head newly read / no longer read). Drawn at random (seed) across both plates. Each tile: the page as scanned
(grey), ONE staff with all five lines and every ledger line out to the head, zoomed so the head is about 40 px tall, one thin box
sized to the head's own ink, the clef in force in small text under the tile; nothing else drawn; every tile the same size (>= 450 px
tall); two per row on `sheet.png`; the key (which arm wrote what) goes to KEY.json outside the folder.
"""
import json
import random
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from tools.omr.annotate import ledger_grid as lg
from tools.omr.preprocessing import render_page
from tools.omr.staged import lane_report as LR
from tools.omr.staged.judged import iter_array

TW, TH, CAP = 520, 520, 22
CLEF_NAME = {("G", "2"): "treble clef", ("F", "4"): "bass clef", ("C", "3"): "alto clef", ("C", "4"): "tenor clef"}


def clefs_by_part_measure(xml):
    """(part id, measure number) -> clef name in force at the measure's start (the last clef met so far, staff 1)."""
    out = {}
    root = ET.fromstring(xml)
    for part in root.iter("part"):
        cur = None
        for m in part.iter("measure"):
            first = cur
            for c in m.iter("clef"):
                cur = CLEF_NAME.get((c.findtext("sign"), c.findtext("line")), "%s clef on line %s" % (c.findtext("sign"), c.findtext("line")))
                if first is None:
                    first = cur
            out[(part.get("id"), m.get("number"))] = first or cur
    return out


def staff_lines(work, plate):
    rp = Path(work) / ("%s.on.gathered.record.json" % plate)
    out = {}
    for o in iter_array(rp, "observations"):
        if o.get("quantity") == "staff_lines":
            out[o["subject"]] = [float(v) for v in o["value"]]
    return out


def changes(work, plate):
    w = Path(work)
    off = json.loads((w / ("%s.off.symbols.json" % plate)).read_text())["hosts"]
    on = json.loads((w / ("%s.on.symbols.json" % plate)).read_text())["hosts"]
    a = {h["rg"]: h for h in off if h.get("rg") and h["kind"] == "note"}
    b = {h["rg"]: h for h in on if h.get("rg") and h["kind"] == "note"}
    out = []
    for rg in sorted(set(a) | set(b)):
        x, y = a.get(rg), b.get(rg)
        if x is not None and y is not None and x["pitch"] == y["pitch"]:
            continue
        h = y or x
        out.append(dict(plate=plate, rg=rg, page=h["page"], box=h["box"], part=h["part"], measure=h["measure"],
                        off=None if x is None else dict(pitch=x["pitch"], blue=x["blue"]),
                        on=None if y is None else dict(pitch=y["pitch"], blue=y["blue"])))
    return out


def tile(gray, box, ys, clef):
    sp = (ys[-1] - ys[0]) / 4.0
    ink = lg.head_ink_box(gray, box, sp)
    hb = ink["box"] if ink.get("ok") else tuple(box)
    k = 40.0 / max(1.0, hb[3] - hb[1])
    top = min(ys[0], hb[1]) - 1.2 * sp
    bot = max(ys[-1], hb[3]) + 1.2 * sp
    k = min(k, (TH - CAP) / (bot - top))
    cx, cy = (hb[0] + hb[2]) / 2.0, (top + bot) / 2.0
    hw, hh = TW / (2 * k), (TH - CAP) / (2 * k)
    X0, Y0 = int(round(cx - hw)), int(round(cy - hh))
    X1, Y1 = int(round(cx + hw)), int(round(cy + hh))
    H, W = gray.shape
    pad = np.full((Y1 - Y0, X1 - X0), 255, np.uint8)
    sx0, sy0, sx1, sy1 = max(0, X0), max(0, Y0), min(W, X1), min(H, Y1)
    pad[sy0 - Y0:sy1 - Y0, sx0 - X0:sx1 - X0] = gray[sy0:sy1, sx0:sx1]
    im = Image.fromarray(pad).resize((TW, TH - CAP), Image.LANCZOS).convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle([(hb[0] - X0) * k - 2, (hb[1] - Y0) * k - 2, (hb[2] - X0) * k + 2, (hb[3] - Y0) * k + 2], outline=(255, 140, 0), width=1)
    t = Image.new("RGB", (TW, TH), "white")
    t.paste(im, (0, 0))
    ImageDraw.Draw(t).text((6, TH - CAP + 5), clef or "clef not known", fill=(60, 60, 60))
    return t, k


def main(work, outdir, keyp, seed=2312, n=12):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    pool = []
    for plate in ("litolff", "brahms"):
        if (Path(work) / ("%s.on.symbols.json" % plate)).exists():
            pool += changes(work, plate)
    print("changed far-head notes:", len(pool), {p: sum(1 for c in pool if c["plate"] == p) for p in ("litolff", "brahms")})
    pick = random.Random(seed).sample(pool, min(n, len(pool)))
    pages, lines, clefs, key, tiles = {}, {}, {}, [], []
    for i, c in enumerate(pick, 1):
        plate = c["plate"]
        if plate not in lines:
            lines[plate] = staff_lines(work, plate)
            clefs[plate] = clefs_by_part_measure((Path(work) / ("%s.on.musicxml" % plate)).read_text())
        if (plate, c["page"]) not in pages:
            pages[(plate, c["page"])] = cv2.cvtColor(render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), c["page"], dpi=600).rgb,
                                                     cv2.COLOR_RGB2GRAY)
        st = "staff/" + "/".join(c["rg"].split("/")[1:4])
        clef = clefs[plate].get((c["part"], str(c["measure"])))
        t, k = tile(pages[(plate, c["page"])], c["box"], lines[plate][st], clef)
        t.save(outdir / ("tile_%02d.png" % i))
        tiles.append(t)
        key.append(dict(tile=i, clef=clef, zoom=round(k, 2), **c))
    rows = (len(tiles) + 1) // 2
    sheet = Image.new("RGB", (2 * TW + 30, rows * (TH + 30) + 10), "white")
    d = ImageDraw.Draw(sheet)
    for j, t in enumerate(tiles):
        x, y = 10 + (j % 2) * (TW + 10), 10 + (j // 2) * (TH + 30)
        sheet.paste(t, (x, y + 18))
        d.text((x, y + 2), "%d" % (j + 1), fill=(0, 0, 0))
    sheet.save(outdir / "sheet.png")
    json.dump(dict(set=str(outdir), seed=seed, question="what note is in the box? (line or space, counted from the staff)",
                   drawn_from="far heads whose written pitch changed, OMR_LEDGER_COUNT_TO_INK off vs on", tiles=key),
              open(keyp, "w"), indent=1, default=str)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], *(int(a) for a in sys.argv[4:6]))
