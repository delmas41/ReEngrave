import sys,collections; sys.path.insert(0,'.')
from tools.omr.staged.record_io import load_record
from tools.omr.staged.adjudicators import key_slots as KS
doc=load_record(sys.argv[1]); rec=doc['record'] if 'record' in doc else doc
cells=collections.defaultdict(list); space={}
for o in rec['observations']:
    if o['quantity']=='glyph_box' and o['subject'].startswith('glyph/'):
        p=o['subject'].split('/')
        if p[4]=='0': cells['/'.join(p[1:4])].append((p[5],o))
    if o['quantity']=='cell_staff_space' and o['subject'].endswith('/0'): space[o['subject'][5:-2]]=o['value']
for st,rows in sorted(cells.items()):
    sp=space.get(st)
    if not sp: continue
    boxes=[KS.KeyBox(o['id'],o['value'][0],*map(float,o['value'][1:])) for _,o in rows if len(o['value'])==5]
    w=KS.key_slot_window(boxes,float(sp))
    if not w: continue
    for b in boxes:
        if KS.stands_in_the_window(w,b):
            print(st,b.cls,[round(v) for v in (b.x,b.y,b.w,b.h)],'window',[round(w.lo),round(w.hi)],'slots',w.slots,
                  'keys',[(x.cls,round(x.x)) for x in boxes if KS._shape(x.cls)])
