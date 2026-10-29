import json, collections, sys
SP = sys.argv[1]
W = '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/2-202-beams-cause-1f79a5/out/lane-report/2.202f/work'
def det(cls): return 'H' if any(t in cls for t in ('Half','Whole')) else 'F'
def slit(g):
    iw = (g['notehead_ink'][-1]['d'] or {}).get('interior_white') or {}
    if not iw.get('rows_read'): return 'U', None
    s = float(iw.get('rows_share') or 0)
    return ('H' if s >= .18 else 'F' if s <= .06 else 'U'), s
def win(g):
    d = g['notehead_ink'][-1]['d'] or {}
    cs = []
    for k in ('ink_raw','ink_net','ink_off_line'):
        w = ((d.get(k) or {}).get('windows') or {}); c, r = w.get('center'), w.get('ring')
        if c is None or r is None: continue
        if c <= .75 and r - c >= .1: return 'H', c
        cs.append(c)
    if cs and min(cs) >= .9: return 'F', min(cs)
    return 'U', (min(cs) if cs else None)
def load(plate):
    d = json.load(open(f'{SP}/{plate}.json'))
    sym = json.load(open(f'{W}/{plate}.on.symbols.json'))
    return d, sym
def head_blob(gs, g, strokes):
    cellsub = gs.rsplit('/',1)[0]
    ids = (g.get('glyph_strokes') or [{}])[-1].get('v') or []
    bl = []
    for i in ids:
        s = strokes.get(cellsub + '/' + str(375000 + i))
        if s: bl.append(s)
    return bl
def space(gs, cells):
    p = gs.split('/'); return cells.get('cell/' + '/'.join(p[1:5]))
