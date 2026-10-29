"""2.229: reasons behind each unread-empty kind and a seeded sample of bars per kind. usage: kindsample.py WORKDIR PLATE N SEED"""
import json, sys, random, collections
work, plate, n, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
D = json.load(open("%s/%s.fates.json" % (work, plate)))
by = collections.defaultdict(list)
for o in D["bars"]: by[o["kind"].split(":")[0] if o["kind"].startswith("other") else o["kind"]].append(o)
random.seed(seed)
for kind, lst in by.items():
    rs = collections.Counter(g[2] for o in lst for g in o["glyphs"])
    cs = collections.Counter(g[1] for o in lst for g in o["glyphs"])
    print(kind, len(lst), "fates", dict(rs.most_common(6)), "classes", dict(cs.most_common(5)))
    print("   sample", [o["key"] for o in random.sample(lst, min(n, len(lst)))])
