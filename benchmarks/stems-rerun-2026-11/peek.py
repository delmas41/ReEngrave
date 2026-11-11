import json, sys
B = [json.loads(l) for l in open(sys.argv[1])]
nar = [r for r in B if r["kept"] and r["fate"] in ("duration_narrowed", "duration_abstained")]
print(len(nar))
for r in nar[:int(sys.argv[2]) if len(sys.argv) > 2 else 8]:
    print(r["n_stem"], r["duration"][:2], r["cands"], r["d"], r["bfs"] and {k: r["bfs"][k] for k in list(r["bfs"])[:6]})
