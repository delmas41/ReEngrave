import json, glob, os
from collections import Counter
ROOT="/Users/seanjohnson/Desktop/ReEngrave"
files=sorted(glob.glob(f"{ROOT}/benchmarks/omr-additive-vs-gated-2026-09/out/contests/*.contests.json"))
diff=Counter(); diff_cat=Counter()
for f in files:
    d=json.load(open(f))
    for pg in d.get("pages",[]):
        for c in pg.get("contests",[]):
            if c.get("class_i")!=c.get("class_j"):
                diff_cat[c["category"]]+=1
                a,b=sorted([c["class_i"],c["class_j"]])
                diff[(a,b)]+=1
print("different-class contests by category:", dict(diff_cat))
for k,v in diff.most_common(15): print("  ",k,v)
print()
# reach of the three ownership decisions across both families
for fam,pat in (("scan",f"{ROOT}/benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json"),
                ("engraved",f"{ROOT}/benchmarks/omr-orchestral-e2e/fixtures/*.omr.json")):
    dup=clip=unl=det=nh=0
    for f in sorted(glob.glob(pat)):
        d=json.load(open(f))
        dup+=d.get("n_cross_staff_duplicates_removed",0)
        clip+=d.get("n_clipped_notehead_fragments_dropped",0)
        unl+=d.get("n_unladdered_noteheads_dropped",0)
        det+=d.get("n_detections_total",0); nh+=d.get("n_noteheads_total",0)
    print(f"{fam}: detections_kept={det} noteheads_kept={nh}")
    print(f"   cross-staff duplicates removed = {dup}  ({dup/max(det,1):.1%} of kept detections)")
    print(f"   clipped notehead fragments     = {clip} ({clip/max(nh,1):.2%} of kept noteheads)")
    print(f"   unladdered noteheads dropped   = {unl} ({unl/max(nh,1):.2%} of kept noteheads)")
