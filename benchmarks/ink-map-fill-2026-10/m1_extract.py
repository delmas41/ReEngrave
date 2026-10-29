"""2.220 m1: glyph boxes (page px) + head duration verdicts from the 2.202f ON mini-record (main's defaults), target pages only."""
import json, sys, pathlib, collections
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a44a05b0ad517dce3')
from tools.omr.staged.judged import iter_array
W = pathlib.Path('/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/2-202-beams-cause-1f79a5/out/lane-report/2.202f/work')
plate = sys.argv[1]
pages = set(int(p) for p in sys.argv[2].split(','))
out = pathlib.Path(sys.argv[3])
boxes = {}
extra = collections.defaultdict(dict)
KEEP = ('notehead_letter_ink', 'head_oval', 'cell_staff_space', 'notehead_ink')
sp = {}
for o in iter_array(W / f'{plate}.on.mini-record.json', 'observations'):
    s = o.get('subject') or ''
    parts = s.split('/')
    if len(parts) < 2 or not parts[1].isdigit() or int(parts[1]) not in pages:
        continue
    q = o.get('quantity')
    if q == 'glyph_box':
        boxes[s] = {'cls': o['value'][0], 'can': o['value'][1:], 'page': (o.get('detail') or {}).get('bbox_page_px')}
    elif q == 'cell_staff_space':
        sp[s] = o['value']
    elif q in KEEP:
        d = o.get('detail') or {}
        if q == 'notehead_ink':
            d = {'interior_white': d.get('interior_white')}
        extra[s][q] = {'v': o.get('value'), 'd': d}
ver = {}
for v in iter_array(W / f'{plate}.on.mini-record.json', 'verdicts'):
    s = v.get('subject')
    if s not in boxes or v.get('quantity') not in ('duration', 'notehead_is_not_a_notehead'):
        continue
    ver.setdefault(s, {})[v['quantity']] = {'o': v.get('outcome'), 'v': v.get('value'), 'r': v.get('reason')}
json.dump({'boxes': boxes, 'extra': extra, 'sp': sp, 'ver': ver}, open(out, 'w'))
print(plate, len(boxes), len(extra), len(ver))
