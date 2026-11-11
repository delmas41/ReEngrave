"""2.280 r3: today's kept-head stem-row counts against the 2.280 11-08 population file (out/2.280/pop_PLATE.json on lane-2.280-stem-diagnosis).
usage: vs1108.py HEADS.jsonl POP.json PAGES   -- same pages, same definition (kept heads, no touching Q.STEM row), copies and rests NOT excluded (the pop file has no fates)."""
import collections
import json
import sys

rows = [json.loads(l) for l in open(sys.argv[1])]
pop = json.load(open(sys.argv[2]))
pages = [int(p) for p in sys.argv[3].split(",")]
for pg in pages:
    a = [r for r in pop if r["page"] == pg]
    b = [r for r in rows if r["page"] == pg and r["kept"]]
    sa = {r["sub"]: r["n_stem"] for r in a}
    sb = {r["sub"]: r["n_stem"] for r in b}
    both = set(sa) & set(sb)
    print("page %d: 11-08 kept %d no-stem %d | today kept %d no-stem %d | same sub ids %d; stem row gained %d lost %d (by sub id; ids shift when the box list shifts)" % (
        pg, len(a), sum(v == 0 for v in sa.values()), len(b), sum(v == 0 for v in sb.values()), len(both),
        sum(1 for s in both if sa[s] == 0 and sb[s] > 0), sum(1 for s in both if sa[s] > 0 and sb[s] == 0)))
