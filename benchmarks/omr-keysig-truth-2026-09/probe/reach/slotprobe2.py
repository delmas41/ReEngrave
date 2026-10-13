import sys,collections,json,statistics; sys.path.insert(0,'.'); sys.path.insert(0,'out/probe')
from load import load
rec=load(sys.argv[1])
THR=float(sys.argv[2]) if len(sys.argv)>2 else 0.5
truth={}
for r in json.load(open('benchmarks/omr-keysig-truth-2026-09/readers-read.json')):
    truth[f"{r['page']}/{r['system']}/{r['staff']}"]=r['truth_fifths']
pieces={}; cbox={}; sp_page={}; csp={}; boxes=collections.defaultdict(list); lines={}
for o in rec['observations']:
    q=o['quantity']; s=o['subject']
    if q=='cell_ink_pieces' and s.endswith('/0') and s.startswith('cell/'): pieces[s[5:-2]]=o['detail']['pieces']
    elif q=='cell_box' and s.endswith('/0'): cbox[s[5:-2]]=o['value']
    elif q=='staff_spacing': sp_page[s[6:]]=o['value']
    elif q=='cell_staff_space' and s.endswith('/0'): csp[s[5:-2]]=o['value']
    elif q=='glyph_box' and s.split('/')[4]=='0': boxes['/'.join(s.split('/')[1:4])].append(o)
    elif q=='staff_lines' and s.startswith('staff/'): lines[s[6:]]=o['value']
def present(st,xk,sp):
    top=lines[st][0]; bot=lines[st][4]
    sel=[p for p in pieces[st] if xk-0.1*sp<=(p[0]+p[2])/2<xk+1.05*sp and p[3]>top-1.6*sp and p[1]<bot+1.6*sp and (p[3]-p[1])<4.5*sp]
    area=sum(p[4] for p in sel); ext=(max(p[3] for p in sel)-min(p[1] for p in sel))/sp if sel else 0
    return area>=THR and ext>=1.5
res=collections.Counter(); rows=[]
for st,t in truth.items():
    if st not in pieces: continue
    ks=sorted(b['value'][1] for b in boxes[st] if b['value'][0]=='keyFlat')
    if not ks: res['no flat boxes']+=1; continue
    sp=sp_page[st]; scale=csp[st]/sp; x0c=cbox[st][0]
    # chain from left: slots by 0.5 sp, gap<=2.0
    cen=[ks[0]]
    for x in ks[1:]:
        if x-cen[-1]>0.5*csp[st]:
            if x-cen[-1]>2.0*csp[st]: break
            cen.append(x)
    n=len(cen); pitch=statistics.median([b-a for a,b in zip(cen,cen[1:])])/scale if n>1 else 1.16*sp
    last=x0c+cen[-1]/scale
    ext=0
    while ext<5 and present(st,last+(ext+1)*pitch,sp): ext+=1
    pred=-(n+ext); tr=t
    tag='right' if pred==tr else 'wrong'
    res[(tag, 'n=%d'%n)]+=1
    if tag=='wrong': rows.append((st,'truth',tr,'n',n,'ext',ext,'pred',pred))
for k,v in sorted(res.items(),key=str): print(k,v)
for r in rows: print(r)
