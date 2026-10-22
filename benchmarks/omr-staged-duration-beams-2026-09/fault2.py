"""What ONE bar reads, per staff, event by event -- the shape of the error.

⚠️ It is how Fault 2 was settled without a crop: bar 211 came out
`quarter + 8th-rest` four times over, which is four EIGHTHS whose FLAG was
never read, and the truth encoding the page was rendered from says exactly
that (100 eighths, 80 eighth rests).

    python3 .../fault2.py <staged.json> 1/5 6   # page/cell, staves to print
"""
import json, sys
from collections import Counter
rec=json.load(open(sys.argv[1]))['record']
dur={v['subject']:v for v in rec['verdicts'] if v['quantity']=='duration'}
events={v['subject']:v for v in rec['verdicts'] if v['quantity']=='event'}
gbox={o['subject']:o for o in rec['observations'] if o['quantity']=='glyph_box'}
rests={o['subject']:o['value'] for o in rec['observations'] if o['quantity']=='rest'}
def beats(v):
    if v is None: return None
    if v['outcome']=='decided': return (v.get('value') or {}).get('beats')
    c=v.get('candidates') or []
    return (c[0].get('value') or {}).get('beats') if c else None
CELL=sys.argv[2]  # e.g. 1/5
pg,ce=CELL.split('/')
tot=Counter()
for key,ev in events.items():
    _,p,sy,st,c=key.split('/')
    if p!=pg or c!=ce or ev['outcome']!='decided': continue
    gl=lambda i: f"glyph/{p}/{sy}/{st}/{c}/{i}"
    evs=(ev.get('value') or {}).get('events') or []
    parts=[]
    s=0.0
    for e in evs:
        gs=e.get('glyphs') or []
        bs=[beats(dur.get(gl(i))) for i in gs]
        bs=[b for b in bs if b]
        b=Counter(bs).most_common(1)[0][0] if bs else None
        if b: s+=b
        kinds=[rests.get(gl(i)) or (gbox.get(gl(i),{}).get('value') or ['?'])[0] for i in gs]
        parts.append(f"{b}:{'+'.join(str(k)[:14] for k in kinds)}")
    tot[round(s,3)]+=1
    if len(sys.argv)>3 and int(sys.argv[3])>0:
        print(f"staff {st:>2}  sum={s:5.2f}  " + "  ".join(parts))
        sys.argv[3]=str(int(sys.argv[3])-1)
print('cell',CELL,'sums:',tot.most_common())
