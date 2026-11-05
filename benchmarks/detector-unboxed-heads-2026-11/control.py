"""CONTROL (CLAUDE rule 7): do the cached raw candidates, served at conf 0.25 / iou 0.7 / class-wise (STAGED's call), reproduce the
detector boxes the 20261103-night record holds?  Compares per cell the multiset of (class, page box) of the cache with the record rows
whose reader is 'detector' (glyph_box).  usage: python3 control.py PAGE"""
import sys, json
sys.path.insert(0, '.'); sys.path.insert(0, 'benchmarks/detector-unboxed-heads-2026-11')
import cachelook as cl
from tools.omr.staged import cell_map
from tools.omr.staged.gather import _system_local

pg = int(sys.argv[1])
(pws, cells), = cell_map.load_prepared(cl.PDF['litolff'], [pg])
names = cl.class_names()
rec = {}
for line in open(cl.R / 'lane-report-slices-20261103-night/litolff/observations.jsonl'):
    if '"quantity": "glyph_box"' not in line or '"subject": "glyph/%d/' % pg not in line:
        continue
    o = json.loads(line)
    if o['reader'] != 'detector':
        continue
    s = o['subject'].split('/')
    rec.setdefault((int(s[2]), int(s[3]), int(s[4])), []).append((o['value'][0], o['detail'].get('bbox_page_px')))
local = _system_local(pws.staves)
tot = bad = missing = same = 0
for c in cells:
    k = local.get(c.staff_index)
    if k is None:
        continue
    key = (k[0], k[1], c.measure_index)
    isz, o = cl.lookup(c, confs=(0.25,))
    if 0.25 not in o:
        missing += 1
        continue
    meta, arr, _ = o[0.25]
    served = cl.serve(c, meta, arr)
    r = rec.get(key, [])
    S = sorted((names[b[0]],) + tuple(round(v) for v in (*cl.to_page(c, b[2], b[3]), *cl.to_page(c, b[4], b[5]))) for b in served)
    Rr = sorted((n,) + tuple(round(v) for v in bb) for n, bb in r if bb)
    tot += 1
    def close(a, b):
        return a[0] == b[0] and all(abs(x - y) <= 1.6 for x, y in zip(a[1:], b[1:]))
    ok = len(S) == len(Rr) and all(close(a, b) for a, b in zip(S, Rr))
    if ok:
        same += 1
    else:
        bad += 1
        if bad <= 5:
            print(key, len(S), len(Rr), [x for x in S if x not in Rr][:3], [x for x in Rr if x not in S][:3])
print('page', pg, 'cells', tot, 'identical (within 1.6 px rounding)', same, 'differ', bad, 'no-entry', missing)
