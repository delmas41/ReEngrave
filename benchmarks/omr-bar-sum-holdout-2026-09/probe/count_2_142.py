import json,sys,collections
d=json.load(open(sys.argv[1])); B=d['boxes']; V=d['verdicts']
def ov(a,b):
    iw=min(a[2],b[2])-max(a[0],b[0]); ih=min(a[3],b[3])-max(a[1],b[1])
    if iw<=0 or ih<=0: return 0
    return iw*ih/min((a[2]-a[0])*(a[3]-a[1]),(b[2]-b[0])*(b[3]-b[1]))
cell=lambda s:'/'.join(s.split('/')[:5])
bycell=collections.defaultdict(list)
for s,(c,sc,bb) in B.items(): bycell[cell(s)].append(s)
heads=[s for s,(c,_,_) in B.items() if c.startswith('notehead')]
print('notehead boxes',len(heads))
C=collections.Counter(); ex=collections.defaultdict(list)
for s in heads:
    v=V.get(s,{}); nn=v.get('notehead_is_not_a_notehead'); dur=v.get('duration')
    refused = nn and nn[0]=='decided' and nn[1] is True
    wr = v.get('notehead_is_a_whole_rest'); wrt = wr and wr[0]=='decided' and wr[1] is True
    er = v.get('notehead_is_an_eighth_rest'); ert= er and er[0]=='decided' and er[1] is True
    hasdur = dur and dur[0]=='decided'
    twins=[t for t in bycell[cell(s)] if t!=s and B[t][2] and ov(B[s][2],B[t][2])>=0.5]
    tcls=[B[t][0] for t in twins]
    beamtw=any(c=='beam' for c in tcls); resttw=any(c.startswith('rest') for c in tcls)
    key=[]
    key.append('refused:'+nn[2] if refused else 'NOT_refused')
    if wrt: key.append('wholeRestInk')
    if ert: key.append('eighthRestInk')
    if beamtw: key.append('beamTwin')
    if resttw: key.append('restTwin')
    key.append('dur' if hasdur else 'nodur')
    C[tuple(key)]+=1
    if len(ex[tuple(key)])<4: ex[tuple(key)].append(s)
tot_dur=sum(n for k,n in C.items() if 'dur' in k)
print('with decided duration',tot_dur)
for k,n in sorted(C.items(),key=lambda x:-x[1]):
    if ('beamTwin' in k or 'restTwin' in k or 'wholeRestInk' in k or 'eighthRestInk' in k or (k[0].startswith('refused') and 'dur' in k)): print(n,k,ex[k][:2])
