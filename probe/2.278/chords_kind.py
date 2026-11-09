import json, sys, collections
G = json.load(open(sys.argv[1]))
c = collections.Counter(); h = collections.Counter()
for g in G:
    t = tuple(sorted({x["duration_type"] for x in g["heads"]}))
    c[t] += 1; h[t] += len(g["heads"])
for k, v in c.most_common(): print(k, v, "groups", h[k], "heads")
