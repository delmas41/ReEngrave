"""ROADMAP 2.206 (read-only): crop look at what the eraser takes. usage: crops.py PLATE PICKS.json OUTDIR
PICKS.json: [[cellkey, [x, y, w, h] or null, label], ...] (cell canonical px). One PNG per pick: four panels side by side --
(1) the cell binary, (2) main's erase: black = kept, light grey = erased inside the line band, RED = erased outside the band (overcut),
BLUE = line-band ink kept although nothing crosses (residue); (3) the 'reach' variant, same colours; (4) the 'band' variant, same colours."""
import json
import os
import sys
import collections

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, ".")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach as R  # noqa: E402
from tools.omr.staged import gather as G, pipeline  # noqa: E402


def paint(binary, er, diag, sp, main_diag):
    h, w = binary.shape
    ink = binary == 0
    rgb = np.full((h, w, 3), 255, np.uint8)
    rgb[ink & (er == 0)] = (0, 0, 0)
    rgb[ink & (er != 0)] = (200, 200, 200)
    rows = np.arange(h)[:, None]
    took = ink & (er != 0)
    for i, d in enumerate(diag):
        m = main_diag[i]["model"]
        if m is None:
            continue
        cen, hh = m
        lo_b, hi_b = cen - hh - R.BAND_PAD_PX, cen + hh + R.BAND_PAD_PX
        near = (rows >= (cen - 0.5 * sp)[None, :]) & (rows <= (cen + 0.5 * sp)[None, :])
        outside = (rows < lo_b[None, :]) | (rows > hi_b[None, :])
        oc = took & near & outside
        oc &= (oc.sum(axis=0) >= R.MIN_OVERCUT_SP * sp)[None, :]
        rgb[oc] = (230, 0, 0)
        kept = d["present"] & ~d["erase_cols"]
        extra = np.maximum(lo_b - d["tops"], 0) + np.maximum(d["bottoms"] - hi_b, 0)
        res_cols = kept & (extra <= R.RESIDUE_EXTRA_SP * sp)
        inband = (rows >= lo_b[None, :]) & (rows <= hi_b[None, :])
        rgb[ink & (er == 0) & inband & res_cols[None, :]] = (0, 90, 255)
    return rgb


def main():
    plate, picks_path, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    picks = json.load(open(picks_path))
    by_page = collections.defaultdict(list)
    for n, p in enumerate(picks):
        by_page[int(p[0].split("/")[0])].append((n, p))
    for pg, items in sorted(by_page.items()):
        pws, cells = pipeline.prepare_pages(R.PDF[plate], [pg], dpi=600)[0]
        loc = G.gather_geometry(G.Log(), pws)
        index = {}
        for c in cells:
            key = loc.get(c.staff_index)
            if key is not None:
                index["%d/%s/%s/%s" % (pg, key[0], key[1], c.measure_index)] = c
        for n, (ck, box, label) in items:
            c = index.get(ck)
            if c is None:
                print("missing", ck)
                continue
            ys = list(c.staff_line_ys_canonical)
            panels, main_diag = [], None
            for v in R.VARIANTS:
                er, diag, sp = R.erase_variant(c.binary, ys, v)
                if v == "main":
                    main_diag = diag
                panels.append(paint(c.binary, er, diag, sp, main_diag))
            h, w = c.binary.shape
            if box:
                x, y, bw, bh = box
                pad = int(0.8 * sp)
                x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(w, x + bw + pad), min(h, y + bh + pad)
            else:
                x0, y0, x1, y1 = 0, 0, w, h
            raw = np.repeat(np.where(c.binary[y0:y1, x0:x1] == 0, 0, 255).astype(np.uint8)[:, :, None], 3, axis=2)
            tiles = [raw] + [p[y0:y1, x0:x1] for p in panels]
            gap = np.full((y1 - y0, 6, 3), (255, 200, 0), np.uint8)
            strip = np.concatenate(sum([[t, gap] for t in tiles], [])[:-1], axis=1)
            im = Image.fromarray(strip)
            if im.width < 900:
                f = 900 / im.width
                im = im.resize((int(im.width * f), int(im.height * f)), Image.NEAREST)
            canvas = Image.new("RGB", (im.width, im.height + 18), "white")
            canvas.paste(im, (0, 18))
            ImageDraw.Draw(canvas).text((4, 3), "%02d %s %s  | raw | main | reach | band" % (n, ck, label), fill=(0, 0, 0))
            canvas.save(os.path.join(outdir, "c%02d.png" % n))
        print("page", pg, "done", flush=True)


if __name__ == "__main__":
    main()
