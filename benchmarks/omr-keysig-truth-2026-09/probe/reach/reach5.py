import sys,collections; sys.path.insert(0,'.'); sys.path.insert(0,'out/probe')
from load import load
from tools.omr.key_signature_geometry import fit_key_signature, slot_positions
rec=load(sys.argv[1]); FR=float(sys.argv[2]) if len(sys.argv)>2 else 0.5
gb={}
for o in rec['observations']:
    if o['quantity']=='glyph_box' and o['subject'].split('/')[4]=='0' and o['value'][0].startswith(('key','accidental')):
        sj=o['subject'].split('/'); gb[('/'.join(sj[1:4]),o['value'][1])]=o['value']

mk=collections.defaultdict(list); clef={}; lines={}; sp_page={}; cbox={}; csp={}; keyv={}
for o in rec['observations']:
    q=o['quantity']; s=o['subject']
    if q=='keysig_marker': mk[s[6:]].append(o)
    elif q=='staff_lines': lines[s[6:]]=o['value']
    elif q=='staff_spacing': sp_page[s[6:]]=o['value']
    elif q=='cell_box' and s.endswith('/0'): cbox[s[5:-2]]=o['value']
    elif q=='cell_staff_space' and s.endswith('/0'): csp[s[5:-2]]=o['value']
for v in rec['verdicts']:
    if v['quantity']=='clef' and v['outcome']=='decided': clef[v['subject'][6:]]=v['value']
    if v['quantity']=='key_signature' and v['subject'].startswith('staff/'): keyv[v['subject'][6:]]=(v['outcome'],v['value'],v['reason'])
res=collections.Counter(); ex=collections.defaultdict(list)
for st,ms in mk.items():
    c=clef.get(st)
    if c is None or st not in csp or st not in lines: res['noclef/space']+=1; continue
    sp=csp[st]; scale=sp/sp_page[st]; top=(lines[st][0]-cbox[st][1])*scale
    ms=sorted(ms,key=lambda o:o['detail']['x'])
    kinds={o['value'] for o in ms}
    if len(kinds)!=1: res['mixed']+=1; continue
    kind=kinds.pop()
    acc={'keyFlat':'b','keySharp':'#'}.get(kind)
    if acc is None: res['natural']+=1; continue
    slots=[]
    for o in ms:
        if slots and o['detail']['x']-slots[-1][-1]['detail']['x']<=0.5*sp: slots[-1].append(o)
        else: slots.append([o])
    run=[slots[0]]
    for a in slots[1:]:
        if a[0]['detail']['x']-run[-1][-1]['detail']['x']>2.0*sp: break
        run.append(a)
    def yy(o):
        v=gb.get((st,o['detail']['x']))
        return (v[2]+FR*v[4]) if v else o['detail']['y_center']
    pos=[ (yy(max(s,key=lambda o:o['score']))-top)/(sp/2) for s in run]
    fit=fit_key_signature(pos,c,acc)
    n=len(run)
    tag='fit_none' if fit is None else ('ok' if (abs(fit.fifths)==n and not fit.inferred_slots) else 'gap_or_count_differs')
    res[tag]+=1
    if tag!='ok': ex[tag].append((st,c,acc,n,[round(p,1) for p in pos],None if fit is None else (fit.fifths,fit.inferred_slots), keyv.get(st), (slot_positions(c,acc) or [])[:n+1]))
print(res)
for t,l in ex.items():
    print(t)
    for e in l[:25]: print(' ',e)
