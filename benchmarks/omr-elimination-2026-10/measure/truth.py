"""2.120 truth-side measurement (a),(b),(d), rebuilt after the wipe. python3 measure/truth.py -> measure/truth.json"""
import json, sys, collections, statistics
sys.path.insert(0, ".")
import table as T, descriptors as D
REPO = "/Users/seanjohnson/Desktop/ReEngrave"
p = json.load(open(REPO + "/data/hand-truth/pages/imslp317803/0.json"))
g = D.page_gray(REPO + "/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 0)
m = D.StaffModel(p)
rows = []
for b in p["boxes"]:
    d = D.describe(b["rect"], g, m); c, tr = T.candidates(d); s = T.symbol_of(b["cls"])
    rows.append(dict(id=b["id"], cls=b["cls"], sym=s, d=d, conv=sorted(c["conv"]), all=sorted(c["all"]),
                     why=tr.get(s, [])))
json.dump(rows, open("measure/truth.json", "w"))
n = len(rows); none = sum(r["sym"] is None for r in rows)
sc = sum(r["sym"] in r["conv"] for r in rows); sa = sum(r["sym"] in r["all"] for r in rows)
print("n", n, "outside table", none, "survive conv", sc, "survive all", sa)
fails = [r for r in rows if r["sym"] not in r["all"]]
byrule = collections.Counter((r["sym"], w[1].split(" ")[0] + " " + w[1].split(" ")[1] if w[1].startswith(("loc","zone")) else w[1].split(" ")[0]) for r in fails for w in r["why"])
print("FAILURES by (symbol, rule):", byrule.most_common())
for r in fails:
    d = r["d"]; print(" ", r["id"], r["cls"], "w%.2f h%.2f fill%.2f %s %s out%.1f edge%s" % (d["w"], d["h"], d["fill"], d["loc"], d["zone"], d["out_sp"], d["edge"]), "|", "; ".join(w[1] for w in r["why"]))
print("\nPER CLASS: n, survive_all, size_all med/p90/max, size_conv med")
pc = collections.defaultdict(list)
for r in rows: pc[r["cls"]].append(r)
for k, v in sorted(pc.items(), key=lambda kv: -len(kv[1])):
    sa_ = [len(r["all"]) for r in v]; scv = [len(r["conv"]) for r in v]
    top = collections.Counter(tuple(r["all"]) for r in v).most_common(1)[0]
    print(" %-22s n%4d surv%4d  all med%4.0f p90%3d max%3d  conv med%3.0f  top:%s x%d" % (k, len(v), sum(r["sym"] in r["all"] for r in v),
          statistics.median(sa_), sorted(sa_)[int(0.9*(len(sa_)-1))], max(sa_), statistics.median(scv), "/".join(top[0]), top[1]))
allsz = [len(r["all"]) for r in rows]; cvsz = [len(r["conv"]) for r in rows]
print("ALL marks: all-set median", statistics.median(allsz), "p90", sorted(allsz)[int(.9*(n-1))], "| conv-set median", statistics.median(cvsz), "| table size", len(T.SYMBOLS))
print("share with all-set <= 3:", sum(x <= 3 for x in allsz), "/", n)
