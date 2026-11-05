"""ROADMAP 2.267 -- for each confirmed unboxed dyad head, what does the detector's RAW output hold at the head?  MEASUREMENT ONLY (no detector run).

For every master cell that contains the head's centre (twins: both padded cells), read the cached raw candidates (best class per anchor, pre-NMS)
for the production call (conf 0.25) and the lowest floor the cache holds for that cell image (0.03 from the rescue pass, else the next), and
classify:
  1  no head-class candidate overlaps the head ink at any cached confidence
  2  a head-class candidate overlaps it, all below the 0.25 cut (score, class reported)
  3  a head-class candidate >= 0.25 overlaps it and class-wise NMS (iou 0.7) removed it (suppressor, IoU, same class reported; would agnostic 0.5 /
     class-wise 0.9 keep it?)
  4  a TALL box (>= 1.8 sp) covers both heads (class, size in sp, hollow/black; >= 0.25 or sub-cut)
"Overlaps the head ink" = IoU >= 0.3 with a head-sized box at the ink (+-0.8 sp x +-0.7 sp), or candidate centre within 0.5 sp of the head centre.
usage: python3 analyze.py CASES.json OUT.json
"""
import json
import sys
import numpy as np
sys.path.insert(0, 'benchmarks/detector-unboxed-heads-2026-11')
import pagecache as pc
import cachelook as cl

TALL_SP = 1.8


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def page_box(cell, cand):
    x0, y0 = cl.to_page(cell, cand['x0'], cand['y0'])
    x1, y1 = cl.to_page(cell, cand['x1'], cand['y1'])
    return (x0, y0, x1, y1)


def analyse_cell(case, cell, key, names):
    sp = case['sp']
    cx, cy = case['cx'], case['cy']
    head = (cx - 0.8 * sp, cy - 0.7 * sp, cx + 0.8 * sp, cy + 0.7 * sp)
    isz, ent = cl.lookup(cell)
    res = dict(cell=list(key) if key else None, cell_box=list(cell.bbox_page_px), imgsz=isz, confs_in_cache=sorted(ent))
    if 0.25 not in ent:
        res['note'] = 'NO production (0.25) entry in the cache for this cell image'
        return res
    floor = min(ent)
    res['floor'] = floor

    def overlaps(bx):
        bcx, bcy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        return iou(head, bx) >= 0.3 or ((bcx - cx) ** 2 + (bcy - cy) ** 2) ** 0.5 <= 0.5 * sp

    # control: the cache served at 0.25 / 0.7 / class-wise
    meta25, arr25, _ = ent[0.25]
    served = cl.serve(cell, meta25, arr25, 0.25, 0.7, False)
    sboxes = [(b[0], b[1], (*cl.to_page(cell, b[2], b[3]), *cl.to_page(cell, b[4], b[5]))) for b in served]
    res['served_head_boxes_here'] = [dict(cls=names[c], score=round(s, 3), box=[round(v, 1) for v in bx]) for c, s, bx in sboxes
                                     if 'notehead' in names[c] and (bx[2] > head[0] - 40 and bx[0] < head[2] + 40 and bx[3] > head[1] - 40 and bx[1] < head[3] + 40)]
    res['served_covering_head'] = [h for h in res['served_head_boxes_here'] if overlaps(h['box'])]

    # raw candidates at the lowest floor, then at 0.25
    for conf in sorted(set([floor, 0.25])):
        meta, arr, _ = ent[conf]
        cands = cl.candidates_cell_px(meta, arr, cl.cell_source(cell).shape[:2])
        rows = []
        for c in cands:
            bx = page_box(cell, c)
            if not overlaps(bx):
                continue
            n = names[c['cls']]
            rows.append(dict(cls=n, score=round(c['score'], 3), box=[round(v, 1) for v in bx], iou_head=round(iou(head, bx), 2),
                             h_sp=round((bx[3] - bx[1]) / sp, 2), w_sp=round((bx[2] - bx[0]) / sp, 2), head_class='notehead' in n))
        rows.sort(key=lambda r: -r['score'])
        res['cands_at_%.2f' % conf] = rows
    # tall boxes (any class that is a notehead) that cover BOTH this head and a boxed head of the same column
    meta, arr, _ = ent[floor]
    tall = []
    for c in cl.candidates_cell_px(meta, arr, cl.cell_source(cell).shape[:2]):
        n = names[c['cls']]
        if 'notehead' not in n:
            continue
        bx = page_box(cell, c)
        if (bx[3] - bx[1]) / sp >= TALL_SP and bx[0] <= cx <= bx[2] and bx[1] <= cy <= bx[3]:
            tall.append(dict(cls=n, score=round(c['score'], 3), box=[round(v, 1) for v in bx], h_sp=round((bx[3] - bx[1]) / sp, 2),
                             w_sp=round((bx[2] - bx[0]) / sp, 2), fill='hollow' if ('Half' in n or 'Whole' in n) else 'black'))
    tall.sort(key=lambda r: -r['score'])
    res['tall_boxes_over_head'] = tall

    # NMS: a head-class candidate >= 0.25 overlapping the head that the served set does not contain
    above = [r for r in res['cands_at_0.25'] if r['head_class']]
    sup = []
    if above:
        cands = cl.candidates_cell_px(meta25, arr25, cl.cell_source(cell).shape[:2])
        for r in above:
            bx = tuple(r['box'])
            kept = any(abs(sb[0] - bx[0]) < 1.0 and abs(sb[1] - bx[1]) < 1.0 and abs(sb[2] - bx[2]) < 1.0 and abs(sb[3] - bx[3]) < 1.0 for c_, s_, sb in sboxes)
            if kept:
                continue
            # which kept box suppressed it (class-wise 0.7: same class, higher score, IoU > 0.7)
            best = None
            for c_, s_, sb in sboxes:
                v = iou(bx, sb)
                if best is None or v > best['iou']:
                    best = dict(cls=names[c_], score=round(s_, 3), iou=round(v, 2), same_class=(names[c_] == r['cls']), box=[round(q, 1) for q in sb])
            r2 = dict(r, suppressed_by=best)
            for nm, iou_, ag in (('agnostic_0.5', 0.5, True), ('classwise_0.9', 0.9, False), ('agnostic_0.7', 0.7, True)):
                alt = cl.serve(cell, meta25, arr25, 0.25, iou_, ag)
                r2['kept_by_' + nm] = any(abs(page_box(cell, dict(x0=a[2], y0=a[3], x1=a[4], y1=a[5]))[0] - bx[0]) < 1.0
                                            and abs(page_box(cell, dict(x0=a[2], y0=a[3], x1=a[4], y1=a[5]))[1] - bx[1]) < 1.0 and names[a[0]] == r['cls'] for a in alt)
            sup.append(r2)
    res['above_cut_removed_by_nms'] = sup
    return res


def best_own(cellres):
    """best head-sized (<= 1.7 sp tall) head-class candidate on the head's ink, at the cache's lowest floor"""
    f = cellres['floor']
    own = [r for r in cellres.get('cands_at_%.2f' % f, []) if r['head_class'] and r['h_sp'] <= 1.7 and r['iou_head'] >= 0.3]
    return max(own, key=lambda r: r['score']) if own else None


def classify(cellres):
    """one verdict per cell: '3' NMS removed a >= 0.25 head candidate | '4' a tall >= 0.25 box covers both | '2' a head-sized sub-cut candidate
    on the ink | '2t' only a TALL sub-cut head-class box over it (merged, below the cut) | '1' none | None (no production entry)."""
    if 'note' in cellres:
        return None
    if cellres.get('above_cut_removed_by_nms'):
        return '3'
    tall = cellres.get('tall_boxes_over_head') or []
    if any(t['score'] > 0.25 for t in tall):
        return '4'
    if best_own(cellres):
        return '2'
    if tall:
        return '2t'
    return '1'


def main(cases_file, out_file):
    names = cl.class_names()
    cases = json.load(open(cases_file))
    out = []
    for cs in cases:
        pws, cells, local = pc.page(cs['doc'], cs['page'])
        # head centre: nearest enclosed hole within 0.8 sp of the given point, if any
        import census as cn
        hs, sp = cn.holes(pws)
        near = sorted(hs, key=lambda h: (h['cx'] - cs['cx']) ** 2 + (h['cy'] - cs['cy']) ** 2)
        if near and ((near[0]['cx'] - cs['cx']) ** 2 + (near[0]['cy'] - cs['cy']) ** 2) ** 0.5 <= 0.8 * sp:
            cs = dict(cs, cx=near[0]['cx'], cy=near[0]['cy'])
        cs = dict(cs, sp=sp)
        per = []
        for cell, key in pc.cells_at(cs['doc'], cs['page'], cs['cx'], cs['cy']):
            per.append(analyse_cell(cs, cell, key, names))
        verdicts = [classify(p) for p in per]
        out.append(dict(case=cs, cells=per, verdict_per_cell=verdicts))
        print(cs['id'], cs['doc'], cs['page'], round(cs['cx']), round(cs['cy']), 'cells', len(per), 'verdicts', verdicts, flush=True)
    json.dump(out, open(out_file, 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
