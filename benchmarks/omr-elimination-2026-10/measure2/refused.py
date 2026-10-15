"""2.120 round 2 (c): every REFUSED notehead box of Brahms p0 -- what Sean's truth says sits under it, and what the table says it can be.
Under = truth boxes whose centre lies inside the detector box, or that contain the detector box's centre (any IoU)."""
import json, sys, pickle, collections
sys.path.insert(0, ".")
import table as T1
REPO = "/Users/seanjohnson/Desktop/ReEngrave"
P = pickle.load(open("measure2/brahms_p0.pkl", "rb")); R = json.load(open("measure2/detector_rows.json"))
page = json.load(open(REPO + "/data/hand-truth/pages/imslp317803/0.json"))
OV = {k: v for k, v in json.load(open("truth_overrides.json")).items() if not k.startswith("_")}
T = [dict(id=b["id"], cls=OV[b["id"]]["now"] if b["id"] in OV else b["cls"], rect=b["rect"]) for b in page["boxes"]]
box = {x["key"]: x["box_page"] for x in P["rows"]}
def under(b):
    cx, cy = (b[0]+b[2])/2, (b[1]+b[3])/2; out = []
    for t in T:
        r = t["rect"]; tx, ty = (r[0]+r[2])/2, (r[1]+r[3])/2
        if (b[0] <= tx <= b[2] and b[1] <= ty <= b[3]) or (r[0] <= cx <= r[2] and r[1] <= cy <= r[3]): out.append(t)
    return out
cnt = collections.Counter()
for r in R:
    if r["status"] != "refused" or not r["refusal"][0].startswith("notehead"): continue
    u = under(box[r["key"]]); syms = sorted(set(T1.symbol_of(t["cls"]) or t["cls"] for t in u))
    isdet_head = any(T1.symbol_of(t["cls"]) in ("head_black", "head_half", "head_whole") for t in u)
    d = r["d"]
    print("%-15s %-28s det %-22s w%.2f h%.2f fill%.2f %-4s %-7s | truth under: %-28s | table set: %s" % (
        r["key"][6:], r["refusal"][1], r["cls"], d["w"], d["h"], d["fill"], d["loc"], d["zone"], ",".join(syms) or "NOTHING", "/".join(r["all2"])))
    cnt[(r["refusal"][1], "head under" if isdet_head else ("other: " + ",".join(syms)) if syms else "nothing under")] += 1
print()
for k, v in sorted(cnt.items()): print(k, v)

# summary: refused notehead boxes with NO head under them (a refusal that is right), by what the table can say
print("\nSUMMARY -- refused notehead boxes whose truth-under has NO head (the refusal is right):")
tot = collections.Counter(); ex = collections.defaultdict(list)
for r in R:
    if r["status"] != "refused" or not r["refusal"][0].startswith("notehead"): continue
    u = under(box[r["key"]]); syms = set(T1.symbol_of(t["cls"]) for t in u) - {None}
    if syms & {"head_black", "head_half", "head_whole"}: continue
    st = set(r["all2"]); why = r["refusal"][1]
    if not st: k = "EMPTY set (nothing in the table fits: a piece or unlabeled ink)"
    elif syms & st and len(st) <= 3: k = "true symbol in a set of <=3"
    elif syms & st: k = "true symbol in a set of >3"
    elif not syms: k = "no truth under, non-empty set"
    else: k = "true symbol NOT in set"
    tot[k] += 1; ex[k].append((why, "/".join(sorted(syms)) or "-", len(st)))
for k, v in tot.most_common(): print(" %-62s %d  %s" % (k, v, collections.Counter(ex[k]).most_common(6)))
