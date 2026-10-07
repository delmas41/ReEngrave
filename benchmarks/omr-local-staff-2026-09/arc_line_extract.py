"""lane-arc-not-a-line: arc inputs from ONE load_record: every arc_box (full detail), cell_box, staff_lines, staff_spacing,
arc_kind/arc_owner/instrument verdicts.   python3 arc_line_extract.py <record> <out.pkl>"""
import sys, pickle
sys.path.insert(0, '.')
from tools.omr.staged.record_io import load_record
src, dst = sys.argv[1:3]
rec = load_record(src)['record']
sup = {v['supersedes'] for v in rec['verdicts'] if v.get('supersedes')}
obs = [o for o in rec['observations'] if o['quantity'] in ('arc_box', 'cell_box', 'staff_lines', 'staff_spacing')]
vs = [v for v in rec['verdicts'] if v['id'] not in sup and v['quantity'] in ('arc_owner', 'arc_kind', 'instrument')]
print(len(obs), len(vs), flush=True)
pickle.dump({'obs': obs, 'verdicts': vs}, open(dst, 'wb'))
