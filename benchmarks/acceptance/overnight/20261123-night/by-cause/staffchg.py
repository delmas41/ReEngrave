import json,sys,re,collections
S="/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-reengrave-manager-20261124-12f953/35f75218-68a4-4d67-aae9-7c7cdda49059/scratchpad/bc/"
a=json.load(open(S+sys.argv[1])); b=json.load(open(S+sys.argv[2]))
NORM=lambda x:re.sub(r'(obs|vrd):\d+','ID',x)
def idx(V):
    d={}
    for v in V:
        if v[0].split("/")[0] in ("staff","system","page","doc","movement","cell") or v[0].startswith("staff"):
            v[3]=NORM(v[3]); v[6]=NORM(v[6]); d[(v[0],v[1])]=v
    return d
A=idx(a["verdicts"]); B=idx(b["verdicts"])
c=collections.Counter()
for k in sorted(set(A)|set(B)):
    va,vb=A.get(k),B.get(k)
    if k[0].startswith("cell"): continue
    if va and vb and va[3]==vb[3] and va[2]==vb[2] and va[4]==vb[4]: continue
    if k[1] in ("dynamic_anchor","staff_group","measure_partition","onset_column","event","dynamic","direction","empty_bar_whole_rest"):
        c[k[1]]+=1; continue
    print(k, "|", (va[2],va[4],va[3][:70]) if va else None, "->", (vb[2],vb[4],vb[3][:70]) if vb else None)
print(c)
