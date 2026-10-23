"""2.201 CAUSE (step 2): for each of Sean's answered tiles, find the accidental-family box the production detector (+2.186 merge, 2.193
candidates) draws in front of the tile's head (2.203 tiles: the box IS the accidental) and report how much of the mark's ink the box covers.
No gather: the detector is run on the tile's own cell. usage: det_cut.py OUT.json"""
import json, sys, os
sys.path.insert(0, "."); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from collections import defaultdict
from tools.omr.staged import pipeline, gather as G, stroke_map as SM, one_ink as OI
from tools.omr.staged import weight_routing as WR
from tools.omr.yolo_detector import YoloDetector
import truth_tiles as TT, cause_cut as CC

ACC = ("accidental", "key")


def is_acc(n):
    n = n.lower()
    return n.startswith("accidental") or n.startswith("key")


def analyse(plate, page, tiles, det):
    pws, cells = pipeline.prepare_pages(CC.PDF[plate], [page], dpi=600)[0]
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
        grid = G._cell_grid(c); sp = grid[1] * 2.0
        dets = det.detect(c, conf_threshold=0.25, natural_candidates=True)
        dets = OI.merge(dets) if dets else []
        res = SM.map_strokes(c.image_no_staff, sp, list(c.staff_line_ys_canonical), c.binary)
        up, cb = c.upscale_factor, c.bbox_page_px
        hb = ((bx0 - cb[0]) * up, (by0 - cb[1]) * up, (bx1 - cb[0]) * up, (by1 - cb[1]) * up)   # the tile's box in the cell frame
        accs = []
        for gi, d in enumerate(dets):
            if not is_acc(d.smufl_name) or getattr(d, "one_ink_absorbed_by", None) is not None:
                continue
            x0, y0, x1, y1 = d.x_canonical, d.y_canonical, d.x_canonical + d.width_canonical, d.y_canonical + d.height_canonical
            if t["set"] == "2.203":
                # the tile box is the accidental: take the box with the best IoU
                ix = max(0, min(x1, hb[2]) - max(x0, hb[0])); iy = max(0, min(y1, hb[3]) - max(y0, hb[1]))
                score = ix * iy / max(1e-9, (x1 - x0) * (y1 - y0) + (hb[2] - hb[0]) * (hb[3] - hb[1]) - ix * iy)
                if score < 0.2:
                    continue
            else:
                # the tile box is the head: an accidental stands left of it, overlapping its height band, within 3 sp
                gap = hb[0] - x1
                if gap < -0.5 * sp or gap > 3.0 * sp or y1 < hb[1] - 1.5 * sp or y0 > hb[3] + 1.5 * sp:
                    continue
                score = -abs(gap)
            got = SM.strokes_in_box(res, (x0, y0, x1, y1))
            st = []
            for i, sh in got:
                s = res.strokes[i]
                bx, by, bw, bh = s.box
                st.append(dict(i=i, share=sh, kind=s.kind, box=[bx, by, bx + bw, by + bh], len_sp=s.length_sp, thick_sp=s.thickness_sp,
                               angle=s.angle_deg, hole=s.hole_share, ends=s.end_steps, area=s.area_sp2, touches=s.touches))
            accs.append(dict(gi=gi, cls=d.smufl_name, conf=round(float(d.confidence), 3), box=[x0, y0, x1, y1], score=score,
                             rivals=[(r[0], r[1]) for r in (getattr(d, "one_ink_rivals", None) or ())],
                             natural_score=getattr(d, "natural_score", None), strokes=st))
        accs.sort(key=lambda a: -a["score"])
        out.append(dict(set=t["set"], tile=t["tile"], plate=plate, page=page, sean=t["sean"], measure=c.measure_index, staff=c.staff_index,
                        sp=sp, head_box=[round(v, 1) for v in hb], accs=accs[:3], n_cell_strokes=len(res.strokes)))
    return out


if __name__ == "__main__":
    tiles = TT.load()
    by = defaultdict(list)
    for t in tiles:
        by[(t["plate"], t["page"])].append(t)
    dets = {}
    res = []
    for (plate, page), ts in sorted(by.items()):
        if plate not in dets:
            wp, _r, _d = WR.resolve_staged_weights(CC.PDF[plate], [page], weights="auto", route_weights=True, no_weight_routing=False)
            dets[plate] = YoloDetector(wp)
        print("page", plate, page, len(ts), flush=True)
        res += analyse(plate, page, ts, dets[plate])
        json.dump(res, open(sys.argv[1], "w"), default=float)
