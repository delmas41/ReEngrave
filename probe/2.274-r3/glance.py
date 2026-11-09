import json
import collections

C = json.load(open("census.json"))
print("file OFF/ON", collections.Counter((c["file_off"], c["file_on"]) for c in C))
print("boxes: none", sum(1 for c in C if not c["boxes"]), " cov<0.15", sum(1 for c in C if c["box_cov"] < 0.15), " 0.15-0.8", sum(1 for c in C if 0.15 <= c["box_cov"] < 0.8), " >=0.8", sum(1 for c in C if c["box_cov"] >= 0.8))
print("kept-box cov: <0.15", sum(1 for c in C if c["box_cov_kept"] < 0.15), " 0.15-0.8", sum(1 for c in C if 0.15 <= c["box_cov_kept"] < 0.8), " >=0.8", sum(1 for c in C if c["box_cov_kept"] >= 0.8))
print("curve cov: <0.15", sum(1 for c in C if c["curve_cov"] < 0.15), " 0.15-0.8", sum(1 for c in C if 0.15 <= c["curve_cov"] < 0.8), " >=0.8", sum(1 for c in C if c["curve_cov"] >= 0.8))
print("run cov: none", sum(1 for c in C if not c["runs"]), " <0.8", sum(1 for c in C if c["runs"] and c["run_cov"] < 0.8), " >=0.8", sum(1 for c in C if c["run_cov"] >= 0.8), " union>=0.8", sum(1 for c in C if c["run_union_cov"] >= 0.8))
print("bind entries none", sum(1 for c in C if not c["bind"]))
print("bind status of best entry", collections.Counter(c["bind"][0]["status"] if c["bind"] else None for c in C))
print("heads missing in ON file (either end)", sum(1 for c in C if any(not h.get("written_on", True) for h in c["heads"].values() if h.get("hand_head"))), "no hand head near", sum(1 for c in C if any(not h.get("hand_head") for h in c["heads"].values())))
for c in C[:0]:
    print(c)
