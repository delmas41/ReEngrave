"""Attribute each exported-file change to a switch from the saved-verdict transitions (INFERRED: record rows + reason words + id ranges).
usage: cause.py PLATE BASE.slim TAG.slim OUT.json"""
import re,json,sys,collections
S="/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-reengrave-manager-20261124-12f953/35f75218-68a4-4d67-aae9-7c7cdda49059/scratchpad/bc/"
plate,fa,fb,out=sys.argv[1:5]
NORM=lambda x:re.sub(r'(obs|vrd):\d+','ID',x)
a=json.load(open(S+fa)); b=json.load(open(S+fb))
ch=json.load(open(S+"changes.json"))[plate]
def gl(s):
    try: return int(s.split("/")[-1])
    except: return -1
def idx(V):
    d=collections.defaultdict(dict)
    for v in V:
        v[3]=NORM(v[3]); d[v[0]][v[1]]=v
    return d
A=idx(a["verdicts"]); B=idx(b["verdicts"])
def by(v):
    m=re.search(r'"claim_final": \{[^}]*?"by": "([^"]+)"',v[6]); return m.group(1) if m else ""
# staffs whose clef changed
clefstaffs={s for s in B if "clef" in B[s] and s in A and "clef" in A[s] and A[s]["clef"][3]!=B[s]["clef"][3]}
clefpages={(int(s.split("/")[1]),s.split("/")[2]) for s in clefstaffs}   # (page,system)
def causes_of(s):
    """set of cause labels for subject s from its own transitions"""
    out=set()
    qa=A.get(s,{}); qb=B.get(s,{})
    for q in set(qa)|set(qb):
        va,vb=qa.get(q),qb.get(q)
        sa=None if va is None else (va[2],va[4]); sb=None if vb is None else (vb[2],vb[4])
        if sa==sb:
            if va and vb and q in("pitch",) and va[3]!=vb[3]: out.add("CLEF")   # pitch value changed with same reason: clef/owner path
            continue
        r=vb[4] if vb else ""
        r0=va[4] if va else ""
        if vb and vb[4]=="claimed_by:page_claim" and (not va or va[4]!="claimed_by:page_claim"):
            c=by(vb); out.add({"accidental_ink":"2.336","tremolo":"2.335"}.get(c,"claim?"))
        if r in("eighth_rest_shaped_ink","eighth_rest_shape","rest8th_shape"): out.add("2.334")
        if r in("quarter_rest_shaped_ink","quarter_rest_shape","restQuarter_shape"): out.add("2.339")
        if r=="rest_is_an_accidentals_ink": out.add("2.340")
        if r=="flag_ink_in_beamless_cell": out.add("2.341")
        if q=="accidental_owner" and va is None and gl(s)>=360000: out.add("2.336")
        if q=="accidental" and r in("printed_glyph",) and (not va or va[4]!="printed_glyph"): out.add("2.336")
        if q=="accidental" and r=="carried_in_bar" and (not va or va[4]!="carried_in_bar"): out.add("2.336c")
        if q=="dot_role": out.add("DOT")
        if q=="accidental" and va and vb is None and r0=="from_key_signature": out.add("CLEF")
        if q=="accidental" and va is None and vb and r=="from_key_signature": out.add("CLEF")
    return out
# bar key causes
def barkey(rg):
    m=re.match(r"glyph/(\d+)/(\d+)/(\d+)/(\d+)/",rg or "")
    return tuple(map(int,m.groups())) if m else None
bar_causes=collections.defaultdict(collections.Counter)
subj_cache={}
def cs(s):
    if s not in subj_cache: subj_cache[s]=causes_of(s)
    return subj_cache[s]
# neighbours: every glyph with a transition, keyed by bar
allsub=set(A)|set(B)
for s in allsub:
    if not s.startswith("glyph"): continue
    k=barkey(s)
    for c in cs(s): bar_causes[k][c]+=1
res=collections.defaultdict(collections.Counter); ex=collections.defaultdict(list); per=[]
for c in ch:
    rg=c.get("rg"); kind=c["kind"]; side=c["side"]
    if not rg:
        lab="loose/no-glyph"
    else:
        own=cs(rg)
        # accidental/pitch changes: also the owner(s) of a printed accidental
        if not own and kind in("pitch","accidental","blue"):
            pass
        if own:
            lab="+".join(sorted(own))
        else:
            bc=bar_causes.get(barkey(rg),{})
            lab=("bar:"+"+".join(sorted(bc))) if bc else "none-found"
    res[(kind,side)][lab]+=1
    per.append([kind,side,c.get('page'),lab,rg])
    if len(ex[(kind,side,lab)])<2: ex[(kind,side,lab)].append((c.get("page"),rg))
rows={}
for (k,sd),v in res.items():
    rows["%s|%s"%(k,sd)]=dict(v)
json.dump({"per":per,"plate":plate,"rows":rows,"clefstaffs":sorted(clefstaffs)},open(S+out,"w"),indent=1)
tot=collections.Counter()
for (k,sd),v in sorted(res.items()):
    print("%-14s %-8s %4d  %s"%(k,sd,sum(v.values()),", ".join("%s %d"%(l,n) for l,n in v.most_common(7))))
