"""2.201: the type reader (`accidental_family.family_row`) on Sean's answered tiles, off the same cells det_cut.py reads. Per tile: Sean's answer, the
detector's class type, the strokes' type, whether the box grew. usage: eval_family.py OUT.json [PLATE:PAGE ...]"""
import json, sys, os
sys.path.insert(0, "."); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collections import defaultdict, Counter
from tools.omr.staged import pipeline, gather as G, stroke_map as SM, one_ink as OI, accidental_family as AF
from tools.omr.staged import weight_routing as WR
from tools.omr.yolo_detector import YoloDetector
import truth_tiles as TT, cause_cut as CC
from det_cut import is_acc


def head_blocked(res, dets):
    blocked = set()
    for d in dets:
        if d.category == "notehead":
            for i, sh in SM.strokes_in_box(res, (d.x_canonical, d.y_canonical, d.x_canonical + d.width_canonical, d.y_canonical + d.height_canonical)):
                if sh >= SM.COVER_SHARE_MIN:
                    blocked.add(i)
    return blocked


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
        c = best[1]
        grid = G._cell_grid(c); sp = grid[1] * 2.0
        dets = det.detect(c, conf_threshold=0.25, natural_candidates=True)
        dets = OI.merge(dets) if dets else []
        res = SM.map_strokes(c.image_no_staff, sp, list(c.staff_line_ys_canonical), c.binary)
        up, cb = c.upscale_factor, c.bbox_page_px
        hb = ((bx0 - cb[0]) * up, (by0 - cb[1]) * up, (bx1 - cb[0]) * up, (by1 - cb[1]) * up)
        blocked = head_blocked(res, dets)
        cand = []
        for gi, d in enumerate(dets):
            if not is_acc(d.smufl_name) or getattr(d, "one_ink_absorbed_by", None) is not None:
                continue
            x0, y0, x1, y1 = d.x_canonical, d.y_canonical, d.x_canonical + d.width_canonical, d.y_canonical + d.height_canonical
            if t["set"] == "2.203":
                ix = max(0, min(x1, hb[2]) - max(x0, hb[0])); iy = max(0, min(y1, hb[3]) - max(y0, hb[1]))
                score = ix * iy / max(1e-9, (x1 - x0) * (y1 - y0) + (hb[2] - hb[0]) * (hb[3] - hb[1]) - ix * iy)
                if score < 0.2:
                    continue
            else:
                gap = hb[0] - x1
                if gap < -0.5 * sp or gap > 3.0 * sp or y1 < hb[1] - 1.5 * sp or y0 > hb[3] + 1.5 * sp:
                    continue
                score = -abs(gap)
            box = (x0, y0, x1, y1)
            shares = SM.strokes_in_box(res, box)
            own_blocked = blocked - {i for i, sh in shares if sh >= 0.5 and False}
            fam = AF.family_row(d.smufl_name, box, res.strokes, shares, sp, blocked=sorted(own_blocked),
                                rivals=[r[0] for r in (getattr(d, "one_ink_rivals", None) or ())])
            cand.append((score, dict(gi=gi, cls=d.smufl_name, conf=round(float(d.confidence), 3), fam=fam, det_box=[x0, y0, x1, y1])))
        cand.sort(key=lambda r: -r[0])
        out.append(dict(set=t["set"], tile=t["tile"], plate=plate, page=page, sean=t["sean"], sp=sp, staff=c.staff_index, measure=c.measure_index,
                        acc=cand[0][1] if cand else None, n_acc=len(cand)))
    return out


if __name__ == "__main__":
    tiles = TT.load()
    by = defaultdict(list)
    for t in tiles:
        by[(t["plate"], t["page"])].append(t)
    dets, res = {}, []
    for (plate, page), ts in sorted(by.items()):
        if plate not in dets:
            wp, _r, _d = WR.resolve_staged_weights(CC.PDF[plate], [page], weights="auto", route_weights=True, no_weight_routing=False)
            dets[plate] = YoloDetector(wp)
        res += analyse(plate, page, ts, dets[plate])
        json.dump(res, open(sys.argv[1], "w"), default=float)
    print("tiles", len(res))
    for r in res:
        a = r["acc"]
        if not a:
            print(r["set"], r["tile"], r["sean"], "NO BOX"); continue
        f = a["fam"]
        print("%-6s %-3s %-2s p%-2s sean=%-8s det=%-8s strokes=%-8s %s grown=%s margin=%s" % (
            r["set"], r["tile"], r["plate"][0], r["page"], r["sean"], f["detector_type"], f["type"], f["why"], f["grown"], f["margin"]))
