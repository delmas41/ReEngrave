import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import fixtures, root, chdir_root, SCAN, ENGRAVED, CONTESTS  # fail-loud
chdir_root()

import json, glob, os
from collections import Counter, defaultdict
files=sorted(fixtures(CONTESTS, expect_at_least=20))
tot=0; by_tier=Counter(); by_cat_tier=defaultdict(Counter)
parked=0; loser_higher=0; comparable=0; ties=0
absdelta=[]; per_row={}
same_class=Counter()
for f in files:
    d=json.load(open(f)); nm=d.get("row_id") or os.path.basename(f)
    n=0
    for pg in d.get("pages",[]):
        for c in pg.get("contests",[]):
            tot+=1; n+=1
            t=c["decided_by"]; cat=c.get("category")
            by_tier[t]+=1; by_cat_tier[cat][t]+=1
            same_class[c.get("class_i")==c.get("class_j")]+=1
            if t=="distance" and cat=="notehead": parked+=1
            ci,cj=c.get("conf_i"),c.get("conf_j"); ls=c.get("loser_staff")
            if ci is not None and cj is not None and ls is not None:
                lc = ci if ls==c["staff_i"] else cj
                wc = cj if ls==c["staff_i"] else ci
                comparable+=1
                if lc>wc: loser_higher+=1
                elif lc==wc: ties+=1
                absdelta.append(abs(ci-cj))
    per_row[nm]=n
print("files:",len(files),"total contested pairs:", tot)
print("by tier:", dict(by_tier))
print("same class on both sides:", dict(same_class))
print("\ncategory x tier (n, and how many are REVERSIBLE=parked):")
for cat,c in sorted(by_cat_tier.items(), key=lambda kv:-sum(kv[1].values())):
    rev = c["distance"] if cat=="notehead" else 0
    print(f"  {cat:12s} total={sum(c.values()):5d}  {dict(c)}   reversible={rev}")
print(f"\nREVERSIBLE (parked: rank-0 AND notehead) = {parked} = {parked/tot:.1%}")
print(f"IRREVERSIBLE by construction             = {tot-parked} = {(tot-parked)/tot:.1%}")
print(f"\npairs with both confidences: {comparable}")
print(f"  DELETED copy scored HIGHER than the survivor: {loser_higher} ({loser_higher/comparable:.1%}); ties {ties}")
absdelta.sort(); n=len(absdelta); q=lambda p: round(absdelta[int(p*n)],3)
print(f"  |delta conf| p25={q(.25)} median={q(.5)} p75={q(.75)} p95={q(.95)}")
print("\nper row:")
for k,v in sorted(per_row.items()): print(f"   {k:36s} {v}")
