import sys,json; sys.path.insert(0,'.')
from tools.omr.staged import readout as RO
run=RO.load_run(sys.argv[1])
for key in sys.argv[2:]:
    g=run.glyphs.get(key); print('==',key,g and (g.cls,g.box_canon,g.box_page))
    for s,k,r in run.rows_at(key):
        v=r.get('value')
        extra=''
        if k=='verdict': extra=json.dumps(r.get('detail') or {},default=str)[:700] if r['quantity'] in('duration','head_stem','stem_value') else ''
        print(' ',s,k,r.get('quantity'),r.get('outcome') or '',r.get('reason') or '',str(v)[:150],extra)
