import json,sys,collections,re
S="/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-reengrave-manager-20261124-12f953/35f75218-68a4-4d67-aae9-7c7cdda49059/scratchpad/bc/"
a=json.load(open(S+sys.argv[1])); b=json.load(open(S+sys.argv[2]))
def idx(V):
    d={}
    for v in V: d[(v[0],v[1])]=v
    return d
A=idx(a["verdicts"]); B=idx(b["verdicts"])
def by(v):
    m=re.search(r'"claim_final": \{[^}]*?"by": "([^"]+)"',v[6])
    return m.group(1) if m else None
c=collections.Counter(); ex={}
g=collections.Counter()
for k,v in B.items():
    if v[4]!="claimed_by:page_claim": continue
    va=A.get(k)
    ra="ABSENT" if va is None else va[4]
    if ra==v[4]:
        # same reason; did claimant change?
        if by(va)!=by(v): g[(k[1],by(va),by(v))]+=1
        continue
    key=(k[1],ra,by(v)); c[key]+=1; ex.setdefault(key,[]).append(k[0])
print("NEW page_claim refusals (quantity, base reason, claimant):")
for key,n in c.most_common(): print(n,key,ex[key][:2])
print("same reason, claimant changed:",g.most_common(10))
# all claimants in tag vs base for page_claim
ca=collections.Counter(by(v) for v in A.values() if v[4]=="claimed_by:page_claim"); cb=collections.Counter(by(v) for v in B.values() if v[4]=="claimed_by:page_claim")
print("claimants base",ca.most_common()); print("claimants tag",cb.most_common())
