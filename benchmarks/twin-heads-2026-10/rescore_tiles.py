"""2.212 rework: re-score Sean's 12 tiles (out/print/2.212/answers.json) BY PLACE against the ON arm's gathered record.

    python3 benchmarks/twin-heads-2026-10/rescore_tiles.py WORK_DIR      (lane_report --out DIR/work)

Per pitch tile: right position = 8 - staff_step_from_bottom_line (position 0 = top line). The head's twin group (members named on
the position row's `twin_head`, flag ON) gives each box's position: far-head ledger read if filed, else the box centre. Verdict:
`unchanged` (not a twin / boxes agree: ON == OFF, so Sean's OFF answer stands), `guessed-right-in-candidates` (not wrong, reported
apart), `guessed-right-NOT-in-candidates`.
"""
import json, pathlib, sys
work = pathlib.Path(sys.argv[1]); ans = json.load(open('out/print/2.212/answers.json'))
recs = {}
def rec(plate):
    if plate not in recs:
        p = work / ("%s.on.gathered.record.json" % plate)
        recs[plate] = None
        if p.exists():
            d = json.load(open(p))['record']; idx = {}
            for o in d['observations']: idx.setdefault((o['quantity'], o['subject']), []).append(o)
            recs[plate] = idx
    return recs[plate]
def eff(idx, m):
    f = [o for o in idx.get(('far_head_ledger_position', m), []) if o.get('value') is not None]
    if f: return float(f[-1]['value'])
    p = idx.get(('notehead_staff_position', m)); return float(p[-1]['value']) if p else None
for t in ans['tiles']:
    if t['kind'] != 'pitch' or 'staff_step_from_bottom_line' not in t: continue
    idx = rec(t['plate']); right = 8 - t['staff_step_from_bottom_line']
    if idx is None: print(t['tile'], t['rg'], 'page not in the ON run'); continue
    r = idx.get(('notehead_staff_position', t['rg']))
    tw = (r[-1].get('detail') or {}).get('twin_head') if r else None
    own = eff(idx, t['rg']) if r else None
    if not tw:
        print(t['tile'], t['rg'], 'not a twin: unchanged; OFF right=%s own pos %.2f right pos %d' % (t['off_right'], own if own is not None else -99, right)); continue
    ps = {m: eff(idx, m) for m in tw['members']}; cand = sorted({int(round(v)) for v in ps.values() if v is not None})
    guessed = len(cand) >= 2
    status = ('GUESSED, right in candidates' if right in cand else 'GUESSED, right NOT in candidates') if guessed else ('boxes agree: unchanged (right=%s)' % (int(round(own)) == right))
    print(t['tile'], t['rg'], 'twin', {m.split('/', 2)[-1]: round(v, 2) for m, v in ps.items()}, 'cand', cand, 'right', right, '->', status, '| Sean OFF right=%s old-ON right=%s' % (t['off_right'], t['on_right']))
