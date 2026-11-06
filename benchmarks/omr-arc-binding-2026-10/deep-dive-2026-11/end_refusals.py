"""A tie / bound-slur end that is not a written note: the exporter's own refusal of THAT head (measure only).
python3 end_refusals.py PLATE ARM"""
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ledger as LG
import written as W

plate, arm = sys.argv[1], sys.argv[2]
D = pathlib.Path("scratch/dd")
dump = json.load(open(D / ("%s.%s.arcs.json" % (plate, arm))))
xml = (D / ("%s.%s.musicxml" % (plate, arm))).read_text()
res = LG.build(dump, xml)
wr = W.parse(xml)
ref = collections.defaultdict(list)
for s, r in dump.get("refusals") or ():
    ref[s].append(r)
heads = {h["subject"]: h["box"] for h in dump["heads"]}
mg = {}
c = collections.Counter()
tot = 0
for r in res["rows"]:
    if r.get("lost_rule") not in ("export:tie_not_in_file", "export:slur_bound_not_in_file"):
        continue
    tot += 1
    why = []
    for end, k in zip(("start", "stop"), r["pair"]):
        if k in wr["notes"]:
            continue
        rs = ref.get(k)
        if rs:
            why.append("%s:%s" % (end, "/".join(sorted(set(rs)))))
        else:
            # a twin at the same place that WAS written?
            b = heads.get(k)
            tw = None
            if b:
                cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
                for rg in wr["notes"]:
                    hb = heads.get(rg)
                    if hb and rg != k and abs((hb[0] + hb[2]) / 2 - cx) < 0.6 * (hb[2] - hb[0]) and abs((hb[1] + hb[3]) / 2 - cy) < 0.6 * (hb[3] - hb[1]) \
                            and rg.split("/")[1] == k.split("/")[1]:
                        tw = rg
                        break
            why.append("%s:%s" % (end, "no_refusal_logged_twin_written" if tw else "no_refusal_logged"))
    c[(r["lost_rule"][7:], tuple(sorted(w.split(":", 1)[1] for w in why)))] += 1
print("pairs lost to an end not in the file:", tot)
for k, v in c.most_common(20):
    print(v, k)
