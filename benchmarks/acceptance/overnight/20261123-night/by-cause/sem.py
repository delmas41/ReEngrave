import re as _re
NORM=lambda x:_re.sub(r'(obs|vrd):\d+','ID',x)
import json,sys,collections,re
S="/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-reengrave-manager-20261124-12f953/35f75218-68a4-4d67-aae9-7c7cdda49059/scratchpad/bc/"
a=json.load(open(S+sys.argv[1])); b=json.load(open(S+sys.argv[2]))
N=int(sys.argv[3]) if len(sys.argv)>3 else 60
VALQ={"duration","pitch","accidental","arc_kind","dot_role","tie_pair","clef","key_signature","stem_value"}
def idx(V):
    d={}
    for v in V: v[3]=NORM(v[3]); d[(v[0],v[1])]=v
    return d
A=idx(a["verdicts"]); B=idx(b["verdicts"])
def by(v):
    m=re.search(r'"claim_final": \{[^}]*?"by": "([^"]+)"',v[6]); return m.group(1) if m else ""
def st(v): return "ABSENT" if v is None else v[2]+"/"+v[4]+("[%s]"%by(v) if by(v) else "")
c=collections.Counter(); ex={}; pg={}
for k in set(A)|set(B):
    va,vb=A.get(k),B.get(k)
    sa,sb=st(va),st(vb)
    if sa==sb:
        if k[1] in VALQ and va and vb and va[3]!=vb[3] and k[1]!="stem_value":
            key=(k[1],sa,"VALUE CHANGED")
        else: continue
    else: key=(k[1],sa,sb)
    c[key]+=1; ex.setdefault(key,[]).append(k[0])
tot=sum(c.values()); print("semantic transitions",tot,"distinct",len(c))
for key,n in c.most_common(N):
    pages=collections.Counter(s.split("/")[1] for s in ex[key] if s.startswith("glyph"))
    print(n,key,"| pages",dict(pages.most_common(4)),ex[key][0])
