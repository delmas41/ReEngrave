import sys,collections; sys.path.insert(0,'.')
from tools.omr.staged.record_io import load_record
from tools.omr.staged.adjudicators import key_slots as KS
doc=load_record(sys.argv[1]); rec=doc['record'] if 'record' in doc else doc
cells=collections.defaultdict(list); space={}
for o in rec['observations']:
    if o['quantity']=='glyph_box' and o['subject'].startswith('glyph/'):
        p=o['subject'].split('/')
        if p[4]=='0': cells['/'.join(p[1:4])].append(o)
    if o['quantity']=='cell_staff_space' and o['subject'].endswith('/0'): space[o['subject'][5:-2]]=o['value']
kept=collections.Counter(); ex=[]
for st,rows in sorted(cells.items()):
    sp=space.get(st)
    if not sp: continue
    boxes=[KS.KeyBox(o['id'],o['value'][0],*map(float,o['value'][1:])) for o in rows if len(o['value'])==5]
    w=KS.key_slot_window(boxes,float(sp))
    for b in boxes:
        if KS.is_music_class(b.cls) and b.cls.startswith(('rest','notehead')):
            if w is None: kept[(b.cls[:8],'no window')]+=1
            elif not KS.stands_in_the_window(w,b):
                kept[(b.cls[:8],'window, outside it')]+=1
                if b.cls.startswith('rest') and b.x<w.hi+2.5*float(sp): ex.append((st,b.cls,round((b.cx-w.hi)/float(sp),2),'sp past the window'))
print(dict(kept)); print(ex[:12])
