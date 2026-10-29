import json, sys, pathlib, collections
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/plan-ink-map-step6')
from tools.omr.staged.judged import iter_array
W = pathlib.Path('/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/2-202-beams-cause-1f79a5/out/lane-report/2.202f/work')
plate = sys.argv[1]; out = pathlib.Path(sys.argv[2])
KEEP = {'glyph_box','cell_staff_space','notehead_ink','glyph_strokes','notehead_recentre','stacked_head_fit','head_oval','head_line_cut','stem'}
glyph = collections.defaultdict(dict); cells = {}; blobs = {}; stems = collections.defaultdict(list)
for o in iter_array(W / f'{plate}.on.gathered.record.json', 'observations'):
    q = o.get('quantity'); s = o.get('subject')
    if q == 'stroke':
        if o['value'] in ('blob','vertical','horizontal','curve'):
            d = o['detail']; blobs[s] = {'k': o['value'], 'box': d.get('stroke_box'), 'fill': d.get('fill'), 'hole': d.get('hole_share'), 'touch': d.get('touches'), 'comp': d.get('component'), 'th': d.get('thickness_spaces'), 'len': d.get('length_spaces')}
        continue
    if q not in KEEP: continue
    if q == 'cell_staff_space': cells[s] = o['value']; continue
    if q == 'glyph_box':
        if not str(o['value'][0]).startswith('notehead'): continue
        glyph[s]['box'] = o['value']; glyph[s]['page_box'] = o['detail'].get('bbox_page_px'); glyph[s]['reader'] = o.get('reader'); continue
    if q == 'stem': continue
    glyph[s].setdefault(q, []).append({'v': o.get('value'), 'd': o.get('detail')})
heads = {s: g for s, g in glyph.items() if 'box' in g}
# verdicts from the mini record
ver = collections.defaultdict(dict)
for v in iter_array(W / f'{plate}.on.mini-record.json', 'verdicts'):
    s = v.get('subject')
    if s not in heads: continue
    q = v.get('quantity')
    if q in ('duration', 'notehead_is_not_a_notehead'):
        d = v.get('detail') or {}
        ver[s][q] = {'o': v.get('outcome'), 'v': v.get('value'), 'r': v.get('reason'),
                     'hio': d.get('head_is_open'), 'hff': d.get('head_fill_first'), 'cands': v.get('candidates')}
json.dump({'heads': heads, 'cells': cells, 'strokes': blobs, 'ver': ver}, open(out, 'w'))
print(plate, len(heads), len(blobs), len(ver))
