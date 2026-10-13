import sys,collections,json; sys.path.insert(0,'.'); sys.path.insert(0,'out/probe')
from load import load
rec=load(sys.argv[1])
truth={}
for r in json.load(open('benchmarks/omr-keysig-truth-2026-09/readers-read.json')):
    truth[f"{r['page']}/{r['system']}/{r['staff']}"]=r['truth_fifths']
pieces={}; cbox={}; sp_page={}; csp={}; boxes=collections.defaultdict(list)
for o in rec['observations']:
    q=o['quantity']; s=o['subject']
    if q=='cell_ink_pieces' and s.endswith('/0') and s.startswith('cell/'): pieces[s[5:-2]]=o['detail']['pieces']
    elif q=='cell_box' and s.endswith('/0'): cbox[s[5:-2]]=o['value']
    elif q=='staff_spacing': sp_page[s[6:]]=o['value']
    elif q=='cell_staff_space' and s.endswith('/0'): csp[s[5:-2]]=o['value']
    elif q=='glyph_box' and s.split('/')[4]=='0': boxes['/'.join(s.split('/')[1:4])].append(o)
lines={}
for o in rec['observations']:
    if o['quantity']=='staff_lines' and o['subject'].startswith('staff/'): lines[o['subject'][6:]]=o['value']
res=collections.defaultdict(list)
for st,t in truth.items():
    if t!=-3 or st not in pieces: continue
    bl=boxes[st]; ks=[b for b in bl if b['value'][0]=='keyFlat']
    if len(ks)<1: continue
    scale=csp[st]/sp_page[st]; sp=sp_page[st]; x0c=cbox[st][0]; y0c=cbox[st][1]
    # page x of keys
    kx=sorted(x0c+b['value'][1]/scale for b in ks)
    first=kx[0]
    clef=[b for b in bl if b['value'][0].startswith('clef')]
    top=lines[st][0]; bot=lines[st][4]
    pitch=1.16*sp
    for k in range(1,6):
        xk=first+(k-1)*pitch
        sel=[p for p in pieces[st] if xk-0.1*sp<= (p[0]+p[2])/2 < xk+1.05*sp and p[3]>top-1.6*sp and p[1]<bot+1.6*sp and (p[3]-p[1])<4.5*sp]
        # exclude pieces that are staff-wide
        area=sum(p[4] for p in sel)
        ext=(max(p[3] for p in sel)-min(p[1] for p in sel))/sp if sel else 0
        res[k].append((round(area,2),round(ext,2)))
for k in range(1,6):
    a=sorted(x[0] for x in res[k]); e=sorted(x[1] for x in res[k])
    print('slot',k,'n',len(a),'area min/med/max',a[0],a[len(a)//2],a[-1],'ext min/med/max',e[0],e[len(e)//2],e[-1])
print()
for thr in (0.4,0.6,0.8):
    for k in range(1,6):
        pres=sum(1 for a,e in res[k] if a>=thr and e>=1.5)
        print('thr',thr,'slot',k,'present',pres,'of',len(res[k]))
