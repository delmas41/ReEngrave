# ROADMAP 2.107 probe. Dump a small record's glyph boxes + staff lines to $LETTER_LOOK_SCRATCH/TAG.glyphs.json.
# python3 2.107_dump_glyphs.py RECORD.json TAG
import os
import sys, json
sys.path.insert(0, '.')
from tools.omr.staged import readout as R
S = os.environ.get('LETTER_LOOK_SCRATCH', '.')
path, tag = sys.argv[1], sys.argv[2]
run = R.load_run(path)
rows = []
for k, g in run.glyphs.items():
    st, notes = R.adjudicate_status(run, g)
    rows.append(dict(key=k, page=g.page, system=g.system, staff=g.staff, cell=g.cell, idx=g.index,
                     cls=g.cls, fam=g.family, score=g.score, box=g.box_page, status=st, notes=notes))
geo = {}
try:
    for p in run.pages():
        geo[p] = {str(s): v for s, v in R._system_geometry(run, p).items()}
except Exception as e:
    print('geo fail', e)
json.dump(dict(rows=rows, geo=geo, dpi=run.dpi, pdf=run.pdf), open(f'{S}/{tag}.glyphs.json', 'w'), default=str)
print(len(rows), run.dpi, run.pdf, run.pages())
