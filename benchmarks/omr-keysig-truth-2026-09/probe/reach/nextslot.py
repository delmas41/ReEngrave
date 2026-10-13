import sys,collections,statistics; sys.path.insert(0,'.')
from tools.omr.staged.record_io import load_record
from tools.omr.staged.adjudicators import key_slots as KS
for path in sys.argv[1:]:
    doc=load_record(path); rec=doc['record'] if 'record' in doc else doc
    cells=collections.defaultdict(list); space={}
    for o in rec['observations']:
        if o['quantity']=='glyph_box' and o['subject'].startswith('glyph/'):
            p=o['subject'].split('/')
            if p[4]=='0': cells['/'.join(p[1:4])].append(o)
        if o['quantity']=='cell_staff_space' and o['subject'].endswith('/0'): space[o['subject'][5:-2]]=o['value']
    print(path)
    pitches=[]
    rows=[]
    for st,rs in sorted(cells.items()):
        sp=space.get(st)
        if not sp: continue
        sp=float(sp)
        boxes=[KS.KeyBox(o['id'],o['value'][0],*map(float,o['value'][1:])) for o in rs if len(o['value'])==5]
        w=KS.key_slot_window(boxes,sp)
        if not w or w.slots<2: continue
        keys=sorted([b for b in boxes if b.row_id in w.members],key=lambda b:b.x)
        cen=[keys[0].x]
        for b in keys[1:]:
            if b.x-cen[-1]>0.5*sp: cen.append(b.x)
        d=[(b-a)/sp for a,b in zip(cen,cen[1:])]
        pitches+=d
        pitch=statistics.median(d)
        last=cen[-1]
        for b in boxes:
            if b.cls.startswith(('rest','notehead')) and not KS.stands_in_the_window(w,b) and b.cx>w.lo:
                dx=(b.x-(last+pitch*sp))/sp
                if -1<dx<3: rows.append((round(dx,2),st,b.cls,round(pitch,2)))
    print(' pitches sp: n',len(pitches),'min/med/max',round(min(pitches),2),round(statistics.median(pitches),2),round(max(pitches),2))
    for r in sorted(rows)[:15]: print('  ',r)
