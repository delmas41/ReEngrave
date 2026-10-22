"""ROADMAP 2.179 -- tally MY labels (labels/DOC.txt) per cause, one count per distinct bar (a bar written to two parts counts once)."""
import collections
import json
import sys

doc, census = sys.argv[1], sys.argv[2]
bars = [e["bar"] for e in json.load(open(census))]
seen, main, anyc = set(), collections.Counter(), collections.Counter()
n = 0
for line in open("benchmarks/omr-unseen-symbols-2026-10/probe/labels/%s.txt" % doc):
    if line.startswith("#") or "|" not in line:
        continue
    i, codes, _note = [x.strip() for x in line.split("|", 2)]
    b = bars[int(i)]
    if b in seen:
        continue
    seen.add(b)
    n += 1
    cs = codes.split()
    main[cs[0][0] if cs[0][0] in "abcde" else cs[0]] += 1
    for c in set(x[0] if x[0] in "abcde" else x for x in cs):
        anyc[c] += 1
print(doc, "distinct red bars labelled", n, "of", len(set(bars)))
print("main cause:", dict(sorted(main.items())))
print("any cause :", dict(sorted(anyc.items())))
