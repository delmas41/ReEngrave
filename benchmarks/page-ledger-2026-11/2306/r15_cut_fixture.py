"""2.306 r15: cut a real-page fixture for `page_stems.read` from a page-stem dump (the reader's exact inputs, pickled during a real gather by the
lane's wrapper, `r15 gather_dump.py` in the lane report). Keeps every head, vertical, crosser and stroke within a window around the named heads; a
stroke's contacts are kept only inside the window. Usage: r15_cut_fixture.py DUMP.pkl OUT.json NAME hid[:expect] ..."""
import sys, json, pickle

D = pickle.load(open(sys.argv[1], 'rb'))
out_p, name = sys.argv[2], sys.argv[3]
want = [a.split(':') for a in sys.argv[4:]]
hb = {h['id']: h for h in D['heads']}
boxes = [hb[int(w[0])]['box'] for w in want]
sp = float(hb[int(want[0][0])]['sp'])
X0, Y0 = min(b[0] for b in boxes) - 6 * sp, min(b[1] for b in boxes) - 10 * sp
X1, Y1 = max(b[2] for b in boxes) + 6 * sp, max(b[3] for b in boxes) + 10 * sp
inw = lambda b: b[2] >= X0 and b[0] <= X1 and b[3] >= Y0 and b[1] <= Y1
heads = [dict(id=h['id'], members=h['members'], box=list(h['box']), sp=h['sp'], ink=bool(h.get('ink')), strokes=list(h.get('strokes') or ()))
         for h in D['heads'] if inw(h['box'])]
verts = [dict(ord=int(v['ord']), box=list(v['box']), sp=v['sp']) for v in D['verticals'] if inw(v['box'])]
cross = [dict(ord=int(c['ord']), box=list(c['box']), kind=c['kind']) for c in D['crossers'] if inw(c['box'])]
keep = {int(o) for o, s in D['strokes'].items() if inw(s['box'])}
strokes = {str(o): dict(box=list(D['strokes'][o]['box']), kind=D['strokes'][o]['kind'],
                        touches=[[int(j), float(c)] for j, c in D['strokes'][o].get('touches') or () if int(j) in keep]) for o in sorted(keep)}
held = {str(o): w for o, w in D['held'].items() if int(o) in keep or any(int(o) == v['ord'] for v in verts)}
json.dump(dict(name=name, page=D['page'], window=[X0, Y0, X1, Y1], heads=heads, verticals=verts, crossers=cross, strokes=strokes, held=held,
               expect={w[0]: (w[1] if len(w) > 1 else None) for w in want}), open(out_p, 'w'))
print(out_p, len(heads), 'heads', len(verts), 'verticals', len(strokes), 'strokes')
