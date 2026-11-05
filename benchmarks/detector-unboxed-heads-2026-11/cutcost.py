"""Cost side of a lower head confidence cut, on cells whose cache holds the 0.03 floor (rescue-pass cells: a BIASED subset). Per cut c: head-class boxes
after class-wise NMS 0.7 not in the 0.25 set; how many sit on a notehead box already in the record (any reader), how many cover a confirmed
unboxed head of cases.json, how many are 'other' (unverified). Nothing is judged for precision here. usage: python3 cutcost.py DOC PAGE..."""
import json
import sys
sys.path.insert(0, 'benchmarks/detector-unboxed-heads-2026-11')
import pagecache as pc
import cachelook as cl
import recordrows as rr
from analyze import iou, page_box

doc = sys.argv[1]
names = cl.class_names()
cases = [c for c in json.load(open('benchmarks/detector-unboxed-heads-2026-11/cases.json')) if c['doc'] == doc]
out = {}
for pg in map(int, sys.argv[2:]):
    pws, cells, local = pc.page(doc, pg)
    boxes = [o['detail']['bbox_page_px'] for o in rr.rows(doc, pg) if 'notehead' in o['value'][0] and o['detail'].get('bbox_page_px')]
    tot = {}
    ncell = 0
    for c in cells:
        isz, ent = cl.lookup(c, confs=(0.25, 0.03))
        if 0.25 not in ent or 0.03 not in ent:
            continue
        ncell += 1
        base = {tuple(round(v) for v in b[2:]) for b in cl.serve(c, *ent[0.25][:2], 0.25) if 'notehead' in names[b[0]]}
        for cut in (0.20, 0.15, 0.10, 0.05):
            new = [b for b in cl.serve(c, *ent[0.03][:2], cut) if 'notehead' in names[b[0]] and tuple(round(v) for v in b[2:]) not in base]
            t = tot.setdefault(cut, dict(new=0, on_record_head=0, on_confirmed_case=0, other=0))
            for b in new:
                bx = (*cl.to_page(c, b[2], b[3]), *cl.to_page(c, b[4], b[5]))
                t['new'] += 1
                if any(iou(bx, r) >= 0.3 for r in boxes):
                    t['on_record_head'] += 1
                elif any(cs['page'] == pg and bx[0] <= cs['cx'] <= bx[2] and bx[1] <= cs['cy'] <= bx[3] for cs in cases):
                    t['on_confirmed_case'] += 1
                else:
                    t['other'] += 1
    out[pg] = dict(cells_with_floor_entry=ncell, by_cut=tot)
    print(doc, pg, out[pg], flush=True)
json.dump(out, open('benchmarks/detector-unboxed-heads-2026-11/cutcost-%s.json' % doc, 'w'), indent=1)
