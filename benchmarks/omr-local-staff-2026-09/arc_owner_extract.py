"""arc_owner inputs from ONE load_record: notehead glyph boxes, arc boxes, staff spacing + lines, the glyph_owner / arc_owner /
instrument verdicts, margin labels.  python3 ext2.py <record> <out.pkl>"""
import sys, pickle
sys.path.insert(0, '.')
from tools.omr.staged.record_io import load_record
src, dst = sys.argv[1:3]
res = load_record(src); rec = res['record']
sup = {v['supersedes'] for v in rec['verdicts'] if v.get('supersedes')}
obs = []
for o in rec['observations']:
    q = o['quantity']
    if q == 'glyph_box':
        if (o.get('detail') or {}).get('category') != 'notehead':
            continue
    elif q not in ('arc_box', 'staff_spacing', 'staff_lines', 'margin_label'):
        continue
    d = dict(o); d['detail'] = {k: v for k, v in (o.get('detail') or {}).items() if k in ('bbox_page_px', 'category', 'frame_note')}
    if q in ('staff_lines', 'margin_label'):
        d['detail'] = o.get('detail') or {}
    obs.append(d)
vs = []
for v in rec['verdicts']:
    if v['id'] in sup: continue
    if v['quantity'] in ('arc_owner', 'glyph_owner', 'instrument', 'arc_kind'):
        vs.append(v)
print(len(obs), len(vs), flush=True)
pickle.dump({'obs': obs, 'verdicts': vs}, open(dst, 'wb'))
