import sys,json,collections,ast,re
sys.path.insert(0,'.'); import cmp as C
tags=["bra01","bra3","bra7","bra8","bra10","bra12","bra18","bra21","bra25","lit"]
def written(p):
    for l in open(p):
        if l.strip().startswith('written: {'): return ast.literal_eval(l.split('written: ',1)[1].strip())
def census(p):
    for l in open(p):
        m=re.search(r"'notehead': \{'marks': (\d+), 'detected_more_than_once': (\d+), 'written_once': (\d+)",l)
        if m: return int(m.group(3))
def held(p):
    for l in open(p):
        m=re.search(r'held-out bars \("unread"\): (\d+)',l)
        if m: return int(m.group(1))
rows=[]; groups={}
for t in tags:
    A=C.summary(C.load(f"runs/{t}-off.json")); B=C.summary(C.load(f"runs/{t}-on.json"))
    wa,wb=written(f"runs/{t}-off.log"),written(f"runs/{t}-on.log")
    ties=(wa['tie_links_marked'],wb['tie_links_marked'])
    rows.append((t,wa['notes'],wb['notes'],census(f"runs/{t}-off.log"),census(f"runs/{t}-on.log"),held(f"runs/{t}-off.log"),held(f"runs/{t}-on.log"),ties))
    byg=collections.defaultdict(list)
    for k,v in B.items():
        f=v['fit']
        if f and f[2] and 'hollow_pair' in f[2]: byg[k.rsplit('/',1)[0]].append(k)
    for g,mem in byg.items():
        nm=B[mem[0]]['fit'][2]
        refused_off=sum(1 for k in mem if (A[k]['refused'] or (0,))[0] is True and A[k]['refused'][1]=='stacked_head_duplicate')
        groups[f"{t}|{g}"]=dict(kept=B[mem[0]]['fit'][1]=='hollow_pair',why=nm['hollow_pair'],n=len(mem),ext=nm.get('stem_extension_spaces'),windows=nm.get('windows') or nm.get('best_windows'),refused_off=refused_off,members=mem)
print("tag notes(off,on) written_once(off,on) held(off,on) tie_links(off,on)")
for r in rows: print(r)
json.dump(groups,open('out/hollow_groups.json','w'),indent=0)
k=[g for g,v in groups.items() if v['kept']]
print("kept groups",len(k),"of which Brahms",sum(1 for g in k if g.startswith('bra')),"Litolff",sum(1 for g in k if g.startswith('lit')))
print("kept groups with no OFF stacked_head_duplicate refusal:",[g for g in k if groups[g]['refused_off']==0])
for g in k: print(g,groups[g]['n'],groups[g]['ext'],groups[g]['refused_off'])
print("NOT kept, with a stacked refusal in OFF, both slots near hollow:")
for g,v in groups.items():
    if not v['kept'] and v['refused_off']>0 and v['why']!='no slot pair under the boxes': print(g,v['why'],v['n'],v['ext'],v['windows'])
