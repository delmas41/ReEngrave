"""Page-bound slurs whose two heads are both written but whose slur is not: what the file has at those two heads (measure only).
python3 bound_slur_lost.py PLATE ARM"""
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
starts = collections.defaultdict(list)
stops = collections.defaultdict(list)
for a, b in wr["slurs"]:
    starts[a].append(b)
    stops[b].append(a)
for a, b in wr["ties"]:
    starts[a].append(("tie", b))
c = collections.Counter()
for r in res["rows"]:
    lr = r.get("lost_rule") or ""
    if "both_heads_in_file_arc_not_marked" not in lr:
        continue
    a, b = r["pair"]
    sa, sb = starts.get(a, []), stops.get(b, [])
    ba = stops.get(a, [])
    key = ("slur_starts_at_a:%s" % bool(sa), "slur_stops_at_b:%s" % bool(sb), "slur_stops_at_a:%s" % bool(ba),
           "same_measure_group:%s" % (wr["notes"][a]["grp"] == wr["notes"][b]["grp"]), lr.split(":")[0].split("export:")[-1])
    c[key] += 1
for k, v in c.most_common():
    print(v, k)
