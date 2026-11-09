"""2.280 probe 12: the 2.167 population, today. Kept heads with no touching stem row, EXCLUDING (as 2.167 did) copies owned by another staff, refused non-notes and whole-rest ink,
by the export's own fate (p8_fates.py, current tree), bucketed by p3's causes. usage: p12_likeforlike.py plate"""
import collections
import json
import sys

plate = sys.argv[1]
B = json.load(open("out/2.280/bucketsfull_%s.json" % plate))
fates = {}
for l in open("out/2.280/fates_%s.jsonl" % plate):
    r = json.loads(l)
    fates[r["sub"]] = r
EXCL = ("owned_by_another_staff", "ink_is_a_whole_rest")
c = collections.Counter()
cf = collections.Counter()
tot = 0
nrest = 0
for s, b in B.items():
    f = fates.get(s)
    fate = f["fate"] if f else "NO_ROW"
    cf[(b["stratum"], fate)] += 1
    if fate.startswith("not_a_notehead") or fate in EXCL:
        continue
    wr = f and f["whole_rest"] and f["whole_rest"][0] == "decided" and f["whole_rest"][2] is True
    if wr:                      # 2.270: a measured whole-rest block is WRITTEN AS A REST now (fate 'written'); it is not a head
        nrest += 1
        continue
    tot += 1
    cz = b["cause"]
    key = "PAIRED" if "PAIRED" in cz else "WIDE" if "WIDE" in cz else "TALL" if "TALL" in cz else "SHORT" if "SHORT" in cz else \
        "EDGE" if "EDGE" in cz else "never a candidate (erased image)" if "never" in cz else "only on original image" if "ORIGINAL" in cz else \
        "contact fails (stem found)" if cz.startswith("ii") else "no vertical ink"
    c[key] += 1
print(plate, "like-for-like population (2.167 exclusions) n=%d" % tot)
for k, v in c.most_common():
    print("  %3d  %4.1f%%  %s" % (v, 100.0 * v / tot, k))
print("  (excluded: %d rest blocks written as rests since 2.270, whole_rest decided True)" % nrest)
print("fates among the no-stem heads:", dict(collections.Counter(f for (_, f) in cf.elements()).most_common(8)))
