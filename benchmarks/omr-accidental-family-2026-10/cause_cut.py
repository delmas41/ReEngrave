"""2.201 CAUSE: how often does an accidental box cut off its mark's ink? Re-runs the stroke map (no gather) on the pages of Sean's answered
tiles and reports, per tile, the strokes the box covers / partly covers, and how far the full strokes run past the box.
usage: python3 cause_cut.py OUT.json [PLATE:PAGE ...]   (default: every page in the tile list)"""
import json, sys, os
sys.path.insert(0, ".")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from collections import defaultdict
from tools.omr.staged import pipeline, gather as G, stroke_map as SM
import truth_tiles as TT
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}


def analyse(plate, page, tiles):
    pws, cells = pipeline.prepare_pages(PDF[plate], [page], dpi=600)[0]
    out = []
    for t in tiles:
        bx0, by0, bx1, by1 = t["box"]
        best = None
        for c in cells:
            cb = c.bbox_page_px
            ix = max(0, min(bx1, cb[2]) - max(bx0, cb[0])); iy = max(0, min(by1, cb[3]) - max(by0, cb[1]))
            fr = ix * iy / max(1e-9, (bx1 - bx0) * (by1 - by0))
            if best is None or fr > best[0]:
                best = (fr, c)
        fr, c = best
        grid = G._cell_grid(c)
        res = SM.map_strokes(c.image_no_staff, grid[1] * 2, list(c.staff_line_ys_canonical), c.binary)
        up, cb = c.upscale_factor, c.bbox_page_px
        cbox = ((bx0 - cb[0]) * up, (by0 - cb[1]) * up, (bx1 - cb[0]) * up, (by1 - cb[1]) * up)
        sp = grid[1] * 2.0
        got = SM.strokes_in_box(res, cbox)
        rows = []
        for i, sh in got:
            s = res.strokes[i]
            x, y, w, h = s.box
            rows.append(dict(i=i, share=sh, kind=s.kind, box=[x, y, x + w, y + h], len_sp=s.length_sp, thick_sp=s.thickness_sp, angle=s.angle_deg,
                             ends=s.end_steps, hole=s.hole_share, area=s.area_sp2, touches=s.touches,
                             above_sp=round(max(0, cbox[1] - y) / sp, 2), below_sp=round(max(0, y + h - cbox[3]) / sp, 2),
                             left_sp=round(max(0, cbox[0] - x) / sp, 2), right_sp=round(max(0, x + w - cbox[2]) / sp, 2)))
        out.append(dict(set=t["set"], tile=t["tile"], plate=plate, page=page, sean=t["sean"], cell_frac=round(fr, 2), measure=c.measure_index,
                        staff=c.staff_index, sp=sp, cbox=[round(v, 1) for v in cbox], strokes=rows, n_cell_strokes=len(res.strokes)))
    return out


if __name__ == "__main__":
    tiles = TT.load()
    by = defaultdict(list)
    for t in tiles:
        by[(t["plate"], t["page"])].append(t)
    want = set(tuple([a.split(":")[0], int(a.split(":")[1])]) for a in sys.argv[2:]) if len(sys.argv) > 2 else None
    res = []
    for (plate, page), ts in sorted(by.items()):
        if want and (plate, page) not in want:
            continue
        print("page", plate, page, len(ts), flush=True)
        res += analyse(plate, page, ts)
        json.dump(res, open(sys.argv[1], "w"))
